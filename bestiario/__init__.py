"""Bestiário de D&D 5e — API pública do pacote."""

from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.cliente_api import (
    buscar_monstro,
    filtrar_monstros,
    sincronizar_base_completa,
)
from bestiario.extracao import extrair_ataque
from bestiario.relatorios import gerar_relatorio_perfeito

__all__ = [
    "criar_base_de_dados",
    "registrar_monstro",
    "buscar_monstro",
    "filtrar_monstros",
    "sincronizar_base_completa",
    "extrair_ataque",
    "gerar_relatorio_perfeito",
]
