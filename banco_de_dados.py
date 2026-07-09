import sqlite3
import re

def criar_base_de_dados():
    conexao = sqlite3.connect("bestiario_combate.db")
    cursor = conexao.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monstros (
            nome TEXT PRIMARY KEY,
            tamanho TEXT,
            tipo TEXT,
            classe_armadura INTEGER,
            pontos_vida INTEGER,
            nivel_desafio REAL,
            forca INTEGER,
            destreza INTEGER,
            constituicao INTEGER,
            inteligencia INTEGER,
            sabedoria INTEGER,
            carisma INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            nome_acao TEXT,
            descricao TEXT,
            bonus_ataque INTEGER,
            dados_dano TEXT,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    ''')

    conexao.commit()
    return conexao

def registrar_monstro(conexao, monstro):
    cursor = conexao.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO monstros 
        (nome, tamanho, tipo, classe_armadura, pontos_vida, nivel_desafio, 
         forca, destreza, constituicao, inteligencia, sabedoria, carisma)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        monstro.get('name'), 
        monstro.get('size'), 
        monstro.get('type'),
        monstro.get('armor_class'), 
        monstro.get('hit_points'), 
        monstro.get('cr'),
        monstro.get('strength'), 
        monstro.get('dexterity'), 
        monstro.get('constitution'),
        monstro.get('intelligence'), 
        monstro.get('wisdom'), 
        monstro.get('charisma')
    ))

    cursor.execute("DELETE FROM acoes WHERE monstro_nome = ?", (monstro.get('name'),))

    todas_acoes = []
    for categoria in ['actions', 'special_abilities', 'legendary_actions', 'reactions']:
        lista_categoria = monstro.get(categoria)
        if lista_categoria: # Só adiciona se não for None ou vazio
            todas_acoes.extend(lista_categoria)

    for acao in todas_acoes:
        nome_acao = acao.get('name')
        desc = acao.get('desc', '')
        bonus = acao.get('attack_bonus')
        dano = acao.get('damage_dice')

        if bonus is None:
            busca_ataque = re.search(r"([+\-]\d+) to hit", desc)
            if busca_ataque:
                bonus = int(busca_ataque.group(1))

        damage_bonus = acao.get('damage_bonus')
        if dano is not None and damage_bonus:
            sinal = "+" if damage_bonus > 0 else "-"
            dano = f"{dano} {sinal} {abs(damage_bonus)}"
        elif dano is None:
            busca_dano = re.search(r"\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)", desc)
            if busca_dano:
                dano = busca_dano.group(1)

        cursor.execute('''
            INSERT INTO acoes (monstro_nome, nome_acao, descricao, bonus_ataque, dados_dano)
            VALUES (?, ?, ?, ?, ?)
        ''', (monstro.get('name'), nome_acao, desc, bonus, dano))

    conexao.commit()