"""Rotas HTML do site: raiz, aba "Todos os monstros" e destinos mínimos.

Nenhuma rota escreve SQL — a listagem chama `bestiario/consultas.py`, do
mesmo jeito que `api/rotas.py`. A conexão chega pela **mesma dependência**
`obter_conexao` que a Spec 8 define: é o único ponto que o teste substitui
via `app.dependency_overrides`, e reaproveitá-la (em vez de abrir uma
conexão própria) é o que torna o site testável sem `bestiario_combate.db`.

`/relatorios` e `/pesquisar` só existem aqui como destino de link — o
construtor de análises e a busca com fichas fixadas chegam nas Specs 9b e
9c. Renderizam o bloco padrão de `base.html`, sem template próprio.
"""

import sqlite3
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from api.rotas import verificar_banco_sincronizado
from bestiario.consultas import PRESETS, executar_consulta, vocabulario
from bestiario.excecoes import FiltroDesconhecido, ValorDeFiltroInvalido

roteador = APIRouter(include_in_schema=False)
# Ancorado em `__file__`, não no diretório de trabalho: `uv run uvicorn` e o
# `pytest` podem ser chamados de lugares diferentes.
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

# (chave da aba, rótulo, caminho) — usado pela moldura para montar as três abas
# e destacar a corrente. Vive aqui, não em `base.html`, porque é dado de rota.
ABAS = (
    ("relatorios", "Relatórios", "/relatorios"),
    ("pesquisar", "Pesquisar", "/pesquisar"),
    ("monstros", "Todos os monstros", "/monstros"),
)

# (coluna, rótulo, alinhada à direita) — as seis colunas ordenáveis da aba
# "Todos os monstros", na ordem em que aparecem na tabela.
_COLUNAS_TODOS = (
    ("nome", "Nome", False),
    ("tipo", "Tipo", False),
    ("tamanho", "Tamanho", False),
    ("desafio", "Desafio", True),
    ("pontos_vida", "Pontos de vida", True),
    ("classe_armadura", "Armadura", True),
)


# (chave do filtro, rótulo em português). São os dez filtros de recorte que têm
# vocabulário; a faixa de desafio é o décimo primeiro e tem campo próprio.
# `nome` fica fora de propósito: é por trecho e pertence à busca da aba
# Pesquisar — procurar por nome aqui competiria com ela.
FILTROS_DA_TELA = (
    ("tipo", "Tipo"),
    ("tamanho", "Tamanho"),
    ("alinhamento", "Alinhamento"),
    ("ambiente", "Ambiente"),
    ("resiste_a", "Resiste a"),
    ("imune_a", "Imune a"),
    ("vulneravel_a", "Vulnerável a"),
    ("imune_a_condicao", "Imune à condição"),
    ("impoe", "Impõe"),
    ("relacao", "Relação com dano"),
)

# (dimensão, rótulo) — as sete que o núcleo aceita em `comparacao`.
DIMENSOES_DA_TELA = (
    ("tipo", "tipo"),
    ("tamanho", "tamanho"),
    ("alinhamento", "alinhamento"),
    ("desafio", "desafio"),
    ("ambiente", "ambiente"),
    ("tipo_dano", "tipo de dano"),
    ("condicao_imposta", "condição imposta"),
)

# Um monstro cai em mais de um grupo nestas, então a soma da coluna de contagem
# passa do total. Sem aviso, o usuário conclui que a conta está errada.
_DIMENSOES_MULTIVALORADAS = {"ambiente", "tipo_dano", "condicao_imposta"}

# "Média de" por extenso porque `202` lido isolado engana — parece o total de um
# dragão, não a média dos 43 — e engana em silêncio.
_COLUNAS_COMPARACAO = (
    ("valor", "Valor", False),
    ("monstros", "Monstros", True),
    ("media_pontos_vida", "Média de pontos de vida", True),
    ("media_classe_armadura", "Média de classe de armadura", True),
    ("media_desafio", "Média de desafio", True),
    ("media_dano", "Média de dano", True),
    ("media_bonus_ataque", "Média de bônus de ataque", True),
)

_COLUNAS_LISTA = (
    ("nome", "Nome", False),
    ("tipo", "Tipo", False),
    ("tamanho", "Tamanho", False),
    ("desafio", "Desafio", True),
    ("pontos_vida", "Pontos de vida", True),
    ("classe_armadura", "Armadura", True),
    ("dano_medio", "Dano médio", True),
)

