# CLAUDE.md — Bestiário de D&D 5e

## O que é esse projeto

Bestiário de D&D 5e é uma ferramenta em Python que consome a API pública
**Open5e v2** (`https://api.open5e.com/v2/creatures/`, escopo SRD 2014 —
~325 criaturas) para buscar, armazenar e analisar os monstros do D&D 5ª
edição. O objetivo é criar um banco de dados local rico o suficiente para
permitir pesquisas e análises sofisticadas — hoje via terminal/SQL, e a partir
das Specs 7-9 via site e API HTTP acessíveis a qualquer pessoa sem conhecimento
técnico.

## Estrutura de arquivos

```
Bestiario_dEd_python/
├── main.py               # Ponto de entrada — menu interativo no terminal
├── bestiario/            # Núcleo: domínio, dados e consulta (sem web)
│   ├── __init__.py       # Re-exportações da API pública do pacote
│   ├── cliente_api.py    # Comunicação HTTP com a API Open5e
│   ├── banco.py          # Camada de dados: criação do SQLite e inserção
│   ├── extracao.py       # Extração de bônus/dano das ações (regex)
│   ├── calculos.py       # Derivações puras: modificador, saves, média de dado
│   ├── consultas.py      # Montagem parametrizada de query + presets
│   ├── excecoes.py       # Erros de domínio (dimensão/filtro inválido)
│   ├── relatorios.py     # Relatórios do terminal — delegam a consultas.py
│   └── modelos.py        # Entidades do domínio (placeholder até a Spec 3)
├── api/                  # Superfície JSON — FastAPI, sem SQL próprio
├── web/                  # Superfície HTML — FastAPI + Jinja2, inclui a API
│   ├── __init__.py
│   ├── app.py             # Aplicação servida por `uv run uvicorn web.app:app`
│   ├── rotas.py           # Raiz, `/monstros`; `/relatorios` e `/pesquisar` (9b/9c)
│   ├── templates/          # `base.html` (moldura) e `todos.html`
│   └── static/estilo.css   # Identidade visual portada do esboço aprovado
├── openapi.yaml          # Contrato da API, comparado ao gerado pelo código
├── tests/                # Testes pytest espelhando o pacote
├── pyproject.toml        # Projeto e dependências gerenciados por uv
├── bestiario_combate.db  # Banco SQLite com os dados já sincronizados
└── CLAUDE.md             # Este arquivo
```

**Regra de camadas:** `api/` e `web/` são duas apresentações da mesma coisa e
**nenhuma das duas escreve SQL** — as duas chamam `bestiario/consultas.py`. A
camada de consulta não sabe se quem pergunta é um navegador ou um script.

## Tecnologias usadas

- **Python 3.13** gerenciado por `uv` (interpretador baixado pelo próprio uv)
- **SQLite** via módulo `sqlite3` da stdlib
- **requests** — chamadas HTTP para a API Open5e
- **pandas** — manipulação de dados para relatórios
- **tabulate** — formatação de tabelas no terminal
- **FastAPI + uvicorn** — servidor da API JSON e, desde a Spec 9a, do site
- **Jinja2** — templates HTML renderizados no servidor (`web/templates/`)
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

### Tabelas de combate (`acoes`/`ataques` populadas na Spec 4; `efeitos` na Spec 5)
- `acoes` (id PK, monstro_nome FK, `categoria`, `nome_acao`, `descricao`) —
  `categoria` = `action`|`legendary_action`|`reaction` (de `action_type`) ou
  `special_ability` (de `traits`); `BONUS_ACTION` não existe no SRD 2014.
