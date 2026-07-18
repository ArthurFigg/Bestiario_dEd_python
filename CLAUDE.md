# CLAUDE.md — Bestiário de D&D 5e

## O que é esse projeto

Bestiário de D&D 5e é uma ferramenta em Python que consome a API pública
**Open5e v2** (`https://api.open5e.com/v2/creatures/`, escopo SRD 2014 —
~325 criaturas) para buscar, armazenar e analisar os monstros do D&D 5ª
edição. O objetivo é criar um banco de dados local rico o suficiente para
permitir pesquisas e análises sofisticadas — hoje via terminal/SQL,
futuramente via front-end web acessível a qualquer pessoa sem conhecimento
técnico.

## Estrutura de arquivos

```
Bestiario_dEd_python/
├── main.py               # Ponto de entrada — menu interativo no terminal
├── bestiario/            # Pacote organizado por responsabilidade
│   ├── __init__.py       # Re-exportações da API pública do pacote
│   ├── cliente_api.py    # Comunicação HTTP com a API Open5e
│   ├── banco.py          # Camada de dados: criação do SQLite e inserção
│   ├── extracao.py       # Extração de bônus/dano das ações (regex)
│   ├── relatorios.py     # Relatórios prontos usando pandas + tabulate
│   └── modelos.py        # Entidades do domínio (placeholder até a Spec 3)
├── tests/                # Testes pytest espelhando o pacote
├── pyproject.toml        # Projeto e dependências gerenciados por uv
├── bestiario_combate.db  # Banco SQLite com os dados já sincronizados
└── CLAUDE.md             # Este arquivo
```

## Tecnologias usadas

- **Python 3.13** gerenciado por `uv` (interpretador baixado pelo próprio uv)
- **SQLite** via módulo `sqlite3` da stdlib
- **requests** — chamadas HTTP para a API Open5e
- **pandas** — manipulação de dados para relatórios
- **tabulate** — formatação de tabelas no terminal
- **API externa**: `https://api.open5e.com/v2/creatures/` (paginada, sem auth), fixada no documento SRD 2014 via `document__key=srd-2014`

## Schema do banco de dados

Schema relacional normalizado de **8 tabelas** (v2, SRD 2014). Valores guardados em
chaves canônicas em inglês da API (`fire`, `dragon`, `prone`) — tradução é camada de
apresentação futura. `FOREIGN KEY` aplicadas via `PRAGMA foreign_keys = ON` (por
conexão, setado em `criar_base_de_dados`).

### `monstros` (nível monstro)
`nome` (TEXT PK), `tamanho`, `tipo` (chaves da v2: `huge`, `dragon`),
`classe_armadura`, `pontos_vida` (INTEGER), `nivel_desafio` (REAL, de
`challenge_rating`), atributos `forca`…`carisma` (INTEGER, de `ability_scores`).
Enriquecida com:
- **Sentidos**: `alcance_visao_cega`, `alcance_visao_penumbra`,
  `alcance_sentido_tremor`, `alcance_visao_verdadeira`, `percepcao_passiva` — NULL
  quando o sentido não existe.
- **Saves**: `forca_save`…`carisma_save` — de `saving_throws_all`, valores derivados
  (nunca NULL por falta de proficiência).
- **Velocidade**: `velocidade_caminhada`, `velocidade_voo`, `velocidade_natacao`,
  `velocidade_escalada`, `velocidade_escavacao`, `pode_pairar` (0/1) — de `speed_all`.
- **Lore**: `alinhamento` (TEXT), `idiomas` (TEXT, de `languages.as_string`).

### Tabelas de lista (uma linha por valor — análise exata via COUNT/JOIN)
- `monstro_interacao_dano` (id PK, monstro_nome FK, `tipo_dano`, `relacao` =
  `imunidade`|`resistencia`|`vulnerabilidade`)
- `monstro_imunidade_condicao` (id PK, monstro_nome FK, `condicao`)
- `monstro_ambiente` (id PK, monstro_nome FK, `ambiente`)
- `monstro_pericia` (id PK, monstro_nome FK, `pericia`, `bonus`)

