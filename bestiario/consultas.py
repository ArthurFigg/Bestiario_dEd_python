"""Camada de consulta: monta e executa SQL a partir de filtros nomeados.

É o único lugar do projeto onde SQL de leitura é escrito. O menu (`main.py`), os
relatórios, a API e o site chamam daqui — nenhum deles monta query própria, porque
o mesmo `SELECT` em dois arquivos diverge na primeira correção que só chega a um.

Devolve **listas de dicionários**, nunca DataFrame: pandas é ferramenta de
apresentação, e devolver DataFrame obrigaria a API a importá-lo só para desmontar
de volta. As chaves seguem os nomes do contrato e do glossário (`desafio`, não
`nivel_desafio`) — a tradução acontece aqui, uma vez.
"""

import sqlite3
from pathlib import Path

from bestiario.calculos import ATRIBUTOS, modificador, saves_proficientes
from bestiario.excecoes import FiltroDesconhecido, ValorDeFiltroInvalido

# --------------------------------------------------------------------------
# Listas brancas
# --------------------------------------------------------------------------

# Filtro → cláusula sobre a tabela `monstros` (alias `m`). Um marcador cada.
_FILTROS_SIMPLES = {
    "tipo": "m.tipo = ?",
    "tamanho": "m.tamanho = ?",
    "alinhamento": "m.alinhamento = ?",
    "desafio_min": "m.nivel_desafio >= ?",
    "desafio_max": "m.nivel_desafio <= ?",
    "nome": "m.nome LIKE ?",
}

# Filtro que mora em tabela filha → subconsulta EXISTS, nunca JOIN: JOIN
# multiplicaria linhas e estragaria contagem e média.
_FILTROS_EXISTS = {
    "ambiente": (
        "SELECT 1 FROM monstro_ambiente x "
        "WHERE x.monstro_nome = m.nome AND x.ambiente = ?"
    ),
    "imune_a": (
        "SELECT 1 FROM monstro_interacao_dano x "
        "WHERE x.monstro_nome = m.nome AND x.tipo_dano = ? "
        "AND x.relacao = 'imunidade'"
    ),
    "resiste_a": (
        "SELECT 1 FROM monstro_interacao_dano x "
        "WHERE x.monstro_nome = m.nome AND x.tipo_dano = ? "
        "AND x.relacao = 'resistencia'"
    ),
    "vulneravel_a": (
        "SELECT 1 FROM monstro_interacao_dano x "
        "WHERE x.monstro_nome = m.nome AND x.tipo_dano = ? "
        "AND x.relacao = 'vulnerabilidade'"
    ),
    "imune_a_condicao": (
        "SELECT 1 FROM monstro_imunidade_condicao x "
        "WHERE x.monstro_nome = m.nome AND x.condicao = ?"
    ),
    "impoe": (
        "SELECT 1 FROM acoes ac JOIN efeitos ef ON ef.acao_id = ac.id "
        "WHERE ac.monstro_nome = m.nome AND ef.condicao = ?"
    ),
    "relacao": (
        "SELECT 1 FROM monstro_interacao_dano x "
        "WHERE x.monstro_nome = m.nome AND x.relacao = ?"
    ),
}

FILTROS = tuple(_FILTROS_SIMPLES) + tuple(_FILTROS_EXISTS)

# Dimensão de `comparacao` → (expressão do valor, JOIN necessário).
# O valor sai sempre como texto: `LinhaDeComparacao.valor` é string no contrato.
_DIMENSOES = {
    "tipo": ("m.tipo", ""),
    "tamanho": ("m.tamanho", ""),
    "alinhamento": ("COALESCE(m.alinhamento, 'sem alinhamento')", ""),
    "desafio": ("CAST(m.nivel_desafio AS TEXT)", ""),
    "ambiente": (
        "dim.ambiente",
        "JOIN monstro_ambiente dim ON dim.monstro_nome = m.nome",
    ),
    "tipo_dano": (
        "dim.tipo_dano",
        "JOIN monstro_interacao_dano dim ON dim.monstro_nome = m.nome",
    ),
    "condicao_imposta": (
        "dim.condicao",
        "JOIN acoes dac ON dac.monstro_nome = m.nome "
        "JOIN efeitos dim ON dim.acao_id = dac.id AND dim.condicao IS NOT NULL",
    ),
}

