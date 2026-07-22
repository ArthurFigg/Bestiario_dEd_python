"""Relatórios sobre o banco local — um por função, orquestrados em sequência.

Cada relatório é uma função de leitura (conexão → DataFrame) que também imprime a
tabela via tabulate. Retornar o DataFrame mantém cada relatório testável isolado; a
orquestradora `gerar_todos_relatorios` roda todos contra uma conexão. Novos
relatórios entram como funções novas, sem tocar as existentes — daí a lista
`TODOS_OS_RELATORIOS` como único ponto de registro.

Os valores exibidos são as chaves canônicas em inglês do banco (`fire`, `dragon`,
`poisoned`) — tradução para PT-BR é camada de apresentação futura (Spec 7).
"""

import sqlite3

import pandas as pd
from tabulate import tabulate


def _exibir(titulo, df):
    print(f"\n{titulo}")
    print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))


def relatorio_mais_resistentes(conexao):
    """Os 5 monstros com mais pontos de vida (tabela `monstros`, inalterada)."""
    df = pd.read_sql_query(
        """
        SELECT nome, tipo, pontos_vida AS hp, classe_armadura AS ac
        FROM monstros
        WHERE pontos_vida IS NOT NULL AND classe_armadura IS NOT NULL
        ORDER BY pontos_vida DESC
        LIMIT 5
        """,
        conexao,
    )
    _exibir("OS 5 MAIS RESISTENTES:", df)
    return df


def relatorio_top_ataques(conexao):
    """Top 5 ataques por acerto — usa `ataques.bonus_ataque` (schema das Specs 3-4),
    não mais `acoes.bonus_ataque` (coluna eliminada)."""
    df = pd.read_sql_query(
        """
        SELECT m.nome, a.nome_ataque AS ataque, a.bonus_ataque AS bonus,
               a.dano_dado AS dano, a.dano_tipo AS tipo_dano
        FROM monstros m
        JOIN acoes ac ON m.nome = ac.monstro_nome
        JOIN ataques a ON a.acao_id = ac.id
        WHERE a.bonus_ataque IS NOT NULL
        ORDER BY a.bonus_ataque DESC
        LIMIT 5
        """,
        conexao,
    )
    _exibir("TOP 5 ATAQUES MAIS PRECISOS:", df)
    return df


def relatorio_letalidade_por_tipo(conexao):
    """Bônus de ataque médio agrupado por tipo — agrega `ataques.bonus_ataque`."""
    df = pd.read_sql_query(
        """
        SELECT m.tipo,
               ROUND(AVG(a.bonus_ataque), 2) AS media_bonus,
               COUNT(a.id) AS total_ataques
        FROM monstros m
        JOIN acoes ac ON m.nome = ac.monstro_nome
        JOIN ataques a ON a.acao_id = ac.id
        WHERE a.bonus_ataque IS NOT NULL
        GROUP BY m.tipo
        ORDER BY media_bonus DESC
        """,
        conexao,
    )
    _exibir("LETALIDADE MÉDIA POR TIPO:", df)
    return df


def relatorio_por_ambiente(conexao):
    """Quantos monstros habitam cada ambiente (JOIN `monstro_ambiente`)."""
    df = pd.read_sql_query(
        """
        SELECT ambiente, COUNT(*) AS total
        FROM monstro_ambiente
        GROUP BY ambiente
        ORDER BY total DESC
        """,
        conexao,
    )
    _exibir("MONSTROS POR AMBIENTE:", df)
    return df


def relatorio_comparacao_tipos(conexao):
    """CR, HP e AC médios por tipo — comparação entre categorias de monstro."""
    df = pd.read_sql_query(
        """
        SELECT tipo,
               ROUND(AVG(nivel_desafio), 2) AS cr_medio,
               ROUND(AVG(pontos_vida), 1) AS hp_medio,
               ROUND(AVG(classe_armadura), 1) AS ac_medio,
               COUNT(*) AS total
        FROM monstros
        GROUP BY tipo
        ORDER BY cr_medio DESC
        """,
        conexao,
    )
    _exibir("COMPARAÇÃO ENTRE TIPOS (médias):", df)
    return df


def relatorio_interacao_dano(conexao):
    """Contagem de monstros por tipo de dano e relação (imunidade/resistência/
    vulnerabilidade), via `monstro_interacao_dano`."""
    df = pd.read_sql_query(
        """
        SELECT tipo_dano, relacao, COUNT(*) AS total
        FROM monstro_interacao_dano
        GROUP BY tipo_dano, relacao
        ORDER BY total DESC
        """,
        conexao,
    )
    _exibir("IMUNIDADE / RESISTÊNCIA / VULNERABILIDADE A DANO:", df)
    return df


def relatorio_condicoes_impostas(conexao):
    """Condições mais impostas e quais monstros as causam (JOIN `efeitos`→`acoes`→
    `monstros`, tabela `efeitos` da Spec 5)."""
    df = pd.read_sql_query(
        """
        SELECT e.condicao,
               COUNT(DISTINCT m.nome) AS monstros,
               GROUP_CONCAT(DISTINCT m.nome) AS quais
        FROM efeitos e
        JOIN acoes ac ON e.acao_id = ac.id
        JOIN monstros m ON ac.monstro_nome = m.nome
        WHERE e.condicao IS NOT NULL
        GROUP BY e.condicao
        ORDER BY monstros DESC
        """,
        conexao,
    )
    _exibir("CONDIÇÕES MAIS IMPOSTAS:", df)
    return df


# Ponto único de registro: adicionar um relatório = incluir a função aqui.
TODOS_OS_RELATORIOS = [
    relatorio_mais_resistentes,
    relatorio_top_ataques,
    relatorio_letalidade_por_tipo,
    relatorio_por_ambiente,
    relatorio_comparacao_tipos,
    relatorio_interacao_dano,
    relatorio_condicoes_impostas,
]


def gerar_todos_relatorios(caminho="bestiario_combate.db"):
    """Roda todos os relatórios em sequência contra o banco em `caminho`."""
    conexao = sqlite3.connect(caminho)
    print("\n" + "=" * 60)
    print(" RELATÓRIOS — BESTIÁRIO D&D 5E")
    print("=" * 60)
    for relatorio in TODOS_OS_RELATORIOS:
        relatorio(conexao)
    conexao.close()


if __name__ == "__main__":
    gerar_todos_relatorios()
