"""Extração híbrida de ataques + extração 100% regex de efeitos, a partir do `desc`.

Ataques: o `attacks[]` enumera os ataques e traz acerto/alcance confiáveis
(`to_hit_mod`, `reach`, `range`), mas o dano estruturado é lixo (`damage_type`
~99% "thunder", `damage_bonus` ~99% null). Por isso o dano vem da regex sobre o
bloco "Hit:" do `desc`; o estruturado só entra como fallback quando a regex não
casa.

Efeitos (save/condição/área): a v2 não tem nenhum campo estruturado pra isso —
é 100% regex sobre o `desc`, a parte assumidamente lossy da ingestão (Spec 5).

Todas as funções são puras (string/dict → dict ou lista de dicts), sem I/O.
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


# --- Extração de efeitos (save / condição / área) — Spec 5 ---

# "DC 21 Dexterity saving throw" → CD do save principal contra o monstro.
_SAVE = re.compile(
    r"DC\s+(\d+)\s+"
    r"(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+"
    r"saving throw",
    re.IGNORECASE,
)
# "escape DC 14" (agarrar/prender) → CD de escape, sem atributo (FOR/DES à escolha).
_ESCAPE = re.compile(r"escape DC\s+(\d+)", re.IGNORECASE)

# As 15 condições canônicas do SRD. "knocked prone" casa via a palavra "prone" isolada.
_CONDICOES_CANONICAS = [
    "blinded",
    "charmed",
    "deafened",
    "exhaustion",
    "frightened",
    "grappled",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
]
_CONDICAO = re.compile(r"\b(" + "|".join(_CONDICOES_CANONICAS) + r")\b", re.IGNORECASE)

# "60-foot cone" (espaço) ou "20-foot-radius sphere" (hífen, forma mais comum
# do SRD pra radius) → área geométrica nomeada.
_AREA_GEOMETRICA = re.compile(
    r"(\d+)-foot[\s-]+(cone|line|cube|sphere|radius)", re.IGNORECASE
)
# "within 120 feet" / "within 10 ft." → emanação ao redor do monstro.
_EMANACAO = re.compile(r"within\s+(\d+)\s*(?:ft\.?|feet)", re.IGNORECASE)


def extrair_efeitos(desc):
    """Save (CD+atributo), condições e área a partir do `desc` de uma ação/trait.

    Retorna uma linha por condição encontrada, todas compartilhando o mesmo save/
    área da ação (múltiplos saves distintos na mesma ação herdam o principal —
    limitação lossy aceita). Sem condição mas com save/área: uma linha com
    `condicao=None`. Sem save, condição nem área: lista vazia (não gera efeito).
    """
    cd, atributo = _extrair_save_principal(desc)
    area_tipo, area_tamanho = _extrair_area(desc)
    condicoes = _extrair_condicoes(desc)

    if not condicoes:
        if cd is None and area_tipo is None:
            return []
        return [_montar_linha_efeito(cd, atributo, None, area_tipo, area_tamanho)]

    return [
        _montar_linha_efeito(cd, atributo, condicao, area_tipo, area_tamanho)
        for condicao in condicoes
    ]


def _montar_linha_efeito(cd, atributo, condicao, area_tipo, area_tamanho):
    return {
        "cd_resistencia": cd,
        "atributo_resistencia": atributo,
        "condicao": condicao,
        "area_tipo": area_tipo,
        "area_tamanho": area_tamanho,
    }


def _extrair_save_principal(desc):
    # O save considerado é o primeiro DC que aparece no texto (save ou escape),
    # não necessariamente o primeiro regex que casar — por isso compara posições.
    candidatos = []
    m = _SAVE.search(desc)
    if m:
        candidatos.append((m.start(), int(m.group(1)), m.group(2).lower()))
    m = _ESCAPE.search(desc)
    if m:
        candidatos.append((m.start(), int(m.group(1)), None))
    if not candidatos:
        return None, None
    candidatos.sort(key=lambda c: c[0])
    _, cd, atributo = candidatos[0]
    return cd, atributo


def _extrair_condicoes(desc):
    encontradas = []
    for m in _CONDICAO.finditer(desc):
        condicao = m.group(1).lower()
        if condicao not in encontradas:
            encontradas.append(condicao)
    return encontradas


def _extrair_area(desc):
    # Mesma lógica do save: a primeira área que aparece no texto, geométrica ou
    # emanação, vence — não a ordem de tentativa dos regexes.
    candidatos = []
    m = _AREA_GEOMETRICA.search(desc)
    if m:
        candidatos.append((m.start(), int(m.group(1)), m.group(2).lower()))
    m = _EMANACAO.search(desc)
    if m:
        candidatos.append((m.start(), int(m.group(1)), "emanation"))
    if not candidatos:
        return None, None
    candidatos.sort(key=lambda c: c[0])
    _, tamanho, tipo = candidatos[0]
    return tipo, tamanho
