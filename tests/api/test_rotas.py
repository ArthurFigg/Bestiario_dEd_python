"""Testes de comportamento da API, via `TestClient` contra a fixture de teste.

Cobre os critérios verificáveis da Spec 8: prefixo aplicado uma vez, busca por
trecho x busca exata, ordenação, omissão de sentido/deslocamento ausente,
erros em RFC 7807 e o 503 de base não sincronizada.
"""

from urllib.parse import quote


def _url(nome):
    return f"/api/v1/monstros/{quote(nome)}"


# --- prefixo e /docs ---------------------------------------------------------


def test_prefixo_e_aplicado_uma_unica_vez(cliente_api):
    resposta = cliente_api.get("/api/v1/monstros")
    assert resposta.status_code == 200


def test_docs_responde_200(cliente_api):
    assert cliente_api.get("/docs").status_code == 200


def test_nenhuma_rota_de_html_aparece_no_esquema(cliente_api):
    esquema = cliente_api.get("/openapi.json").json()
    assert all(caminho.startswith("/api/v1") for caminho in esquema["paths"])


# --- /monstros: envelope, busca, ordenação -----------------------------------


def test_listar_monstros_devolve_envelope_de_paginacao(cliente_api):
    corpo = cliente_api.get("/api/v1/monstros").json()
    assert {"total", "limite", "deslocamento", "itens"} <= set(corpo)


def test_busca_por_trecho_devolve_mais_de_um_monstro(cliente_api):
    corpo = cliente_api.get("/api/v1/monstros?nome=drag").json()
    assert len(corpo["itens"]) > 1


def test_busca_exata_no_caminho_devolve_um_monstro_so(cliente_api):
    resposta = cliente_api.get(_url("Goblin"))
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Goblin"


def test_ordenar_por_pontos_vida_decrescente_traz_o_maior_primeiro(cliente_api):
    corpo = cliente_api.get(
        "/api/v1/monstros?ordenar_por=pontos_vida&sentido=decrescente"
    ).json()
    assert corpo["itens"][0]["nome"] == "Adult Red Dragon"


def test_ordenar_por_fora_do_enum_nao_quebra(cliente_api):
    resposta = cliente_api.get("/api/v1/monstros?ordenar_por=cor")
    assert resposta.status_code == 200


def test_desafio_invertido_devolve_200_com_itens_vazio(cliente_api):
    corpo = cliente_api.get("/api/v1/monstros?desafio_min=20&desafio_max=5").json()
    assert corpo["itens"] == []


# --- ficha completa ------------------------------------------------------


def test_ficha_completa_traz_acoes_com_ataques_aninhados(cliente_api):
    corpo = cliente_api.get(_url("Adult Red Dragon")).json()
    mordida = [acao for acao in corpo["acoes"] if acao["nome"] == "Bite"][0]
    assert mordida["ataques"][0]["nome"] == "Bite attack"


def test_ficha_omite_sentido_ausente(cliente_api):
    corpo = cliente_api.get(_url("Goblin")).json()
    assert "visao_cega" not in corpo["sentidos"]


def test_ficha_omite_deslocamento_zero_ou_nulo(cliente_api):
    corpo = cliente_api.get(_url("Adult Red Dragon")).json()
    assert "natacao" not in corpo["deslocamento"]
    assert "escalada" not in corpo["deslocamento"]


def test_ficha_traz_so_os_testes_de_resistencia_proficientes(cliente_api):
    corpo = cliente_api.get(_url("Adult Red Dragon")).json()
    atributos = [t["atributo"] for t in corpo["testes_de_resistencia"]]
    # Os quatro do SRD, e não os seis: só proficiente aparece.
    assert atributos == ["destreza", "constituicao", "sabedoria", "carisma"]


def test_nome_inexistente_responde_404_em_problem_json(cliente_api):
    resposta = cliente_api.get(_url("Tarrasque"))
    assert resposta.status_code == 404
    assert resposta.headers["content-type"] == "application/problem+json"


