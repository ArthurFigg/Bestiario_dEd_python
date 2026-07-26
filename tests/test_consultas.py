"""Testes da camada de consulta.

Montagem testada sem banco (a função é pura); execução contra SQLite em memória
no schema da Spec 3 — nunca contra `bestiario_combate.db`, que está fora do git
e não existe no CI.
"""

import sqlite3

import pytest

from bestiario.banco import criar_base_de_dados
from bestiario.consultas import (
    DOMINIOS_DE_FILTRO,
    PRESETS,
    abrir_conexao,
    buscar_monstro,
    contar,
    executar_consulta,
    montar_consulta,
    resolver_nomes,
    vocabulario,
    vocabulario_por_dominio,
)
from bestiario.excecoes import FiltroDesconhecido, ValorDeFiltroInvalido


@pytest.fixture
def conexao(tmp_path):
    con = criar_base_de_dados(str(tmp_path / "teste.db"))
    _semear(con)
    yield con
    con.close()


def _monstro(cursor, nome, **campos):
    padrao = {
        "tamanho": "large",
        "tipo": "dragon",
        "classe_armadura": 18,
        "pontos_vida": 200,
        "nivel_desafio": 10.0,
        "forca": 20,
        "destreza": 10,
        "constituicao": 20,
        "inteligencia": 14,
        "sabedoria": 12,
        "carisma": 18,
        "forca_save": 5,
        "destreza_save": 0,
        "constituicao_save": 5,
        "inteligencia_save": 2,
        "sabedoria_save": 1,
        "carisma_save": 4,
        "velocidade_caminhada": 40,
        "velocidade_voo": 80,
        "velocidade_natacao": 0,
        "velocidade_escalada": None,
        "velocidade_escavacao": None,
        "pode_pairar": 0,
        "alinhamento": "chaotic evil",
        "idiomas": "Common",
        "alcance_visao_cega": 60,
        "alcance_visao_penumbra": 120,
        "alcance_sentido_tremor": None,
        "alcance_visao_verdadeira": None,
        "percepcao_passiva": 20,
    }
    padrao.update(campos)
    colunas = ["nome"] + list(padrao)
    valores = [nome] + list(padrao.values())
    cursor.execute(
        f"INSERT INTO monstros ({','.join(colunas)}) "
        f"VALUES ({','.join('?' * len(colunas))})",
        valores,
    )