### Tabelas de combate (criadas vazias; populadas nas Specs 4-5)
- `acoes` (id PK, monstro_nome FK, `categoria`, `nome_acao`, `descricao`)
- `ataques` (id PK, acao_id FK, `nome_ataque`, `tipo_ataque`, `bonus_ataque`,
  `alcance`, `alcance_longo`, `dano_dado`, `dano_bonus`, `dano_tipo`,
  `dano_extra_dado`, `dano_extra_bonus`, `dano_extra_tipo`)
- `efeitos` (id PK, acao_id FK, `cd_resistencia`, `atributo_resistencia`,
  `condicao`, `area_tipo`, `area_tamanho`)

Idempotência: `INSERT OR REPLACE` em `monstros`; `DELETE` das linhas de lista do
monstro **antes** do REPLACE (as FKs ativas exigem apagar filhos antes do pai).

## O que já funciona

- [x] Busca individual de monstro por nome via API
- [x] Filtro por tipo ou CR percorrendo todas as páginas da API
- [x] Sincronização completa da API para o banco local (opção 4 do menu)
- [x] Inserção com `INSERT OR REPLACE` — re-rodar não duplica
- [x] Extração de `bonus_ataque` e `dados_dano` via regex quando a API não retorna direto
- [x] `dados_dano` combina `damage_dice` + `damage_bonus` da API (ex: "1d6 + 2")
- [x] Relatórios básicos: top 5 mais resistentes, top 5 ataques, letalidade por tipo
- [x] Git configurado e com histórico
- [x] Guard `if __name__ == "__main__"` em `bestiario.py` — menu não roda ao importar
- [x] Tratamento de erros HTTP com `try/except` nas três funções de chamada à API
- [x] `nivel_desafio` salvo como REAL (campo `challenge_rating` da v2 — ordenação numérica correta)
- [x] URLs migradas para a API v2 (`/v2/creatures/`, SRD 2014) — ver Spec 2
- [x] Idempotência no re-sync: `INSERT OR REPLACE` em `monstros` + `DELETE` das linhas
  de lista antes do REPLACE (as FKs ativas exigem apagar filhos antes do pai)
- [x] `bestiario_combate.db` regenerado para o schema v2 (SRD 2014): **325 monstros**,
  tabelas de lista populadas (473 interações de dano, 339 imunidades a condição,
  1638 ambientes, 527 perícias); `acoes`/`ataques`/`efeitos` vazias até as Specs 4-5.
  Artefato regenerável — fora do git, recriar via opção 4 do menu.
- [x] `.gitignore` criado — `__pycache__/` e `*.pyc` fora do controle de versão

## O que está incompleto ou pode melhorar

- [x] ~~**Dados faltando no banco**~~ — **resolvido na Spec 3**: imunidades/
  resistências/vulnerabilidades a dano, imunidades a condição, ambientes,
  alinhamento, sentidos, velocidade, saves e perícias agora são persistidos
  (tabela `monstros` enriquecida + 4 tabelas de lista normalizadas).
- [ ] **Categoria das ações não é salva**: todas as ações vão para a mesma
  tabela sem coluna indicando se é `action`, `legendary_action`, etc.
  Além disso, `bonus_actions` não é capturado nem como categoria.
- [ ] **Sem pesquisa no banco local**: todas as buscas de tipo/CR vão para a
  API mesmo depois de sincronizar. Deveria consultar o SQLite primeiro.
- [ ] **Sem front-end**: a interface é 100% terminal.
- [ ] **Sem testes automatizados**.
- [ ] **Sem `requirements.txt`**: dependências não estão documentadas formalmente.

## Próximas melhorias planejadas — status (specs)

As melhorias abaixo foram especificadas no conjunto de 6 specs em
`.claude/specs/` (todas com `Revisão: aprovada` após o `/spec-review` da
Sessão 5). Implementação ainda não iniciada — ordem em "Plano de 6 specs".

