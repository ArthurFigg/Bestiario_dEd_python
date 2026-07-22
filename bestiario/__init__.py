"""Bestiário de D&D 5e — API pública do pacote."""

from bestiario.banco import (
    consultar_por_cr,
    consultar_por_tipo,
    criar_base_de_dados,
    registrar_monstro,
)
from bestiario.cliente_api import (
    buscar_monstro,
    filtrar_monstros,
    sincronizar_base_completa,
)
from bestiario.extracao import extrair_ataque
from bestiario.relatorios import gerar_todos_relatorios

__all__ = [
    "criar_base_de_dados",
    "registrar_monstro",
    "consultar_por_tipo",
    "consultar_por_cr",
    "buscar_monstro",
    "filtrar_monstros",
    "sincronizar_base_completa",
    "extrair_ataque",
    "gerar_todos_relatorios",
]
