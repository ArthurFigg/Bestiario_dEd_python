"""Fixture compartilhada: banco de teste isolado e cliente HTTP contra a API e o site.

Nasce aqui (Spec 8) porque vem antes da Spec 9a, que **amplia** esta fixture em
vez de criar a sua — API e site precisam do mesmo conjunto de monstros
nomeados (`Adult Red Dragon`, `Goblin`, dois nomes contendo "drag"). Nunca
toca `bestiario_combate.db`: está fora do git e não existe no CI. As Specs 9b
e 9c ampliam de novo, em vez de criar fixtures próprias.

Cada requisição do `TestClient` abre a **própria** conexão para o arquivo de
teste, em vez de compartilhar uma única conexão global: o FastAPI roda
endpoints síncronos numa thread do pool, e uma conexão `sqlite3` só pode ser
usada na mesma thread que a criou. Um arquivo temporário por teste (via
`tmp_path`) resolve isso sem precisar de banco `:memory:` com cache
compartilhado — mais simples, e ainda assim isolado do arquivo real.
"""

import pytest
from fastapi.testclient import TestClient

from bestiario.banco import criar_base_de_dados
from bestiario.calculos import modificador
from bestiario.consultas import abrir_conexao


def _monstro(cursor, nome, **campos):
    padrao = {
        "tamanho": "large",
        "tipo": "dragon",
        "classe_armadura": 18,
        "pontos_vida": 200,
        "nivel_desafio": 10.0,
        "forca": 20,
        "destreza": 10,
        "constituicao": 20,
        "inteligencia": 14,
        "sabedoria": 12,
        "carisma": 18,
        # `forca_save` propositalmente proficiente (13 != modificador(20)=5):
        # é o que dá à Ficha um teste de resistência para exercitar.
        "forca_save": 13,
        "destreza_save": modificador(10),
        "constituicao_save": modificador(20),
        "inteligencia_save": modificador(14),
        "sabedoria_save": modificador(12),
        "carisma_save": modificador(18),
        "velocidade_caminhada": 40,
        "velocidade_voo": 80,
        "velocidade_natacao": 0,
        "velocidade_escalada": None,
        "velocidade_escavacao": None,
        "pode_pairar": 1,
        "alinhamento": "chaotic evil",
        "idiomas": "Common, Draconic",
        "alcance_visao_cega": 60,
        "alcance_visao_penumbra": 120,
        "alcance_sentido_tremor": None,
        "alcance_visao_verdadeira": None,
        "percepcao_passiva": 23,
    }
    padrao.update(campos)
    colunas = ["nome"] + list(padrao)
    valores = [nome] + list(padrao.values())
    cursor.execute(
        f"INSERT INTO monstros ({','.join(colunas)}) "
        f"VALUES ({','.join('?' * len(colunas))})",
        valores,
    )