1. **Enriquecer o schema** (imunidades, resistências, vulnerabilidades,
   imunidades a condições, ambientes, alinhamento, sentidos, velocidade,
   saves) → **Spec 3** (`schema_e_ingestao_monstro`) — aprovada.
2. **Coluna de categoria em `acoes` + capturar categorias de ação** →
   **Spec 4** (`extracao_acoes_ataques`) — aprovada. Ressalva empírica:
   `BONUS_ACTION` não existe no SRD 2014 (0 de 944 ações); a categoria cobre
   `action`/`legendary_action`/`reaction`/`special_ability`.
3. **Consulta local primeiro** → **Spec 6** (`relatorios_e_consulta_local`) —
   aprovada. Decisão: local primeiro, com a API v2 como fallback.
4. **Documentar dependências** → resolvido de forma diferente: `uv` +
   `pyproject.toml` com teto de versão na **Spec 1** (`fundacao`), em vez de
   `requirements.txt` (regra do CLAUDE.md global).
5. **Expandir relatórios** (por ambiente, comparação entre tipos, imunidade/
   resistência a dano, condições impostas) → **Spec 6** — aprovada.
6. **Front-end web** — ainda **não especificado**; segue como passo futuro
   (junto da tradução PT-BR, planejada como Spec 7 — ver Sessão 4).

Não mapeadas 1:1 na lista antiga, mas parte do plano: **Spec 2**
(migração para a API v2, SRD 2014) e **Spec 5** (extração de efeitos —
save DC, condição, área; parte lossy isolada).

## Histórico de sessões

### Sessão 2 — 2026-05-08

**O que foi feito nesta sessão:**

1. **`bestiario.py` — URLs atualizadas para `/v1/`**
   A Open5e adicionou versionamento na API. O endpoint antigo
   `https://api.open5e.com/monsters/` passou a retornar 404.
   As três URLs do código foram atualizadas para `https://api.open5e.com/v1/monsters/`.

2. **`banco_de_dados.py` — `dados_dano` agora combina `damage_dice` + `damage_bonus`**
   A API v1 separa o dano em dois campos: `damage_dice` (ex: `"1d6"`) e
   `damage_bonus` (ex: `2`). O código anterior salvava só `"1d6"`, ignorando
   o bônus. Agora combina os dois: `"1d6 + 2"`. Se `damage_dice` for None,
   o regex na descrição ainda é usado como fallback.

3. **`banco_de_dados.py` — `nivel_desafio` corrigido para REAL**
   Antes: salvo como TEXT usando `challenge_rating` (ex: `"1/4"`, `"14"`),
   o que quebrava ordenações numéricas. Agora: usa o campo `cr` da API,
   que já vem como float (ex: `0.25`, `14.0`), e a coluna é do tipo REAL.

**Atenção:** as correções acima ficaram sem commit por quase dois meses —
o banco já tinha sido ressincronizado localmente com o schema novo, mas o
código nunca foi versionado.

### Sessão 3 — 2026-07-08

**O que foi feito nesta sessão:**

1. **Projeto migrou de pasta** — de `Documents\projetos\treino` para
   `OneDrive\Imagens\Documentos\projetos\treino\Bestiario_dEd_python`.
2. **`git pull`** — trouxe 1 commit do origin (`README.md`), fast-forward
   sem conflito.
3. **Commit das correções pendentes da sessão 2** (URLs `v1`, `nivel_desafio`
   REAL, combinação de `dados_dano`, `DELETE FROM acoes` antes de reinserir)
   que estavam havia meses no working tree sem nunca ter sido versionadas.
4. **`.gitignore` criado** e `__pycache__/*.pyc` removido do controle de
   versão (`git rm --cached`).
5. **Verificação do banco via query direta** confirmou que
   `bestiario_combate.db` já estava consistente com o schema novo — o item
   "banco desatualizado, prioridade máxima" foi removido da lista de
   melhorias por já estar resolvido.

