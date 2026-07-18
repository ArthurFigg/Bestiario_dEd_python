from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.relatorios import gerar_relatorio_perfeito


def test_gerar_relatorio_roda_sem_erro_sobre_banco_populado(tmp_path, capsys):
    caminho = str(tmp_path / "teste.db")
    conexao = criar_base_de_dados(caminho)
    registrar_monstro(conexao, {
        "name": "Goblin de Teste",
        "type": "humanoid",
        "armor_class": 15,
        "hit_points": 7,
        "cr": 0.25,
        "actions": [{
            "name": "Scimitar",
            "desc": "Melee Weapon Attack: +4 to hit.",
            "attack_bonus": 4,
            "damage_dice": "1d6",
            "damage_bonus": 2,
        }],
    })
    conexao.close()

    gerar_relatorio_perfeito(caminho)

    saida = capsys.readouterr().out
    assert "RELATÓRIO DE DADOS CONSOLIDADOS" in saida
