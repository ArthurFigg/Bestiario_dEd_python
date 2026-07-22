"""Ponto de entrada — menu interativo no terminal. Rode com `python main.py`."""

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
from bestiario.relatorios import gerar_todos_relatorios


def _projetar_local(linha):
    """Linha do SQLite (nome, tipo, nivel_desafio) → conjunto comum + origem."""
    nome, tipo, cr = linha
    return {"nome": nome, "tipo": tipo, "cr": cr, "origem": "local"}


def _projetar_api(monstro):
    """Dict v2 da API → mesmo conjunto comum + origem (na v2 `type` é um objeto)."""
    tipo = monstro.get("type")
    if isinstance(tipo, dict):
        tipo = tipo.get("key")
    return {
        "nome": monstro.get("name"),
        "tipo": tipo,
        "cr": monstro.get("challenge_rating"),
        "origem": "API",
    }


def consultar_tipo(conexao, tipo):
    """Filtra por tipo: SQLite primeiro, API v2 como fallback quando não há local."""
    locais = consultar_por_tipo(conexao, tipo)
    if locais:
        return [_projetar_local(linha) for linha in locais]
    return [_projetar_api(m) for m in filtrar_monstros("type", tipo)]


def consultar_cr(conexao, cr):
    """Filtra por CR: SQLite primeiro, API v2 como fallback quando não há local.

    CR inválido faz `consultar_por_cr` devolver vazio (sem quebrar); então o fluxo
    cai para o fallback, que também não acha nada, e o menu exibe a mensagem padrão.
    """
    locais = consultar_por_cr(conexao, cr)
    if locais:
        return [_projetar_local(linha) for linha in locais]
    return [_projetar_api(m) for m in filtrar_monstros("challenge_rating", cr)]


def _formatar_linha_filtro(resultado):
    """Rotula a procedência — [local] veio do banco, [API] veio do fallback."""
    return (
        f"[{resultado['origem']}] {resultado['nome']} "
        f"(tipo: {resultado['tipo']}, CR: {resultado['cr']})"
    )


def _exibir_resultados(resultados):
    if not resultados:
        print("Nenhum monstro encontrado.")
        return
    for resultado in resultados:
        print(_formatar_linha_filtro(resultado))


def executar_menu():
    conexao_db = criar_base_de_dados()

    while True:
        print("\nBem-vindo ao Bestiário de D&D 5e!")
        print("1. Buscar e registrar por nome")
        print("2. Buscar por tipo (local primeiro, API como fallback)")
        print("3. Buscar por desafio (local primeiro, API como fallback)")
        print("4. Sincronizar base completa no SQL")
        print("5. Ver relatórios")
        print("6. Sair")
        opcao = input("Digite o número da opção desejada: ")

        if opcao == "1":
            nome_monstro = input("Digite o nome do monstro: ")
            monstro = buscar_monstro(nome_monstro)
            if monstro:
                print(f"Nome: {monstro['name']}")
                print(f"Tipo: {monstro['type']}")
                print(f"Desafio: {monstro['challenge_rating']}")
                registrar_monstro(conexao_db, monstro)
                print("Monstro registrado com sucesso.")
            else:
                print("Monstro não encontrado.")

        elif opcao == "2":
            tipo = input("Digite o tipo do monstro: ").strip().lower()
            _exibir_resultados(consultar_tipo(conexao_db, tipo))

        elif opcao == "3":
            desafio = input("Digite o desafio: ").strip()
            _exibir_resultados(consultar_cr(conexao_db, desafio))

        elif opcao == "4":
            print("Sincronizando... Isso pode demorar alguns minutos.")
            sincronizar_base_completa(conexao_db)
            print("Banco de dados atualizado com sucesso.")

        elif opcao == "5":
            gerar_todos_relatorios()

        elif opcao == "6":
            break


if __name__ == "__main__":
    executar_menu()
