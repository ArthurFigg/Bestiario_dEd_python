import pytest

from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.relatorios import (
    TODOS_OS_RELATORIOS,
    gerar_todos_relatorios,
    relatorio_condicoes_impostas,
    relatorio_interacao_dano,
    relatorio_por_ambiente,
    relatorio_top_ataques,
)


def _adult_red_dragon():
    """Dragão: ataque de acerto alto, imunidade a fire, dois ambientes."""
    return {
        "name": "Adult Red Dragon",
        "size": {"key": "huge"},
        "type": {"key": "dragon"},
        "armor_class": 19,
        "hit_points": 256,
        "challenge_rating": 17.0,
        "environments": [
            {"name": "Hills", "key": "hills"},
            {"name": "Mountain", "key": "mountain"},
        ],
        "resistances_and_immunities": {
            "damage_immunities": [{"name": "Fire", "key": "fire"}],
            "damage_resistances": [],
            "damage_vulnerabilities": [],
            "condition_immunities": [],
        },
        "actions": [
            {
                "name": "Bite",
                "action_type": "ACTION",
                "desc": (
                    "Melee Weapon Attack: +14 to hit, reach 10 ft., one target. "
                    "Hit: 19 (2d10 + 8) piercing damage."
                ),
                "attacks": [
                    {
                        "name": "Bite attack",
                        "to_hit_mod": 14,
                        "reach": 10,
                        "range": None,
                        "long_range": None,
                        "damage_die_count": 2,
                        "damage_die_type": "D10",
                    }
                ],
            }
        ],
    }


def _cobra_venenosa():
    """Monstro cujo desc impõe a condição `poisoned` (exercita `efeitos`)."""
    return {
        "name": "Giant Poison Snake",
        "size": {"key": "medium"},
        "type": {"key": "beast"},
        "armor_class": 14,
        "hit_points": 30,
        "challenge_rating": 2.0,
        "environments": [{"name": "Swamp", "key": "swamp"}],
        "resistances_and_immunities": {
            "damage_immunities": [],
            "damage_resistances": [{"name": "Poison", "key": "poison"}],
            "damage_vulnerabilities": [],
            "condition_immunities": [],
        },
        "actions": [
            {
                "name": "Bite",
                "action_type": "ACTION",
                "desc": (
                    "Melee Weapon Attack: +6 to hit, reach 10 ft., one target. "
                    "Hit: 10 (3d6) piercing damage, and the target must succeed on "
                    "a DC 15 Constitution saving throw or be poisoned for 1 minute."
                ),
                "attacks": [
                    {
                        "name": "Bite attack",
                        "to_hit_mod": 6,
                        "reach": 10,
                        "range": None,
                        "long_range": None,
                        "damage_die_count": 3,
                        "damage_die_type": "D6",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def banco_populado(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "relatorios.db"))
    registrar_monstro(conexao, _adult_red_dragon())
    registrar_monstro(conexao, _cobra_venenosa())
    yield conexao
    conexao.close()


@pytest.fixture
def banco_vazio(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "vazio.db"))
    yield conexao
    conexao.close()


def test_top_ataques_ordena_por_ataques_bonus_ataque(banco_populado):
    # O dragão (Bite +14) lidera a cobra (Bite +6). A query roda sobre
    # ataques.bonus_ataque — se ainda usasse acoes.bonus_ataque, daria erro de coluna.
    df = relatorio_top_ataques(banco_populado)
    assert df.iloc[0]["nome"] == "Adult Red Dragon"


def test_por_ambiente_agrega_de_monstro_ambiente(banco_populado):
    df = relatorio_por_ambiente(banco_populado)
    assert dict(zip(df["ambiente"], df["total"])) == {
        "hills": 1,
        "mountain": 1,
        "swamp": 1,
    }


def test_interacao_dano_conta_um_imune_a_fire(banco_populado):
    df = relatorio_interacao_dano(banco_populado)
    imune_fire = df[(df["tipo_dano"] == "fire") & (df["relacao"] == "imunidade")]
    assert int(imune_fire["total"].iloc[0]) == 1


def test_condicoes_impostas_lista_o_monstro_que_impoe(banco_populado):
    df = relatorio_condicoes_impostas(banco_populado)
    poisoned = df[df["condicao"] == "poisoned"]
    assert poisoned["quais"].iloc[0] == "Giant Poison Snake"


def test_todos_os_relatorios_contra_banco_vazio_nao_quebram(banco_vazio, capsys):
    for relatorio in TODOS_OS_RELATORIOS:
        relatorio(banco_vazio)
    assert "OS 5 MAIS RESISTENTES" in capsys.readouterr().out


def test_gerar_todos_relatorios_roda_standalone_por_caminho(tmp_path, capsys):
    caminho = str(tmp_path / "orquestrador.db")
    conexao = criar_base_de_dados(caminho)
    registrar_monstro(conexao, _adult_red_dragon())
    conexao.close()

    gerar_todos_relatorios(caminho)

    assert "RELATÓRIOS — BESTIÁRIO D&D 5E" in capsys.readouterr().out
