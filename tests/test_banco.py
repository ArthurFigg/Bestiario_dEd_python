import sqlite3

import pytest

from bestiario.banco import criar_base_de_dados, registrar_monstro


def _adult_red_dragon():
    """Dict v2 (SRD 2014) com a estrutura real da API, usado como gabarito."""
    return {
        "name": "Adult Red Dragon",
        "size": {"name": "Huge", "key": "huge"},
        "type": {"name": "Dragon", "key": "dragon"},
        "armor_class": 19,
        "hit_points": 256,
        "challenge_rating": 17.0,
        "ability_scores": {
            "strength": 27,
            "dexterity": 10,
            "constitution": 25,
            "intelligence": 16,
            "wisdom": 13,
            "charisma": 21,
        },
        "saving_throws_all": {
            "strength": 8,
            "dexterity": 6,
            "constitution": 13,
            "intelligence": 3,
            "wisdom": 7,
            "charisma": 11,
        },
        "blindsight_range": 60,
        "darkvision_range": 120,
        "tremorsense_range": None,
        "truesight_range": None,
        "passive_perception": 23,
        "speed_all": {
            "unit": "feet",
            "walk": 40,
            "crawl": 20,
            "hover": False,
            "fly": 80,
            "burrow": 0,
            "climb": 40,
            "swim": 20,
        },
        "alignment": "chaotic evil",
        "languages": {"as_string": "Common, Draconic"},
        "resistances_and_immunities": {
            "damage_immunities": [{"name": "Fire", "key": "fire"}],
            "damage_resistances": [],
            "damage_vulnerabilities": [],
            "condition_immunities": [],
        },
        "environments": [
            {"name": "Hills", "key": "hills"},
            {"name": "Mountain", "key": "mountain"},
        ],
        "skill_bonuses": {"perception": 13, "stealth": 6},
        "actions": [
            {
                "name": "Bite",
                "action_type": "ACTION",
                "desc": (
                    "Melee Weapon Attack: +14 to hit, reach 10 ft., one target. "
                    "Hit: 19 (2d10 + 8) piercing damage plus 7 (2d6) fire damage."
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
            },
            {
                "name": "Multiattack",
                "action_type": "ACTION",
                "desc": "The dragon makes three attacks.",
                "attacks": [],
            },
        ],
        "traits": [
            {
                "name": "Legendary Resistance (3/Day)",
                "desc": "If the dragon fails a saving throw, it succeeds instead.",
            }
        ],
    }


def _guarda_com_spear():
    """Fixture mínima para o caso 'Melee or Ranged' (attacks[] com 2 entradas)."""
    return {
        "name": "Guarda de Teste",
        "size": {"key": "medium"},
        "type": {"key": "humanoid"},
        "actions": [
            {
                "name": "Spear",
                "action_type": "ACTION",
                "desc": (
                    "Melee or Ranged Weapon Attack: +3 to hit, reach 5 ft. or "
                    "range 20/60 ft., one target. Hit: 4 (1d6 + 1) piercing damage."
                ),
                "attacks": [
                    {
                        "name": "Spear Melee attack",
                        "to_hit_mod": 3,
                        "reach": 5,
                        "range": 20,
                        "long_range": 60,
                    },
                    {
                        "name": "Spear Ranged attack",
                        "to_hit_mod": 3,
                        "reach": None,
                        "range": 20,
                        "long_range": 60,
                    },
                ],
            }
        ],
    }


@pytest.fixture
def conexao(tmp_path):
    con = criar_base_de_dados(str(tmp_path / "teste.db"))
    yield con
    con.close()


def test_criar_base_cria_todas_as_tabelas(conexao):
    cursor = conexao.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = {linha[0] for linha in cursor.fetchall()}
    esperadas = {
        "monstros",
        "monstro_interacao_dano",
        "monstro_imunidade_condicao",
        "monstro_ambiente",
        "monstro_pericia",
        "acoes",
        "ataques",
        "efeitos",
    }
    assert esperadas <= tabelas


def test_ingestao_grava_sentidos(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT alcance_visao_cega, alcance_visao_penumbra, percepcao_passiva "
        "FROM monstros WHERE nome = ?",
        ("Adult Red Dragon",),
    )
    assert cursor.fetchone() == (60, 120, 23)


def test_save_nao_proficiente_usa_valor_derivado(conexao):
    # Dragões não são proficientes em save de Força; saving_throws_all traz o
    # valor derivado (mod de atributo), então a coluna não pode ficar NULL.
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT forca_save FROM monstros WHERE nome = ?", ("Adult Red Dragon",)
    )
    assert cursor.fetchone()[0] == 8


