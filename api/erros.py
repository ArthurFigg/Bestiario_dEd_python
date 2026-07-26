"""Tradutores de erro para RFC 7807 (`application/problem+json`).

`registrar_tratadores(app)` é o único ponto de entrada. `api/app.py` a chama
ao montar a aplicação, e a Spec 9a vai chamá-la de novo em `web/app.py`.
Incluir o roteador leva as rotas, não os tratadores: sem essa função, a
entrada real do projeto devolveria o formato padrão do FastAPI (ou um erro
cru) onde o contrato promete 404, 422 ou 503 em RFC 7807.
"""

import unicodedata

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.modelos import Problema
from bestiario.excecoes import FiltroDesconhecido, ValorDeFiltroInvalido


class MonstroNaoEncontrado(Exception):
    """Não existe monstro com esse nome exato (a busca não diferencia caixa)."""

    def __init__(self, nome):
        self.nome = nome
        super().__init__(f"Nenhum monstro chamado {nome!r}.")


class BaseNaoSincronizada(Exception):
    """A base local não tem nenhum monstro — falta rodar a sincronização."""


_ESQUEMA_PROBLEMA = Problema.model_json_schema()

# `responses` extra de cada rota — a 404 só existe em `/monstros/{nome}`, e o
# `default` (onde mora o 503) vale para as seis. O FastAPI só gera 200 e 422
# sozinho; sem isso, o teste de contrato passaria sem cobrir justamente as
# respostas que o projeto mais depende de não perder.
RESPOSTA_DEFAULT = {
    "default": {
        "description": (
            "Erro inesperado. Inclui 503 quando a base ainda não foi sincronizada."
        ),
        "content": {"application/problem+json": {"schema": _ESQUEMA_PROBLEMA}},
    }
}

RESPOSTA_404 = {
    404: {
        "description": "Não existe monstro com esse nome.",
        "content": {"application/problem+json": {"schema": _ESQUEMA_PROBLEMA}},
    }
}

# O FastAPI só adiciona o 422 sozinho quando nenhum `default`/`4XX` já está
# declarado (ver `fastapi.openapi.utils.get_openapi_path`) — como toda rota
# aqui declara `default`, o 422 precisa ser explícito também, ou ele
# desapareceria do esquema gerado e o teste de contrato passaria sem cobri-lo.
RESPOSTA_422 = {
    422: {
        "description": (
            "Parâmetro fora do vocabulário ou do intervalo aceito. O campo "
            "`detail` aponta o parâmetro culpado e remete a `/vocabulario`."
        ),
        "content": {"application/problem+json": {"schema": _ESQUEMA_PROBLEMA}},
    }
}


def _slug(titulo):
    """Título humano → identificador ASCII para o campo `type` do RFC 7807.

    Sem a remoção de acento, `Filtro inválido` viraria `/erros/filtro-inválido` —
    e o contrato declara `type` como `uri-reference`, que não admite caractere
    não-ASCII sem percent-encoding. O `type` é chave de indexação de erro para
    quem consome, então precisa ser estável e escrevível.
    """
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore")
    return sem_acento.decode("ascii").lower().replace(" ", "-")


def _resposta(status, titulo, detail=None, instance=None):
    corpo = {"type": f"/erros/{_slug(titulo)}", "title": titulo, "status": status}
    if detail:
        corpo["detail"] = detail
    if instance:
        corpo["instance"] = instance
    return JSONResponse(
        status_code=status, content=corpo, media_type="application/problem+json"
    )


PREFIXO_DA_API = "/api/"


def registrar_tratadores(app, pagina_de_base_nao_sincronizada=None):
    """Registra os cinco tratadores que convertem erro em RFC 7807.

    `pagina_de_base_nao_sincronizada` é opcional e só o site passa: recebe o
    `request` e devolve a página HTML explicativa. Sem ela — o caso de
    `api.app:app` — todo erro sai em RFC 7807, que é o certo para quem consome
    a API por programa.

    A distinção existe porque **quem abre o site é pessoa, não programa**: JSON
    cru na tela não diz a ninguém que falta rodar a opção 4 do menu. E como o
    `.db` está fora do git, base ausente é o primeiro que qualquer clone novo
    encontra, não um caso raro. O corte é por **superfície**: a página responde
    200 (é o estado inicial esperado, e ela diz o que fazer), a API responde 503
    (quem chama por programa precisa do sinal na faixa de status).
    """

    @app.exception_handler(ValorDeFiltroInvalido)
    async def _tratar_valor_invalido(request, exc: ValorDeFiltroInvalido):
        detail = (
            f"{exc.valor!r} não é um valor aceito em {exc.parametro!r}. "
            "Consulte /vocabulario para os valores aceitos."
        )
        return _resposta(422, "Filtro inválido", detail, str(request.url.path))

    @app.exception_handler(FiltroDesconhecido)
    async def _tratar_filtro_desconhecido(request, exc: FiltroDesconhecido):
        return _resposta(422, "Filtro desconhecido", str(exc), str(request.url.path))

    @app.exception_handler(RequestValidationError)
    async def _tratar_erro_de_validacao(request, exc: RequestValidationError):
        # Formato padrão do FastAPI substituído: a API promete um formato de
        # erro só, e dois formatos obrigaria quem consome a tratar os dois.
        detalhes = "; ".join(
            f"{'.'.join(str(parte) for parte in erro['loc'])}: {erro['msg']}"
            for erro in exc.errors()
        )
        return _resposta(422, "Parâmetro inválido", detalhes, str(request.url.path))

    @app.exception_handler(MonstroNaoEncontrado)
    async def _tratar_nao_encontrado(request, exc: MonstroNaoEncontrado):
        return _resposta(404, "Monstro não encontrado", str(exc), str(request.url.path))

    @app.exception_handler(BaseNaoSincronizada)
    async def _tratar_base_vazia(request, exc: BaseNaoSincronizada):
        # Rota sob /api/ sempre recebe JSON, mesmo dentro do site: quem chama
        # ali é programa, e programa precisa do 503 na faixa de status.
        pede_html = pagina_de_base_nao_sincronizada is not None and not str(
            request.url.path
        ).startswith(PREFIXO_DA_API)
        if pede_html:
            return pagina_de_base_nao_sincronizada(request)
        detail = (
            "A base local não tem nenhum monstro. Rode a opção 4 do menu "
            "(sincronizar com a API) para popular o banco."
        )
        return _resposta(503, "Base não sincronizada", detail, str(request.url.path))