# Preset → rótulo. Só os que esta tela sabe exibir: `saida` admite `monstros` e
# `comparacao`, então o preset de modo `lista_ataques` ("Top ataques") deixaria
# o formulário num estado irrepresentável. Ele segue no terminal e na API.
PRESETS_DA_TELA = (
    ("comparacao_tipos", "Comparação entre tipos"),
    ("letalidade_por_tipo", "Letalidade por tipo"),
    ("por_ambiente", "Monstros por ambiente"),
    ("imunidade_a_dano", "Imunidade a dano"),
    ("condicoes_impostas", "Condições impostas"),
    ("mais_resistentes", "Mais resistentes"),
)


def _filtros_da_query(request):
    """Filtros vindos da query string pelos nomes da tela. Vazio não restringe."""
    filtros = {
        chave: request.query_params.get(chave)
        for chave, _ in FILTROS_DA_TELA
        if request.query_params.get(chave)
    }
    for extremo in ("desafio_min", "desafio_max"):
        valor = request.query_params.get(extremo)
        if not valor:
            continue
        try:
            filtros[extremo] = float(valor)
        except ValueError:
            # Faixa com texto não numérico é ignorada, não derruba a página.
            pass
    return filtros


def _como_digitado(request, chave, valor):
    """Devolve o texto original da query string, não o valor convertido.

    O formulário não pode reescrever o que a pessoa digitou: quem envia `17` vê
    `17` de volta, e não `17.0`.
    """
    return request.query_params.get(chave, valor if valor is not None else "")


def _url_de_preset(nome, modo):
    """Preset vira link que **preenche o formulário**, não tela pronta e fechada.

    O usuário vê como a análise foi montada e pode mexer — resolve a tela em
    branco e ensina a ferramenta usando ela mesma.
    """
    preset = dict(PRESETS[nome])
    parametros = dict(preset.pop("filtros", {}) or {})
    parametros["modo"] = modo
    if preset.get("modo") == "comparacao":
        parametros["saida"] = "comparacao"
        parametros["por"] = preset["por"]
    else:
        parametros["saida"] = "monstros"
    return "?" + urlencode(parametros)


def _executar_relatorio(conexao, filtros, saida, por, combinar):
    """Executa, e transforma valor/chave inválidos em aviso em vez de erro 500.

    Link velho ou editado à mão não pode derrubar a página: o parâmetro culpado
    é descartado, os demais seguem valendo, e o aviso diz o que foi ignorado.
    """
    avisos = []
    filtros = dict(filtros)
    while True:
        try:
            modo_da_saida = "comparacao" if saida == "comparacao" else "lista_monstros"
            extra = {"por": por} if saida == "comparacao" else {}
            linhas = executar_consulta(
                conexao, filtros, modo=modo_da_saida, combinar=combinar, **extra
            )
            # A faixa de resumo não é opcional e não tem botão que a ligue: ela
            # responde "qual a média de dano desses monstros" sem o usuário
            # precisar pedir. Por isso sai na mesma requisição, sempre.
            resumo = executar_consulta(
                conexao, filtros, modo="resumo", combinar=combinar
            )[0]
            return linhas, resumo, por, avisos
        except ValorDeFiltroInvalido as erro:
            avisos.append(
                f"O valor {erro.valor!r} não é reconhecido em "
                f"{erro.parametro!r} e foi ignorado."
            )
            filtros.pop(erro.parametro, None)
        except FiltroDesconhecido:
            avisos.append(f"A dimensão {por!r} não existe; usando 'tipo'.")
            por = "tipo"


def _contexto_base(request, aba_atual, modo):
    """Contexto comum a toda página: abas, alternância de modo, link do rodapé.

    O alternador Resumida/Completa preserva os demais parâmetros da URL atual
    (como `ordenar_por`) e troca só `modo` — mudar a exibição não pode perder
    a ordenação que o usuário já escolheu.
    """
    outros = {
        chave: valor for chave, valor in request.query_params.items() if chave != "modo"
    }
    return {
        "request": request,
        "aba_atual": aba_atual,
        "modo": modo,
        "abas": ABAS,
        "url_resumida": f"?{urlencode({**outros, 'modo': 'resumida'})}",
        "url_completa": f"?{urlencode({**outros, 'modo': 'completa'})}",
    }


def pagina_de_base_nao_sincronizada(request):
    """Página humana para o 503, no lugar do RFC 7807 que a API devolve.

    Vale para banco **vazio**, **ausente** e com **schema defasado** — o `.db`
    está fora do git, então clone novo cai aqui antes de qualquer outra coisa, e
    "sincronize a base" é a mesma cura nos três casos.

    Responde **200**, não 503: para quem abre o site isto não é falha, é o estado
    inicial esperado, e a página diz o que fazer. O 503 continua valendo sob
    `/api/`, onde quem chama é programa e precisa do sinal na faixa de status.
    """
    aba = next(
        (chave for chave, _, caminho in ABAS if request.url.path == caminho),
        "monstros",
    )
    contexto = _contexto_base(
        request, aba, request.query_params.get("modo", "resumida")
    )
    contexto["mensagem"] = (
        "A base local ainda não foi sincronizada. Rode `python main.py` e "
        "escolha a opção 4 (sincronizar base completa) para baixar os 325 "
        "monstros do SRD 2014."
    )
    return templates.TemplateResponse(request, "base.html", contexto)