**Pendente, decisão do usuário:**
- `bestiario_combate.db` (4MB) continua *tracked* no git — considerar se vale
  a pena versionar um binário de dados desse tamanho, ou tratar como artefato
  gerado (adicionar ao `.gitignore` e documentar como recriar via sync).
- Dar `git push` dos commits locais.

**Próximo passo sugerido:** enriquecer o schema com os campos identificados
(imunidades, resistências, ambientes, etc.) uma coluna por vez.

## Sobre o desenvolvedor — leia antes de qualquer ação

**Objetivo do projeto**: portfólio profissional para mostrar a recrutadores.
Isso significa que qualidade, legibilidade e boas práticas importam tanto
quanto funcionalidade. O código precisa impressionar quem vai ler, não só
funcionar.

**Como trabalhar comigo**: explica cada mudança em detalhes antes ou depois
de fazê-la. Não só "o quê" mas "por quê" — qual problema resolve, qual padrão
está sendo seguido, o que eu deveria aprender com aquela decisão. Se for um
conceito novo, dá um exemplo concreto. Nunca faz uma mudança grande sem
explicar o raciocínio por trás.

**O que mais me empolga**: a lógica Python e a integração com a API. Quando
for escolher por onde começar uma melhoria, prioriza o lado do código Python
e da comunicação com a Open5e. O banco de dados e o front-end vêm depois.

**Perfil**: desenvolvedor em formação, ainda aprendendo. Prefere soluções
simples e legíveis em vez de código sofisticado demais. Se existir uma forma
mais simples de resolver, escolhe ela e explica por que é a melhor escolha
para este momento.

## Contexto para decisões futuras

- O projeto tem como público-alvo final **usuários sem conhecimento técnico**,
  então o front-end precisa ser simples e intuitivo
- A API Open5e é **gratuita e sem autenticação** — basta HTTP GET, endpoint atual: `https://api.open5e.com/v2/creatures/` (escopo SRD 2014, `document__key=srd-2014`)
- O banco `bestiario_combate.db` está no schema v2 (SRD 2014): 325 monstros, com
  `acoes`/`ataques`/`efeitos` vazias até as Specs 4-5. É artefato regenerável (fora do
  git; recriar via opção 4 do menu)
- O código será lido por recrutadores — comentários claros e estrutura
  organizada são tão importantes quanto funcionalidade
- Preferência por **soluções simples e legíveis** em vez de over-engineering

## Como rodar

```bash
# Instalar dependências
uv sync

# Menu principal
python main.py

# Só os relatórios
python bestiario/relatorios.py
```

## Setup do ambiente

**Python:** 3.13 — penúltima estável (N-1); 3.14 é a mais recente e o projeto
não usa recurso exclusivo dela, então 3.13 dá o piso mais compatível para
pandas. O `uv` baixa o interpretador gerenciado, independente do que há na máquina.

**Comandos de execucao:**
```bash
uv init --python 3.13
uv add requests>=2.32,<3.0 pandas>=2.2,<3.0 tabulate>=0.9,<1.0
uv add --dev pytest>=8.0,<9.0
```

**Pastas a criar:**
```bash
mkdir -p bestiario tests
touch bestiario/__init__.py
```

**Conteudo do `.env.example`:**
```
nenhuma
```
(A API Open5e é gratuita e sem autenticação — não há variável de ambiente
agora. A tradução via Grok, planejada para a Spec 7 futura, trará uma chave
quando for especificada.)

**Dependencias que ficam de fora agora** (entram quando a spec chegar):
- nenhuma — a Spec 1 (fundação) já move `cliente_api.py` (requests),
  `relatorios.py` (pandas + tabulate) e `banco.py` (sqlite3, stdlib), então
  as três deps de produção são necessárias desde o início.
- Specs 2-6 não introduzem dependências novas (SQLite é stdlib).
- Front-end web + cliente Grok para tradução: Spec 7 (futura, ainda não especificada).

