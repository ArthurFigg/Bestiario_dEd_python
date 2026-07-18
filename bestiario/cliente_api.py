"""Comunicação com a API Open5e (v2), fixada no documento SRD 2014.

Retorna os dicts estruturados da v2 sem transformar em entidades: persistência é
a Spec 3, extração de ações/ataques/efeitos são as Specs 4-5. O escopo SRD 2014
(`document__key=srd-2014`, ~325 criaturas) elimina duplicatas de outras fontes na
origem, mantendo `nome` como chave.
"""

import requests

from bestiario.banco import registrar_monstro

URL_BASE = "https://api.open5e.com/v2/creatures/"
DOCUMENTO_SRD = "srd-2014"


def buscar_monstro(nome):
    """Retorna o dict da criatura do SRD 2014 com esse nome, ou None se não houver.

    `name__iexact` casa o nome de forma exata mas insensível a maiúsculas (o filtro
    `name` cru é case-sensitive); combinado com o documento fixo, só o SRD 2014 volta.
    """
    params = {"document__key": DOCUMENTO_SRD, "name__iexact": nome.strip()}
    try:
        resposta = requests.get(URL_BASE, params=params, timeout=10)
    except requests.exceptions.RequestException:
        print("Erro de conexão. Verifique sua internet e tente novamente.")
        return None
    if resposta.status_code != 200:
        return None
    resultados = resposta.json().get("results", [])
    return resultados[0] if resultados else None


def filtrar_monstros(chave, valor):
    """Filtra criaturas do SRD 2014 por `type` ou `challenge_rating` (server-side)."""
    params = {"document__key": DOCUMENTO_SRD, chave: valor}
    erro = "Erro de conexão durante a busca. Verifique sua internet."
    resultados = []
    for pagina in _paginar(params, erro):
        resultados.extend(pagina.get("results", []))
    return resultados


def sincronizar_base_completa(conexao):
    erro = "Erro de conexão durante a sincronização. Verifique sua internet."
    for pagina in _paginar({"document__key": DOCUMENTO_SRD}, erro):
        for criatura in pagina.get("results", []):
            registrar_monstro(conexao, criatura)


def _paginar(params, erro):
    """Gera cada página do SRD 2014 seguindo o campo `next` até ele ser None.

    Os `params` só vão na primeira requisição; a URL de `next` já os carrega embutidos.
    Para em erro de conexão (com mensagem) ou status ≠ 200, entregando o que obteve.
    """
    url_atual = URL_BASE
    primeira = True
    while url_atual:
        try:
            resposta = requests.get(
                url_atual,
                params=params if primeira else None,
                timeout=10,
            )
        except requests.exceptions.RequestException:
            print(erro)
            return
        if resposta.status_code != 200:
            return
        dados = resposta.json()
        yield dados
        url_atual = dados.get("next")
        primeira = False
