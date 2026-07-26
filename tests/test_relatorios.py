"""Testes dos relatórios do terminal, agora delegando ao núcleo de consulta.

Os valores esperados são **fixos e escritos à mão**, nunca recalculados com a
implementação nova: teste que recalcula passaria mesmo se o resultado mudasse, que
é exatamente o risco de uma refatoração como esta.
"""

from pathlib import Path

import pytest

from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.relatorios import (
    TODOS_OS_RELATORIOS,
    gerar_todos_relatorios,
    relatorio_comparacao_tipos,
    relatorio_condicoes_impostas,
    relatorio_interacao_dano,
    relatorio_letalidade_por_tipo,
    relatorio_mais_resistentes,
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


def _young_red_dragon():
    """Segundo dragão, com **dois** ataques.

    Existe para provar que a média de bônus é por monstro: com dois ataques de +10,
    ele pesa uma vez na média do tipo `dragon`, não duas.
    """
    return {
        "name": "Young Red Dragon",
        "size": {"key": "large"},
        "type": {"key": "dragon"},
        "armor_class": 18,
        "hit_points": 178,
        "challenge_rating": 10.0,
        "environments": [{"name": "Mountain", "key": "mountain"}],
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
                    "Melee Weapon Attack: +10 to hit, reach 10 ft., one target. "
                    "Hit: 17 (2d10 + 6) piercing damage."
                ),
                "attacks": [
                    {
                        "name": "Bite attack",
                        "to_hit_mod": 10,
                        "reach": 10,
                        "range": None,
                        "long_range": None,
                        "damage_die_count": 2,
                        "damage_die_type": "D10",
                    }
                ],
            },
            {
                "name": "Claw",
                "action_type": "ACTION",
                "desc": (
                    "Melee Weapon Attack: +10 to hit, reach 5 ft., one target. "
                    "Hit: 13 (2d6 + 6) slashing damage."
                ),
                "attacks": [
                    {
                        "name": "Claw attack",
                        "to_hit_mod": 10,
                        "reach": 5,
                        "range": None,
                        "long_range": None,
                        "damage_die_count": 2,
                        "damage_die_type": "D6",
                    }
                ],
            },
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
    registrar_monstro(conexao, _young_red_dragon())
    registrar_monstro(conexao, _cobra_venenosa())
    yield conexao
    conexao.close()


@pytest.fixture
def banco_vazio(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "vazio.db"))
    yield conexao
    conexao.close()


# --- os dois de saída preservada -------------------------------------------


def test_mais_resistentes_ordena_por_pontos_vida(banco_populado):
    df = relatorio_mais_resistentes(banco_populado)
    assert list(df["nome"]) == [
        "Adult Red Dragon",
        "Young Red Dragon",
        "Giant Poison Snake",
    ]


def test_mais_resistentes_usa_cabecalhos_do_glossario(banco_populado):
    df = relatorio_mais_resistentes(banco_populado)
    assert list(df.columns) == ["nome", "tipo", "pontos_vida", "classe_armadura"]


def test_top_ataques_ordena_por_bonus_de_ataque(banco_populado):
    # O dragão adulto (+14) lidera o jovem (+10) e a cobra (+6).
    df = relatorio_top_ataques(banco_populado)
    assert df.iloc[0]["nome"] == "Adult Red Dragon"


def test_top_ataques_preserva_as_colunas_de_antes(banco_populado):
    df = relatorio_top_ataques(banco_populado)
    assert list(df.columns) == ["nome", "ataque", "bonus", "dano", "tipo_dano"]


# --- os cinco que mudaram de formato ---------------------------------------


def test_por_ambiente_conta_monstros_por_ambiente(banco_populado):
    df = relatorio_por_ambiente(banco_populado)
    assert dict(zip(df["ambiente"], df["monstros"])) == {
        "hills": 1,
        "mountain": 2,
        "swamp": 1,
    }


def test_por_ambiente_usa_a_coluna_monstros_e_nao_total(banco_populado):
    df = relatorio_por_ambiente(banco_populado)
    assert "total" not in df.columns


def test_letalidade_por_tipo_tira_media_por_monstro(banco_populado):
    # dragon: adulto +14, jovem com dois ataques de +10 (média 10).
    # Por monstro dá (14 + 10) / 2 = 12,0. Por linha de ataque daria 11,33 —
    # o jovem pesaria duas vezes só por ter mais ações.
    df = relatorio_letalidade_por_tipo(banco_populado)
    dragao = df[df["tipo"] == "dragon"]
    assert dragao["media_bonus_ataque"].iloc[0] == 12.0


def test_letalidade_por_tipo_conta_monstros_e_nao_ataques(banco_populado):
    df = relatorio_letalidade_por_tipo(banco_populado)
    assert df[df["tipo"] == "dragon"]["monstros"].iloc[0] == 2


def test_comparacao_tipos_ordena_por_contagem_de_monstros(banco_populado):
    # Antes ordenava por desafio médio, o que poria `dragon` (13,5) na frente de
    # `beast` (2,0) de todo jeito. Agora ordena por contagem: dragon 2, beast 1.
    df = relatorio_comparacao_tipos(banco_populado)
    assert list(df["tipo"]) == ["dragon", "beast"]


def test_comparacao_tipos_usa_cabecalhos_do_glossario(banco_populado):
    df = relatorio_comparacao_tipos(banco_populado)
    assert list(df.columns) == [
        "tipo",
        "media_desafio",
        "media_pontos_vida",
        "media_classe_armadura",
        "monstros",
    ]


def test_interacao_dano_produz_um_bloco_por_relacao(banco_populado, capsys):
    relatorio_interacao_dano(banco_populado)
    saida = capsys.readouterr().out
    assert all(
        titulo in saida
        for titulo in (
            "IMUNIDADE A DANO",
            "RESISTÊNCIA A DANO",
            "VULNERABILIDADE A DANO",
        )
    )


def test_interacao_dano_conta_dois_imunes_a_fire(banco_populado):
    df = relatorio_interacao_dano(banco_populado)
    imune_fire = df[(df["tipo_dano"] == "fire") & (df["relacao"] == "imunidade")]
    assert int(imune_fire["monstros"].iloc[0]) == 2


def test_interacao_dano_nao_mistura_relacoes_no_mesmo_grupo(banco_populado):
    # `poison` só aparece como resistência: se as três relações fossem agrupadas
    # juntas, ele apareceria também na imunidade.
    df = relatorio_interacao_dano(banco_populado)
    poison = df[df["tipo_dano"] == "poison"]
    assert list(poison["relacao"]) == ["resistencia"]


def test_condicoes_impostas_agrupa_por_condicao(banco_populado):
    df = relatorio_condicoes_impostas(banco_populado)
    assert df[df["condicao"] == "poisoned"]["monstros"].iloc[0] == 1


def test_condicoes_impostas_nao_traz_mais_a_coluna_de_nomes(banco_populado):
    df = relatorio_condicoes_impostas(banco_populado)
    assert "quais" not in df.columns


# --- invariantes da refatoração --------------------------------------------


def _fonte_dos_relatorios():
    return Path("bestiario/relatorios.py").read_text(encoding="utf-8")


def test_relatorios_nao_usa_mais_read_sql_query():
    assert "read_sql_query" not in _fonte_dos_relatorios()


def test_relatorios_nao_tem_mais_sql_escrito():
    # Distingue caixa de propósito: o módulo tem `from tabulate import tabulate`.
    fonte = _fonte_dos_relatorios()
    assert "SELECT" not in fonte and "FROM " not in fonte


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