DIMENSOES = tuple(_DIMENSOES)

# Nomes exatos das chaves devolvidas por `comparacao` e `resumo` — iguais aos do
# contrato. Saem sempre todas, em bloco: a tela mostra o conjunto pronto.
METRICAS = (
    "monstros",
    "media_pontos_vida",
    "media_classe_armadura",
    "media_desafio",
    "media_dano",
    "media_bonus_ataque",
)

# Grão → (ordenações aceitas, ordenação padrão). Valor fora da lista cai no padrão
# em vez de levantar erro: ordenação é preferência de exibição, e ignorá-la ainda
# responde a pergunta certa. Link editado à mão não deve derrubar página.
ORDENACOES = {
    "monstros": (
        (
            "nome",
            "tipo",
            "tamanho",
            "desafio",
            "pontos_vida",
            "classe_armadura",
            "dano_medio",
        ),
        ("nome", "crescente"),
    ),
    "ataques": (
        ("bonus_ataque", "dano_medio"),
        ("bonus_ataque", "decrescente"),
    ),
}

MODOS = ("lista_monstros", "lista_ataques", "comparacao", "resumo")

# Filtro cujo domínio é **fechado e estrutural** — fixado pelo schema e pelo enum do
# contrato, não pelo conteúdo do banco. Validado contra esta tupla, nunca contra o
# vocabulário lido: num banco vazio o vocabulário é vazio, e `relacao=imunidade`
# continua sendo um valor legítimo. Corrigido ao implementar a 7b, que precisava
# do filtro para o relatório de imunidade/resistência rodar contra banco vazio.
_VALORES_FIXOS = {
    "relacao": ("imunidade", "resistencia", "vulnerabilidade"),
}

# Filtro → (tabela, coluna, cláusula extra) para leitura do vocabulário.
_VOCABULARIO = {
    "tipo": ("monstros", "tipo", ""),
    "tamanho": ("monstros", "tamanho", ""),
    "alinhamento": ("monstros", "alinhamento", ""),
    "ambiente": ("monstro_ambiente", "ambiente", ""),
    "imune_a": (
        "monstro_interacao_dano",
        "tipo_dano",
        "WHERE relacao = 'imunidade'",
    ),
    "resiste_a": (
        "monstro_interacao_dano",
        "tipo_dano",
        "WHERE relacao = 'resistencia'",
    ),
    "vulneravel_a": (
        "monstro_interacao_dano",
        "tipo_dano",
        "WHERE relacao = 'vulnerabilidade'",
    ),
    "imune_a_condicao": ("monstro_imunidade_condicao", "condicao", ""),
    "relacao": ("monstro_interacao_dano", "relacao", ""),
}

# Filtros que compartilham **domínio de valores**, e as seis chaves com que o
# contrato os publica. A validação usa o domínio, não o filtro isolado: `radiant`
# é um tipo de dano legítimo mesmo que nenhum monstro seja imune a ele, e
# "ninguém é imune a radiant" é pergunta coerente sem resposta — devolve vazio,
# pelo mesmo motivo que `desafio_min=20, desafio_max=5` devolve vazio. Só valor
# que não existe em domínio nenhum (`fogo`) é engano de quem escreveu, e esse
# continua levantando.
#
# Validar por filtro fazia `/vocabulario` mentir: ele anunciava `radiant` em
# `tipos_dano` e o filtro `imune_a=radiant` respondia 422 — justo no endpoint que
# existe para o consumidor não precisar adivinhar.
DOMINIOS_DE_FILTRO = {
    "tipos": ("tipo",),
    "tamanhos": ("tamanho",),
    "alinhamentos": ("alinhamento",),
    "ambientes": ("ambiente",),
    "tipos_dano": ("imune_a", "resiste_a", "vulneravel_a"),
    "condicoes": ("imune_a_condicao", "impoe"),
}

# Filtro → chave de domínio a que ele pertence. Derivado do mapa acima para a
# validação não precisar percorrê-lo a cada chamada.
_DOMINIO_DO_FILTRO = {
    filtro: dominio
    for dominio, filtros in DOMINIOS_DE_FILTRO.items()
    for filtro in filtros
}

