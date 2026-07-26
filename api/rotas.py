"""Roteador sem prefixo com os seis endpoints de leitura do bestiário.

Nenhuma rota escreve consulta própria: cada uma monta filtros a partir da
query string, chama `bestiario/consultas.py` e serializa o dicionário que
voltou. Quem aplica o prefixo `/api/v1` é a aplicação que inclui este
roteador — `api/app.py` nos testes desta spec, e `web/app.py` na Spec 9a.
"""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Query

from api.erros import (
    RESPOSTA_404,
    RESPOSTA_422,
    RESPOSTA_DEFAULT,
    BaseNaoSincronizada,
    MonstroNaoEncontrado,
)
from api.modelos import (
    LinhaDeComparacao,
    ListaDeAtaques,
    ListaDeMonstros,
    Monstro,
    Resumo,
    Vocabulario,
)
from bestiario.consultas import (
    abrir_conexao,
    buscar_monstro,
    contar,
    executar_consulta,
    vocabulario_por_dominio,
)

roteador = APIRouter()

# Caminho padrão do banco de produção. Nos testes, `obter_conexao` é
# substituída por completo via `app.dependency_overrides` — é o único ponto
# de substituição, por isso a conexão chega às rotas por dependência, nunca
# por import de módulo nem variável global.
CAMINHO_BANCO_PADRAO = "bestiario_combate.db"

# `ordenar_por` continua **tolerante**: o contrato promete que valor fora da
# lista cai na ordenação padrão sem erro, e quem aplica isso é o núcleo. Por
# isso ele não é `Literal` — seria 422 onde o contrato promete 200. O enum vai
# para o esquema por `json_schema_extra`, para o /docs listar os valores sem
# que o FastAPI passe a rejeitá-los.
_ORDENACAO_DE_MONSTROS = [
    "nome",
    "tipo",
    "tamanho",
    "desafio",
    "pontos_vida",
    "classe_armadura",
    "dano_medio",
]

_ORDENACAO_DE_ATAQUES = ["bonus_ataque", "dano_medio"]

# `sentido` **é** estrito: o contrato lhe dá enum sem cláusula de tolerância, e
# aceitar `sentido=qualquercoisa` como crescente seria erro em silêncio.
_SENTIDO = Literal["crescente", "decrescente"]

_DIMENSOES_DE_COMPARACAO = Literal[
    "tipo",
    "tamanho",
    "alinhamento",
    "desafio",
    "ambiente",
    "tipo_dano",
    "condicao_imposta",
]


def obter_conexao():
    """Abre uma conexão nova por requisição. Ponto de substituição do teste.

    Arquivo **ausente** vira o mesmo 503 de banco vazio: `abrir_conexao` abre em
    modo `ro`, então caminho inexistente levanta em vez de criar banco vazio em
    silêncio. Para quem chama, os dois casos têm a mesma causa e a mesma cura —
    rodar a opção 4 do menu —, e o `bestiario_combate.db` está fora do git, o que
    faz do clone novo o caminho mais provável de todos.
    """
    try:
        conexao = abrir_conexao(CAMINHO_BANCO_PADRAO)
    except sqlite3.OperationalError as erro:
        raise BaseNaoSincronizada() from erro
    try:
        yield conexao
    finally:
        conexao.close()


def verificar_banco_sincronizado(conexao: sqlite3.Connection = Depends(obter_conexao)):
    """Contagem barata a cada requisição — banco sem monstro nenhum vira 503.

    Schema velho ou incompleto cai aqui também: `contar` levanta se a tabela não
    existe, e a resposta certa continua sendo "sincronize a base".
    """
    try:
        vazio = contar(conexao) == 0
    except sqlite3.OperationalError as erro:
        raise BaseNaoSincronizada() from erro
    if vazio:
        raise BaseNaoSincronizada()
    return conexao


def filtros_de_dominio(
    tipo: str | None = None,
    tamanho: str | None = None,
    alinhamento: str | None = None,
    desafio_min: float | None = Query(None, ge=0, le=30, description="Inclusivo."),
    desafio_max: float | None = Query(None, ge=0, le=30, description="Inclusivo."),
    ambiente: str | None = None,
    resiste_a: str | None = None,
    imune_a: str | None = None,
    vulneravel_a: str | None = None,
    imune_a_condicao: str | None = None,
    impoe: str | None = None,
    relacao: Literal["imunidade", "resistencia", "vulnerabilidade"] | None = None,
    combinar: Literal["todos", "qualquer"] = "todos",
) -> dict:
    """Os doze filtros de domínio, comuns aos quatro endpoints que os aceitam."""
    valores = {
        "tipo": tipo,
        "tamanho": tamanho,
        "alinhamento": alinhamento,
        "desafio_min": desafio_min,
        "desafio_max": desafio_max,
        "ambiente": ambiente,
        "resiste_a": resiste_a,
        "imune_a": imune_a,
        "vulneravel_a": vulneravel_a,
        "imune_a_condicao": imune_a_condicao,
        "impoe": impoe,
        "relacao": relacao,
    }
    filtros = {chave: valor for chave, valor in valores.items() if valor is not None}
    filtros["combinar"] = combinar
    return filtros


