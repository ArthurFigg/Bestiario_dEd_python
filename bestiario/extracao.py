"""Extração híbrida de ataques: array `attacks[]` estruturado da v2 + regex no `desc`.

O `attacks[]` enumera os ataques e traz acerto/alcance confiáveis (`to_hit_mod`,
`reach`, `range`), mas o dano estruturado é lixo (`damage_type` ~99% "thunder",
`damage_bonus` ~99% null). Por isso o dano vem da regex sobre o bloco "Hit:" do
`desc`; o estruturado só entra como fallback quando a regex não casa. Funções puras.
"""

import re

# Prefixo do desc: "Melee/Ranged [or Ranged] Weapon/Spell Attack".
_PREFIXO_ATAQUE = re.compile(
    r"(Melee|Ranged)(\s+or\s+Ranged)?\s+(Weapon|Spell)\s+Attack", re.IGNORECASE
)
# Bloco de dano: "(2d10 + 8) piercing damage" → dado, sinal/valor opcionais, tipo.
_DANO = re.compile(
    r"\((\d+d\d+)(?:\s*([+\-])\s*(\d+))?\)\s+(\w+)\s+damage", re.IGNORECASE
)
# Dano fixo sem dado: "Hit: 1 piercing damage" (vermes de CR baixo) → valor, tipo.
_DANO_FIXO = re.compile(r"Hit:\s+(\d+)\s+(\w+)\s+damage", re.IGNORECASE)


def extrair_ataque(desc, attack):
    """Campos da tabela `ataques` a partir do desc + uma entrada de attacks[].

    Pura (string/dict → dict), sem I/O. `reach` presente marca a variante corpo-a-corpo;
    ausente marca a variante à distância (desempate dos casos "Melee or Ranged").
    """
    tem_reach = attack.get("reach") is not None
    if tem_reach:
        alcance, alcance_longo = attack.get("reach"), None
    else:
        alcance, alcance_longo = attack.get("range"), attack.get("long_range")

    return {
        "nome_ataque": attack.get("name"),
        "tipo_ataque": _derivar_tipo_ataque(desc, tem_reach),
        "bonus_ataque": attack.get("to_hit_mod"),
        "alcance": alcance,
        "alcance_longo": alcance_longo,
        **_extrair_danos(desc, attack),
    }


def _derivar_tipo_ataque(desc, tem_reach):
    m = _PREFIXO_ATAQUE.search(desc)
    if not m:
        return None
    arma = m.group(3).lower()  # weapon | spell
    if m.group(2):  # "or Ranged" → ambíguo, desempata pela presença de reach
        alcance = "melee" if tem_reach else "ranged"
    else:
        alcance = m.group(1).lower()  # melee | ranged
    return f"{alcance}_{arma}"


def _extrair_danos(desc, attack):
    achados = _DANO.findall(desc)
    if achados:
        dado, bonus, tipo = _montar_dano(achados[0])
        extra_dado, extra_bonus, extra_tipo = (
            _montar_dano(achados[1]) if len(achados) > 1 else (None, None, None)
        )
        return {
            "dano_dado": dado,
            "dano_bonus": bonus,
            "dano_tipo": tipo,
            "dano_extra_dado": extra_dado,
            "dano_extra_bonus": extra_bonus,
            "dano_extra_tipo": extra_tipo,
        }

    fixo = _DANO_FIXO.search(desc)
    if fixo:
        # Dano fixo sem dado: o valor vai em dano_bonus (o total é dado + bonus,
        # então o bonus sozinho representa o dano constante) e o tipo em dano_tipo.
        return {
            "dano_dado": None,
            "dano_bonus": int(fixo.group(1)),
            "dano_tipo": fixo.group(2).lower(),
            "dano_extra_dado": None,
            "dano_extra_bonus": None,
            "dano_extra_tipo": None,
        }

    return _dano_fallback(attack)


def _montar_dano(grupos):
    dado, sinal, valor, tipo = grupos  # de _DANO.findall
    bonus = None
    if valor:
        bonus = -int(valor) if sinal == "-" else int(valor)
    return dado, bonus, tipo.lower()


def _dano_fallback(attack):
    # Regex falhou: monta o dado do estruturado; bônus/tipo ficam NULL (o estruturado
    # é sabidamente errado, então não se inventa valor). O ataque nunca é perdido.
    contagem = attack.get("damage_die_count")
    tipo_dado = attack.get("damage_die_type")
    dado = f"{contagem}{tipo_dado.lower()}" if contagem and tipo_dado else None
    return {
        "dano_dado": dado,
        "dano_bonus": None,
        "dano_tipo": None,
        "dano_extra_dado": None,
        "dano_extra_bonus": None,
        "dano_extra_tipo": None,
    }
