"""Testes do site (Spec 9a), via `TestClient` contra a fixture compartilhada.

Cobre os critérios verificáveis da spec: redirecionamento da raiz, envelope da
API incluída sob `web.app:app`, `/docs`, tratadores de erro replicados,
ordenação e coluna fora da lista branca na aba "Todos os monstros", o modo de
exibição viajando entre abas, o rodapé com link da API e a página explicativa
de banco vazio.
"""

from pathlib import Path


def test_raiz_redireciona_para_relatorios(cliente_web):
    resposta = cliente_web.get("/", follow_redirects=False)
    assert resposta.status_code in (302, 307)
    assert resposta.headers["location"] == "/relatorios"


def test_monstros_responde_200_com_uma_linha_por_monstro_da_fixture(cliente_web):
    resposta = cliente_web.get("/monstros")
    assert resposta.status_code == 200
    # Um link "pesquisar" por monstro — mais preciso que contar <tr>, que
    # também aparece no cabeçalho da tabela.
    assert resposta.text.count('href="/pesquisar?fixados=') == 4


def test_api_incluida_responde_200_com_prefixo_aplicado_uma_vez(cliente_web):
    resposta = cliente_web.get("/api/v1/monstros")
    assert resposta.status_code == 200


def test_docs_responde_200_em_web_app(cliente_web):
    assert cliente_web.get("/docs").status_code == 200


def test_tratadores_de_erro_da_api_valem_tambem_no_site(cliente_web):
    resposta = cliente_web.get("/api/v1/monstros?resiste_a=fogo")
    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == "application/problem+json"


def test_ordenar_por_desafio_decrescente_traz_o_maior_primeiro(cliente_web):
    resposta = cliente_web.get("/monstros?ordenar_por=desafio&sentido=decrescente")
    texto = resposta.text
    assert texto.index("Adult Red Dragon") < texto.index("Goblin")


def test_ordenar_por_fora_da_lista_branca_cai_no_padrao_por_nome(cliente_web):
    resposta = cliente_web.get("/monstros?ordenar_por=cor")
    assert resposta.status_code == 200
    texto = resposta.text
    # Ordem alfabética padrão: "Adult Blue Dragon" vem antes de "Adult Red Dragon".
    assert texto.index("Adult Blue Dragon") < texto.index("Adult Red Dragon")


def test_modo_completa_viaja_para_os_links_das_outras_abas(cliente_web):
    resposta = cliente_web.get("/monstros?modo=completa")
    assert 'href="/relatorios?modo=completa"' in resposta.text
    assert 'href="/pesquisar?modo=completa"' in resposta.text


def test_rodape_traz_link_para_docs(cliente_web):
    resposta = cliente_web.get("/monstros")
    assert 'href="/docs"' in resposta.text


def test_banco_vazio_mostra_pagina_explicativa_em_vez_de_tabela_vazia(
    cliente_web_banco_vazio,
):
    resposta = cliente_web_banco_vazio.get("/monstros")
    assert resposta.status_code == 200
    assert "sincroniz" in resposta.text.lower()
    assert "<table>" not in resposta.text


def test_clicar_no_nome_leva_para_pesquisar_com_o_nome_fixado(cliente_web):
    resposta = cliente_web.get("/monstros")
    assert "/pesquisar?fixados=Goblin" in resposta.text


def test_relatorios_e_pesquisar_respondem_200_como_destino_minimo(cliente_web):
    assert cliente_web.get("/relatorios").status_code == 200
    assert cliente_web.get("/pesquisar").status_code == 200


def test_nenhum_modulo_do_site_escreve_sql_diretamente():
    """Mira **execução** de SQL, não a palavra `sqlite3` — o type hint
    `sqlite3.Connection` em `web/rotas.py` é documentação, não violação.
    """
    proibidos = (".execute(", ".executemany(", "SELECT ", "read_sql", ".cursor(")
    diretorio_web = Path(__file__).resolve().parents[2] / "web"
    for arquivo in diretorio_web.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        for termo in proibidos:
            assert termo not in texto, f"{arquivo.name} contém {termo!r}"