def semear_bestiario(conexao):
    """Conjunto pequeno e conhecido, montado para exercitar cada regra da API."""
    c = conexao.cursor()
    # Atributos e testes do SRD: For não é proficiente (save 8 == modificador
    # de 27), os outros quatro são. Fiel de propósito — monstro com o nome do
    # SRD e números inventados é armadilha para quem ler o teste depois.
    _monstro(
        c,
        "Adult Red Dragon",
        pontos_vida=256,
        nivel_desafio=17.0,
        classe_armadura=19,
        forca=27,
        forca_save=8,
        destreza=10,
        destreza_save=6,
        constituicao=25,
        constituicao_save=13,
        inteligencia=16,
        inteligencia_save=3,
        sabedoria=13,
        sabedoria_save=7,
        carisma=21,
        carisma_save=11,
    )
    _monstro(
        c,
        "Adult Blue Dragon",
        pontos_vida=225,
        nivel_desafio=16.0,
        classe_armadura=19,
    )
    _monstro(
        c,
        "Goblin",
        tipo="humanoid",
        tamanho="small",
        pontos_vida=7,
        nivel_desafio=0.25,
        classe_armadura=15,
        forca=8,
        forca_save=modificador(8),
        alinhamento=None,
        velocidade_voo=0,
        pode_pairar=0,
        alcance_visao_cega=None,
        alcance_visao_penumbra=60,
        percepcao_passiva=9,
    )
    _monstro(
        c,
        "Vampire",
        tipo="undead",
        pontos_vida=144,
        nivel_desafio=13.0,
        forca_save=modificador(18),
    )

    c.executemany(
        "INSERT INTO monstro_interacao_dano (monstro_nome, tipo_dano, relacao) "
        "VALUES (?,?,?)",
        [
            ("Adult Red Dragon", "fire", "imunidade"),
            ("Vampire", "necrotic", "resistencia"),
            ("Vampire", "radiant", "vulnerabilidade"),
        ],
    )
    c.executemany(
        "INSERT INTO monstro_ambiente (monstro_nome, ambiente) VALUES (?,?)",
        [
            ("Adult Red Dragon", "mountain"),
            ("Adult Red Dragon", "desert"),
            ("Adult Blue Dragon", "desert"),
            ("Goblin", "forest"),
            ("Vampire", "urban"),
        ],
    )
    c.executemany(
        "INSERT INTO monstro_imunidade_condicao (monstro_nome, condicao) VALUES (?,?)",
        [("Vampire", "charmed")],
    )
    c.executemany(
        "INSERT INTO monstro_pericia (monstro_nome, pericia, bonus) VALUES (?,?,?)",
        [("Adult Red Dragon", "perception", 13)],
    )

    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Adult Red Dragon", "action", "Bite", "Melee Weapon Attack..."),
    )
    mordida = c.lastrowid
    c.execute(
        "INSERT INTO ataques (acao_id, nome_ataque, tipo_ataque, bonus_ataque, "
        "alcance, dano_dado, dano_bonus, dano_tipo, dano_medio, dano_extra_dado, "
        "dano_extra_bonus, dano_extra_tipo, dano_extra_medio) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            mordida,
            "Bite attack",
            "melee_weapon",
            14,
            10,
            "2d10",
            8,
            "piercing",
            19.0,
            "2d6",
            2,
            "fire",
            9.0,
        ),
    )
    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Adult Red Dragon", "action", "Fire Breath", "DC 21 Dexterity..."),
    )
    sopro = c.lastrowid
    c.execute(
        "INSERT INTO efeitos (acao_id, cd_resistencia, atributo_resistencia, "
        "condicao, area_tipo, area_tamanho) VALUES (?,?,?,?,?,?)",
        (sopro, 21, "dexterity", None, "cone", 60),
    )
    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Vampire", "action", "Bite", "..."),
    )
    mordida_vampiro = c.lastrowid
    c.execute(
        "INSERT INTO ataques (acao_id, nome_ataque, bonus_ataque, dano_dado, "
        "dano_bonus, dano_medio) VALUES (?,?,?,?,?,?)",
        (mordida_vampiro, "Bite attack", 9, "1d6", 4, 7.5),
    )
    c.execute(
        "INSERT INTO efeitos (acao_id, cd_resistencia, atributo_resistencia, "
        "condicao, area_tipo, area_tamanho) VALUES (?,?,?,?,?,?)",
        (mordida_vampiro, 18, "constitution", "charmed", None, None),
    )
    # Ação lendária: a ficha separa por categoria, e sem uma delas o teste da
    # seção própria não teria o que exercitar.
    c.execute(
        "INSERT INTO acoes (monstro_nome, categoria, nome_acao, descricao) "
        "VALUES (?,?,?,?)",
        ("Adult Red Dragon", "legendary_action", "Wing Attack", "..."),
    )
    asa = c.lastrowid
    # Duas condições na mesma ação viram duas linhas em `efeitos`, repetindo CD
    # e área — é assim que a Spec 5 grava, e a ficha tem de exibir um selo de CD
    # e um de área, não dois de cada.
    c.executemany(
        "INSERT INTO efeitos (acao_id, cd_resistencia, atributo_resistencia, "
        "condicao, area_tipo, area_tamanho) VALUES (?,?,?,?,?,?)",
        [
            (asa, 19, "dexterity", "prone", "cone", 15),
            (asa, 19, "dexterity", "grappled", "cone", 15),
        ],
    )
    conexao.commit()


@pytest.fixture
def caminho_banco_de_teste(tmp_path):
    """Caminho de um SQLite de teste populado — nunca `bestiario_combate.db`."""
    caminho = str(tmp_path / "teste.db")
    conexao = criar_base_de_dados(caminho)
    semear_bestiario(conexao)
    conexao.close()
    return caminho


@pytest.fixture
def caminho_banco_vazio(tmp_path):
    """Banco no schema certo, sem nenhum monstro — exercita o 503."""
    caminho = str(tmp_path / "vazio.db")
    criar_base_de_dados(caminho).close()
    return caminho


def _cliente_apontado_para(app, caminho):
    """Substitui `obter_conexao` pelo arquivo de teste, para qualquer aplicação.

    `api/app.py` e `web/app.py` importam a **mesma** função `obter_conexao` de
    `api/rotas.py` — sobrescrever essa única chave em `dependency_overrides`
    vale para as duas, seja a app da Spec 8 ou a que a Spec 9a inclui.
    """
    from api.rotas import obter_conexao

    def _conexao_de_teste():
        conexao = abrir_conexao(caminho)
        try:
            yield conexao
        finally:
            conexao.close()

    app.dependency_overrides[obter_conexao] = _conexao_de_teste
    cliente = TestClient(app)
    try:
        yield cliente
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cliente_api(caminho_banco_de_teste):
    """`TestClient` contra `api.app:app`, apontado para o banco de teste populado."""
    from api.app import app

    yield from _cliente_apontado_para(app, caminho_banco_de_teste)


@pytest.fixture
def cliente_api_banco_vazio(caminho_banco_vazio):
    """`TestClient` contra `api.app:app`, apontado para um banco sem monstros."""
    from api.app import app

    yield from _cliente_apontado_para(app, caminho_banco_vazio)


@pytest.fixture
def cliente_web(caminho_banco_de_teste):
    """`TestClient` contra `web.app:app`, apontado para o banco de teste populado."""
    from web.app import app

    yield from _cliente_apontado_para(app, caminho_banco_de_teste)


@pytest.fixture
def cliente_web_banco_vazio(caminho_banco_vazio):
    """`TestClient` contra `web.app:app`, apontado para um banco sem monstros."""
    from web.app import app

    yield from _cliente_apontado_para(app, caminho_banco_vazio)