- `ataques` (id PK, acao_id FK, `nome_ataque`, `tipo_ataque`, `bonus_ataque`,
  `alcance`, `alcance_longo`, `dano_dado`, `dano_bonus`, `dano_tipo`, `dano_medio`,
  `dano_extra_dado`, `dano_extra_bonus`, `dano_extra_tipo`, `dano_extra_medio`) —
  extração híbrida: `attacks[]` estruturado enumera os ataques (acerto/alcance),
  regex do `desc` é o gabarito do dano; fallback para `damage_die_count`/`type` se
  a regex falha.
  **`dano_medio`/`dano_extra_medio` (REAL) são gravados, não calculados na leitura**
  (Revisão 1 da Spec 4, 2026-07-26): são coluna de ordenação da API e convivem com
  paginação — calculados em Python depois do `LIMIT`, ordenariam só a página já
  recortada, sem erro nenhum. Dano fixo (`1 piercing damage`) grava o próprio bônus;
  só ataque sem dado **nem** bônus grava NULL — 4 dos 542.
- `efeitos` (id PK, acao_id FK, `cd_resistencia`, `atributo_resistencia`,
  `condicao`, `area_tipo`, `area_tamanho`) — criada vazia; populada na Spec 5.

Idempotência: `INSERT OR REPLACE` em `monstros`; `DELETE` das linhas de lista do
monstro **antes** do REPLACE (as FKs ativas exigem apagar filhos antes do pai).

## O que já funciona

- [x] Busca individual de monstro por nome via API
- [x] Filtro por tipo ou CR percorrendo todas as páginas da API
- [x] Sincronização completa da API para o banco local (opção 4 do menu)
- [x] Inserção com `INSERT OR REPLACE` — re-rodar não duplica
- [x] População de `acoes` (com coluna `categoria`) e `ataques` via extração
  híbrida — array `attacks[]` estruturado como enumerador + regex do `desc` como
  gabarito do dano; fallback para o estruturado quando a regex falha (Spec 4)
- [x] População de `efeitos` (save CD + atributo, incluindo escape DC; condição
  imposta — 15 condições canônicas do SRD, uma linha por condição; área
  geométrica nomeada ou emanação `within X ft`) — 100% regex sobre o `desc`,
  parte assumidamente lossy da ingestão (Spec 5)
- [x] Relatórios básicos: top 5 mais resistentes, top 5 ataques, letalidade por tipo
- [x] Git configurado e com histórico
- [x] Guard `if __name__ == "__main__"` em `bestiario.py` — menu não roda ao importar
- [x] Tratamento de erros HTTP com `try/except` nas três funções de chamada à API
- [x] `nivel_desafio` salvo como REAL (campo `challenge_rating` da v2 — ordenação numérica correta)
- [x] URLs migradas para a API v2 (`/v2/creatures/`, SRD 2014) — ver Spec 2
- [x] Idempotência no re-sync: `INSERT OR REPLACE` em `monstros` + `DELETE` das linhas
  de lista antes do REPLACE (as FKs ativas exigem apagar filhos antes do pai)
- [x] `bestiario_combate.db` no schema v2 (SRD 2014), **totalmente populado**:
  325 monstros, 1476 ações, 542 ataques, 518 efeitos, mais as tabelas de lista
  (473 interações de dano, 339 imunidades a condição, 1638 ambientes, 527 perícias).
  Artefato regenerável — fora do git, recriar via opção 4 do menu.
  **Armadilha conhecida:** o arquivo pode ficar defasado em relação ao código sem
  nenhum sinal de erro. Em 2026-07-25 a tabela `efeitos` estava com 0 linhas porque
  o banco fora sincronizado antes da Spec 5 entrar — o código estava certo o tempo
  todo. Ao estranhar dado ausente, re-sincronizar antes de investigar o código.
- [x] `.gitignore` criado — `__pycache__/` e `*.pyc` fora do controle de versão
- [x] Consulta local-primeiro nos filtros de tipo/desafio (opções 2 e 3): consulta o
  banco antes da API v2, com fallback para a v2 quando não há dado local e rótulo
  de origem `[local]`/`[API]` na saída (Spec 6). Desde a **Spec 7c** quem responde a
  parte local é o núcleo (`consultas.py`), não `banco.py`; a política não mudou.
  Entrada vazia não consulta nada — nem o núcleo, nem a API.
