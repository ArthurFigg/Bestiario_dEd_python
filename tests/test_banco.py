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


def test_tabelas_de_combate_ficam_vazias_apos_ingestao(conexao):
    registrar_monstro(conexao, _adult_red_dragon())
    cursor = conexao.cursor()
    total = sum(
        cursor.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        for tabela in ("acoes", "ataques", "efeitos")
    )
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
