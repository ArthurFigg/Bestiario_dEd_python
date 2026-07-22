"""Camada de dados: criação do schema relacional (SQLite) e ingestão do monstro.

Schema normalizado de 8 tabelas: `monstros` (nível monstro) + 4 tabelas de lista
(dano, condição, ambiente, perícia) + `acoes`/`ataques` (Spec 4) e `efeitos`
(Spec 5). A ingestão lê o dict estruturado da API v2 (SRD 2014) e grava nível
monstro, tabelas de lista, ações/ataques e efeitos (save/condição/área, extraídos
do `desc` — parte assumidamente lossy). Valores guardados em chaves canônicas em
inglês da v2 (`fire`, `dragon`) — tradução é camada de apresentação futura.
"""

import sqlite3

from bestiario.extracao import extrair_ataque, extrair_efeitos

# action_type da v2 → valor da coluna `categoria` (traits usam 'special_ability').
CATEGORIA_POR_ACTION_TYPE = {
    "ACTION": "action",
    "LEGENDARY_ACTION": "legendary_action",
    "REACTION": "reaction",
}

# (campo em resistances_and_immunities, valor da coluna `relacao`)
RELACOES_DANO = [
    ("damage_immunities", "imunidade"),
    ("damage_resistances", "resistencia"),
    ("damage_vulnerabilities", "vulnerabilidade"),
]

TABELAS_DE_LISTA = [
    "monstro_interacao_dano",
    "monstro_imunidade_condicao",
    "monstro_ambiente",
    "monstro_pericia",
]


def criar_base_de_dados(caminho="bestiario_combate.db"):
    conexao = sqlite3.connect(caminho)
    cursor = conexao.cursor()
    # SQLite ignora FOREIGN KEY sem este PRAGMA (é por conexão, não persiste no .db).
    cursor.execute("PRAGMA foreign_keys = ON")

    cursor.execute("""
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
            carisma INTEGER,
            alcance_visao_cega INTEGER,
            alcance_visao_penumbra INTEGER,
            alcance_sentido_tremor INTEGER,
            alcance_visao_verdadeira INTEGER,
            percepcao_passiva INTEGER,
            forca_save INTEGER,
            destreza_save INTEGER,
            constituicao_save INTEGER,
            inteligencia_save INTEGER,
            sabedoria_save INTEGER,
            carisma_save INTEGER,
            velocidade_caminhada INTEGER,
            velocidade_voo INTEGER,
            velocidade_natacao INTEGER,
            velocidade_escalada INTEGER,
            velocidade_escavacao INTEGER,
            pode_pairar INTEGER,
            alinhamento TEXT,
            idiomas TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monstro_interacao_dano (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            tipo_dano TEXT,
            relacao TEXT,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monstro_imunidade_condicao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            condicao TEXT,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monstro_ambiente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            ambiente TEXT,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monstro_pericia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            pericia TEXT,
            bonus INTEGER,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    """)

    # Tabelas de combate — criadas vazias aqui; populadas nas Specs 4-5.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monstro_nome TEXT,
            categoria TEXT,
            nome_acao TEXT,
            descricao TEXT,
            FOREIGN KEY (monstro_nome) REFERENCES monstros (nome)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ataques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao_id INTEGER,
            nome_ataque TEXT,
            tipo_ataque TEXT,
            bonus_ataque INTEGER,
            alcance INTEGER,
            alcance_longo INTEGER,
            dano_dado TEXT,
            dano_bonus INTEGER,
            dano_tipo TEXT,
            dano_extra_dado TEXT,
            dano_extra_bonus INTEGER,
            dano_extra_tipo TEXT,
            FOREIGN KEY (acao_id) REFERENCES acoes (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS efeitos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao_id INTEGER,
            cd_resistencia INTEGER,
            atributo_resistencia TEXT,
            condicao TEXT,
            area_tipo TEXT,
            area_tamanho INTEGER,
            FOREIGN KEY (acao_id) REFERENCES acoes (id)
        )
    """)

    conexao.commit()
    return conexao


def registrar_monstro(conexao, monstro):
    """Ingere um dict da v2: nível monstro + tabelas de lista + ações/ataques."""
    cursor = conexao.cursor()
    nome = monstro.get("name")
    # Apaga os filhos ANTES do INSERT OR REPLACE do monstro: com as FKs ativas, o
    # REPLACE deleta a linha-pai e falharia se filhos ainda a referenciassem.
    _apagar_tabelas_de_lista(cursor, nome)
    _apagar_acoes(cursor, nome)
    _gravar_monstro(cursor, monstro)
    _inserir_tabelas_de_lista(cursor, monstro)
    _inserir_acoes_e_ataques(cursor, monstro)
    conexao.commit()


def _gravar_monstro(cursor, m):
    tamanho = (m.get("size") or {}).get("key")
    tipo = (m.get("type") or {}).get("key")
    idiomas = (m.get("languages") or {}).get("as_string")
    atributos = m.get("ability_scores") or {}
    saves = m.get("saving_throws_all") or {}
    velocidade = m.get("speed_all") or {}

    cursor.execute(
        """
        INSERT OR REPLACE INTO monstros (
            nome, tamanho, tipo, classe_armadura, pontos_vida, nivel_desafio,
            forca, destreza, constituicao, inteligencia, sabedoria, carisma,
            alcance_visao_cega, alcance_visao_penumbra, alcance_sentido_tremor,
            alcance_visao_verdadeira, percepcao_passiva,
            forca_save, destreza_save, constituicao_save,
            inteligencia_save, sabedoria_save, carisma_save,
            velocidade_caminhada, velocidade_voo, velocidade_natacao,
            velocidade_escalada, velocidade_escavacao, pode_pairar,
            alinhamento, idiomas
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            m.get("name"),
            tamanho,
            tipo,
            m.get("armor_class"),
            m.get("hit_points"),
            m.get("challenge_rating"),
            atributos.get("strength"),
            atributos.get("dexterity"),
            atributos.get("constitution"),
            atributos.get("intelligence"),
            atributos.get("wisdom"),
            atributos.get("charisma"),
            m.get("blindsight_range"),
            m.get("darkvision_range"),
            m.get("tremorsense_range"),
            m.get("truesight_range"),
            m.get("passive_perception"),
            saves.get("strength"),
            saves.get("dexterity"),
            saves.get("constitution"),
            saves.get("intelligence"),
            saves.get("wisdom"),
            saves.get("charisma"),
            velocidade.get("walk"),
            velocidade.get("fly"),
            velocidade.get("swim"),
            velocidade.get("climb"),
            velocidade.get("burrow"),
            1 if velocidade.get("hover") else 0,
            m.get("alignment"),
            idiomas,
        ),
    )