@roteador.get("/")
def raiz():
    return RedirectResponse("/relatorios")


@roteador.get("/relatorios")
def relatorios(
    request: Request,
    modo: str = "resumida",
    saida: str = "comparacao",
    por: str = "tipo",
    combinar: str = "todos",
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    filtros = _filtros_da_query(request)
    saida = saida if saida in ("monstros", "comparacao") else "comparacao"
    linhas, resumo, por, avisos = _executar_relatorio(
        conexao, filtros, saida, por, combinar
    )

    contexto = _contexto_base(request, "relatorios", modo)
    contexto.update(
        {
            "filtros": filtros,
            "desafio_min": _como_digitado(request, "desafio_min", None),
            "desafio_max": _como_digitado(request, "desafio_max", None),
            "saida": saida,
            "por": por,
            # Cabeçalho da primeira coluna da comparação: o rótulo da dimensão,
            # não a palavra "Valor". Agrupando por ambiente, a coluna É o
            # ambiente — dizer "Valor" esconde por que ela está ali.
            "rotulo_da_dimensao": dict(DIMENSOES_DA_TELA).get(por, por).capitalize(),
            "combinar": combinar,
            "linhas": linhas,
            "resumo": resumo,
            "avisos": avisos,
            "vocabulario": vocabulario(conexao),
            "filtros_da_tela": FILTROS_DA_TELA,
            "dimensoes": DIMENSOES_DA_TELA,
            "colunas": _COLUNAS_COMPARACAO if saida == "comparacao" else _COLUNAS_LISTA,
            "multivalorada": por in _DIMENSOES_MULTIVALORADAS,
            "presets": [
                (rotulo, _url_de_preset(chave, modo))
                for chave, rotulo in PRESETS_DA_TELA
            ],
            # O recorte viaja como **filtros**, não como lista de nomes: a aba
            # Pesquisar não tem teto de monstros, e 325 nomes estourariam a URL.
            # `combinar` e `modo` vão junto — sem eles, o recorte seria
            # reavaliado de outro jeito e exibiria outro conjunto, sem erro.
            "url_pesquisar": "/pesquisar?"
            + urlencode({**filtros, "combinar": combinar, "modo": modo}),
        }
    )
    return templates.TemplateResponse(request, "relatorios.html", contexto)


@roteador.get("/pesquisar")
def pesquisar(request: Request, modo: str = "resumida"):
    contexto = _contexto_base(request, "pesquisar", modo)
    contexto["mensagem"] = "A busca com fichas comparadas chega na próxima spec."
    return templates.TemplateResponse(request, "base.html", contexto)


def _proximo_sentido(coluna, ordenar_por, sentido):
    """Primeiro clique num cabeçalho ordena crescente; o segundo, decrescente."""
    if coluna != ordenar_por:
        return "crescente"
    return "decrescente" if sentido == "crescente" else "crescente"


@roteador.get("/monstros")
def listar_todos_os_monstros(
    request: Request,
    ordenar_por: str = "nome",
    sentido: str = "crescente",
    modo: str = "resumida",
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    # Mesma dependência da API, e não `obter_conexao`: esta também cobre banco
    # que **abre** mas está com schema defasado ou incompleto, caso em que a
    # consulta só falharia lá dentro e viraria 500 com traceback na tela. É a
    # armadilha que o CLAUDE.md registra — banco defasado não emite sinal.
    # Sem filtro nesta aba: é a de folhear.
    monstros = executar_consulta(
        conexao,
        modo="lista_monstros",
        ordenar_por=ordenar_por,
        sentido=sentido,
        limite=None,
    )
    contexto = _contexto_base(request, "monstros", modo)
    contexto["monstros"] = monstros
    contexto["colunas"] = [
        {
            "chave": chave,
            "rotulo": rotulo,
            "num": num,
            "url": "?"
            + urlencode(
                {
                    "ordenar_por": chave,
                    "sentido": _proximo_sentido(chave, ordenar_por, sentido),
                    "modo": modo,
                }
            ),
        }
        for chave, rotulo, num in _COLUNAS_TODOS
    ]
    return templates.TemplateResponse(request, "todos.html", contexto)
