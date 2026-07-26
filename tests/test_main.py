"""Orquestração dos filtros do menu: núcleo primeiro, API v2 como fallback.

A lógica de fallback vive em `main.py` (a UI orquestra; `consultas.py` só lê e
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
        {"nome": "Goblin", "tipo": "humanoid", "desafio": 0.25, "origem": "local"}
    )
    assert linha.startswith("[local]")


def test_linha_de_resultado_api_recebe_rotulo_api():
    linha = main._formatar_linha_filtro(
        {"nome": "Goblin", "tipo": "humanoid", "desafio": 0.25, "origem": "API"}
    )
    assert linha.startswith("[API]")


def test_filtro_cr_invalido_nao_quebra_e_segue_para_o_fallback(conexao, monkeypatch):
    monkeypatch.setattr(main, "filtrar_monstros", lambda chave, valor: [])
    resultados = main.consultar_desafio(conexao, "abc")
    assert resultados == []


def test_desafio_usa_local_sem_chamar_api(conexao, monkeypatch):
    registrar_monstro(conexao, _dragao())
    monkeypatch.setattr(main, "filtrar_monstros", _falha_se_chamado)
    resultados = main.consultar_desafio(conexao, "17")
    assert [r["origem"] for r in resultados] == ["local"]


def test_fallback_de_desafio_repassa_o_texto_digitado_e_nao_o_float(
    conexao, monkeypatch
):
    # `challenge_rating=17` acha na Open5e; `17.0` volta vazio sem erro nenhum.
    # A conversão para número serve só ao núcleo, cuja coluna é REAL.
    registros = {}

    def _captura(chave, valor):
        registros["chamada"] = (chave, valor)
        return []

    monkeypatch.setattr(main, "filtrar_monstros", _captura)
    main.consultar_desafio(conexao, "17")
    assert registros["chamada"] == ("challenge_rating", "17")


def test_tipo_fora_do_vocabulario_nao_vaza_excecao_e_cai_no_fallback(
    conexao, monkeypatch
):
    # Banco vazio: qualquer tipo está fora do vocabulário local e o núcleo levanta
    # ValorDeFiltroInvalido. O menu captura — o tipo pode existir na API.
    monkeypatch.setattr(main, "filtrar_monstros", _api_devolve_goblin)
    resultados = main.consultar_tipo(conexao, "dragao")
    assert resultados[0]["origem"] == "API"


def test_linha_de_resultado_usa_rotulo_desafio_e_nao_cr():
    linha = main._formatar_linha_filtro(
        {"nome": "Goblin", "tipo": "humanoid", "desafio": 0.25, "origem": "local"}
    )
    assert "Desafio:" in linha and "CR:" not in linha


def test_projecao_da_api_extrai_a_chave_do_tipo_objeto():
    # Na v2 `type` é objeto. A opção 1 do menu imprimia o dict cru na tela até a
    # Spec 7c passar a projetar antes de exibir.
    dados = main._projetar_api(_dragao())
    assert dados["tipo"] == "dragon"


def test_tipo_vazio_nao_devolve_o_bestiario_inteiro(conexao, monkeypatch):
    # O núcleo trata filtro vazio como "sem filtro" e devolveria todos. Quem só
    # apertou Enter não pediu isso, e a API nem deve ser consultada.
    registrar_monstro(conexao, _dragao())
    monkeypatch.setattr(main, "filtrar_monstros", _falha_se_chamado)
    assert main.consultar_tipo(conexao, "") == []


def test_desafio_vazio_nao_consulta_a_api(conexao, monkeypatch):
    # A Open5e ignora `challenge_rating=` vazio e devolve o SRD inteiro.
    monkeypatch.setattr(main, "filtrar_monstros", _falha_se_chamado)
    assert main.consultar_desafio(conexao, "   ") == []