# --- /ataques ------------------------------------------------------------


def test_ataques_ignora_sentido_e_ordena_sempre_decrescente(cliente_api):
    resposta = cliente_api.get(
        "/api/v1/ataques?ordenar_por=dano_medio&sentido=crescente"
    )
    itens = resposta.json()["itens"]
    danos = [item["dano_medio"] for item in itens]
    assert danos == sorted(danos, reverse=True)


def test_ataque_traz_nome_do_monstro_e_da_acao(cliente_api):
    corpo = cliente_api.get("/api/v1/ataques").json()
    item = corpo["itens"][0]
    assert item["monstro"] and item["acao"] and item["nome"]


# --- /comparacoes e /resumo -----------------------------------------------


def test_comparacoes_sem_por_responde_422(cliente_api):
    assert cliente_api.get("/api/v1/comparacoes").status_code == 422


def test_comparacoes_com_por_responde_200(cliente_api):
    resposta = cliente_api.get("/api/v1/comparacoes?por=tipo")
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)


def test_resumo_responde_200_com_uma_linha(cliente_api):
    corpo = cliente_api.get("/api/v1/resumo").json()
    assert "monstros" in corpo


# --- /vocabulario ----------------------------------------------------------


def test_vocabulario_tem_exatamente_as_seis_chaves_do_contrato(cliente_api):
    corpo = cliente_api.get("/api/v1/vocabulario").json()
    assert set(corpo) == {
        "tipos",
        "tamanhos",
        "alinhamentos",
        "ambientes",
        "tipos_dano",
        "condicoes",
    }


def test_vocabulario_nao_carrega_contagem(cliente_api):
    corpo = cliente_api.get("/api/v1/vocabulario").json()
    assert all(isinstance(valor, str) for valor in corpo["tipos"])


# --- erros de filtro e de validação ----------------------------------------


def test_valor_fora_do_vocabulario_responde_422_citando_o_parametro(cliente_api):
    resposta = cliente_api.get("/api/v1/monstros?resiste_a=fogo")
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert "resiste_a" in detalhe and "/vocabulario" in detalhe


def test_limite_fora_do_intervalo_responde_422_em_rfc7807(cliente_api):
    resposta = cliente_api.get("/api/v1/monstros?limite=500")
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert resposta.headers["content-type"] == "application/problem+json"
    assert {"type", "title", "status"} <= set(corpo)


# --- banco não sincronizado -------------------------------------------------


def test_banco_vazio_responde_503_citando_a_sincronizacao(cliente_api_banco_vazio):
    resposta = cliente_api_banco_vazio.get("/api/v1/monstros")
    assert resposta.status_code == 503
    assert "sincroniz" in resposta.json()["detail"].lower()


def test_banco_vazio_responde_503_em_qualquer_endpoint(cliente_api_banco_vazio):
    assert cliente_api_banco_vazio.get("/api/v1/vocabulario").status_code == 503


# --- filtros uniformes -------------------------------------------------------


def test_mesmo_filtro_funciona_nos_quatro_endpoints_filtraveis(cliente_api):
    assert cliente_api.get("/api/v1/monstros?tipo=dragon").status_code == 200
    assert cliente_api.get("/api/v1/ataques?tipo=dragon").status_code == 200
    assert (
        cliente_api.get("/api/v1/comparacoes?por=tipo&tipo=dragon").status_code == 200
    )
    assert cliente_api.get("/api/v1/resumo?tipo=dragon").status_code == 200


# --- nenhuma rota escreve SQL ------------------------------------------------


def test_nenhum_modulo_da_api_escreve_sql_diretamente():
    """Procura **execução** de SQL, não a palavra `sqlite3`.

    Proibir o nome do módulo custaria o type hint `sqlite3.Connection` nos
    parâmetros de conexão, que é documentação e não execução — o teste passaria
    a piorar o código que deveria proteger.
    """
    from pathlib import Path

    proibidos = (".execute(", ".executemany(", "SELECT ", "read_sql", ".cursor(")
    diretorio_api = Path(__file__).resolve().parents[2] / "api"
    for arquivo in diretorio_api.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in texto, f"{arquivo.name} contém {termo!r}"


