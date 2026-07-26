"""Derivações puras das regras de D&D — sem I/O, sem pandas, sem sqlite.

Nasce na revisão da Spec 4 com `media_de_dado`, porque a ingestão precisa gravar
a média do dano no banco. A Spec 7a acrescenta aqui `modificador` e
`saves_proficientes`. Manter a fórmula num módulo só evita que a mesma conta
exista na ingestão e na camada de consulta e as duas divirjam com o tempo.
"""

import re

# "2d10", "1d6" — o formato que a extração grava em `ataques.dano_dado`.
_DADO = re.compile(r"^(\d+)d(\d+)$")


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
