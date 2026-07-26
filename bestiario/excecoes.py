"""Erros de domínio do bestiário.

As duas exceções herdam de `ErroDoBestiario` para a API capturar as duas de uma
vez ao traduzir para RFC 7807, sem precisar listar cada subclasse.
"""


class ErroDoBestiario(Exception):
    """Base de todo erro de domínio do projeto."""


class FiltroDesconhecido(ErroDoBestiario):
    """Chave de filtro, dimensão ou métrica fora da lista branca."""

    def __init__(self, chave, aceitas=None):
        self.chave = chave
        self.aceitas = sorted(aceitas) if aceitas else []
        detalhe = f"Chave desconhecida: {chave!r}."
        if self.aceitas:
            detalhe += f" Aceitas: {', '.join(self.aceitas)}."
        super().__init__(detalhe)


class ValorDeFiltroInvalido(ErroDoBestiario):
    """Chave válida, valor fora do vocabulário lido do banco.

    Carrega `parametro` e `valor` porque a API precisa nomear os dois no `detail`
    do RFC 7807 — quem errou `resiste_a=fogo` tem de descobrir que o certo é `fire`.
    """

    def __init__(self, parametro, valor):
        self.parametro = parametro
        self.valor = valor
        super().__init__(
            f"Valor {valor!r} não existe no vocabulário de {parametro!r}. "
            f"Consulte /vocabulario para os valores aceitos."
        )