# Presets: nome → parâmetros prontos. Não é código, é parâmetro — cobrem os
# relatórios de `relatorios.py`, que passam a chamá-los na 7b.
PRESETS = {
    "mais_resistentes": {
        "modo": "lista_monstros",
        "ordenar_por": "pontos_vida",
        "sentido": "decrescente",
        "limite": 5,
    },
    "top_ataques": {
        "modo": "lista_ataques",
        "ordenar_por": "bonus_ataque",
        "sentido": "decrescente",
        "limite": 5,
    },
    "por_ambiente": {"modo": "comparacao", "por": "ambiente"},
    "comparacao_tipos": {"modo": "comparacao", "por": "tipo"},
    "letalidade_por_tipo": {"modo": "comparacao", "por": "tipo"},
    "imunidade_a_dano": {
        "modo": "comparacao",
        "por": "tipo_dano",
        "filtros": {"relacao": "imunidade"},
    },
    "resistencia_a_dano": {
        "modo": "comparacao",
        "por": "tipo_dano",
        "filtros": {"relacao": "resistencia"},
    },
    "vulnerabilidade_a_dano": {
        "modo": "comparacao",
        "por": "tipo_dano",
        "filtros": {"relacao": "vulnerabilidade"},
    },
    "condicoes_impostas": {"modo": "comparacao", "por": "condicao_imposta"},
}

# Média dos ataques de um monstro. Subconsulta correlacionada em vez de JOIN pelo
# mesmo motivo dos filtros: JOIN duplicaria a linha do monstro.
_SUB_DANO = (
    "(SELECT ROUND(AVG(a.dano_medio), 2) FROM ataques a "
    "JOIN acoes c ON a.acao_id = c.id WHERE c.monstro_nome = m.nome)"
)
_SUB_BONUS = (
    "(SELECT ROUND(AVG(a.bonus_ataque), 2) FROM ataques a "
    "JOIN acoes c ON a.acao_id = c.id WHERE c.monstro_nome = m.nome)"
)

_SELECT_MONSTROS = f"""
    SELECT m.nome AS nome, m.tipo AS tipo, m.tamanho AS tamanho,
           m.nivel_desafio AS desafio, m.pontos_vida AS pontos_vida,
           m.classe_armadura AS classe_armadura,
           {_SUB_DANO} AS dano_medio
    FROM monstros m
"""

_SELECT_ATAQUES = """
    SELECT m.nome AS monstro, ac.nome_acao AS acao, ac.categoria AS categoria,
           at.nome_ataque AS nome_ataque, at.tipo_ataque AS tipo_ataque,
           at.bonus_ataque AS bonus_ataque, at.alcance AS alcance,
           at.alcance_longo AS alcance_longo, at.dano_dado AS dano_dado,
           at.dano_bonus AS dano_bonus, at.dano_tipo AS dano_tipo,
           at.dano_medio AS dano_medio, at.dano_extra_dado AS dano_extra_dado,
           at.dano_extra_bonus AS dano_extra_bonus,
           at.dano_extra_tipo AS dano_extra_tipo,
           at.dano_extra_medio AS dano_extra_medio
    FROM ataques at
    JOIN acoes ac ON at.acao_id = ac.id
    JOIN monstros m ON ac.monstro_nome = m.nome
"""


# --------------------------------------------------------------------------
# Montagem — pura, sem conexão
# --------------------------------------------------------------------------


def montar_consulta(
    filtros=None,
    modo="lista_monstros",
    por=None,
    ordenar_por=None,
    sentido=None,
    limite=None,
    deslocamento=None,
    combinar="todos",
):
    """Devolve `(sql, parametros)` sem tocar em banco.

    Pura de propósito: dá para testar o SQL montado — inclusive que todo valor
    entra por marcador — sem precisar de fixture de banco.
    """
    if modo not in MODOS:
        raise FiltroDesconhecido(modo, MODOS)

    filtros, combinar = _normalizar(filtros, combinar)

    if modo == "lista_monstros":
        return _montar_lista(
            _SELECT_MONSTROS,
            "monstros",
            filtros,
            combinar,
            ordenar_por,
            sentido,
            limite,
            deslocamento,
        )
    if modo == "lista_ataques":
        return _montar_lista(
            _SELECT_ATAQUES,
            "ataques",
            filtros,
            combinar,
            ordenar_por,
            sentido,
            limite,
            deslocamento,
        )
    return _montar_comparacao(filtros, combinar, por, agrupado=(modo == "comparacao"))