def _renomear_ataque(bruto):
    """`nome_ataque` (núcleo) vira `nome` (contrato) — único campo que diverge."""
    ataque = dict(bruto)
    ataque["nome"] = ataque.pop("nome_ataque")
    return ataque


def _serializar_acao(acao):
    acao = dict(acao)
    acao["ataques"] = [_renomear_ataque(ataque) for ataque in acao["ataques"]]
    return acao


@roteador.get(
    "/monstros",
    response_model=ListaDeMonstros,
    response_model_exclude_unset=True,
    tags=["monstros"],
    responses={**RESPOSTA_422, **RESPOSTA_DEFAULT},
)
def listar_monstros(
    filtros: dict = Depends(filtros_de_dominio),
    nome: str | None = Query(
        None, description="Trecho do nome, sem diferenciar maiúsculas."
    ),
    ordenar_por: str = Query(
        "nome",
        description="Coluna de ordenação. Valor fora da lista cai no padrão.",
        json_schema_extra={"enum": _ORDENACAO_DE_MONSTROS},
    ),
    sentido: _SENTIDO = Query("crescente", description="Direção da ordenação."),
    limite: int = Query(50, ge=1, le=200),
    deslocamento: int = Query(0, ge=0),
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    if nome:
        filtros["nome"] = nome
    total = contar(conexao, filtros)
    itens = executar_consulta(
        conexao,
        filtros,
        modo="lista_monstros",
        ordenar_por=ordenar_por,
        sentido=sentido,
        limite=limite,
        deslocamento=deslocamento,
    )
    return ListaDeMonstros(
        total=total, limite=limite, deslocamento=deslocamento, itens=itens
    )


@roteador.get(
    "/monstros/{nome}",
    response_model=Monstro,
    response_model_exclude_unset=True,
    tags=["monstros"],
    responses={**RESPOSTA_404, **RESPOSTA_422, **RESPOSTA_DEFAULT},
)
def buscar_monstro_por_nome(
    nome: str, conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado)
):
    ficha = buscar_monstro(conexao, nome)
    if ficha is None:
        raise MonstroNaoEncontrado(nome)
    ficha = dict(ficha)
    ficha["acoes"] = [_serializar_acao(acao) for acao in ficha["acoes"]]
    return Monstro(**ficha)


@roteador.get(
    "/ataques",
    response_model=ListaDeAtaques,
    response_model_exclude_unset=True,
    tags=["ataques"],
    responses={**RESPOSTA_422, **RESPOSTA_DEFAULT},
)
def listar_ataques(
    filtros: dict = Depends(filtros_de_dominio),
    ordenar_por: str = Query(
        "bonus_ataque",
        description="Critério de ordenação decrescente.",
        json_schema_extra={"enum": _ORDENACAO_DE_ATAQUES},
    ),
    limite: int = Query(50, ge=1, le=200),
    deslocamento: int = Query(0, ge=0),
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    # Sem `sentido`: o grão de ataques ordena sempre decrescente (maior bônus
    # e maior dano primeiro é a única leitura útil de uma lista de ataques).
    # Aceitar `sentido` aqui criaria parâmetro não documentado.
    total = contar(conexao, filtros, grao="ataques")
    linhas = executar_consulta(
        conexao,
        filtros,
        modo="lista_ataques",
        ordenar_por=ordenar_por,
        limite=limite,
        deslocamento=deslocamento,
    )
    itens = [_renomear_ataque(linha) for linha in linhas]
    return ListaDeAtaques(
        total=total, limite=limite, deslocamento=deslocamento, itens=itens
    )


@roteador.get(
    "/comparacoes",
    response_model=list[LinhaDeComparacao],
    tags=["análise"],
    responses={**RESPOSTA_422, **RESPOSTA_DEFAULT},
)
def comparar_monstros(
    por: _DIMENSOES_DE_COMPARACAO = Query(..., description="Dimensão de agrupamento."),
    filtros: dict = Depends(filtros_de_dominio),
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    return executar_consulta(conexao, filtros, modo="comparacao", por=por)


@roteador.get(
    "/resumo",
    response_model=Resumo,
    tags=["análise"],
    responses={**RESPOSTA_422, **RESPOSTA_DEFAULT},
)
def resumir_monstros(
    filtros: dict = Depends(filtros_de_dominio),
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    linha = executar_consulta(conexao, filtros, modo="resumo")[0]
    return Resumo(**linha)


@roteador.get(
    "/vocabulario",
    response_model=Vocabulario,
    tags=["metadados"],
    responses=RESPOSTA_DEFAULT,
)
def obter_vocabulario(
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    # O agrupamento em seis chaves mora no núcleo, junto da validação que o usa.
    # Tê-lo aqui faria a rota anunciar um recorte e o filtro cobrar outro.
    return Vocabulario(**vocabulario_por_dominio(conexao))
