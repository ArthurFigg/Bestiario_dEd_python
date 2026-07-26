"""Rotas HTML do site: raiz, aba "Todos os monstros" e destinos mínimos.

Nenhuma rota escreve SQL — a listagem chama `bestiario/consultas.py`, do
mesmo jeito que `api/rotas.py`. A conexão chega pela **mesma dependência**
`obter_conexao` que a Spec 8 define: é o único ponto que o teste substitui
via `app.dependency_overrides`, e reaproveitá-la (em vez de abrir uma
conexão própria) é o que torna o site testável sem `bestiario_combate.db`.

`/relatorios` e `/pesquisar` só existem aqui como destino de link — o
construtor de análises e a busca com fichas fixadas chegam nas Specs 9b e
9c. Renderizam o bloco padrão de `base.html`, sem template próprio.
"""

import sqlite3
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from api.rotas import verificar_banco_sincronizado
from bestiario.consultas import executar_consulta

roteador = APIRouter(include_in_schema=False)
# Ancorado em `__file__`, não no diretório de trabalho: `uv run uvicorn` e o
# `pytest` podem ser chamados de lugares diferentes.
templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

# (chave da aba, rótulo, caminho) — usado pela moldura para montar as três abas
# e destacar a corrente. Vive aqui, não em `base.html`, porque é dado de rota.
ABAS = (
    ("relatorios", "Relatórios", "/relatorios"),
    ("pesquisar", "Pesquisar", "/pesquisar"),
    ("monstros", "Todos os monstros", "/monstros"),
)

# (coluna, rótulo, alinhada à direita) — as seis colunas ordenáveis da aba
# "Todos os monstros", na ordem em que aparecem na tabela.
_COLUNAS_TODOS = (
    ("nome", "Nome", False),
    ("tipo", "Tipo", False),
    ("tamanho", "Tamanho", False),
    ("desafio", "Desafio", True),
    ("pontos_vida", "Pontos de vida", True),
    ("classe_armadura", "Armadura", True),
)


def _contexto_base(request, aba_atual, modo):
    """Contexto comum a toda página: abas, alternância de modo, link do rodapé.

    O alternador Resumida/Completa preserva os demais parâmetros da URL atual
    (como `ordenar_por`) e troca só `modo` — mudar a exibição não pode perder
    a ordenação que o usuário já escolheu.
    """
    outros = {
        chave: valor for chave, valor in request.query_params.items() if chave != "modo"
    }
    return {
        "request": request,
        "aba_atual": aba_atual,
        "modo": modo,
        "abas": ABAS,
        "url_resumida": f"?{urlencode({**outros, 'modo': 'resumida'})}",
        "url_completa": f"?{urlencode({**outros, 'modo': 'completa'})}",
    }


def pagina_de_base_nao_sincronizada(request):
    """Página humana para o 503, no lugar do RFC 7807 que a API devolve.

    Vale para banco **vazio**, **ausente** e com **schema defasado** — o `.db`
    está fora do git, então clone novo cai aqui antes de qualquer outra coisa, e
    "sincronize a base" é a mesma cura nos três casos.

    Responde **200**, não 503: para quem abre o site isto não é falha, é o estado
    inicial esperado, e a página diz o que fazer. O 503 continua valendo sob
    `/api/`, onde quem chama é programa e precisa do sinal na faixa de status.
    """
    aba = next(
        (chave for chave, _, caminho in ABAS if request.url.path == caminho),
        "monstros",
    )
    contexto = _contexto_base(
        request, aba, request.query_params.get("modo", "resumida")
    )
    contexto["mensagem"] = (
        "A base local ainda não foi sincronizada. Rode `python main.py` e "
        "escolha a opção 4 (sincronizar base completa) para baixar os 325 "
        "monstros do SRD 2014."
    )
    return templates.TemplateResponse(request, "base.html", contexto)


@roteador.get("/")
def raiz():
    return RedirectResponse("/relatorios")


@roteador.get("/relatorios")
def relatorios(request: Request, modo: str = "resumida"):
    contexto = _contexto_base(request, "relatorios", modo)
    contexto["mensagem"] = "O construtor de relatórios chega na próxima spec."
    return templates.TemplateResponse(request, "base.html", contexto)


@roteador.get("/pesquisar")
def pesquisar(request: Request, modo: str = "resumida"):
    contexto = _contexto_base(request, "pesquisar", modo)
    contexto["mensagem"] = "A busca com fichas comparadas chega na próxima spec."
    return templates.TemplateResponse(request, "base.html", contexto)


def _proximo_sentido(coluna, ordenar_por, sentido):
    """Primeiro clique num cabeçalho ordena crescente; o segundo, decrescente."""
    if coluna != ordenar_por:
        return "crescente"
    return "decrescente" if sentido == "crescente" else "crescente"


@roteador.get("/monstros")
def listar_todos_os_monstros(
    request: Request,
    ordenar_por: str = "nome",
    sentido: str = "crescente",
    modo: str = "resumida",
    conexao: sqlite3.Connection = Depends(verificar_banco_sincronizado),
):
    # Mesma dependência da API, e não `obter_conexao`: esta também cobre banco
    # que **abre** mas está com schema defasado ou incompleto, caso em que a
    # consulta só falharia lá dentro e viraria 500 com traceback na tela. É a
    # armadilha que o CLAUDE.md registra — banco defasado não emite sinal.
    # Sem filtro nesta aba: é a de folhear.
    monstros = executar_consulta(
        conexao,
        modo="lista_monstros",
        ordenar_por=ordenar_por,
        sentido=sentido,
        limite=None,
    )
    contexto = _contexto_base(request, "monstros", modo)
    contexto["monstros"] = monstros
    contexto["colunas"] = [
        {
            "chave": chave,
            "rotulo": rotulo,
            "num": num,
            "url": "?"
            + urlencode(
                {
                    "ordenar_por": chave,
                    "sentido": _proximo_sentido(chave, ordenar_por, sentido),
                    "modo": modo,
                }
            ),
        }
        for chave, rotulo, num in _COLUNAS_TODOS
    ]
    return templates.TemplateResponse(request, "todos.html", contexto)
