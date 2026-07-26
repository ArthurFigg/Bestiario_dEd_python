"""Testes das derivações puras. Sem mock: é tudo função pura, sem I/O."""

from bestiario.calculos import media_de_dado


def test_media_de_dado_com_dado_e_bonus():
    assert media_de_dado("2d10", 8) == 19.0


def test_media_de_dado_sem_bonus():
    assert media_de_dado("1d6", None) == 3.5


def test_media_de_dado_com_bonus_negativo():
    assert media_de_dado("1d4", -1) == 1.5


def test_media_de_dado_fixo_vale_o_proprio_bonus():
    # 15 ataques do SRD são "1 piercing damage": sem dado, o bônus é a média.
    assert media_de_dado(None, 1) == 1.0


def test_media_de_dado_sem_dano_nenhum_devolve_none():
    assert media_de_dado(None, None) is None


def test_media_de_dado_com_texto_livre_e_sem_bonus_devolve_none():
    assert media_de_dado("um punhado de dados", None) is None


def test_media_de_dado_com_dado_invalido_mas_com_bonus_usa_o_bonus():
    assert media_de_dado("", 4) == 4.0


def test_media_de_dado_arredonda_em_duas_casas():
    assert media_de_dado("1d3", 0) == 2.0
