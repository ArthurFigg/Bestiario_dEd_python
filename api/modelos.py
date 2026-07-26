"""Modelos Pydantic que materializam os schemas do `openapi.yaml`.

Nomes de campo e obrigatoriedade seguem o contrato ao pé da letra — é o que o
teste de contrato compara contra o esquema gerado pelo FastAPI. Nenhum modelo
aqui calcula nada: os valores já chegam prontos do núcleo
(`bestiario/consultas.py`); os modelos só formalizam o formato de saída.

`Sentidos` e `Deslocamento` têm todo campo opcional com `None` como padrão.
A omissão de verdade não vem daqui: vem de `response_model_exclude_unset`
nas rotas, combinado com o núcleo já devolver só as chaves presentes — um
campo nunca passado ao validar o dicionário fica "não setado" e some da
resposta.
"""

from typing import Literal

from pydantic import BaseModel


class Atributo(BaseModel):
    valor: int
    modificador: int


class Atributos(BaseModel):
    forca: Atributo
    destreza: Atributo
    constituicao: Atributo
    inteligencia: Atributo
    sabedoria: Atributo
    carisma: Atributo


class TesteDeResistencia(BaseModel):
    atributo: Literal[
        "forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"
    ]
    bonus: int


class Sentidos(BaseModel):
    visao_cega: int | None = None
    visao_penumbra: int | None = None
    sentido_tremor: int | None = None
    visao_verdadeira: int | None = None
    percepcao_passiva: int | None = None


class Deslocamento(BaseModel):
    caminhada: int | None = None
    voo: int | None = None
    natacao: int | None = None
    escalada: int | None = None
    escavacao: int | None = None
    pode_pairar: bool = False


class Pericia(BaseModel):
    pericia: str
    bonus: int


class Efeito(BaseModel):
    cd_resistencia: int | None = None
    atributo_resistencia: str | None = None
    condicao: str | None = None
    area_tipo: str | None = None
    area_tamanho: int | None = None


class Ataque(BaseModel):
    nome: str
    tipo_ataque: str | None = None
    bonus_ataque: int | None = None
    alcance: int | None = None
    alcance_longo: int | None = None
    dano_dado: str | None = None
    dano_bonus: int | None = None
    dano_tipo: str | None = None
    dano_medio: float | None = None
    dano_extra_dado: str | None = None
    dano_extra_bonus: int | None = None
    dano_extra_tipo: str | None = None
    dano_extra_medio: float | None = None


class AtaqueComMonstro(Ataque):
    """O ataque com o dono junto, para a listagem de grão de ataque."""

    monstro: str
    acao: str


class Acao(BaseModel):
    categoria: Literal["action", "legendary_action", "reaction", "special_ability"]
    nome: str
    descricao: str
    ataques: list[Ataque] = []
    efeitos: list[Efeito] = []


class MonstroResumido(BaseModel):
    """A forma enxuta, usada nas listas."""

    nome: str
    tipo: str
    tamanho: str
    desafio: float
    pontos_vida: int
    classe_armadura: int
    dano_medio: float | None = None


class Monstro(BaseModel):
    """A ficha completa, com as ações aninhadas."""

    nome: str
    tipo: str
    tamanho: str
    alinhamento: str | None = None
    desafio: float
    pontos_vida: int
    classe_armadura: int
    idiomas: str | None = None
    atributos: Atributos
    testes_de_resistencia: list[TesteDeResistencia] = []
    sentidos: Sentidos = Sentidos()
    deslocamento: Deslocamento = Deslocamento()
    pericias: list[Pericia] = []
    imunidades_a_dano: list[str] = []
    resistencias_a_dano: list[str] = []
    vulnerabilidades_a_dano: list[str] = []
    imunidades_a_condicao: list[str] = []
    ambientes: list[str] = []
    acoes: list[Acao] = []


class ListaDeMonstros(BaseModel):
    total: int
    limite: int
    deslocamento: int
    itens: list[MonstroResumido]


class ListaDeAtaques(BaseModel):
    total: int
    limite: int
    deslocamento: int
    itens: list[AtaqueComMonstro]


class LinhaDeComparacao(BaseModel):
    valor: str
    monstros: int
    media_pontos_vida: float | None = None
    media_classe_armadura: float | None = None
    media_desafio: float | None = None
    media_dano: float | None = None
    media_bonus_ataque: float | None = None


class Resumo(BaseModel):
    monstros: int
    media_pontos_vida: float | None = None
    media_classe_armadura: float | None = None
    media_desafio: float | None = None
    media_dano: float | None = None
    media_bonus_ataque: float | None = None


class Vocabulario(BaseModel):
    """Cada lista traz os valores aceitos pelo filtro de mesmo nome."""

    tipos: list[str]
    tamanhos: list[str]
    alinhamentos: list[str]
    ambientes: list[str]
    tipos_dano: list[str]
    condicoes: list[str]


class Problema(BaseModel):
    """Formato de erro do RFC 7807."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