- [x] **Aba Pesquisar** (Spec 9c): fichas acumuladas lado a lado, sem limite de
  quantidade. O bloco de estatísticas (`_ficha.html`) é compartilhado com a aba
  Todos, que abre **uma** linha por vez no modo Completa. **Navegação nos dois
  sentidos**: o selo da ficha (`imune a fire`) leva ao relatório já filtrado, e o
  resultado do relatório vem para cá como filtros — nunca como lista de nomes, que
  estouraria a URL. A API tem dois consumidores dentro do próprio projeto: a busca
  incremental por `fetch` em `/api/v1/monstros?nome=` e o link JSON de cada ficha.
  Sem JavaScript o campo continua funcionando como formulário comum.
- [x] **Aba Relatórios** (Spec 9b): construtor de análises por cliques, com os onze
  filtros nomeados em português e opções vindas do vocabulário do banco (com a
  contagem ao lado). **Um cartão, uma escolha** — ver os monstros ou comparar por
  uma das sete dimensões; sem seletor de métrica e sem gráfico, resultado da poda
  de 2026-07-25. Faixa de resumo sempre visível com as seis métricas, seis presets
  que preenchem o formulário em vez de abrir tela pronta, aviso em dimensão
  multivalorada, e valor ou dimensão inválidos viram aviso na tela em vez de 500.
- [x] **Camada de consulta** (`consultas.py`, Spec 7a): monta query parametrizada a
  partir de filtros nomeados com lista branca, valida valor contra o vocabulário lido
  do banco, ordena e pagina no SQL, conta ignorando paginação, lê a ficha completa de
  um monstro (ações com ataques e efeitos aninhados) e resolve lista de nomes.
  Devolve dicionários, nunca DataFrame. `calculos.py` traz as derivações puras
  (modificador, saves proficientes, média de dado) e `excecoes.py` os erros de
  domínio que a API traduz para RFC 7807.
- [x] **Relatórios delegando ao núcleo** (Spec 7b): nenhuma query mora em
  `relatorios.py`. Dois relatórios mantiveram a saída; **cinco mudaram**, de forma
  declarada: "letalidade por tipo" passa a tirar média **por monstro** (antes um
  monstro com seis ataques pesava seis vezes e inflava tipos com muitas ações),
  "comparação entre tipos" e "letalidade" ordenam por contagem em vez de média,
  "imunidade/resistência a dano" virou três blocos (um por relação) em vez de tabela
  de duas dimensões, e "condições impostas" perdeu a coluna com os nomes de quem
  impõe. Standalone agora é `python -m bestiario.relatorios`.
- [x] Relatórios reescritos para o schema v2 (`ataques.bonus_ataque` no lugar de
  `acoes.bonus_ataque`) + 4 relatórios ricos (por ambiente, comparação entre tipos,
  imunidade/resistência a dano, condições impostas); `relatorios.py` com uma função
  por relatório + orquestradora, executável via menu ("Ver relatórios") ou standalone
  (Spec 6)

## O que está incompleto ou pode melhorar

- [x] ~~**Dados faltando no banco**~~ — **resolvido na Spec 3**: imunidades/
  resistências/vulnerabilidades a dano, imunidades a condição, ambientes,
  alinhamento, sentidos, velocidade, saves e perícias agora são persistidos
  (tabela `monstros` enriquecida + 4 tabelas de lista normalizadas).
- [x] ~~**Categoria das ações não é salva**~~ — **resolvido na Spec 4**: a coluna
  `categoria` de `acoes` é populada (`action`/`legendary_action`/`reaction` de
  `action_type` + `special_ability` de `traits`). `BONUS_ACTION` não existe no
  SRD 2014 (0 de 944 ações), então não é previsto.
- [x] ~~**Sem pesquisa no banco local**~~ — **resolvido na Spec 6**: os filtros de
  tipo/desafio (opções 2 e 3) consultam o banco primeiro e só caem para a API v2 no
  fallback, com rótulo de origem `[local]`/`[API]`. A **Spec 7c** trocou o executor
  pelo núcleo e renomeou `consultar_cr` para `consultar_desafio` (o rótulo impresso
  virou `Desafio:`).