def test_ingestao_grava_velocidades(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT velocidade_voo, velocidade_escalada FROM monstros WHERE nome = ?",
        ("Adult Red Dragon",),
    )
    assert cursor.fetchone() == (80, 40)


def test_imunidade_a_dano_vira_linha_com_relacao(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT tipo_dano, relacao FROM monstro_interacao_dano WHERE monstro_nome = ?",
        ("Adult Red Dragon",),
    )
    assert cursor.fetchall() == [("fire", "imunidade")]


def test_pericia_vira_linha_com_bonus(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT bonus FROM monstro_pericia WHERE monstro_nome = ? AND pericia = ?",
        ("Adult Red Dragon", "perception"),
    )
    assert cursor.fetchone()[0] == 13


def test_reingestao_nao_duplica_linhas_de_lista(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM monstro_ambiente WHERE monstro_nome = ?",
        ("Adult Red Dragon",),
    )
    assert cursor.fetchone()[0] == 2


def test_efeitos_fica_vazia_apos_ingestao(conexao):
    # acoes/ataques passam a ser populadas na Spec 4; efeitos só na Spec 5.
    registrar_monstro(conexao, _adult_red_dragon())
    total = conexao.execute("SELECT COUNT(*) FROM efeitos").fetchone()[0]
    assert total == 0


def test_foreign_keys_esta_ativado(conexao):
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_fk_rejeita_linha_de_lista_orfa(conexao):
    # Com as FKs aplicadas, uma linha de lista que aponta para um monstro
    # inexistente é rejeitada — prova que o schema relacional é real, não decorativo.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            "INSERT INTO monstro_ambiente (monstro_nome, ambiente) VALUES (?, ?)",
            ("Monstro Inexistente", "hills"),
        )


def test_action_vira_acao_com_categoria(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    linha = conexao.execute(
        "SELECT categoria FROM acoes WHERE monstro_nome = ? AND nome_acao = ?",
        ("Adult Red Dragon", "Bite"),
    ).fetchone()
    assert linha == ("action",)


def test_action_bite_popula_ataques_com_dano_do_desc(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    linha = conexao.execute(
        "SELECT a.nome_ataque, a.bonus_ataque, a.alcance, a.dano_dado, a.dano_bonus, "
        "a.dano_tipo, a.dano_extra_dado, a.dano_extra_tipo "
        "FROM ataques a JOIN acoes ac ON a.acao_id = ac.id "
        "WHERE ac.monstro_nome = ? AND ac.nome_acao = ?",
        ("Adult Red Dragon", "Bite"),
    ).fetchone()
    assert linha == ("Bite attack", 14, 10, "2d10", 8, "piercing", "2d6", "fire")


def test_trait_vira_special_ability_sem_ataque(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    acao = conexao.execute(
        "SELECT id, categoria FROM acoes WHERE monstro_nome = ? AND nome_acao = ?",
        ("Adult Red Dragon", "Legendary Resistance (3/Day)"),
    ).fetchone()
    ataques = conexao.execute(
        "SELECT COUNT(*) FROM ataques WHERE acao_id = ?", (acao[0],)
    ).fetchone()[0]
    assert acao[1] == "special_ability" and ataques == 0


def test_action_sem_ataque_nao_gera_linha_em_ataques(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    acao = conexao.execute(
        "SELECT id FROM acoes WHERE monstro_nome = ? AND nome_acao = ?",
        ("Adult Red Dragon", "Multiattack"),
    ).fetchone()
    ataques = conexao.execute(
        "SELECT COUNT(*) FROM ataques WHERE acao_id = ?", (acao[0],)
    ).fetchone()[0]
    assert ataques == 0


def test_melee_or_ranged_gera_duas_linhas_em_ataques(conexao):
    registrar_monstro(conexao, _guarda_com_spear())
    linhas = conexao.execute(
        "SELECT a.tipo_ataque, a.alcance, a.alcance_longo "
        "FROM ataques a JOIN acoes ac ON a.acao_id = ac.id "
        "WHERE ac.monstro_nome = ? ORDER BY a.tipo_ataque",
        ("Guarda de Teste",),
    ).fetchall()
    assert linhas == [("melee_weapon", 5, None), ("ranged_weapon", 20, 60)]


def test_reingestao_nao_duplica_acoes_nem_ataques(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    registrar_monstro(conexao, _adult_red_dragon())
    acoes = conexao.execute(
        "SELECT COUNT(*) FROM acoes WHERE monstro_nome = ?", ("Adult Red Dragon",)
    ).fetchone()[0]
    ataques = conexao.execute(
        "SELECT COUNT(*) FROM ataques a JOIN acoes ac ON a.acao_id = ac.id "
        "WHERE ac.monstro_nome = ?",
        ("Adult Red Dragon",),
    ).fetchone()[0]
    assert (acoes, ataques) == (3, 1)