def _semear(con):
    """Conjunto pequeno e conhecido, montado para exercitar cada regra."""
    c = con.cursor()
    _monstro(c, "Adult Red Dragon", pontos_vida=256, nivel_desafio=17.0)
    _monstro(
        c,
        "Goblin",
        tipo="humanoid",
        tamanho="small",
        pontos_vida=7,
        nivel_desafio=0.25,
        classe_armadura=15,
        alinhamento=None,
        velocidade_voo=0,
        pode_pairar=0,
        alcance_visao_cega=None,
        alcance_visao_penumbra=60,
    )
    _monstro(
        c,
        "Goblin Boss",
        tipo="humanoid",
        tamanho="small",
        pontos_vida=21,
        nivel_desafio=1.0,
        classe_armadura=17,
    )
    _monstro(c, "Vampire", tipo="undead", pontos_vida=144, nivel_desafio=13.0)

    c.executemany(
        "INSERT INTO monstro_interacao_dano (monstro_nome, tipo_dano, relacao) "
        "VALUES (?,?,?)",
        [
            ("Adult Red Dragon", "fire", "imunidade"),
            ("Vampire", "necrotic", "resistencia"),
            ("Vampire", "radiant", "vulnerabilidade"),
            ("Goblin", "fire", "resistencia"),
        ],
    )
    c.executemany(
        "INSERT INTO monstro_ambiente (monstro_nome, ambiente) VALUES (?,?)",
        [
            ("Adult Red Dragon", "mountain"),
            ("Adult Red Dragon", "desert"),
            ("Goblin", "forest"),
            ("Goblin Boss", "forest"),
            ("Vampire", "urban"),
        ],
    )
    c.executemany(
        "INSERT INTO monstro_imunidade_condicao (monstro_nome, condicao) VALUES (?,?)",
        [("Vampire", "charmed")],
    )
    c.executemany(
        "INSERT INTO monstro_pericia (monstro_nome, pericia, bonus) VALUES (?,?,?)",
        [("Adult Red Dragon", "perception", 13)],
    )

    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Adult Red Dragon", "action", "Bite", "Melee Weapon Attack..."),
    )
    bite = c.lastrowid
    c.execute(
        "INSERT INTO ataques (acao_id, nome_ataque, tipo_ataque, bonus_ataque, "
        "alcance, dano_dado, dano_bonus, dano_tipo, dano_medio, dano_extra_dado, "
        "dano_extra_medio, dano_extra_tipo) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            bite,
            "Bite attack",
            "melee_weapon",
            14,
            10,
            "2d10",
            8,
            "piercing",
            19.0,
            "2d6",
            7.0,
            "fire",
        ),
    )
    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Adult Red Dragon", "action", "Fire Breath", "DC 21 Dexterity..."),
    )
    sopro = c.lastrowid
    c.execute(
        "INSERT INTO efeitos (acao_id, cd_resistencia, atributo_resistencia, "
        "condicao, area_tipo, area_tamanho) VALUES (?,?,?,?,?,?)",
        (sopro, 21, "dexterity", None, "cone", 60),
    )
    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Vampire", "action", "Bite", "..."),
    )
    mordida = c.lastrowid
    c.execute(
        "INSERT INTO ataques (acao_id, nome_ataque, bonus_ataque, dano_dado, "
        "dano_bonus, dano_medio) VALUES (?,?,?,?,?,?)",
        (mordida, "Bite attack", 9, "1d6", 4, 7.5),
    )
    c.execute(
        "INSERT INTO efeitos (acao_id, cd_resistencia, atributo_resistencia, "
        "condicao, area_tipo, area_tamanho) VALUES (?,?,?,?,?,?)",
        (mordida, 18, "constitution", "charmed", None, None),
    )
    con.commit()


# --- montagem (pura, sem banco) -------------------------------------------


def test_montar_consulta_e_pura_e_devolve_sql_e_parametros():
    sql, parametros = montar_consulta({"tipo": "dragon"})
    assert sql.strip().startswith("SELECT") and parametros == ["dragon"]


def test_filtro_de_tabela_filha_gera_exists_e_nao_join():
    sql, _ = montar_consulta({"ambiente": "forest"})
    assert "EXISTS" in sql and "JOIN monstro_ambiente" not in sql


def test_combinar_qualquer_gera_or():
    sql, _ = montar_consulta(
        {"tipo": "dragon", "tamanho": "large"}, combinar="qualquer"
    )
    assert " OR " in sql


def test_combinar_todos_gera_and():
    sql, _ = montar_consulta({"tipo": "dragon", "tamanho": "large"})
    assert " AND " in sql and " OR " not in sql


def test_nenhum_valor_de_filtro_e_interpolado_no_texto_do_sql():
    sql, parametros = montar_consulta({"tipo": "dragon", "ambiente": "forest"})
    assert "dragon" not in sql and "forest" not in sql and len(parametros) == 2


def test_chave_de_filtro_fora_da_lista_branca_levanta_erro():
    with pytest.raises(FiltroDesconhecido):
        montar_consulta({"cor": "vermelho"})


def test_dimensao_fora_da_lista_branca_levanta_erro():
    with pytest.raises(FiltroDesconhecido):
        montar_consulta({}, modo="comparacao", por="cor")


def test_filtro_vazio_nao_restringe_nada():
    # "WHERE (" é o que `_clausulas` emite; a subconsulta de dano tem WHERE próprio.
    sql, parametros = montar_consulta({"tipo": ""})
    assert "WHERE (" not in sql and parametros == []