**CI — `.github/workflows/tests.yml`:**
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run pytest -v
```

## API Open5e — referência rápida

```
GET https://api.open5e.com/v2/creatures/?document__key=srd-2014        # lista SRD 2014 (325)
GET https://api.open5e.com/v2/creatures/?document__key=srd-2014&name__iexact=Goblin  # por nome
GET https://api.open5e.com/v2/creatures/?document__key=srd-2014&type=humanoid         # filtro
GET https://api.open5e.com/v2/creatures/?document__key=srd-2014&challenge_rating=17   # filtro CR
GET https://api.open5e.com/v2/creatures/{key}/   # criatura específica (ex: srd_goblin)
Paginação: campo "next" no JSON com a URL da próxima página (já carrega os params)
Sem autenticação necessária
```

### Sessao 4 — 2026-07-16

**Decisao macro:** reconstrucao da camada de dados para "tudo virar dado
analisavel" (cada ataque, efeito, tipo de dano, DC de save vira campo
consultavel, nao texto livre). Diagnostico da sessao: a tabela `monstros`
ja estava 100% preenchida e os NULLs em `acoes` (bonus_ataque/dados_dano)
eram legitimos (habilidades passivas) — a regex atual acerta 100% dos casos
com dano real. O ganho de verdade e enriquecer o schema e estruturar
ataques/efeitos.

**Decisoes de arquitetura tomadas:**
1. **Migrar da API v1 para a v2** (`/v2/creatures/`) — a v2 entrega sentidos,
   saves, resistencias, velocidade e ataques ja estruturados.
2. **Apenas SRD 2014** (`document__key=srd-2014`, ~325 monstros). A v2 mistura
   ~10 fontes (SRD, A5E, Tome of Beasts, etc.) e repete o mesmo monstro entre
   elas; restringir ao SRD oficial elimina duplicatas e mantem `nome` como
   PRIMARY KEY. (Atencao: isso e MENOS que os 2319 atuais — troca quantidade
   por qualidade/riqueza.)
3. **Extracao hibrida**: usa os campos estruturados da v2 + regex no `desc`
   como gabarito (a conversao v2 tem erros/omissoes nos ataques — ex: dano de
   fogo secundario faltando, damage_type errado).
4. **Schema relacional normalizado**: monstros + acoes + ataques + efeitos +
   tabelas de lista (monstro_interacao_dano com coluna `relacao`,
   monstro_imunidade_condicao, monstro_ambiente, monstro_pericia). ~9 tabelas.
5. **Traducao PT-BR** e passo FUTURO, so no front-end (Spec 7): dict estatico
   para vocabulario controlado + Grok (tier gratuito) para texto livre. Banco
   e terminal ficam em ingles. Ver memoria `traducao-camada-frontend`.
6. **Banco e artefato regeneravel**: migracao = apagar `bestiario_combate.db`
   uma vez e re-sincronizar com o schema novo.

**Plano de 6 specs (criterio: menor pedaco testavel autonomamente):**
1. Fundacao (uv + pyproject + reestrutura em pacote `bestiario/`, entrada
   vira `main.py`) — v1 preservado
2. Cliente API v2 (SRD 2014)
3. Novo schema + ingestao dos campos do monstro
4. Extracao de acoes + ataques (nucleo hibrido) — PROXIMA
5. Extracao de efeitos (save DC, condicao, area — parte lossy, isolada)
6. Relatorios + consulta local primeiro

**Feito nesta sessao:** specs 1, 2 e 3 criadas em `.claude/specs/`
(`fundacao.md`, `cliente_api_v2.md`, `schema_e_ingestao_monstro.md`), todas
com `Revisao: pendente`. Nenhum codigo implementado ainda.

**Proximo passo (retomar aqui):** criar as specs 4, 5 e 6 (rodar `/spec`),
depois `/spec-review` no conjunto (obrigatorio antes de implementar), depois
executar setup e implementar spec por spec. Ha um hook de gate ativo que
bloqueia implementacao enquanto houver specs com revisao pendente.

### Sessão 5 — 2026-07-16

**O que foi feito nesta sessão:**

1. **Specs 4, 5 e 6 criadas** (`/spec`): `extracao_acoes_ataques.md`,
   `extracao_efeitos.md`, `relatorios_e_consulta_local.md`. Completam o plano
   de 6 specs iniciado na Sessão 4.
2. **`/spec-review` do conjunto** — 6 verificadores em paralelo, checando cada
   spec contra o CLAUDE.md e contra as demais. Resultado: nenhum conflito de
   contrato entre specs (interfaces de tabelas/colunas batem); dependências
   confirmam a ordem numérica (dados → extração → apresentação).
3. **Correção aplicada**: a Spec 4 não populava `ataques.nome_ataque` (coluna
   do schema da Spec 3, ficaria sempre NULL). Ajustada para preencher a partir
   de `attacks[].name`.
4. **Decisão de nomenclatura** (afetou Specs 3-6): as colunas de combate que
   estavam em inglês foram traduzidas para consistência com o resto do schema
   (que é em português) e com a regra global de idioma —
   `to_hit`→`bonus_ataque`, `save_dc`→`cd_resistencia`,
   `save_atributo`→`atributo_resistencia`. Valores de dado seguem em inglês
   canônico da API (`fire`, `prone`, `dexterity`), conforme decidido na Sessão 4.
5. **Todas as 6 specs marcadas `Revisão: aprovada`** — gate de implementação
   destravado.

**Diagnósticos empíricos da API v2 que embasaram as specs** (verificados
percorrendo os 325 monstros do SRD 2014 via `?document__key=srd-2014`):
- A conversão estruturada de ataques da v2 é **não confiável para dano**:
  `damage_type` vem ~99% como `"thunder"` (lixo constante) e `damage_bonus`
  ~99% `null`. Confiáveis: `to_hit_mod`, `reach`, `range`, `attack_type`,
  `damage_die_count`/`type`. Por isso a extração híbrida usa o **`desc` como
  gabarito do dano** (regex parseia o bloco "Hit:" inteiro) e o estruturado
  só para acerto/alcance.
- O array `attacks[]` estruturado **sinaliza 100% dos ataques** (0 ações com
  `attacks: []` e "to hit" no `desc`) — serve de enumerador; a regex só corrige.
- As 18 ações "Melee or Ranged" viram 2 linhas em `ataques` (a v2 já as separa
  em 2 entradas de `attacks[]`).
- `action_type` no SRD 2014: `ACTION`, `LEGENDARY_ACTION`, `REACTION` (sem
  `BONUS_ACTION`); `traits` é campo separado (habilidades passivas).
- **Save/condição/área não têm nenhum campo estruturado** na v2 — 100% regex
  no `desc` (por isso a Spec 5 é a parte "lossy"). No SRD: 208 ações com save,
  266 com algum efeito, 54 com 2+ condições, ~96 emanações "within X ft".
- Cobertura das tabelas ricas no SRD: 322/325 com ambiente, 160 com
  resistência/imunidade — todos os relatórios da Spec 6 nascem com dado real.

**Setup executado (fim da sessão):** `/planejar-setup` documentou a seção
"Setup do ambiente" e o setup foi rodado — `uv init --python 3.13`
(Python 3.13.12), `uv add` das 3 deps de produção (requests 2.34.2,
pandas 2.3.3, tabulate 0.10.0) + `pytest 8.4.2` como dev, pacote `bestiario/`
(com `__init__.py`) e `tests/` criados. `.gitignore` ganhou `.venv/` e
`.pytest_cache/`. `main.py` é o placeholder do `uv init` (será substituído
pelo menu na Spec 1). `pytest` roda (sem testes ainda).

**Próximo passo (retomar aqui):** implementar a **Spec 1 (fundacao)** —
mover o código flat (`bestiario.py`, `banco_de_dados.py`,
`analise_bestiario.py`) para os módulos do pacote `bestiario/` preservando o
comportamento (ainda v1), com os testes; fechar com `/spec-close`. Depois
seguir a ordem 2→6.
