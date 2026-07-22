# Bestiário de D&D 5e

![Python](https://img.shields.io/badge/Python-3.13-blue)

Ferramenta de linha de comando que consome a API pública **Open5e v2** para
buscar, armazenar e analisar os monstros de Dungeons & Dragons 5ª edição. Os
dados são normalizados em um banco SQLite local, permitindo consultas e análises
offline direto do terminal.

## Sobre

Projeto de estudo focado em consumo de API REST, modelagem de banco relacional e
análise de dados. O escopo é fixado no documento **SRD 2014** da Open5e
(`document__key=srd-2014`, ~325 criaturas), o que elimina duplicatas de outras
fontes e mantém o nome do monstro como chave.

O diferencial está na ingestão: cada ataque, efeito, tipo de dano e CD de
resistência vira um campo consultável — não texto livre. Isso é feito com uma
**extração híbrida**, que combina os campos estruturados da API v2 com expressões
regulares sobre a descrição de cada ação.

## Funcionalidades

- **Busca por nome** — consulta um monstro na API Open5e e o registra no banco local.
- **Filtro por tipo ou nível de desafio (CR)** — consulta o **SQLite primeiro** e só
  recorre à API como fallback quando não há dado local; cada resultado é rotulado com
  a origem (`[local]` ou `[API]`).
- **Sincronização completa** — baixa todos os ~325 monstros do SRD 2014 para o banco,
  de forma idempotente (re-sincronizar não duplica registros).
- **Extração estruturada** — ações, ataques (acerto, alcance, dano) e efeitos
  (CD de resistência, condição imposta, área) são extraídos do texto e normalizados.
- **Relatórios de análise** — 7 relatórios prontos via pandas + tabulate:
  - os mais resistentes (por pontos de vida);
  - ataques mais precisos (por bônus de ataque);
  - letalidade média por tipo;
  - monstros por ambiente;
  - comparação entre tipos (CR, HP e CA médios);
  - imunidade / resistência / vulnerabilidade a dano;
  - condições mais impostas e quais monstros as causam.

## Pré-requisitos

- **Python 3.13** — não precisa instalar manualmente; o `uv` baixa o interpretador
  gerenciado.
- **[uv](https://docs.astral.sh/uv/)** — gerenciador de pacotes e ambiente.

A API Open5e é gratuita e sem autenticação: não há chaves nem variáveis de ambiente
para configurar.

## Instalação

```bash
git clone https://github.com/ArthurFigg/Bestiario_dEd_python.git
cd Bestiario_dEd_python
uv sync
```

## Uso

Inicie o menu interativo:

```bash
uv run python main.py
```

O menu oferece:

```
1. Buscar e registrar por nome
2. Buscar por tipo (local primeiro, API como fallback)
3. Buscar por desafio (local primeiro, API como fallback)
4. Sincronizar base completa no SQL
5. Ver relatórios
6. Sair
```

Na primeira execução, o banco `bestiario_combate.db` é criado automaticamente (vazio).
Use a **opção 4** para populá-lo com os monstros do SRD 2014 — isso é pré-requisito
para que os filtros locais e os relatórios tenham dados.

Os relatórios também podem ser gerados de forma independente, sem abrir o menu:

```bash
uv run python bestiario/relatorios.py
```

## Estrutura do projeto

```
Bestiario_dEd_python/
├── main.py               # Ponto de entrada — menu interativo no terminal
├── bestiario/            # Pacote principal, organizado por responsabilidade
│   ├── cliente_api.py    # Comunicação HTTP com a API Open5e v2 (SRD 2014)
│   ├── banco.py          # Camada de dados: schema SQLite, ingestão e consultas locais
│   ├── extracao.py       # Extração de ataques e efeitos do texto (regex híbrida)
│   ├── relatorios.py     # Relatórios de análise (pandas + tabulate)
│   └── modelos.py        # Entidades do domínio (placeholder)
├── tests/                # Suíte de testes espelhando o pacote (pytest)
└── pyproject.toml        # Projeto e dependências gerenciados pelo uv
```

O arquivo `bestiario_combate.db` é um artefato gerado em tempo de execução (fora do
controle de versão) — recrie-o pela opção 4 do menu.

## Testes

```bash
uv run pytest -v
```

A suíte usa fixtures com banco temporário e mocks apenas na fronteira HTTP (a API
nunca é chamada de verdade nos testes).

## Dependências

| Pacote | Versão | Uso |
|---|---|---|
| requests | `>=2.32,<3.0` | Chamadas HTTP à API Open5e |
| pandas | `>=2.2,<3.0` | Manipulação de dados nos relatórios |
| tabulate | `>=0.9,<1.0` | Formatação de tabelas no terminal |

## Destaques técnicos

- **Extração híbrida** — o array estruturado da API v2 enumera os ataques (acerto e
  alcance confiáveis), enquanto a regex sobre a descrição serve de gabarito para o
  dano (o dano estruturado da v2 é notoriamente incorreto), com fallback ao
  estruturado quando a regex não casa.
- **Schema relacional normalizado** — 8 tabelas com `FOREIGN KEY` aplicadas via
  `PRAGMA foreign_keys = ON`; valores guardados em chaves canônicas em inglês
  (`fire`, `dragon`, `prone`), deixando a tradução como camada de apresentação futura.
- **Consulta local-primeiro** — os filtros priorizam o banco e só caem para a API
  quando necessário, com a origem do dado sinalizada ao usuário.
- **Ingestão idempotente** — `INSERT OR REPLACE` no monstro e limpeza das linhas
  filhas antes da reinserção, respeitando a ordem imposta pelas foreign keys.