def test_web_nao_abre_conexao_por_fora_da_dependencia():
    diretorio_web = Path(__file__).resolve().parents[2] / "web"
    for arquivo in diretorio_web.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        assert "sqlite3.connect" not in texto, f"{arquivo.name} abre conexão própria"


def test_estilo_css_nao_referencia_recurso_externo():
    caminho = Path(__file__).resolve().parents[2] / "web" / "static" / "estilo.css"
    texto = caminho.read_text(encoding="utf-8")
    assert "http://" not in texto
    assert "https://" not in texto


def test_estilo_css_embute_as_duas_fontes_em_base64():
    caminho = Path(__file__).resolve().parents[2] / "web" / "static" / "estilo.css"
    texto = caminho.read_text(encoding="utf-8")
    assert "Cinzel" in texto
    assert "EB Garamond" in texto
    assert texto.count("src: url(data:font/woff2;base64,") >= 2


# --- base ausente: página humana, não JSON -----------------------------------


def _cliente_sem_banco(tmp_path, monkeypatch):
    """Simula clone novo: o `.db` está no `.gitignore`, então não existe."""
    from fastapi.testclient import TestClient

    from api import rotas as rotas_api
    from web.app import app

    monkeypatch.setattr(
        rotas_api, "CAMINHO_BANCO_PADRAO", str(tmp_path / "nao_existe.db")
    )
    return TestClient(app, raise_server_exceptions=False)


def test_site_com_banco_ausente_responde_html_e_nao_json(tmp_path, monkeypatch):
    cliente = _cliente_sem_banco(tmp_path, monkeypatch)
    resposta = cliente.get("/monstros")
    assert resposta.headers["content-type"].startswith("text/html")


def test_site_com_banco_ausente_responde_200_como_o_banco_vazio(tmp_path, monkeypatch):
    """Mesma página, mesmo código: o corte é por superfície, não por causa."""
    cliente = _cliente_sem_banco(tmp_path, monkeypatch)
    assert cliente.get("/monstros").status_code == 200


def test_pagina_de_base_ausente_indica_a_opcao_4_do_menu(tmp_path, monkeypatch):
    cliente = _cliente_sem_banco(tmp_path, monkeypatch)
    assert "opção 4" in cliente.get("/monstros").text


def test_pagina_de_base_ausente_mantem_a_moldura_com_as_abas(tmp_path, monkeypatch):
    # Erro não pode devolver página órfã: o usuário precisa conseguir navegar.
    cliente = _cliente_sem_banco(tmp_path, monkeypatch)
    corpo = cliente.get("/monstros").text
    assert "Todos os monstros" in corpo and "Relatórios" in corpo


def test_api_do_site_com_banco_ausente_continua_em_rfc7807(tmp_path, monkeypatch):
    """Sob `/api/`, quem chama é programa — recebe JSON mesmo no site."""
    cliente = _cliente_sem_banco(tmp_path, monkeypatch)
    resposta = cliente.get("/api/v1/monstros")
    assert resposta.status_code == 503
    assert resposta.headers["content-type"].startswith("application/problem+json")


def test_docs_do_site_anuncia_o_mesmo_info_da_api(cliente_web):
    """O `/docs` que o rodapé manda abrir é o do site, mas o teste de contrato lê
    a aplicação da API — sem esta trava, os dois divergiriam em silêncio."""
    from api.app import app as app_api

    esquema_site = cliente_web.get("/openapi.json").json()
    assert esquema_site["info"] == app_api.openapi()["info"]


def test_schema_defasado_nao_derruba_o_site_com_500(tmp_path, monkeypatch):
    """Banco que abre mas não tem as tabelas: a armadilha registrada no CLAUDE.md.

    Antes caía dentro de `executar_consulta` e virava traceback na tela.
    """
    import sqlite3

    from fastapi.testclient import TestClient

    from api import rotas as rotas_api
    from web.app import app

    caminho = tmp_path / "defasado.db"
    sqlite3.connect(caminho).close()  # arquivo válido, sem nenhuma tabela
    monkeypatch.setattr(rotas_api, "CAMINHO_BANCO_PADRAO", str(caminho))
    with TestClient(app, raise_server_exceptions=False) as cliente:
        resposta = cliente.get("/monstros")
    assert resposta.status_code == 200
    assert "sincroniz" in resposta.text.lower()
