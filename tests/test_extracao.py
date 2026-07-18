from bestiario.extracao import extrair_ataque

# Bite do Adult Red Dragon (estrutura real da v2): estruturado confiável em
# to_hit/reach, mas damage_type='thunder' é lixo — o dano vem do desc.
_BITE_DESC = (
    "Melee Weapon Attack: +14 to hit, reach 10 ft., one target. "
    "Hit: 19 (2d10 + 8) piercing damage plus 7 (2d6) fire damage."
)
_BITE_ATTACK = {
    "name": "Bite attack",
    "to_hit_mod": 14,
    "reach": 10,
    "range": None,
    "long_range": None,
    "damage_die_count": 2,
    "damage_die_type": "D10",
}


def test_parseia_dano_primario_do_desc():
    d = extrair_ataque(_BITE_DESC, _BITE_ATTACK)
    assert (d["dano_dado"], d["dano_bonus"], d["dano_tipo"]) == ("2d10", 8, "piercing")


def test_parseia_dano_secundario_do_desc():
    d = extrair_ataque(_BITE_DESC, _BITE_ATTACK)
    assert (d["dano_extra_dado"], d["dano_extra_bonus"], d["dano_extra_tipo"]) == (
        "2d6",
        None,
        "fire",
    )


def test_usa_to_hit_e_reach_do_estruturado():
    d = extrair_ataque(_BITE_DESC, _BITE_ATTACK)
    assert (d["bonus_ataque"], d["alcance"], d["alcance_longo"]) == (14, 10, None)


def test_corrige_o_damage_type_lixo_do_estruturado():
    # O estruturado diria 'thunder'; a regex do desc dá o tipo real 'piercing'.
    assert extrair_ataque(_BITE_DESC, _BITE_ATTACK)["dano_tipo"] == "piercing"


def test_ataque_sem_bonus_e_sem_dano_secundario():
    desc = "Melee Weapon Attack: +2 to hit, reach 5 ft. Hit: 3 (1d6) piercing damage."
    attack = {"name": "Bite", "to_hit_mod": 2, "reach": 5}
    d = extrair_ataque(desc, attack)
    assert d["dano_bonus"] is None and d["dano_extra_dado"] is None


def test_dano_fixo_sem_dado_vai_para_bonus_e_tipo():
    # Vermes de CR baixo: "Hit: 1 piercing damage" (sem dado). O valor vira
    # dano_bonus e o tipo é preservado; dano_dado fica NULL (não há dado).
    desc = "Melee Weapon Attack: +0 to hit, reach 5 ft. Hit: 1 piercing damage."
    attack = {"name": "Bite", "to_hit_mod": 0, "reach": 5}
    d = extrair_ataque(desc, attack)
    assert (d["dano_dado"], d["dano_bonus"], d["dano_tipo"]) == (None, 1, "piercing")


def test_fallback_usa_dado_estruturado_quando_regex_falha():
    # desc sem bloco "(XdY) ... damage" parseável → cai para damage_die_count/type.
    desc = "The creature does something weird without a standard damage line."
    attack = {
        "name": "Odd",
        "to_hit_mod": 5,
        "reach": 5,
        "damage_die_count": 2,
        "damage_die_type": "D8",
    }
    d = extrair_ataque(desc, attack)
    assert (d["dano_dado"], d["dano_bonus"], d["dano_tipo"]) == ("2d8", None, None)


def test_tipo_ataque_ranged_weapon():
    desc = (
        "Ranged Weapon Attack: +5 to hit, range 80/320 ft. "
        "Hit: 5 (1d8 + 1) piercing damage."
    )
    attack = {
        "name": "Shortbow",
        "to_hit_mod": 5,
        "reach": None,
        "range": 80,
        "long_range": 320,
    }
    assert extrair_ataque(desc, attack)["tipo_ataque"] == "ranged_weapon"


def test_tipo_ataque_melee_spell():
    desc = "Melee Spell Attack: +7 to hit, reach 5 ft. Hit: 10 (3d6) necrotic damage."
    attack = {"name": "Touch", "to_hit_mod": 7, "reach": 5}
    assert extrair_ataque(desc, attack)["tipo_ataque"] == "melee_spell"


_SPEAR_DESC = (
    "Melee or Ranged Weapon Attack: +3 to hit, reach 5 ft. or range 20/60 ft., "
    "one target. Hit: 4 (1d6 + 1) piercing damage."
)


def test_melee_or_ranged_com_reach_e_melee():
    attack = {
        "name": "Spear Melee attack",
        "to_hit_mod": 3,
        "reach": 5,
        "range": 20,
        "long_range": 60,
    }
    d = extrair_ataque(_SPEAR_DESC, attack)
    assert (d["tipo_ataque"], d["alcance"], d["alcance_longo"]) == (
        "melee_weapon",
        5,
        None,
    )


def test_melee_or_ranged_sem_reach_e_ranged():
    attack = {
        "name": "Spear Ranged attack",
        "to_hit_mod": 3,
        "reach": None,
        "range": 20,
        "long_range": 60,
    }
    d = extrair_ataque(_SPEAR_DESC, attack)
    assert (d["tipo_ataque"], d["alcance"], d["alcance_longo"]) == (
        "ranged_weapon",
        20,
        60,
    )
