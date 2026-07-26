"""Testes das derivações puras. Sem mock: é tudo função pura, sem I/O."""

from bestiario.calculos import media_de_dado, modificador, saves_proficientes


def _adult_red_dragon():
    """Valores do SRD: proficiente em Des, Con, Sab e Car."""
    return {
        "forca": 27,
        "forca_save": 8,
        "destreza": 10,
        "destreza_save": 6,
        "constituicao": 25,
        "constituicao_save": 13,
        "inteligencia": 16,
        "inteligencia_save": 3,
        "sabedoria": 13,
        "sabedoria_save": 7,
        "carisma": 21,
        "carisma_save": 11,
    }


def test_modificador_de_atributo_alto():
    assert modificador(27) == 8


def test_modificador_de_atributo_medio_e_zero():
    assert modificador(10) == 0


def test_modificador_de_atributo_baixo_e_negativo():
    assert modificador(7) == -2


def test_modificador_de_valor_ausente_devolve_none():
    assert modificador(None) is None


def test_saves_proficientes_do_adult_red_dragon():
    assert saves_proficientes(_adult_red_dragon()) == [
        "destreza",
        "constituicao",
        "sabedoria",
        "carisma",
    ]


def test_saves_proficientes_ignora_atributo_cujo_save_e_o_proprio_modificador():
    # Força: 27 → modificador 8, save 8. Sem proficiência, logo fora da lista.
    assert "forca" not in saves_proficientes(_adult_red_dragon())


def test_saves_proficientes_sem_nenhuma_proficiencia_devolve_lista_vazia():
    linha = {
        a: 10
        for a in (
            "forca",
            "destreza",
            "constituicao",
            "inteligencia",
            "sabedoria",
            "carisma",
        )
    }
    linha.update({f"{a}_save": 0 for a in list(linha)})
    assert saves_proficientes(linha) == []


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
