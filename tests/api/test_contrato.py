"""Compara `openapi.yaml` (o contrato) com o OpenAPI gerado por `api.app:app`.

Teste **contido**, não estrito: a lista de caminhos é exigida por igualdade
exata (endpoint criado sem documentar quebra o teste); parâmetros, status
codes e campos de resposta são exigidos por subconjunto — o gerado pode ter
mais, nunca menos. Igualdade estrita no arquivo inteiro quebraria por ordem
de chave e por campo que o FastAPI acrescenta sozinho, e um teste que dá
alarme falso acaba sendo apagado — decisão registrada na spec.

`servers[0].url` do contrato é o prefixo: o contrato declara os caminhos sem
`/api/v1`, e é isso que esta comparação normaliza antes de confrontar com o
gerado.
"""

from pathlib import Path

import pytest
import yaml

from api.app import app

CAMINHO_CONTRATO = Path(__file__).resolve().parents[2] / "openapi.yaml"
CONTRATO = yaml.safe_load(CAMINHO_CONTRATO.read_text(encoding="utf-8"))
PREFIXO = CONTRATO["servers"][0]["url"]

_OPERACOES = [
    (caminho, metodo)
    for caminho, metodos in CONTRATO["paths"].items()
    for metodo in metodos
]


@pytest.fixture(scope="module")
def gerado():
    return app.openapi()


def _resolver_ref(ref, documento):
    alvo = documento
    for parte in ref.lstrip("#/").split("/"):
        alvo = alvo[parte]
    return alvo


def _resolver_schema(schema, documento):
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        return _resolver_schema(_resolver_ref(schema["$ref"], documento), documento)
    return schema


def _propriedades(schema, documento):
    schema = _resolver_schema(schema, documento)
    props = {}
    for sub in schema.get("allOf", []):
        props.update(_propriedades(sub, documento))
    props.update(schema.get("properties", {}))
    return props


def _verificar_schema(rotulo, esperado, doc_esperado, obtido, doc_obtido, caminho=""):
    esperado = _resolver_schema(esperado, doc_esperado)
    obtido = _resolver_schema(obtido, doc_obtido)

    if "items" in esperado:
        _verificar_schema(
            rotulo,
            esperado["items"],
            doc_esperado,
            obtido.get("items", {}),
            doc_obtido,
            caminho + "[]",
        )
        return

    props_esperadas = _propriedades(esperado, doc_esperado)
    if not props_esperadas:
        return
    props_obtidas = _propriedades(obtido, doc_obtido)
    faltando = set(props_esperadas) - set(props_obtidas)
    assert not faltando, f"{rotulo}{caminho}: campo(s) {faltando} ausente(s) no gerado"
    for campo, sub_esperado in props_esperadas.items():
        _verificar_schema(
            rotulo,
            sub_esperado,
            doc_esperado,
            props_obtidas[campo],
            doc_obtido,
            f"{caminho}.{campo}",
        )


def _nomes_de_parametros(operacao, documento):
    nomes = set()
    for parametro in operacao.get("parameters", []):
        if "$ref" in parametro:
            parametro = _resolver_ref(parametro["$ref"], documento)
        nomes.add(parametro["name"])
    return nomes


def _esquema_da_resposta(resposta):
    conteudo = (resposta or {}).get("content", {})
    for media_type in ("application/json", "application/problem+json"):
        if media_type in conteudo:
            return conteudo[media_type]["schema"]
    return None


def test_conjunto_de_caminhos_bate_exatamente_com_o_contrato(gerado):
    caminhos_contrato = {PREFIXO + caminho for caminho in CONTRATO["paths"]}
    assert caminhos_contrato == set(gerado["paths"])


def test_prefixo_aplicado_uma_unica_vez(gerado):
    assert "/api/v1/api/v1" not in "".join(gerado["paths"])


@pytest.mark.parametrize("caminho,metodo", _OPERACOES)
def test_parametros_prometidos_existem_no_gerado(gerado, caminho, metodo):
    operacao = CONTRATO["paths"][caminho][metodo]
    operacao_gerada = gerado["paths"][PREFIXO + caminho][metodo]
    esperados = _nomes_de_parametros(operacao, CONTRATO)
    obtidos = _nomes_de_parametros(operacao_gerada, gerado)
    assert esperados <= obtidos


@pytest.mark.parametrize("caminho,metodo", _OPERACOES)
def test_status_codes_prometidos_existem_no_gerado(gerado, caminho, metodo):
    operacao = CONTRATO["paths"][caminho][metodo]
    operacao_gerada = gerado["paths"][PREFIXO + caminho][metodo]
    esperados = {str(status) for status in operacao["responses"]}
    obtidos = {str(status) for status in operacao_gerada["responses"]}
    assert esperados <= obtidos


@pytest.mark.parametrize("caminho,metodo", _OPERACOES)
def test_campos_de_resposta_prometidos_existem_no_gerado(gerado, caminho, metodo):
    operacao = CONTRATO["paths"][caminho][metodo]
    operacao_gerada = gerado["paths"][PREFIXO + caminho][metodo]
    for status, resposta in operacao["responses"].items():
        resposta_gerada = operacao_gerada["responses"].get(str(status))
        if resposta_gerada is None:
            continue  # já reportado por test_status_codes_prometidos_existem_no_gerado
        esquema_esperado = _esquema_da_resposta(resposta)
        if esquema_esperado is None:
            continue
        esquema_obtido = _esquema_da_resposta(resposta_gerada)
        _verificar_schema(
            f"{metodo.upper()} {caminho} [{status}]",
            esquema_esperado,
            CONTRATO,
            esquema_obtido,
            gerado,
        )