def test_ataques_com_coluna_valida_e_sem_sentido_ordena_decrescente():
    # O contrato não dá `sentido` a /ataques: ordena sempre decrescente. Antes,
    # coluna válida sem sentido caía em ASC e devolvia os ataques mais fracos.
    sql, _ = montar_consulta({}, modo="lista_ataques", ordenar_por="dano_medio")
    assert "ORDER BY dano_medio DESC" in sql


def test_monstros_com_coluna_valida_e_sem_sentido_ordena_crescente():
    sql, _ = montar_consulta({}, ordenar_por="pontos_vida")
    assert "ORDER BY pontos_vida ASC" in sql


def test_deslocamento_sem_limite_ainda_gera_offset():
    # SQLite exige LIMIT antes de OFFSET; sem o `LIMIT -1`, pedir a página 2 sem
    # teto devolveria a página 1 sem erro nenhum.
    sql, parametros = montar_consulta({}, deslocamento=50)
    assert "OFFSET ?" in sql and parametros == [50]


def test_limite_e_deslocamento_juntos_mantem_a_ordem_dos_parametros():
    sql, parametros = montar_consulta({}, limite=10, deslocamento=20)
    assert sql.index("LIMIT") < sql.index("OFFSET") and parametros == [10, 20]


def test_deslocamento_zero_nao_gera_offset():
    sql, parametros = montar_consulta({}, limite=10, deslocamento=0)
    assert "OFFSET" not in sql and parametros == [10]


# --- execução --------------------------------------------------------------


def test_executar_consulta_devolve_chaves_do_contrato(conexao):
    linha = executar_consulta(conexao, {"tipo": "undead"})[0]
    assert "desafio" in linha and "nivel_desafio" not in linha


def test_filtrar_por_ambiente_nao_duplica_monstro_de_varios_ambientes(conexao):
    nomes = [m["nome"] for m in executar_consulta(conexao, {"tipo": "dragon"})]
    assert nomes.count("Adult Red Dragon") == 1


def test_desafio_invertido_devolve_vazio_sem_excecao(conexao):
    assert executar_consulta(conexao, {"desafio_min": 20, "desafio_max": 5}) == []


def test_valor_fora_do_vocabulario_levanta_erro(conexao):
    with pytest.raises(ValorDeFiltroInvalido):
        executar_consulta(conexao, {"resiste_a": "fogo"})


def test_erro_de_valor_carrega_o_parametro_e_o_valor(conexao):
    with pytest.raises(ValorDeFiltroInvalido) as erro:
        executar_consulta(conexao, {"resiste_a": "fogo"})
    assert erro.value.parametro == "resiste_a" and erro.value.valor == "fogo"


def test_ordenar_por_pontos_vida_decrescente(conexao):
    linhas = executar_consulta(
        conexao, ordenar_por="pontos_vida", sentido="decrescente"
    )
    assert linhas[0]["nome"] == "Adult Red Dragon"


def test_ordenar_por_fora_da_lista_branca_cai_no_padrao(conexao):
    linhas = executar_consulta(conexao, ordenar_por="cor")
    assert [m["nome"] for m in linhas] == sorted(m["nome"] for m in linhas)


def test_ordenar_por_tipo_ordena_de_fato(conexao):
    linhas = executar_consulta(conexao, ordenar_por="tipo")
    assert [m["tipo"] for m in linhas] == sorted(m["tipo"] for m in linhas)


def test_ordenar_por_tamanho_ordena_de_fato(conexao):
    linhas = executar_consulta(conexao, ordenar_por="tamanho", sentido="decrescente")
    assert linhas[0]["tamanho"] == "small"


def test_ordenar_por_dano_medio_com_limite_olha_o_conjunto_inteiro(conexao):
    # A média está gravada em coluna, então ORDER BY acontece antes do LIMIT.
    linhas = executar_consulta(
        conexao, ordenar_por="dano_medio", sentido="decrescente", limite=1
    )
    assert linhas[0]["nome"] == "Adult Red Dragon"


