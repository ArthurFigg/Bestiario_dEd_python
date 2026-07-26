"""Aplicação FastAPI do site: HTML renderizado no servidor + a API incluída.

Entrada real do projeto (`uv run uvicorn web.app:app`). Inclui o roteador da
Spec 8 sob `/api/v1` — nunca monta como sub-aplicação, o que duplicaria o
prefixo e jogaria `/docs` para dentro dele (ver `api/app.py`) — e registra os
mesmos tratadores de erro que `api/app.py` registra: incluir o roteador leva
as rotas, não os tratadores, e sem isso `/api/v1/monstros?resiste_a=fogo`
responderia 500 aqui enquanto responde 422 em `api.app:app`.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.erros import registrar_tratadores
from api.rotas import METADADOS
from api.rotas import roteador as roteador_api
from web.rotas import pagina_de_base_nao_sincronizada
from web.rotas import roteador as roteador_web

app = FastAPI(**METADADOS)

app.include_router(roteador_api, prefix="/api/v1")
# A página HTML só vale para as rotas do site: sob `/api/`, quem chama é
# programa e continua recebendo RFC 7807, igual a `api.app:app`.
registrar_tratadores(app, pagina_de_base_nao_sincronizada)
app.include_router(roteador_web)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)
