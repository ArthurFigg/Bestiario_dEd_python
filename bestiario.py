import requests

def buscar_monstro(nome):

    nome = nome.lower().strip().replace(" ", "-")
    url = f"https://api.open5e.com/monsters/{nome}/"

    resposta = requests.get(url)
    if resposta.status_code == 200:
        monstro = resposta.json()
        return monstro
    else:
        return None
    
def filtrar_monstros(chave, valor):
    url_base = "https://api.open5e.com/monsters/" 
    resposta = requests.get(url_base) # Buscamos a lista geral (Página 1)
    
    if resposta.status_code == 200:
        todos_monstros = resposta.json().get('results', [])
        
        # Aqui acontece a filtragem manual
        resultados_filtrados = []
        for monstro in todos_monstros:
            # Comparamos o valor que está no monstro com o que o usuário quer
            if str(monstro.get(chave)).lower() in str(valor).lower():
                resultados_filtrados.append(monstro)
        
        return resultados_filtrados
    return []



while True:
    print("Bem-vindo ao Bestiário de D&D 5e!")
    print("Como você deseja buscar um monstro?")
    print("1. Buscar por nome")
    print("2. Buscar por tipo")
    print("3. Buscar por desafio")
    print("4. Ver todos os monstros")
    print("5. Sair")
    opcao = input("Digite o número da opção desejada: ")

    if opcao == "1":
        nome_monstro = input("Digite o nome do monstro: ")
        monstro = buscar_monstro(nome_monstro)
        if monstro:
            print(f"Nome: {monstro['name']}")
            print(f"Tipo: {monstro['type']}")
            print(f"Desafio: {monstro['challenge_rating']}")
            print(f"Descrição: {monstro['desc']}")
            print("\n---Ações e Ataques---")
            for acao in monstro['actions']:
                print(f"Ação: {acao['name']}")
                print(f"Descrição: {acao['desc']}")
                print("\n")
        else:
            print("Monstro não encontrado.")

    elif opcao == "2":
        tipo = input("Digite o tipo do monstro (ex: dragon, undead, beast, etc.): ").strip().lower()
        monstros = filtrar_monstros('type', tipo)
        if monstros:
            print(f"Monstros do tipo {tipo}:")
            for monstro in monstros:
                print(f"- {monstro['name']} (Desafio: {monstro['challenge_rating']})")
        else:
            print("Nenhum monstro encontrado desse tipo.")

    elif opcao == "3":
        desafio = input("Digite o desafio do monstro (ex: 1/4, 1, 2, etc.): ").strip()
        monstros = filtrar_monstros('challenge_rating', desafio)
        if monstros:
            print(f"Monstros com desafio {desafio}:")
            for monstro in monstros:
                print(f"- {monstro['name']} (Tipo: {monstro['type']})")
        else:
            print("Nenhum monstro encontrado com esse desafio.")

    elif opcao == "4":
        url_base = "https://api.open5e.com/monsters/"
        resposta = requests.get(url_base, timeout=5)

        if resposta.status_code == 200:
            todos_monstros = resposta.json().get('results', [])
            print("Lista de todos os monstros:")
            for monstro in todos_monstros:
                print(f"- {monstro['name']} (Tipo: {monstro['type']}, "
                      f"Desafio: {monstro['challenge_rating']})")
        else:
            print("Não foi possível recuperar a lista de monstros.")

    elif opcao == "5":
        print("Saindo do Bestiário. Até logo!")
        break

    else:
        print("Opção inválida. Tente novamente.")