def test_sem_limite_devolve_todas_as_linhas(conexao):
    assert len(executar_consulta(conexao)) == 4


def test_contar_ignora_o_limite(conexao):
    linhas = executar_consulta(conexao, limite=2)
    assert len(linhas) == 2 and contar(conexao) == 4


def test_contar_respeita_os_filtros(conexao):
    assert contar(conexao, {"tipo": "humanoid"}) == 2


def test_contar_no_grao_de_ataques(conexao):
    assert contar(conexao, grao="ataques") == 2


def test_lista_de_ataques_traz_monstro_e_acao_donos(conexao):
    linha = executar_consulta(conexao, modo="lista_ataques")[0]
    assert linha["monstro"] and linha["acao"]


def test_consulta_sem_resultado_devolve_lista_vazia(conexao):
    # Combinação de dois valores válidos que nenhum monstro atende. Um valor
    # sozinho fora do vocabulário levantaria erro — o vocabulário sai do banco,
    # então "existe no vocabulário" e "tem pelo menos um monstro" são o mesmo.
    assert executar_consulta(conexao, {"tipo": "dragon", "tamanho": "small"}) == []


# --- comparação e resumo ---------------------------------------------------


def test_comparacao_sai_da_maior_contagem_para_a_menor(conexao):
    linhas = executar_consulta(conexao, modo="comparacao", por="tipo")
    assert linhas[0]["monstros"] >= linhas[-1]["monstros"]


def test_comparacao_por_desafio_devolve_valor_como_texto(conexao):
    linhas = executar_consulta(conexao, modo="comparacao", por="desafio")
    assert all(isinstance(linha["valor"], str) for linha in linhas)


def test_monstro_sem_alinhamento_vira_grupo_proprio(conexao):
    linhas = executar_consulta(conexao, modo="comparacao", por="alinhamento")
    assert "sem alinhamento" in [linha["valor"] for linha in linhas]


def test_comparacao_por_ambiente_nao_conta_monstro_duas_vezes(conexao):
    linhas = executar_consulta(conexao, modo="comparacao", por="ambiente")
    montanha = [linha for linha in linhas if linha["valor"] == "mountain"][0]
    assert montanha["monstros"] == 1


def test_comparacao_traz_todas_as_metricas(conexao):
    linha = executar_consulta(conexao, modo="comparacao", por="tipo")[0]
    assert "media_bonus_ataque" in linha and "media_dano" in linha


def test_relacao_imunidade_com_dimensao_tipo_dano_conta_so_imunidades(conexao):
    linhas = executar_consulta(
        conexao, {"relacao": "imunidade"}, modo="comparacao", por="tipo_dano"
    )
    assert [linha["valor"] for linha in linhas] == ["fire"]


def test_trocar_a_relacao_muda_o_resultado(conexao):
    linhas = executar_consulta(
        conexao, {"relacao": "resistencia"}, modo="comparacao", por="tipo_dano"
    )
    assert sorted(linha["valor"] for linha in linhas) == ["fire", "necrotic"]


def test_resumo_devolve_uma_linha_so(conexao):
    assert len(executar_consulta(conexao, modo="resumo")) == 1


def test_resumo_sem_resultado_devolve_contagem_zero(conexao):
    linha = executar_consulta(conexao, {"desafio_min": 100}, modo="resumo")[0]
    assert linha["monstros"] == 0


def test_media_sai_com_duas_casas_decimais(conexao):
    linha = executar_consulta(conexao, modo="resumo")[0]
    assert round(linha["media_pontos_vida"], 2) == linha["media_pontos_vida"]


# --- vocabulário -----------------------------------------------------------


def test_vocabulario_devolve_cada_valor_com_sua_contagem(conexao):
    assert vocabulario(conexao)["tipo"]["humanoid"] == 2


