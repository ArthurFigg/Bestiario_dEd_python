"""Comunicação com a API Open5e (v1).

Busca individual, filtro paginado e sincronização completa para o banco local.
A migração para a API v2 é a Spec 2; aqui as URLs permanecem em /v1/.
"""

import requests

from bestiario.banco import registrar_monstro

URL_BASE = "https://api.open5e.com/v1/monsters/"


def buscar_monstro(nome):
    nome = nome.lower().strip().replace(" ", "-")
    url = f"{URL_BASE}{nome}/"
    try:
        resposta = requests.get(url, timeout=10)
    except requests.exceptions.RequestException:
        print("Erro de conexão. Verifique sua internet e tente novamente.")
        return None
    if resposta.status_code == 200:
        return resposta.json()
    return None


def filtrar_monstros(chave, valor):
    url_atual = URL_BASE
    resultados_filtrados = []
    while url_atual:
        try:
            resposta = requests.get(url_atual, timeout=10)
        except requests.exceptions.RequestException:
            print("Erro de conexão durante a busca. Verifique sua internet.")
            break
        if resposta.status_code == 200:
            dados = resposta.json()
            for monstro in dados.get('results', []):
                if str(monstro.get(chave)).lower() in str(valor).lower():
                    resultados_filtrados.append(monstro)
            url_atual = dados.get('next')
        else:
            break
    return resultados_filtrados


def sincronizar_base_completa(conexao):
    url_atual = URL_BASE
    while url_atual:
        try:
            resposta = requests.get(url_atual, timeout=10)
        except requests.exceptions.RequestException:
            print("Erro de conexão durante a sincronização. Verifique sua internet.")
            break
        if resposta.status_code == 200:
            dados = resposta.json()
            for monstro in dados.get('results', []):
                registrar_monstro(conexao, monstro)
            url_atual = dados.get('next')
        else:
            break
