"""Orquestração dos filtros do menu: SQLite primeiro, API v2 como fallback.

A lógica de fallback vive em `main.py` (a UI orquestra; `banco.py` só lê e
`cliente_api.py` só busca), então é aqui que ela é testada — mockando o cliente v2
para provar quando ele é ou não chamado.
"""

import pytest

import main
from bestiario.banco import criar_base_de_dados, registrar_monstro


def _dragao():
    return {
        "name": "Adult Red Dragon",
        "size": {"key": "huge"},
        "type": {"key": "dragon"},
        "armor_class": 19,
        "hit_points": 256,
        "challenge_rating": 17.0,
    }


def _falha_se_chamado(*args, **kwargs):
    raise AssertionError("o fallback da API não deveria ter sido chamado")


def _api_devolve_goblin(chave, valor):
    return [{"name": "Goblin", "type": {"key": "humanoid"}, "challenge_rating": 0.25}]


@pytest.fixture
def conexao(tmp_path):
    con = criar_base_de_dados(str(tmp_path / "teste.db"))
    yield con
    con.close()


def test_filtro_por_tipo_usa_local_sem_chamar_api(conexao, monkeypatch):
    registrar_monstro(conexao, _dragao())
    monkeypatch.setattr(main, "filtrar_monstros", _falha_se_chamado)
    resultados = main.consultar_tipo(conexao, "dragon")
    assert [r["origem"] for r in resultados] == ["local"]


def test_filtro_por_tipo_cai_para_api_quando_nao_ha_local(conexao, monkeypatch):
    monkeypatch.setattr(main, "filtrar_monstros", _api_devolve_goblin)
    resultados = main.consultar_tipo(conexao, "humanoid")
    assert resultados[0]["origem"] == "API"


def test_fallback_repassa_chave_e_valor_para_o_cliente_v2(conexao, monkeypatch):
    registros = {}

    def _captura(chave, valor):
        registros["chamada"] = (chave, valor)
        return []

    monkeypatch.setattr(main, "filtrar_monstros", _captura)
    main.consultar_tipo(conexao, "humanoid")
    assert registros["chamada"] == ("type", "humanoid")


def test_linha_de_resultado_local_recebe_rotulo_local():
    linha = main._formatar_linha_filtro(
        {"nome": "Goblin", "tipo": "humanoid", "cr": 0.25, "origem": "local"}
    )
    assert linha.startswith("[local]")


def test_linha_de_resultado_api_recebe_rotulo_api():
    linha = main._formatar_linha_filtro(
        {"nome": "Goblin", "tipo": "humanoid", "cr": 0.25, "origem": "API"}
    )
    assert linha.startswith("[API]")


def test_filtro_cr_invalido_nao_quebra_e_segue_para_o_fallback(conexao, monkeypatch):
    monkeypatch.setattr(main, "filtrar_monstros", lambda chave, valor: [])
    resultados = main.consultar_cr(conexao, "abc")
    assert resultados == []
