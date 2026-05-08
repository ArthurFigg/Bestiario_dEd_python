import requests
from banco_de_dados import criar_base_de_dados, registrar_monstro

def buscar_monstro(nome):
    nome = nome.lower().strip().replace(" ", "-")
    url = f"https://api.open5e.com/monsters/{nome}/"
    try:
        resposta = requests.get(url, timeout=10)
    except requests.exceptions.RequestException:
        print("Erro de conexão. Verifique sua internet e tente novamente.")
        return None
    if resposta.status_code == 200:
        return resposta.json()
    return None

def filtrar_monstros(chave, valor):
    url_atual = "https://api.open5e.com/monsters/"
    resultados_filtrados = []
    while url_atual:
        try:
            resposta = requests.get(url_atual, timeout=10)
        except requests.exceptions.RequestException:
            print("Erro de conexão durante a busca. Verifique sua internet.")
            break
        if resposta.status_code == 200:
            dados = resposta.json()
            for monstro in dados.get('results', []):
                if str(monstro.get(chave)).lower() in str(valor).lower():
                    resultados_filtrados.append(monstro)
            url_atual = dados.get('next')
        else:
            break
    return resultados_filtrados

def sincronizar_base_completa(conexao):
    url_atual = "https://api.open5e.com/monsters/"
    while url_atual:
        try:
            resposta = requests.get(url_atual, timeout=10)
        except requests.exceptions.RequestException:
            print("Erro de conexão durante a sincronização. Verifique sua internet.")
            break
        if resposta.status_code == 200:
            dados = resposta.json()
            for monstro in dados.get('results', []):
                registrar_monstro(conexao, monstro)
            url_atual = dados.get('next')
        else:
            break

if __name__ == "__main__":
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