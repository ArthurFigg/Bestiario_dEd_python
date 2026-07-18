"""Extração de dados de combate (bônus de ataque e dano) a partir das ações.

A API v1 nem sempre devolve `attack_bonus`/`damage_dice` estruturados; quando
faltam, o valor é recuperado por regex no texto livre da descrição (`desc`).
Estas funções isolam essa lógica para que `banco.py` só orquestre a persistência.
"""

import re


def extrair_bonus_ataque(bonus, desc):
    """Devolve o bônus de ataque; se vier None, tenta extrair '+X to hit' do desc."""
    if bonus is not None:
        return bonus

    busca_ataque = re.search(r"([+\-]\d+) to hit", desc)
    if busca_ataque:
        return int(busca_ataque.group(1))
    return None


def extrair_dados_dano(dano, damage_bonus, desc):
    """Devolve os dados de dano combinando damage_dice + damage_bonus.

    Se `dano` (damage_dice) existe e há bônus, combina no formato "1d6 + 2".
    Se `dano` é None, faz fallback por regex procurando "(XdY + Z)" no desc.
    """
    if dano is not None:
        if damage_bonus:
            sinal = "+" if damage_bonus > 0 else "-"
            return f"{dano} {sinal} {abs(damage_bonus)}"
        return dano

    busca_dano = re.search(r"\((\d+d\d+(?:\s*[+\-]\s*\d+)?)\)", desc)
    if busca_dano:
        return busca_dano.group(1)
    return None
