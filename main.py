"""Ponto de entrada — menu interativo no terminal. Rode com `python main.py`."""

from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.cliente_api import (
    buscar_monstro,
    filtrar_monstros,
    sincronizar_base_completa,
)


def executar_menu():
    conexao_db = criar_base_de_dados()

    while True:
        print("\nBem-vindo ao Bestiário de D&D 5e!")
        print("1. Buscar e registrar por nome")
        print("2. Buscar por tipo (Pesquisa completa)")
        print("3. Buscar por desafio (Pesquisa completa)")
        print("4. Sincronizar base completa no SQL")
        print("5. Sair")
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
            monstros = filtrar_monstros('type', tipo)
            if monstros:
                for monstro in monstros:
                    print(f"- {monstro['name']} (Desafio: {monstro['challenge_rating']})")
            else:
                print("Nenhum monstro encontrado.")

        elif opcao == "3":
            desafio = input("Digite o desafio: ").strip()
            monstros = filtrar_monstros('challenge_rating', desafio)
            if monstros:
                for monstro in monstros:
                    print(f"- {monstro['name']} (Tipo: {monstro['type']})")
            else:
                print("Nenhum monstro encontrado.")

        elif opcao == "4":
            print("Sincronizando... Isso pode demorar alguns minutos.")
            sincronizar_base_completa(conexao_db)
            print("Banco de dados atualizado com sucesso.")

        elif opcao == "5":
            break


if __name__ == "__main__":
    executar_menu()
