"""Relatórios sobre o banco local — um por função, orquestrados em sequência.

Cada relatório monta parâmetros, chama `consultas.py` e exibe: **nenhuma query
mora aqui**. Antes da Spec 7b cada função carregava a própria consulta, e o mesmo
SQL vivendo em dois lugares diverge na primeira correção que só chega a um — os
números do terminal passariam a discordar dos do site sem ninguém perceber.

Retornar o DataFrame mantém cada relatório testável isolado; a orquestradora
`gerar_todos_relatorios` roda todos contra uma conexão. Novos relatórios entram
como funções novas, sem tocar as existentes — daí a lista `TODOS_OS_RELATORIOS`
como único ponto de registro.

Os valores exibidos são as chaves canônicas em inglês do banco (`fire`, `dragon`,
`poisoned`) — tradução para PT-BR é camada de apresentação futura (Spec 10).
"""

import sqlite3

import pandas as pd
from tabulate import tabulate

from bestiario.consultas import executar_consulta

# Relação → título do bloco no relatório de interação com dano.
_RELACOES = {
    "imunidade": "IMUNIDADE A DANO",
    "resistencia": "RESISTÊNCIA A DANO",
    "vulnerabilidade": "VULNERABILIDADE A DANO",
}


def _exibir(titulo, df):
    print(f"\n{titulo}")
    print(tabulate(df, headers="keys", tablefmt="psql", showindex=False))


def _tabela(linhas, colunas, renomear=None):
    """Seleciona as colunas que este relatório imprime e renomeia para exibição.

    O núcleo devolve sempre o conjunto pronto — a forma enxuta inteira, ou as seis
    métricas. Nenhum relatório imprime tudo isso, então selecionar é parte da
    apresentação, não do motor. Banco vazio ainda produz a tabela com cabeçalho.
    """
    df = pd.DataFrame(linhas)
    df = pd.DataFrame(columns=colunas) if df.empty else df[colunas]
    return df.rename(columns=renomear) if renomear else df


def relatorio_mais_resistentes(conexao):
    """Os 5 monstros com mais pontos de vida."""
    linhas = executar_consulta(
        conexao, ordenar_por="pontos_vida", sentido="decrescente", limite=5
    )
    df = _tabela(linhas, ["nome", "tipo", "pontos_vida", "classe_armadura"])
    _exibir("OS 5 MAIS RESISTENTES:", df)
    return df


def relatorio_top_ataques(conexao):
    """Top 5 ataques por acerto."""
    linhas = executar_consulta(
        conexao,
        modo="lista_ataques",
        ordenar_por="bonus_ataque",
        sentido="decrescente",
        limite=5,
    )
    df = _tabela(
        linhas,
        ["monstro", "nome_ataque", "bonus_ataque", "dano_dado", "dano_tipo"],
        {
            "monstro": "nome",
            "nome_ataque": "ataque",
            "bonus_ataque": "bonus",
            "dano_dado": "dano",
            "dano_tipo": "tipo_dano",
        },
    )
    _exibir("TOP 5 ATAQUES MAIS PRECISOS:", df)
    return df


def relatorio_letalidade_por_tipo(conexao):
    """Bônus de ataque médio por tipo de monstro.

    A média é **por monstro**, não por linha de ataque: antes da 7b um monstro com
    seis ataques pesava seis vezes na média do tipo dele, inflando quem tem muitas
    ações. A contagem também mudou de ataques para monstros, e a ordenação passou a
    ser por contagem — o modo `comparacao` do núcleo ordena assim, como o contrato
    promete.
    """
    linhas = executar_consulta(conexao, modo="comparacao", por="tipo")
    df = _tabela(
        linhas,
        ["valor", "media_bonus_ataque", "monstros"],
        {"valor": "tipo"},
    )
    _exibir("LETALIDADE MÉDIA POR TIPO:", df)
    return df


def relatorio_por_ambiente(conexao):
    """Quantos monstros habitam cada ambiente."""
    linhas = executar_consulta(conexao, modo="comparacao", por="ambiente")
    df = _tabela(linhas, ["valor", "monstros"], {"valor": "ambiente"})
    _exibir("MONSTROS POR AMBIENTE:", df)
    return df


def relatorio_comparacao_tipos(conexao):
    """Desafio, pontos de vida e classe de armadura médios por tipo.

    Ordena por contagem de monstros, não mais por desafio médio: é a ordenação fixa
    do modo `comparacao`.
    """
    linhas = executar_consulta(conexao, modo="comparacao", por="tipo")
    df = _tabela(
        linhas,
        [
            "valor",
            "media_desafio",
            "media_pontos_vida",
            "media_classe_armadura",
            "monstros",
        ],
        {"valor": "tipo"},
    )
    _exibir("COMPARAÇÃO ENTRE TIPOS (médias):", df)
    return df


def relatorio_interacao_dano(conexao):
    """Contagem de monstros por tipo de dano, um bloco para cada relação.

    Antes era uma tabela de duas dimensões (tipo de dano × relação). O núcleo não
    agrupa por duas dimensões — nenhum outro consumidor precisaria disso —, então
    são três comparações, cada uma restrita a uma relação. O DataFrame devolvido
    junta as três com a coluna `relacao`, para quem chama continuar tendo uma
    tabela só.
    """
    blocos = []
    for relacao, titulo in _RELACOES.items():
        linhas = executar_consulta(
            conexao, {"relacao": relacao}, modo="comparacao", por="tipo_dano"
        )
        bloco = _tabela(linhas, ["valor", "monstros"], {"valor": "tipo_dano"})
        _exibir(f"{titulo}:", bloco)
        bloco.insert(1, "relacao", relacao)
        blocos.append(bloco)
    return pd.concat(blocos, ignore_index=True)


def relatorio_condicoes_impostas(conexao):
    """Condições mais impostas por alguma ação.

    Perdeu a coluna com os nomes de quem impõe cada uma: concatenar nomes de grupo
    é agrupamento que só este relatório usaria. Quem quiser os nomes filtra por
    `impoe` e lista os monstros.
    """
    linhas = executar_consulta(conexao, modo="comparacao", por="condicao_imposta")
    df = _tabela(linhas, ["valor", "monstros"], {"valor": "condicao"})
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