- [x] ~~**Relatórios limitados ao schema antigo**~~ — **resolvido na Spec 6**:
  baseline reescrito para o schema v2 + 4 relatórios ricos (por ambiente, comparação
  entre tipos, imunidade/resistência a dano, condições impostas).
- [x] ~~**Sem front-end e sem API HTTP**~~ — **resolvido nas Specs 8 e 9**: a API
  vive em `/api/v1/` com `/docs` navegável, e o site tem as três abas de pé. Só a
  tradução PT-BR segue aberta, na Spec 10 — banco e terminal continuam em inglês
  de propósito.
- [ ] **Média de dano ignora o dano secundário** — decisão de 2026-07-26: deixar
  como está. `_SUB_DANO` em `consultas.py` agrega só `dano_medio`, então o Bite do
  Adult Red Dragon conta como 19 e não como 26 (2d10+8 perfurante mais 2d6 de
  fogo). São 122 ataques do SRD com dano extra, o que subestima tipos que somam
  dano elemental. O valor por ataque está certo no banco e a API publica os dois
  campos — a perda é só no agregado (coluna de lista, comparação e faixa de
  resumo). A Spec 7a nunca decidiu o caso. Mudar altera número que a API publica,
  então pede reabrir a 7a.
- [x] ~~**SQL espalhado**~~ — **resolvido nas Specs 7b e 7c**: `consultas.py` é o
  único lugar do projeto que lê o banco. Os 7 relatórios e as opções 2 e 3 do menu
  delegam a ele, e `consultar_por_tipo`/`consultar_por_cr` deixaram de existir.
- [x] ~~**Sem testes automatizados**~~ — **resolvido**: suíte pytest com 307 testes
  espelhando o pacote (cliente API, banco/ingestão, extração, derivações puras,
  camada de consulta, relatórios e orquestração dos filtros); mocks só na fronteira
  HTTP, e a camada de consulta testada contra SQLite em memória.
- [x] ~~**Sem `requirements.txt`**~~ — **resolvido de forma diferente**: dependências
  documentadas em `pyproject.toml` (com teto de versão) e gerenciadas por `uv`,
  conforme a regra global do CLAUDE.md.

## Próximas melhorias planejadas — status (specs)

As melhorias abaixo foram especificadas no conjunto de 6 specs em
`.claude/specs/` e **todas foram implementadas e concluídas** (release v0.1.0,
2026-07-22). A ordem seguida foi a do "Plano de 6 specs".

1. **Enriquecer o schema** (imunidades, resistências, vulnerabilidades,
   imunidades a condições, ambientes, alinhamento, sentidos, velocidade,
   saves) → **Spec 3** (`schema_e_ingestao_monstro`) — concluída.
2. **Coluna de categoria em `acoes` + capturar categorias de ação** →
   **Spec 4** (`extracao_acoes_ataques`) — concluída. Ressalva empírica:
   `BONUS_ACTION` não existe no SRD 2014 (0 de 944 ações); a categoria cobre
   `action`/`legendary_action`/`reaction`/`special_ability`.
3. **Consulta local primeiro** → **Spec 6** (`relatorios_e_consulta_local`) —
   concluída. Decisão: local primeiro, com a API v2 como fallback.
4. **Documentar dependências** → resolvido de forma diferente: `uv` +
   `pyproject.toml` com teto de versão na **Spec 1** (`fundacao`), em vez de
   `requirements.txt` (regra do CLAUDE.md global).
5. **Expandir relatórios** (por ambiente, comparação entre tipos, imunidade/
   resistência a dano, condições impostas) → **Spec 6** — concluída.
6. **Front-end web** — deixou de ser um item só. Virou o bloco de Specs 7-9
   descrito abaixo, e a tradução PT-BR, que estava junto dele, foi separada
   para a Spec 10.

