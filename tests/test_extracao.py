from bestiario.extracao import extrair_bonus_ataque, extrair_dados_dano


def test_bonus_ja_estruturado_e_devolvido_sem_regex():
    assert extrair_bonus_ataque(7, "irrelevante") == 7


def test_bonus_none_e_extraido_do_desc():
    desc = "Melee Weapon Attack: +5 to hit, reach 5 ft., one target."
    assert extrair_bonus_ataque(None, desc) == 5


def test_bonus_none_sem_padrao_no_desc_devolve_none():
    assert extrair_bonus_ataque(None, "Passive ability, no attack roll.") is None


def test_dano_combina_dice_com_bonus_positivo():
    assert extrair_dados_dano("1d6", 2, "") == "1d6 + 2"


def test_dano_combina_dice_com_bonus_negativo():
    assert extrair_dados_dano("2d8", -1, "") == "2d8 - 1"


def test_dano_sem_bonus_devolve_so_o_dice():
    assert extrair_dados_dano("3d6", None, "") == "3d6"


def test_dano_none_faz_fallback_por_regex_no_desc():
    desc = "Hit: 7 (2d6) piercing damage."
    assert extrair_dados_dano(None, None, desc) == "2d6"