def _normalizar(filtros, combinar):
    """Descarta filtro vazio, valida as chaves e separa o `combinar`."""
    filtros = dict(filtros or {})
    # `combinar` chega junto dos filtros quando vem de query string; aceitar os
    # dois caminhos evita que a API tenha de separá-lo antes de chamar.
    combinar = filtros.pop("combinar", combinar) or "todos"

    limpos = {}
    for chave, valor in filtros.items():
        if valor is None or valor == "":
            continue
        if chave not in _FILTROS_SIMPLES and chave not in _FILTROS_EXISTS:
            raise FiltroDesconhecido(chave, FILTROS)
        limpos[chave] = valor
    return limpos, combinar


def _clausulas(filtros, combinar):
    partes, parametros = [], []
    for chave, valor in filtros.items():
        if chave in _FILTROS_SIMPLES:
            partes.append(_FILTROS_SIMPLES[chave])
            parametros.append(f"%{valor}%" if chave == "nome" else valor)
        else:
            partes.append(f"EXISTS ({_FILTROS_EXISTS[chave]})")
            parametros.append(valor)

    if not partes:
        return "", []
    juncao = " OR " if combinar == "qualquer" else " AND "
    return "WHERE (" + juncao.join(partes) + ")", parametros


def _ordenacao(grao, ordenar_por, sentido):
    aceitas, (padrao_coluna, padrao_sentido) = ORDENACOES[grao]
    if ordenar_por not in aceitas:
        ordenar_por = padrao_coluna
    # O sentido padrão do grão vale sempre que ele não vem, inclusive com coluna
    # válida: `/ataques` não tem parâmetro `sentido` no contrato e ordena sempre
    # decrescente, então `ordenar_por=dano_medio` sozinho não pode virar ASC e
    # devolver os ataques mais fracos primeiro.
    sentido = sentido or padrao_sentido
    direcao = "DESC" if sentido == "decrescente" else "ASC"
    # Coluna vem de lista branca — nunca de entrada livre — então interpolar aqui
    # é seguro. Marcador não funciona para nome de coluna em SQL.
    return f"ORDER BY {ordenar_por} {direcao}"


def _montar_lista(
    select, grao, filtros, combinar, ordenar_por, sentido, limite, deslocamento
):
    where, parametros = _clausulas(filtros, combinar)
    sql = f"{select.strip()}\n    {where}\n    {_ordenacao(grao, ordenar_por, sentido)}"

    # Sem limite, devolve tudo: teto é política de superfície pública, e a aba
    # "Todos os monstros" precisa das 325 numa página.
    if limite is not None:
        sql += "\n    LIMIT ?"
        parametros.append(limite)
    elif deslocamento:
        # SQLite exige LIMIT antes de OFFSET; `-1` é o idioma para "sem teto".
        # Sem isso, deslocamento sem limite seria descartado em silêncio e quem
        # pedisse a página 2 receberia a página 1 sem erro nenhum.
        sql += "\n    LIMIT -1"

    if deslocamento:
        sql += " OFFSET ?"
        parametros.append(deslocamento)
    return sql, parametros