Igualmente concluídas, embora não mapeadas 1:1 na lista antiga: **Spec 2**
(migração para a API v2, SRD 2014) e **Spec 5** (extração de efeitos —
save DC, condição, área; parte lossy isolada).

### Bloco em aberto — Specs 7 a 10

Escritas e aprovadas na Sessão 7 (2026-07-26); a 7a já implementada. A ordem segue a
regra de camadas do CLAUDE.md global: dados → lógica → apresentação.

7. **Camada de consulta** — dividida em três specs. **7a (`consultas.py`,
   `calculos.py`, `excecoes.py`) concluída em 2026-07-26**: Python puro, testável
   sem servidor, com lista branca de filtros/dimensões/ordenações. **7b (relatórios
   delegando) e **7c (menu migrado) também concluídas em 2026-07-26**. A 7b fechou o
   item "SQL espalhado"; a 7c removeu `consultar_por_tipo`/`consultar_por_cr` de
   `banco.py`, que voltou a ter responsabilidade única. **Spec 7 fechada** —
   `consultas.py` é o único lugar do projeto que lê o banco.
8. **API JSON** (`api/`) — **concluída em 2026-07-26**. Seis endpoints em `/api/v1/`,
   erros em RFC 7807, `/docs` na raiz e teste de contrato comparando caminhos,
   parâmetros, campos **e status codes** contra o `openapi.yaml`. `api/erros.py`
   expõe `registrar_tratadores(app)`, chamada também por `web/app.py`: incluir o
   roteador leva as rotas, não os tratadores.
9. **Site** (`web/`) — **concluído em 2026-07-26** (9a, 9b e 9c). Três abas
   (Relatórios, Pesquisar, Todos os monstros),
   HTML renderizado no servidor, visual imitando o livro oficial. **9a concluída
   em 2026-07-26**: moldura (`base.html`), identidade visual portada do esboço
   aprovado (`estilo.css`, fontes Cinzel e EB Garamond em base64) e a aba "Todos
   os monstros" de ponta a ponta — 325 linhas, seis colunas ordenáveis pela URL,
   página explicativa quando o banco está **vazio, ausente ou com schema
   defasado** — os três têm a mesma cura, então dão a mesma tela.
   `web.app:app` inclui o roteador
   da Spec 8 sob `/api/v1` e registra os mesmos tratadores de erro, então
   `/docs` e os erros RFC 7807 valem também pela entrada do site.
   **9c**: a aba Pesquisar, com fichas acumuladas sem limite, `_ficha.html`
   compartilhado com a aba Todos (que abre uma linha por vez no modo Completa),
   navegação nos dois sentidos — o selo da ficha leva ao relatório filtrado e o
   resultado do relatório vem para cá como filtros —, e a API consumida pela
   busca incremental e pelo link JSON de cada ficha.
10. **Tradução PT-BR** — primeira spec a exigir segredo (`.env` + chave). Banco e
    terminal continuam em inglês; a tradução é camada de apresentação.

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
- O banco `bestiario_combate.db` está no schema v2 (SRD 2014) e **totalmente
  populado** (325 monstros, 1476 ações, 542 ataques, 518 efeitos). É artefato
  regenerável (fora do git; recriar via opção 4 do menu)
