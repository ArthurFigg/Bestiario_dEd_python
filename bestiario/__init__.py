"""Bestiário de D&D 5e — API pública do pacote."""

from bestiario.banco import (
    consultar_por_cr,
    consultar_por_tipo,
    criar_base_de_dados,
    registrar_monstro,
)
from bestiario.calculos import media_de_dado, modificador, saves_proficientes
from bestiario.cliente_api import (
    buscar_monstro_na_api,
    filtrar_monstros,
    sincronizar_base_completa,
)
from bestiario.consultas import (
    DIMENSOES,
    FILTROS,
    METRICAS,
    ORDENACOES,
    PRESETS,
    abrir_conexao,
    buscar_monstro,
    contar,
    executar_consulta,
    montar_consulta,
    resolver_nomes,
    vocabulario,
)
from bestiario.excecoes import (
    ErroDoBestiario,
    FiltroDesconhecido,
    ValorDeFiltroInvalido,
)
from bestiario.extracao import extrair_ataque
from bestiario.relatorios import gerar_todos_relatorios

__all__ = [
    "criar_base_de_dados",
    "registrar_monstro",
    "consultar_por_tipo",
    "consultar_por_cr",
    # Consulta remota na Open5e. O nome diz de onde o dado vem: depois da 7a,
    # `buscar_monstro` sem qualificador é a consulta local, o caminho principal.
    "buscar_monstro_na_api",
    "filtrar_monstros",
    "sincronizar_base_completa",
    "extrair_ataque",
    "gerar_todos_relatorios",
    "media_de_dado",
    "modificador",
    "saves_proficientes",
    "montar_consulta",
    "executar_consulta",
    "contar",
    "buscar_monstro",
    "resolver_nomes",
    "vocabulario",
    "abrir_conexao",
    "FILTROS",
    "DIMENSOES",
    "METRICAS",
    "ORDENACOES",
    "PRESETS",
    "ErroDoBestiario",
    "FiltroDesconhecido",
    "ValorDeFiltroInvalido",
]