def _montar_comparacao(filtros, combinar, por, agrupado):
    juncao, parametros_juncao = "", []
    projecao_valor = ""

    if agrupado:
        if por not in _DIMENSOES:
            raise FiltroDesconhecido(por, DIMENSOES)
        expressao, juncao = _DIMENSOES[por]
        # Quando a dimensão é tipo_dano, a relação restringe o próprio JOIN e não
        # só o EXISTS: agrupar por tipo de dano misturando as três relações daria
        # uma contagem sem sentido.
        if por == "tipo_dano" and "relacao" in filtros:
            juncao += " AND dim.relacao = ?"
            parametros_juncao.append(filtros["relacao"])
        projecao_valor = f"{expressao} AS valor,"

    where, parametros_where = _clausulas(filtros, combinar)

    # DISTINCT sobre (valor, nome, ...) colapsa a duplicação que o JOIN da dimensão
    # cria — sem isso, monstro de vários ambientes pesaria várias vezes na média.
    interno = f"""
        SELECT DISTINCT {projecao_valor} m.nome AS nome,
               m.pontos_vida AS pontos_vida, m.classe_armadura AS classe_armadura,
               m.nivel_desafio AS nivel_desafio,
               {_SUB_DANO} AS dano_medio, {_SUB_BONUS} AS bonus_medio
        FROM monstros m {juncao}
        {where}
    """

    colunas = (
        "COUNT(*) AS monstros,\n"
        "           ROUND(AVG(pontos_vida), 2) AS media_pontos_vida,\n"
        "           ROUND(AVG(classe_armadura), 2) AS media_classe_armadura,\n"
        "           ROUND(AVG(nivel_desafio), 2) AS media_desafio,\n"
        "           ROUND(AVG(dano_medio), 2) AS media_dano,\n"
        "           ROUND(AVG(bonus_medio), 2) AS media_bonus_ataque"
    )

    if not agrupado:
        return f"SELECT {colunas}\n    FROM ({interno})", (
            parametros_juncao + parametros_where
        )

    sql = (
        f"SELECT valor, {colunas}\n"
        f"    FROM ({interno})\n"
        "    GROUP BY valor\n"
        "    ORDER BY monstros DESC, valor"
    )
    return sql, parametros_juncao + parametros_where


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------


def executar_consulta(conexao, filtros=None, modo="lista_monstros", **opcoes):
    """Executa e devolve lista de dicionários com as chaves do contrato."""
    _validar_valores(conexao, filtros)
    sql, parametros = montar_consulta(filtros, modo, **opcoes)
    return _linhas(conexao.execute(sql, parametros))


def contar(conexao, filtros=None, grao="monstros"):
    """Quantas linhas atendem aos filtros, **ignorando paginação**.

    É a fonte do campo `total` do envelope de paginação do contrato — por isso
    não pode reaproveitar o `LIMIT` da consulta que ela acompanha.
    """
    if grao not in ORDENACOES:
        raise FiltroDesconhecido(grao, tuple(ORDENACOES))
    _validar_valores(conexao, filtros)
    filtros_limpos, combinar = _normalizar(filtros, "todos")
    where, parametros = _clausulas(filtros_limpos, combinar)

    if grao == "monstros":
        origem = "FROM monstros m"
    else:
        origem = (
            "FROM ataques at JOIN acoes ac ON at.acao_id = ac.id "
            "JOIN monstros m ON ac.monstro_nome = m.nome"
        )
    return conexao.execute(f"SELECT COUNT(*) {origem} {where}", parametros).fetchone()[
        0
    ]


def _validar_valores(conexao, filtros):
    """Valor fora do **domínio** levanta erro; fora do filtro específico, não.

    `resiste_a="fogo"` é engano de quem escreveu — devolver vazio esconderia o
    erro. Já `imune_a="radiant"` num banco sem imune a radiant é pergunta coerente
    sem resposta, do mesmo jeito que "de 20 até 5": devolve vazio. É a distinção
    entre valor inexistente e valor sem ocorrência, e é ela que faz
    `/vocabulario` poder ser publicado em seis chaves sem mentir.
    """
    if not filtros:
        return
    lido = None
    for chave, valor in filtros.items():
        if valor is None or valor == "":
            continue
        if chave in _VALORES_FIXOS:
            if valor not in _VALORES_FIXOS[chave]:
                raise ValorDeFiltroInvalido(chave, valor)
            continue
        if chave not in _DOMINIO_DO_FILTRO:
            continue
        if lido is None:
            lido = vocabulario(conexao)
        irmaos = DOMINIOS_DE_FILTRO[_DOMINIO_DO_FILTRO[chave]]
        if not any(valor in lido.get(irmao, {}) for irmao in irmaos):
            raise ValorDeFiltroInvalido(chave, valor)


def _linhas(cursor):
    colunas = [descricao[0] for descricao in cursor.description]
    return [dict(zip(colunas, linha)) for linha in cursor.fetchall()]


# --------------------------------------------------------------------------
# Vocabulário
# --------------------------------------------------------------------------


