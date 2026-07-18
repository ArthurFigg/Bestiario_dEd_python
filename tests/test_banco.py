from bestiario.banco import criar_base_de_dados, registrar_monstro


def _monstro_fake():
    return {
        "name": "Goblin de Teste",
        "size": "Small",
        "type": "humanoid",
        "armor_class": 15,
        "hit_points": 7,
        "cr": 0.25,
        "strength": 8,
        "dexterity": 14,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 8,
        "charisma": 8,
        "actions": [
            {
                "name": "Scimitar",
                "desc": "Melee Weapon Attack: +4 to hit. Hit: 5 (1d6 + 2) slashing.",
                "attack_bonus": 4,
                "damage_dice": "1d6",
                "damage_bonus": 2,
            }
        ],
    }


def test_registrar_monstro_grava_linha_na_tabela(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "teste.db"))
    registrar_monstro(conexao, _monstro_fake())

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT nome, nivel_desafio FROM monstros WHERE nome = ?", ("Goblin de Teste",)
    )
    linha = cursor.fetchone()
    conexao.close()

    assert linha == ("Goblin de Teste", 0.25)


def test_registrar_monstro_persiste_acao_com_dano_combinado(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "teste.db"))
    registrar_monstro(conexao, _monstro_fake())

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT dados_dano FROM acoes WHERE monstro_nome = ?", ("Goblin de Teste",)
    )
    dano = cursor.fetchone()[0]
    conexao.close()

    assert dano == "1d6 + 2"


def test_ressincronizar_mesmo_monstro_nao_duplica_acoes(tmp_path):
    conexao = criar_base_de_dados(str(tmp_path / "teste.db"))
    registrar_monstro(conexao, _monstro_fake())
    registrar_monstro(conexao, _monstro_fake())

    cursor = conexao.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM acoes WHERE monstro_nome = ?", ("Goblin de Teste",)
    )
    total = cursor.fetchone()[0]
    conexao.close()

    assert total == 1
