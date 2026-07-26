"""Ponto de entrada — menu interativo no terminal. Rode com `python main.py`."""

from bestiario.banco import criar_base_de_dados, registrar_monstro
from bestiario.cliente_api import (
    buscar_monstro_na_api,
    filtrar_monstros,
    sincronizar_base_completa,
)
from bestiario.consultas import executar_consulta
from bestiario.excecoes import ValorDeFiltroInvalido
from bestiario.relatorios import gerar_todos_relatorios


def _projetar_local(linha):
    """Dicionário do núcleo → conjunto comum + origem.

    As chaves já vêm no vocabulário do contrato, então não há tradução aqui: o
    núcleo devolve `desafio`, e é `desafio` que segue para a tela.
    """
    return {
        "nome": linha["nome"],
        "tipo": linha["tipo"],
        "desafio": linha["desafio"],
        "origem": "local",
    }


def _projetar_api(monstro):
    """Dict v2 da API → mesmo conjunto comum + origem (na v2 `type` é um objeto)."""
    tipo = monstro.get("type")
    if isinstance(tipo, dict):
        tipo = tipo.get("key")
    return {
        "nome": monstro.get("name"),
        "tipo": tipo,
        "desafio": monstro.get("challenge_rating"),
        "origem": "API",
    }


def consultar_tipo(conexao, tipo):
    """Filtra por tipo: núcleo primeiro, API v2 como fallback quando não há local.

    Entrada vazia não consulta nada. O núcleo trata filtro vazio como "sem filtro"
    e devolveria os 325 — quem só apertou Enter não pediu o bestiário inteiro.
    """
    if not (tipo or "").strip():
        return []
    try:
        locais = executar_consulta(conexao, {"tipo": tipo})
    except ValorDeFiltroInvalido:
        # Tipo fora do vocabulário **local** pode existir na API. Tratar como "não
        # achei aqui" e perguntar lá é a leitura certa; vazar a exceção na tela
        # exporia detalhe de uma camada que o usuário do terminal nem sabe existir.
        locais = []
    if locais:
        return [_projetar_local(linha) for linha in locais]
    return [_projetar_api(m) for m in filtrar_monstros("type", tipo)]


def consultar_desafio(conexao, desafio):
    """Filtra por desafio: núcleo primeiro, API v2 como fallback.

    A conversão para número serve só ao núcleo, cuja coluna é REAL. O **texto
    digitado** é o que vai para a API: `challenge_rating=17` acha, `17.0` volta
    vazio sem erro nenhum. Texto não numérico é tratado como "sem resultado local".

    Entrada vazia não consulta nada — a Open5e ignora `challenge_rating=` vazio e
    devolve o SRD inteiro, e quem só apertou Enter não pediu isso.
    """
    if not (desafio or "").strip():
        return []

    locais = []
    try:
        valor = float(desafio)
    except (TypeError, ValueError):
        valor = None

    if valor is not None:
        locais = executar_consulta(
            conexao, {"desafio_min": valor, "desafio_max": valor}
        )
    if locais:
        return [_projetar_local(linha) for linha in locais]
    return [_projetar_api(m) for m in filtrar_monstros("challenge_rating", desafio)]


def _formatar_linha_filtro(resultado):
    """Rotula a procedência — [local] veio do banco, [API] veio do fallback."""
    return (
        f"[{resultado['origem']}] {resultado['nome']} "
        f"(tipo: {resultado['tipo']}, Desafio: {resultado['desafio']})"
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
            monstro = buscar_monstro_na_api(nome_monstro)
            if monstro:
                # Projeta antes de exibir: na v2 `type` é objeto, e imprimi-lo cru
                # mostrava `{'key': 'dragon', 'name': 'Dragon'}` na tela.
                dados = _projetar_api(monstro)
                print(f"Nome: {dados['nome']}")
                print(f"Tipo: {dados['tipo']}")
                print(f"Desafio: {dados['desafio']}")
                registrar_monstro(conexao_db, monstro)
                print("Monstro registrado com sucesso.")
            else:
                print("Monstro não encontrado.")

        elif opcao == "2":
            tipo = input("Digite o tipo do monstro: ").strip().lower()
            _exibir_resultados(consultar_tipo(conexao_db, tipo))

        elif opcao == "3":
            desafio = input("Digite o desafio: ").strip()
            _exibir_resultados(consultar_desafio(conexao_db, desafio))

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