def vocabulario(conexao):
    """Para cada filtro, os valores distintos com a contagem de monstros de cada um.

    Lido do banco, nunca escrito à mão: vocabulário fixo em código sairia de
    sincronia no próximo re-sync. Esta é a forma canônica — a rota `/vocabulario`
    da API a reduz às seis chaves do contrato e descarta as contagens; a aba
    Relatórios consome a forma rica, que é de onde sai o `dragon (43)` do rótulo.
    """
    resultado = {}
    for filtro, (tabela, coluna, extra) in _VOCABULARIO.items():
        sql = (
            f"SELECT {coluna} AS valor, COUNT(DISTINCT "
            f"{'nome' if tabela == 'monstros' else 'monstro_nome'}) AS total "
            f"FROM {tabela} {extra} "
            f"{'AND' if extra else 'WHERE'} {coluna} IS NOT NULL "
            f"GROUP BY {coluna} ORDER BY total DESC, {coluna}"
        )
        resultado[filtro] = {valor: total for valor, total in conexao.execute(sql)}

    # `impoe` sai de `efeitos`, que não tem monstro_nome — precisa da ponte por acoes.
    resultado["impoe"] = {
        valor: total
        for valor, total in conexao.execute(
            "SELECT ef.condicao AS valor, COUNT(DISTINCT ac.monstro_nome) AS total "
            "FROM efeitos ef JOIN acoes ac ON ef.acao_id = ac.id "
            "WHERE ef.condicao IS NOT NULL "
            "GROUP BY ef.condicao ORDER BY total DESC, ef.condicao"
        )
    }
    return resultado


def vocabulario_por_dominio(conexao):
    """As seis chaves de domínio, cada uma com os valores ordenados, sem contagem.

    É a forma que o contrato publica em `/vocabulario`. Mora aqui, e não na rota,
    porque é o mesmo agrupamento que `_validar_valores` usa — se a API tivesse o
    seu, os dois divergiriam e o endpoint voltaria a anunciar valor que o filtro
    rejeita. A aba Relatórios continua consumindo `vocabulario`, que é por filtro
    e traz a contagem do rótulo.
    """
    lido = vocabulario(conexao)
    return {
        dominio: sorted({valor for filtro in filtros for valor in lido.get(filtro, {})})
        for dominio, filtros in DOMINIOS_DE_FILTRO.items()
    }


# --------------------------------------------------------------------------
# Ficha completa
# --------------------------------------------------------------------------

_SENTIDOS = {
    "visao_cega": "alcance_visao_cega",
    "visao_penumbra": "alcance_visao_penumbra",
    "sentido_tremor": "alcance_sentido_tremor",
    "visao_verdadeira": "alcance_visao_verdadeira",
    "percepcao_passiva": "percepcao_passiva",
}

_DESLOCAMENTO = {
    "caminhada": "velocidade_caminhada",
    "voo": "velocidade_voo",
    "natacao": "velocidade_natacao",
    "escalada": "velocidade_escalada",
    "escavacao": "velocidade_escavacao",
}


def buscar_monstro(conexao, nome):
    """Ficha completa de um monstro, por nome **exato** e sem diferenciar caixa.

    Não usa o filtro `nome`, que é por trecho: "Goblin" por trecho casaria
    "Goblin Boss", e o contrato promete uma criatura ou nada.
    """
    cursor = conexao.execute(
        "SELECT * FROM monstros WHERE nome = ? COLLATE NOCASE", (nome,)
    )
    linhas = _linhas(cursor)
    if not linhas:
        return None

    bruto = linhas[0]
    ficha = {
        "nome": bruto["nome"],
        "tipo": bruto["tipo"],
        "tamanho": bruto["tamanho"],
        "alinhamento": bruto["alinhamento"],
        "idiomas": bruto["idiomas"],
        "classe_armadura": bruto["classe_armadura"],
        "pontos_vida": bruto["pontos_vida"],
        "desafio": bruto["nivel_desafio"],
        "atributos": {
            atributo: {
                "valor": bruto[atributo],
                "modificador": modificador(bruto[atributo]),
            }
            for atributo in ATRIBUTOS
        },
        "testes_de_resistencia": [
            {"atributo": atributo, "bonus": bruto[f"{atributo}_save"]}
            for atributo in saves_proficientes(bruto)
        ],
        "sentidos": {
            chave: bruto[coluna]
            for chave, coluna in _SENTIDOS.items()
            if bruto[coluna] is not None
        },
        "deslocamento": _montar_deslocamento(bruto),
        "pericias": _pericias(conexao, bruto["nome"]),
        "acoes": _acoes(conexao, bruto["nome"]),
    }
    ficha.update(_interacoes_de_dano(conexao, bruto["nome"]))
    ficha["imunidades_a_condicao"] = _coluna(
        conexao,
        "SELECT condicao FROM monstro_imunidade_condicao WHERE monstro_nome = ?",
        bruto["nome"],
    )
    ficha["ambientes"] = _coluna(
        conexao,
        "SELECT ambiente FROM monstro_ambiente WHERE monstro_nome = ?",
        bruto["nome"],
    )
    return ficha


