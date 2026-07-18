"""Camada de dados: criação do SQLite e persistência de monstros e ações.

Schema atual de 2 tabelas (monstros + acoes), ainda alimentado pela API v1.
A regex de extração de combate vive em `extracao.py`; aqui só orquestramos.
"""

import sqlite3

from bestiario.extracao import extrair_bonus_ataque, extrair_dados_dano

CATEGORIAS_ACAO = ["actions", "special_abilities", "legendary_actions", "reactions"]


def criar_base_de_dados(caminho="bestiario_combate.db"):
    conexao = sqlite3.connect(caminho)
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

    # Reinsere as ações do zero para não duplicar ao ressincronizar o mesmo monstro.
    cursor.execute("DELETE FROM acoes WHERE monstro_nome = ?", (monstro.get('name'),))

    todas_acoes = []
    for categoria in CATEGORIAS_ACAO:
        lista_categoria = monstro.get(categoria)
        if lista_categoria:  # Só adiciona se não for None ou vazio
            todas_acoes.extend(lista_categoria)

    for acao in todas_acoes:
        desc = acao.get('desc', '')
        bonus = extrair_bonus_ataque(acao.get('attack_bonus'), desc)
        dano = extrair_dados_dano(acao.get('damage_dice'), acao.get('damage_bonus'), desc)

        cursor.execute('''
            INSERT INTO acoes (monstro_nome, nome_acao, descricao, bonus_ataque, dados_dano)
            VALUES (?, ?, ?, ?, ?)
        ''', (monstro.get('name'), acao.get('name'), desc, bonus, dano))

    conexao.commit()
