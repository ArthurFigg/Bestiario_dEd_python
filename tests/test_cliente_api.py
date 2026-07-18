import requests

from bestiario import cliente_api
from bestiario.cliente_api import (
    DOCUMENTO_SRD,
    buscar_monstro,
    filtrar_monstros,
    sincronizar_base_completa,
)


class _Resposta:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _GetFake:
    """Substitui requests.get: devolve as respostas na ordem e registra as chamadas."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, **kwargs):
        self.chamadas.append((url, kwargs))
        return self.respostas.pop(0)


def _instalar_get(monkeypatch, respostas):
    fake = _GetFake(respostas)
    monkeypatch.setattr(cliente_api.requests, "get", fake)
    return fake


# --- buscar_monstro ---


def test_buscar_monstro_devolve_dict_do_srd_no_status_200(monkeypatch):
    _instalar_get(monkeypatch, [_Resposta(200, {"results": [{"key": "srd_goblin"}]})])
    assert buscar_monstro("goblin")["key"] == "srd_goblin"


def test_buscar_monstro_sem_correspondencia_no_srd_devolve_none(monkeypatch):
    _instalar_get(monkeypatch, [_Resposta(200, {"results": []})])
    assert buscar_monstro("inexistente") is None


def test_buscar_monstro_devolve_none_em_status_404(monkeypatch):
    _instalar_get(monkeypatch, [_Resposta(404, {})])
    assert buscar_monstro("goblin") is None


def test_buscar_monstro_trata_erro_de_conexao(monkeypatch):
    def _lanca(*a, **k):
        raise requests.exceptions.RequestException

    monkeypatch.setattr(cliente_api.requests, "get", _lanca)
    assert buscar_monstro("goblin") is None


def test_buscar_monstro_restringe_ao_documento_srd_2014(monkeypatch):
    fake = _instalar_get(monkeypatch, [_Resposta(200, {"results": [{"key": "x"}]})])
    buscar_monstro("goblin")
    assert fake.chamadas[0][1]["params"]["document__key"] == DOCUMENTO_SRD


# --- filtrar_monstros ---


def test_filtrar_monstros_percorre_multiplas_paginas(monkeypatch):
    _instalar_get(
        monkeypatch,
        [
            _Resposta(
                200, {"results": [{"key": "a"}, {"key": "b"}], "next": "pagina2"}
            ),
            _Resposta(200, {"results": [{"key": "c"}], "next": None}),
        ],
    )
    chaves = [m["key"] for m in filtrar_monstros("type", "humanoid")]
    assert chaves == ["a", "b", "c"]


def test_filtrar_monstros_restringe_ao_documento_srd_2014(monkeypatch):
    fake = _instalar_get(monkeypatch, [_Resposta(200, {"results": [], "next": None})])
    filtrar_monstros("challenge_rating", 17)
    assert fake.chamadas[0][1]["params"]["document__key"] == DOCUMENTO_SRD


def test_filtrar_monstros_erro_de_conexao_devolve_lista_vazia(monkeypatch):
    def _lanca(*a, **k):
        raise requests.exceptions.RequestException

    monkeypatch.setattr(cliente_api.requests, "get", _lanca)
    assert filtrar_monstros("type", "humanoid") == []


# --- sincronizar_base_completa ---


def test_sincronizar_registra_criaturas_de_todas_as_paginas(monkeypatch):
    _instalar_get(
        monkeypatch,
        [
            _Resposta(
                200, {"results": [{"key": "a"}, {"key": "b"}], "next": "pagina2"}
            ),
            _Resposta(200, {"results": [{"key": "c"}], "next": None}),
        ],
    )
    registradas = []
    monkeypatch.setattr(
        cliente_api,
        "registrar_monstro",
        lambda conexao, criatura: registradas.append(criatura["key"]),
    )
    sincronizar_base_completa(conexao=object())
    assert registradas == ["a", "b", "c"]


def test_sincronizar_restringe_ao_documento_srd_2014(monkeypatch):
    fake = _instalar_get(monkeypatch, [_Resposta(200, {"results": [], "next": None})])
    monkeypatch.setattr(cliente_api, "registrar_monstro", lambda c, m: None)
    sincronizar_base_completa(conexao=object())
    assert fake.chamadas[0][1]["params"]["document__key"] == DOCUMENTO_SRD


def test_sincronizar_erro_de_conexao_nao_propaga_excecao(monkeypatch):
    def _lanca(*a, **k):
        raise requests.exceptions.RequestException

    monkeypatch.setattr(cliente_api.requests, "get", _lanca)
    registradas = []
    monkeypatch.setattr(
        cliente_api,
        "registrar_monstro",
        lambda conexao, criatura: registradas.append(criatura),
    )
    sincronizar_base_completa(conexao=object())
    assert registradas == []