- Os filtros de tipo/CR consultam o **SQLite primeiro**, com a API v2 apenas como
  fallback — o pressuposto antigo ("toda busca de tipo/CR vai para a API mesmo depois
  de sincronizar") deixou de valer na Spec 6
- O código será lido por recrutadores — comentários claros e estrutura
  organizada são tão importantes quanto funcionalidade
- Preferência por **soluções simples e legíveis** em vez de over-engineering
- **O projeto passa a expor uma API HTTP** (Spec 8), o que muda uma premissa antiga:
  ele deixa de ser só consumidor da Open5e e vira também provedor. Por isso o
  `/contrato` do fluxo global, antes dispensado, passa a valer aqui
- **Erro se divide por superfície, não por causa** (Spec 9a): a mesma
  `BaseNaoSincronizada` vira **página HTML com 200** no site e **503 RFC 7807**
  sob `/api/`, inclusive dentro do site. Para quem abre o navegador, base não
  sincronizada não é falha — é o estado inicial, e a página diz o que fazer;
  para quem chama por programa, o sinal precisa estar na faixa de status. Quem
  decide é `registrar_tratadores`, que continua sendo **uma função só**.
- **Duas superfícies, um núcleo**: `api/` e `web/` nunca escrevem SQL — as duas
  chamam `bestiario/consultas.py`. Endpoint ou rota que monte query própria é
  violação de camada, mesmo que funcione
- **Quando faltar um dado na tela, a resposta quase nunca é mais um botão** — é o
  dado já estar lá. Princípio tirado do teste do esboço na Sessão 6, quando um
  construtor com nove opções foi reprovado por exigir raciocínio antes de servir

## Como rodar

```bash
# Instalar dependências
uv sync

# Menu principal (inclui a opção "Ver relatórios")
python main.py

# Só os relatórios (standalone)
python -m bestiario.relatorios

# Só a API, sem o site (Spec 8; usada isolada nos testes de contrato)
uv run uvicorn api.app:app --reload
#   API ............... http://127.0.0.1:8000/api/v1/monstros
#   documentação ...... http://127.0.0.1:8000/docs

# Servidor — site e API juntos (Spec 9a; entrada real do projeto)
uv run uvicorn web.app:app --reload
#   site .............. http://127.0.0.1:8000/            (redireciona para /relatorios)
#   todos os monstros . http://127.0.0.1:8000/monstros
#   API ............... http://127.0.0.1:8000/api/v1/monstros
#   documentação ...... http://127.0.0.1:8000/docs
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

**Instaladas na Spec 8:** `fastapi>=0.115,<1.0` e `uvicorn>=0.32,<1.0` de produção;
`httpx>=0.27,<1.0` e `pyyaml>=6.0,<7.0` de desenvolvimento.

**Instalada na Spec 9a:** `jinja2>=3.1,<4.0` de produção.

`httpx` é exigida pelo `TestClient` do FastAPI; `pyyaml` serve ao teste de contrato,
que lê o `openapi.yaml` para compará-lo com o esquema gerado pelo código. Ambas são
de teste, então entram como dev. Tetos de versão conforme a regra global.

O `/planejar-setup` foi **pulado de propósito** para este bloco (decisão do usuário
em 2026-07-25): as deps já estavam decididas, e rodar o passo daria a mesma lista.

**Pastas a criar:**
```bash
mkdir -p bestiario tests
touch bestiario/__init__.py
```

**Conteudo do `.env.example`:**
```
nenhuma
```
(A API Open5e é gratuita e sem autenticação — não há variável de ambiente agora.
As Specs 7-9 também não pedem segredo: o servidor só lê o SQLite local. A primeira
a exigir chave é a **Spec 10** (tradução PT-BR), e é lá que o `.env` nasce.)

**Dependencias que ficam de fora agora** (entram quando a spec chegar):
- nenhuma — a Spec 1 (fundação) já move `cliente_api.py` (requests),
  `relatorios.py` (pandas + tabulate) e `banco.py` (sqlite3, stdlib), então
  as três deps de produção são necessárias desde o início.
- Specs 2-7 não introduzem dependências novas (SQLite é stdlib, e a camada de
  consulta da Spec 7 é Python puro sobre `sqlite3` + pandas, já presentes).
- Spec 8 (instaladas): `fastapi` e `uvicorn` de produção; `httpx` e `pyyaml` de teste.
- Spec 9a (instalada): `jinja2` de produção.
- Spec 10 (tradução): cliente do modelo + `pydantic-settings` ou `python-dotenv`.

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
5. **Traducao PT-BR** e passo FUTURO, so no front-end (Spec 7 *à época* — foi
   renumerada para **Spec 10** na Sessao 6, quando o front virou tres specs):
   dict estatico
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

---
**Encerrado em:** 2026-07-22
**Versao:** v0.1.0
**Testes:** 65 passando
**Specs concluidas:** 6 de 6
**Commits:** 18
**Periodo:** 2026-02-08 a 2026-07-22 (9 dias ativos)

---

### Sessão 6 — 2026-07-25 — reabertura para o front

Projeto reaberto depois do release v0.1.0. Sessão **inteiramente de desenho** —
nenhuma linha de código de aplicação foi escrita.

**Achado que motivou um conserto:** a tabela `efeitos` estava com **0 linhas**,
apesar da Spec 5 constar como concluída. Diagnóstico: o código sempre esteve
certo (`extrair_efeitos` acerta o Fire Breath do Adult Red Dragon), o banco é que
fora sincronizado antes da Spec 5 entrar. Re-sincronizado: 518 efeitos. Lição
registrada na seção "O que já funciona" — banco defasado não emite erro.

**Desenho das telas — decidido pelo usuário:**
1. **Relatórios** — construtor de análises próprias (a mais complexa).
2. **Pesquisar** — busca que acumula monstros na tela para comparar. *(O limite
   de 3 foi eliminado em 2026-07-25: a aba comporta de um a 325.)*
3. **Todos os monstros** — tabela completa dos 325, ordenável.

Botão global **resumida/completa** por aba, mudando todos os monstros de uma vez.

**Decisões de produto:**
- **Construtor por cliques, não linguagem natural.** Descartado LLM gerando SQL —
  eliminaria custo, não-determinismo e uma superfície de injeção real.
- **Filtros nomeados** em português claro, não linha genérica `[campo][operador]
  [valor]`. Combinação global "atende **todos** / **qualquer** filtro", sem
  misturar E e OU (evita parênteses e precedência na tela).
- **Sem gráfico.** Só tabela.
- **A poda do construtor.** A primeira versão tinha dois cartões, "Para cada [X]"
  e nove caixas de métrica. Veredito do usuário testando o esboço: *"no geral está
  confuso demais — se tem que pensar para entender, já mostra que está ruim."*
  Sobrou um cartão e **uma escolha**: `( ) Ver os monstros` / `(•) Comparar por
  [tipo]`. Métricas viraram colunas fixas; faixa de resumo e coluna de dano passam
  a estar sempre na tela, sem seletor. Daí saiu o princípio registrado em "Contexto
  para decisões futuras".
- **Navegação nos dois sentidos:** selo da ficha (`imune a fire`) leva ao relatório
  filtrado; resultado do relatório leva os monstros para a aba Pesquisar já fixados.
- **Link JSON embaixo de cada ficha** na aba Pesquisar — é o que impede a API de
  ficar decorativa, junto com a busca da própria aba consumindo `/api/v1/monstros`.

**Decisão de arquitetura — o projeto passa a expor API.** Motivação declarada:
currículo. Risco enunciado e aceito: API que nada consome é pior que API nenhuma,
por isso os dois consumidores acima. Consequência de fluxo: o `/contrato`, antes
dispensável (projeto só consumia API externa), passa a valer.

**Direção visual — extensão do livro oficial.** Três capturas do Livro do Jogador
PT-BR em `OneDrive\Imagens\Documentos\projetos\imagens pro rpg` são a referência.
Elementos tirados dali: cunha vermelha afilada como separador, zebra verde-salva
nas tabelas, moldura com volutas nos cantos e fio dourado, tarja vermelha no topo
e dourada no pé da ficha, papel claro e quente com grão. Tipografia **Cinzel** +
**EB Garamond**, ambas SIL OFL, embutidas em base64 (as do livro, Modesto e
Bookmania, são comerciais). **Tema único claro** — o livro não tem versão escura.

**Esboço aprovado** ("o front está perfeito"). Mora em pasta de scratchpad, com
o CSS e as fontes: precisa ser copiado para o repositório na Spec 9, sob risco de
se perder. Publicado em
`https://claude.ai/code/artifact/ea08e1e1-cbd8-4aec-a182-0d05b637b7cc`.

**Decisões de processo:** `relatorios.py` **será refatorado** para delegar a
`consultas.py` (SQL num lugar só); `/planejar-setup` **pulado**; `/dominio` **não**
será retroagido, por ser passo de início de projeto e o domínio já estar descrito
aqui.

**Domínio, contrato e specs — feitos nesta sessão:**

- `/dominio` rodou (decisão revista: eu tinha proposto pular, o usuário questionou e
  estava certo — os nomes da API são públicos e caros de mudar, e o dicionário da
  Spec 10 nasce do glossário). Gerou `.claude/specs/_dominio.md`: 4 entidades
  gravadas, 3 calculadas, 14 termos, contexto único.
- `/contrato` rodou. Gerou `openapi.yaml` na raiz — OpenAPI 3.1, 6 endpoints, 18
  schemas, RFC 7807, validado pelo Redocly. **API só de leitura**: escrita criaria
  uma segunda verdade que o re-sync apagaria em silêncio.
- 7 specs criadas: **7a** (núcleo de consulta), **7b** (relatórios delegando),
  **7c** (menu migrado), **8** (API JSON), **9a** (moldura + aba Todos),
  **9b** (aba Relatórios), **9c** (aba Pesquisar). A 7 e a 9 foram divididas por
  passar do limite de score.
- `/spec-review` rodou com 7 verificadores em paralelo e **achou muita coisa real**.

**O que o `/spec-review` pegou, e que já foi corrigido:**

- **A 7a estava incompleta** e era a causa raiz de quase tudo: faltavam ordenação,
  contagem para paginação, leitura de ficha completa, busca por nome exato e
  resolução de lista de nomes. Como `api/` e `web/` têm SQL proibido, esses dados
  não teriam de onde sair. Foi **reescrita**, não remendada.
- **A API montaria em `/api/v1/api/v1/`** — a 8 prefixava e a 9a montava com o mesmo
  prefixo. Resolvido: a API vira roteador **incluído**, não sub-aplicação montada.
  Isso conserta junto o `/docs`, que ficaria em `/api/v1/docs`, fora de onde o
  rodapé aponta.
- **Dependência circular 9a ↔ 9c** pelo bloco de estatísticas. O `_ficha.html` passa
  a nascer inteiro na 9c, que ganhou permissão de editar `todos.html`.
- **O `combinar` não atravessava** do relatório para a aba Pesquisar: mesmo recorte,
  conjunto diferente, sem erro nenhum.
- **Três relatórios não cabem no núcleo** sem torná-lo bem maior (agrupamento por
  duas dimensões, concatenação de nomes). Decisão do usuário: **os três mudam de
  formato**. Princípio registrado: *o motor cresce pelo que vem, não pelo que já foi.*
- **Testes dependiam do banco real**, que está fora do git e não existe no CI.
  Passam a usar fixture única em `tests/web/conftest.py`.
- **Contrato corrigido** antes da implementação: resposta padrão cobrindo o 503,
  filtros `vulneravel_a` e `imune_a_condicao`, ordenação em `/monstros` e
  `dano_medio` na forma enxuta.

**Pendências ao fim da sessão:**

- As 7 specs seguem com `Revisão: pendente`. Falta decidir se os verificadores
  rodam de novo — a 7a foi reescrita, então a revisão dela valeu sobre uma versão
  que não existe mais. Enquanto pendentes, o gate bloqueia implementação.
- **O gate de specs não cobre Bash.** Ele intercepta `Edit` e `Write`, mas o
  `openapi.yaml` foi alterado por script Python sem nenhum aviso. Vale fechar.
- O esboço visual aprovado ainda mora em pasta temporária. A Spec 9a precisa
  copiá-lo para o repositório, ou o CSS e as fontes em base64 se perdem.

**Próximo passo (retomar aqui):** decidir entre re-rodar o `/spec-review` ou aprovar
as specs como estão. Aprovadas, a ordem de implementação é
7a → 7b → 7c → 8 → 9a → 9b → 9c, cada uma fechando com `/spec-close`.
