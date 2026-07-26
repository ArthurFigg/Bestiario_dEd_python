"""Derivações puras das regras de D&D — sem I/O, sem pandas, sem sqlite.

`media_de_dado` nasceu na revisão da Spec 4, porque a ingestão precisa gravar a
média do dano no banco; `modificador` e `saves_proficientes` entraram na Spec 7a.
Manter as fórmulas num módulo só evita que a mesma conta exista na ingestão e na
camada de consulta e as duas divirjam com o tempo.
"""

import re

# "2d10", "1d6" — o formato que a extração grava em `ataques.dano_dado`.
_DADO = re.compile(r"^(\d+)d(\d+)$")

ATRIBUTOS = (
    "forca",
    "destreza",
    "constituicao",
    "inteligencia",
    "sabedoria",
    "carisma",
)


def modificador(valor):
    """Modificador de atributo: (valor - 10) // 2. 27 vira 8, 7 vira -2."""
    if valor is None:
        return None
    return (valor - 10) // 2


def saves_proficientes(linha):
    """Atributos em que o teste de resistência difere do modificador do atributo.

    O schema guarda os seis testes já derivados e nunca nulos, então não há coluna
    de proficiência para ler: a diferença em relação ao modificador é o que a
    denuncia. O bloco impresso do livro só lista os proficientes.

    `linha` é qualquer mapeamento com as chaves de atributo e `{atributo}_save` —
    um `sqlite3.Row` ou um dict servem.
    """
    proficientes = []
    for atributo in ATRIBUTOS:
        valor = linha[atributo]
        save = linha[f"{atributo}_save"]
        if valor is None or save is None:
            continue
        if save != modificador(valor):
            proficientes.append(atributo)
    return proficientes


def media_de_dado(dado, bonus):
    """Média de uma expressão de dano: n × (faces + 1) / 2 + bônus.

    Devolve `None` só quando não há dano nenhum. Dano fixo — sem dado, só bônus,
    como o `1 piercing damage` de 15 ataques do SRD — vale o próprio bônus: um
    valor constante é a sua própria média.
    """
    faces_media = 0.0
    achou_dado = False

    if dado:
        m = _DADO.match(dado.strip())
        if m:
            quantidade, faces = int(m.group(1)), int(m.group(2))
            faces_media = quantidade * (faces + 1) / 2
            achou_dado = True

    if not achou_dado and bonus is None:
        return None

    return round(faces_media + (bonus or 0), 2)