def test_api_nao_abre_conexao_por_fora_da_dependencia():
    """`sqlite3.connect` em `api/` significaria conexão fora do ponto de injeção.

    A dependência do FastAPI é o único caminho — é ela que o teste substitui, e
    é ela que a Spec 9a reaproveita em `web/app.py`.
    """
    from pathlib import Path

    diretorio_api = Path(__file__).resolve().parents[2] / "api"
    for arquivo in diretorio_api.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        assert "sqlite3.connect" not in texto, f"{arquivo.name} abre conexão própria"


# --- correções da revisão de código -------------------------------------------


def test_banco_ausente_responde_503_em_rfc7807(tmp_path, monkeypatch):
    """Clone novo, sem `bestiario_combate.db`, não pode devolver 500 em texto cru.

    O arquivo está fora do git, então este é o caminho mais provável de todos.
    """
    from fastapi.testclient import TestClient

    from api import rotas
    from api.app import app

    monkeypatch.setattr(rotas, "CAMINHO_BANCO_PADRAO", str(tmp_path / "nao_existe.db"))
    with TestClient(app, raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/api/v1/monstros")
    assert resposta.status_code == 503


def test_banco_ausente_responde_com_media_type_de_problema(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from api import rotas
    from api.app import app

    monkeypatch.setattr(rotas, "CAMINHO_BANCO_PADRAO", str(tmp_path / "nao_existe.db"))
    with TestClient(app, raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/api/v1/monstros")
    assert resposta.headers["content-type"].startswith("application/problem+json")


def test_type_do_problema_nao_tem_acento(cliente_api):
    """`type` é `uri-reference` no contrato — acento sem percent-encoding invalida."""
    corpo = cliente_api.get("/api/v1/monstros?resiste_a=fogo").json()
    assert corpo["type"].isascii()


def test_sentido_invalido_e_rejeitado_em_vez_de_virar_crescente(cliente_api):
    """Diferente de `ordenar_por`, o contrato não dá tolerância a `sentido`."""
    assert cliente_api.get("/api/v1/monstros?sentido=qualquercoisa").status_code == 422


def test_esquema_gerado_carrega_o_enum_de_ordenar_por(cliente_api):
    """Tolerante na validação, mas documentado no /docs — o contrato quer os dois."""
    esquema = cliente_api.get("/openapi.json").json()
    parametros = esquema["paths"]["/api/v1/monstros"]["get"]["parameters"]
    ordenar = [p for p in parametros if p["name"] == "ordenar_por"][0]
    assert "dano_medio" in ordenar["schema"]["enum"]


def test_valor_anunciado_no_vocabulario_e_aceito_pelo_filtro_correspondente(
    cliente_api,
):
    """O endpoint existe para o consumidor não adivinhar — então não pode mentir."""
    vocabulario = cliente_api.get("/api/v1/vocabulario").json()
    for tipo_dano in vocabulario["tipos_dano"]:
        for filtro in ("imune_a", "resiste_a", "vulneravel_a"):
            resposta = cliente_api.get(f"/api/v1/monstros?{filtro}={tipo_dano}")
            assert resposta.status_code == 200, f"{filtro}={tipo_dano}"


def test_valor_de_condicao_anunciado_e_aceito_nos_dois_filtros(cliente_api):
    vocabulario = cliente_api.get("/api/v1/vocabulario").json()
    for condicao in vocabulario["condicoes"]:
        for filtro in ("imune_a_condicao", "impoe"):
            resposta = cliente_api.get(f"/api/v1/monstros?{filtro}={condicao}")
            assert resposta.status_code == 200, f"{filtro}={condicao}"