def _montar_deslocamento(bruto):
    # Zero e nulo significam ambos "não possui" — a Spec 3 nunca fixou qual dos
    # dois a ingestão grava, então a ficha não pode depender disso.
    deslocamento = {
        chave: bruto[coluna] for chave, coluna in _DESLOCAMENTO.items() if bruto[coluna]
    }
    # `pode_pairar` não é modo de deslocamento: sai sempre, como booleano. Aplicar
    # a regra de omissão a ele apagaria o campo em vez de devolver `false`.
    deslocamento["pode_pairar"] = bool(bruto["pode_pairar"])
    return deslocamento


def _pericias(conexao, nome):
    return _linhas(
        conexao.execute(
            "SELECT pericia, bonus FROM monstro_pericia WHERE monstro_nome = ? "
            "ORDER BY pericia",
            (nome,),
        )
    )


def _interacoes_de_dano(conexao, nome):
    chaves = {
        "imunidade": "imunidades_a_dano",
        "resistencia": "resistencias_a_dano",
        "vulnerabilidade": "vulnerabilidades_a_dano",
    }
    interacoes = {chave: [] for chave in chaves.values()}
    for tipo_dano, relacao in conexao.execute(
        "SELECT tipo_dano, relacao FROM monstro_interacao_dano "
        "WHERE monstro_nome = ? ORDER BY tipo_dano",
        (nome,),
    ):
        if relacao in chaves:
            interacoes[chaves[relacao]].append(tipo_dano)
    return interacoes


def _coluna(conexao, sql, nome):
    return [linha[0] for linha in conexao.execute(sql + " ORDER BY 1", (nome,))]


def _acoes(conexao, nome):
    acoes = _linhas(
        conexao.execute(
            "SELECT id, categoria, nome_acao AS nome, descricao FROM acoes "
            "WHERE monstro_nome = ? ORDER BY id",
            (nome,),
        )
    )
    for acao in acoes:
        acao["ataques"] = _linhas(
            conexao.execute(
                "SELECT nome_ataque, tipo_ataque, bonus_ataque, alcance, "
                "alcance_longo, dano_dado, dano_bonus, dano_tipo, dano_medio, "
                "dano_extra_dado, dano_extra_bonus, dano_extra_tipo, "
                "dano_extra_medio FROM ataques WHERE acao_id = ? ORDER BY id",
                (acao["id"],),
            )
        )
        acao["efeitos"] = _linhas(
            conexao.execute(
                "SELECT cd_resistencia, atributo_resistencia, condicao, area_tipo, "
                "area_tamanho FROM efeitos WHERE acao_id = ? ORDER BY id",
                (acao["id"],),
            )
        )
        del acao["id"]
    return acoes


def resolver_nomes(conexao, nomes):
    """Devolve `(fichas_encontradas, nomes_inexistentes)`.

    É o que a aba Pesquisar consome em `?fixados=Adult+Red+Dragon,Vampire`: link
    velho não deve derrubar a página, então o que não existe volta como aviso.
    """
    fichas, faltantes = [], []
    for nome in nomes or []:
        ficha = buscar_monstro(conexao, nome)
        if ficha is None:
            faltantes.append(nome)
        else:
            fichas.append(ficha)
    return fichas, faltantes


def abrir_conexao(caminho="bestiario_combate.db"):
    """Conexão **de fato** somente-leitura, via URI em modo `ro`.

    `sqlite3.connect` comum criaria um banco vazio em silêncio se o caminho
    estivesse errado, e o engano só apareceria bem depois como "nenhum monstro
    encontrado". Em modo `ro`, caminho errado falha na hora. Esta camada só lê —
    quem escreve é `banco.py`, que abre a sua própria conexão.
    """
    return sqlite3.connect(f"file:{Path(caminho).as_posix()}?mode=ro", uri=True)