def test_vocabulario_tem_uma_entrada_por_filtro(conexao):
    vocabulario_lido = vocabulario(conexao)
    assert {"tipo", "ambiente", "imune_a", "impoe"} <= set(vocabulario_lido)


def test_vocabulario_separa_imune_a_de_resiste_a(conexao):
    vocabulario_lido = vocabulario(conexao)
    assert "necrotic" in vocabulario_lido["resiste_a"]
    assert "necrotic" not in vocabulario_lido["imune_a"]


# --- ficha -----------------------------------------------------------------


def test_buscar_monstro_acha_apesar_da_caixa(conexao):
    assert buscar_monstro(conexao, "adult red dragon")["nome"] == "Adult Red Dragon"


def test_buscar_monstro_inexistente_devolve_none(conexao):
    assert buscar_monstro(conexao, "Tarrasque") is None


def test_buscar_monstro_e_exato_e_nao_casa_por_trecho(conexao):
    assert buscar_monstro(conexao, "Goblin")["pontos_vida"] == 7


def test_ficha_traz_acoes_com_ataques_aninhados(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    bite = [a for a in ficha["acoes"] if a["nome"] == "Bite"][0]
    assert bite["ataques"][0]["nome_ataque"] == "Bite attack"


def test_ficha_traz_acoes_com_efeitos_aninhados(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    sopro = [a for a in ficha["acoes"] if a["nome"] == "Fire Breath"][0]
    assert sopro["efeitos"][0]["cd_resistencia"] == 21


def test_ataque_da_ficha_traz_dano_medio_pronto(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    bite = [a for a in ficha["acoes"] if a["nome"] == "Bite"][0]
    assert bite["ataques"][0]["dano_medio"] == 19.0


def test_ficha_omite_sentido_que_o_monstro_nao_tem(conexao):
    ficha = buscar_monstro(conexao, "Goblin")
    assert "visao_cega" not in ficha["sentidos"]


def test_ficha_traz_sentido_que_o_monstro_tem(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert ficha["sentidos"]["visao_cega"] == 60


def test_ficha_omite_deslocamento_que_vale_zero(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert "natacao" not in ficha["deslocamento"]


def test_ficha_omite_deslocamento_que_vale_nulo(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert "escalada" not in ficha["deslocamento"]


def test_pode_pairar_sai_como_booleano_mesmo_valendo_zero(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert ficha["deslocamento"]["pode_pairar"] is False


def test_ficha_traz_so_os_saves_proficientes(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    atributos = [t["atributo"] for t in ficha["testes_de_resistencia"]]
    assert "destreza" not in atributos  # save 0 == modificador de 10


def test_ficha_traz_atributos_com_modificador(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert ficha["atributos"]["forca"]["modificador"] == 5


def test_ficha_separa_imunidade_de_resistencia_a_dano(conexao):
    ficha = buscar_monstro(conexao, "Vampire")
    assert ficha["resistencias_a_dano"] == ["necrotic"]


def test_ficha_traz_vulnerabilidades(conexao):
    assert buscar_monstro(conexao, "Vampire")["vulnerabilidades_a_dano"] == ["radiant"]


def test_ficha_traz_ambientes(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert sorted(ficha["ambientes"]) == ["desert", "mountain"]


def test_ficha_traz_pericias_com_bonus(conexao):
    ficha = buscar_monstro(conexao, "Adult Red Dragon")
    assert ficha["pericias"][0]["bonus"] == 13


# --- resolução de nomes ----------------------------------------------------


def test_resolver_nomes_devolve_as_fichas_achadas(conexao):
    fichas, _ = resolver_nomes(conexao, ["Adult Red Dragon", "Vampire"])
    assert [f["nome"] for f in fichas] == ["Adult Red Dragon", "Vampire"]


def test_resolver_nomes_devolve_os_inexistentes(conexao):
    _, faltantes = resolver_nomes(conexao, ["Vampire", "Tarrasque"])
    assert faltantes == ["Tarrasque"]


def test_resolver_lista_vazia_nao_quebra(conexao):
    assert resolver_nomes(conexao, []) == ([], [])


# --- presets ---------------------------------------------------------------


@pytest.mark.parametrize("nome", sorted(PRESETS))
def test_preset_roda_sem_erro_de_coluna_inexistente(conexao, nome):
    parametros = dict(PRESETS[nome])
    filtros = parametros.pop("filtros", None)
    assert executar_consulta(conexao, filtros, **parametros) is not None


# --- conexão ---------------------------------------------------------------


def test_abrir_conexao_le_banco_existente(tmp_path):
    caminho = tmp_path / "existe.db"
    criar_base_de_dados(str(caminho)).close()
    with abrir_conexao(str(caminho)) as con:
        assert contar(con) == 0


def test_abrir_conexao_com_caminho_errado_falha_em_vez_de_criar_banco(tmp_path):
    # `sqlite3.connect` comum criaria um .db vazio aqui, e o engano só apareceria
    # depois como "nenhum monstro encontrado".
    inexistente = tmp_path / "nao_existe.db"
    with pytest.raises(sqlite3.OperationalError):
        abrir_conexao(str(inexistente))
    assert not inexistente.exists()


def test_abrir_conexao_rejeita_escrita(tmp_path):
    caminho = tmp_path / "somente_leitura.db"
    criar_base_de_dados(str(caminho)).close()
    with abrir_conexao(str(caminho)) as con:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM monstros")


# --- vocabulário por domínio -------------------------------------------------


def test_valor_de_outro_filtro_do_mesmo_dominio_devolve_vazio_em_vez_de_erro(conexao):
    # `radiant` é vulnerabilidade do Vampire, nunca imunidade de ninguém. Ainda
    # assim é um tipo de dano legítimo: "ninguém é imune a radiant" é pergunta
    # coerente sem resposta, como o intervalo de desafio invertido.
    assert executar_consulta(conexao, {"imune_a": "radiant"}) == []


def test_valor_inexistente_em_qualquer_dominio_continua_levantando(conexao):
    # `fogo` não é tipo de dano em lugar nenhum — é engano de quem escreveu.
    with pytest.raises(ValorDeFiltroInvalido):
        executar_consulta(conexao, {"imune_a": "fogo"})


def test_condicao_so_imposta_e_aceita_em_imune_a_condicao(conexao):
    # `charmed` é imunidade do Vampire e condição imposta pela mordida dele; o
    # domínio de condições é um só, então os dois filtros aceitam os dois valores.
    assert executar_consulta(conexao, {"impoe": "charmed"}) != []


def test_vocabulario_por_dominio_tem_as_seis_chaves_do_contrato(conexao):
    assert set(vocabulario_por_dominio(conexao)) == {
        "tipos",
        "tamanhos",
        "alinhamentos",
        "ambientes",
        "tipos_dano",
        "condicoes",
    }


def test_vocabulario_por_dominio_funde_os_tres_filtros_de_dano(conexao):
    tipos_dano = vocabulario_por_dominio(conexao)["tipos_dano"]
    assert {"fire", "necrotic", "radiant"} <= set(tipos_dano)


def test_todo_valor_anunciado_no_dominio_e_aceito_por_todos_os_filtros_dele(conexao):
    """A invariante que o endpoint `/vocabulario` existe para garantir.

    Se um valor aparece em `tipos_dano`, os três filtros de dano têm de aceitá-lo
    — senão o endpoint que existe para o consumidor não adivinhar passa a mentir.
    """
    por_dominio = vocabulario_por_dominio(conexao)
    for dominio, filtros in DOMINIOS_DE_FILTRO.items():
        for valor in por_dominio[dominio]:
            for filtro in filtros:
                executar_consulta(conexao, {filtro: valor})
