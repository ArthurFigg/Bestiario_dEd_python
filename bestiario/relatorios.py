"""Relatórios prontos sobre o banco local usando pandas + tabulate."""

import sqlite3

import pandas as pd
from tabulate import tabulate


def gerar_relatorio_perfeito(caminho="bestiario_combate.db"):
    conn = sqlite3.connect(caminho)

    print("\n" + "=" * 60)
    print(" RELATÓRIO DE DADOS CONSOLIDADOS - D&D 5E")
    print("=" * 60)

    query_fortes = """
    SELECT nome, tipo, pontos_vida AS HP, classe_armadura AS AC
    FROM monstros
    WHERE pontos_vida IS NOT NULL
      AND classe_armadura IS NOT NULL
    ORDER BY pontos_vida DESC LIMIT 5
    """
    df_fortes = pd.read_sql_query(query_fortes, conn)
    print("\n OS 5 MAIS RESISTENTES (DADOS COMPLETOS):")
    print(tabulate(df_fortes, headers='keys', tablefmt='psql', showindex=False))

    query_ataques = """
    SELECT
        monstros.nome,
        acoes.nome_acao AS Ataque,
        acoes.bonus_ataque AS Bonus,
        acoes.dados_dano AS Dano
    FROM monstros
    JOIN acoes ON monstros.nome = acoes.monstro_nome
    WHERE acoes.bonus_ataque IS NOT NULL
      AND acoes.dados_dano IS NOT NULL
    ORDER BY acoes.bonus_ataque DESC LIMIT 5
    """
    df_ataques = pd.read_sql_query(query_ataques, conn)
    print("\n TOP 5 ATAQUES MAIS PRECISOS (DADOS COMPLETOS):")
    print(tabulate(df_ataques, headers='keys', tablefmt='psql', showindex=False))

    query_stats = """
    SELECT
        monstros.tipo,
        ROUND(AVG(acoes.bonus_ataque), 2) AS Media_Bonus,
        COUNT(acoes.id) AS Total_Acoes
    FROM monstros
    JOIN acoes ON monstros.nome = acoes.monstro_nome
    WHERE acoes.bonus_ataque IS NOT NULL
    GROUP BY monstros.tipo
    HAVING Total_Acoes > 20
    ORDER BY Media_Bonus DESC
    """
    df_stats = pd.read_sql_query(query_stats, conn)
    print("\n LETALIDADE MÉDIA POR CATEGORIA:")
    print(tabulate(df_stats, headers='keys', tablefmt='psql', showindex=False))

    conn.close()
    print("\n" + "=" * 60)
    print("Filtragem concluída: Apenas registros íntegros foram exibidos.")


if __name__ == "__main__":
    gerar_relatorio_perfeito()
