import requests

from bestiario import cliente_api
from bestiario.cliente_api import buscar_monstro, filtrar_monstros


class _RespostaFake:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_buscar_monstro_devolve_json_no_status_200(monkeypatch):
    monkeypatch.setattr(
        cliente_api.requests, "get",
        lambda *a, **k: _RespostaFake(200, {"name": "Goblin"}),
    )
    assert buscar_monstro("goblin") == {"name": "Goblin"}


def test_buscar_monstro_devolve_none_em_status_nao_200(monkeypatch):
    monkeypatch.setattr(
        cliente_api.requests, "get",
        lambda *a, **k: _RespostaFake(404, {}),
    )
    assert buscar_monstro("inexistente") is None


def test_buscar_monstro_trata_erro_de_conexao(monkeypatch):
    def _lanca(*a, **k):
        raise requests.exceptions.RequestException

    monkeypatch.setattr(cliente_api.requests, "get", _lanca)
    assert buscar_monstro("goblin") is None


def test_filtrar_monstros_percorre_paginas_e_filtra_por_chave(monkeypatch):
    paginas = {
        "https://api.open5e.com/v1/monsters/": _RespostaFake(200, {
            "results": [{"name": "Goblin", "type": "humanoid"},
                        {"name": "Zombie", "type": "undead"}],
            "next": "pagina2",
        }),
        "pagina2": _RespostaFake(200, {
            "results": [{"name": "Skeleton", "type": "undead"}],
            "next": None,
        }),
    }
    monkeypatch.setattr(cliente_api.requests, "get", lambda url, **k: paginas[url])

    resultado = filtrar_monstros("type", "undead")
    nomes = {m["name"] for m in resultado}
    assert nomes == {"Zombie", "Skeleton"}
