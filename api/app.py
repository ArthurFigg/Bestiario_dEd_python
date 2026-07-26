"""Aplicação FastAPI: inclui o roteador sob `/api/v1` e registra os tratadores.

Executável sozinha (`uv run uvicorn api.app:app`), para esta spec fechar sem
depender da Spec 9 — que vai incluir o mesmo roteador em `web/app.py`. O
roteador é **incluído**, não montado como sub-aplicação: montar duplicaria o
prefixo (`/api/v1/api/v1/...`) e jogaria `/docs` para dentro dele.

Título, versão e resumo replicam o campo `info` do `openapi.yaml` — lidos à
mão, não do arquivo, porque `pyyaml` é dependência só de teste (o servidor de
produção não precisa analisar YAML para subir).
"""

from fastapi import FastAPI

from api.erros import registrar_tratadores
from api.rotas import METADADOS, roteador

app = FastAPI(**METADADOS)

app.include_router(roteador, prefix="/api/v1")
registrar_tratadores(app)