def _apagar_tabelas_de_lista(cursor, nome):
    """Remove as linhas de lista do monstro (reingestão idempotente)."""
    for tabela in TABELAS_DE_LISTA:
        cursor.execute(f"DELETE FROM {tabela} WHERE monstro_nome = ?", (nome,))


def _inserir_tabelas_de_lista(cursor, m):
    nome = m.get("name")
    interacoes = m.get("resistances_and_immunities") or {}
    for campo, relacao in RELACOES_DANO:
        for item in interacoes.get(campo) or []:
            cursor.execute(
                "INSERT INTO monstro_interacao_dano "
                "(monstro_nome, tipo_dano, relacao) VALUES (?, ?, ?)",
                (nome, item.get("key"), relacao),
            )

    for item in interacoes.get("condition_immunities") or []:
        cursor.execute(
            "INSERT INTO monstro_imunidade_condicao (monstro_nome, condicao) "
            "VALUES (?, ?)",
            (nome, item.get("key")),
        )

    for item in m.get("environments") or []:
        cursor.execute(
            "INSERT INTO monstro_ambiente (monstro_nome, ambiente) VALUES (?, ?)",
            (nome, item.get("key")),
        )

    for pericia, bonus in (m.get("skill_bonuses") or {}).items():
        cursor.execute(
            "INSERT INTO monstro_pericia (monstro_nome, pericia, bonus) "
            "VALUES (?, ?, ?)",
            (nome, pericia, bonus),
        )


def _apagar_acoes(cursor, nome):
    """Apaga efeitos, ataques e ações do monstro — filhos antes do pai, sem órfãos."""
    cursor.execute(
        "DELETE FROM efeitos WHERE acao_id IN "
        "(SELECT id FROM acoes WHERE monstro_nome = ?)",
        (nome,),
    )
    cursor.execute(
        "DELETE FROM ataques WHERE acao_id IN "
        "(SELECT id FROM acoes WHERE monstro_nome = ?)",
        (nome,),
    )
    cursor.execute("DELETE FROM acoes WHERE monstro_nome = ?", (nome,))


def _inserir_acoes_e_ataques(cursor, m):
    nome = m.get("name")
    for acao in m.get("actions") or []:
        categoria = CATEGORIA_POR_ACTION_TYPE.get(acao.get("action_type"))
        desc = acao.get("desc", "")
        acao_id = _inserir_acao(cursor, nome, categoria, acao)
        for attack in acao.get("attacks") or []:
            _inserir_ataque(cursor, acao_id, desc, attack)
        _inserir_efeitos(cursor, acao_id, desc)
    # traits são habilidades passivas: viram `acoes` special_ability, sem ataque.
    for trait in m.get("traits") or []:
        acao_id = _inserir_acao(cursor, nome, "special_ability", trait)
        _inserir_efeitos(cursor, acao_id, trait.get("desc", ""))


def _inserir_acao(cursor, nome, categoria, acao):
    cursor.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?, ?, ?, ?)",
        (nome, categoria, acao.get("name"), acao.get("desc")),
    )
    return cursor.lastrowid


def _inserir_ataque(cursor, acao_id, desc, attack):
    d = extrair_ataque(desc, attack)
    cursor.execute(
        """
        INSERT INTO ataques (
            acao_id, nome_ataque, tipo_ataque, bonus_ataque, alcance, alcance_longo,
            dano_dado, dano_bonus, dano_tipo,
            dano_extra_dado, dano_extra_bonus, dano_extra_tipo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            acao_id,
            d["nome_ataque"],
            d["tipo_ataque"],
            d["bonus_ataque"],
            d["alcance"],
            d["alcance_longo"],
            d["dano_dado"],
            d["dano_bonus"],
            d["dano_tipo"],
            d["dano_extra_dado"],
            d["dano_extra_bonus"],
            d["dano_extra_tipo"],
        ),
    )


def _inserir_efeitos(cursor, acao_id, desc):
    for efeito in extrair_efeitos(desc):
        cursor.execute(
            """
            INSERT INTO efeitos (
                acao_id, cd_resistencia, atributo_resistencia,
                condicao, area_tipo, area_tamanho
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                acao_id,
                efeito["cd_resistencia"],
                efeito["atributo_resistencia"],
                efeito["condicao"],
                efeito["area_tipo"],
                efeito["area_tamanho"],
            ),
        )
