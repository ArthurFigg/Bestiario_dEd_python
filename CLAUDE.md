# CLAUDE.md — Bestiário de D&D 5e

## O que é esse projeto

Bestiário de D&D 5e é uma ferramenta em Python que consome a API pública
**Open5e** (`https://api.open5e.com/monsters/`) para buscar, armazenar e
analisar todos os monstros do D&D 5ª edição. O objetivo é criar um banco
de dados local rico o suficiente para permitir pesquisas e análises
sofisticadas — hoje via terminal/SQL, futuramente via front-end web
acessível a qualquer pessoa sem conhecimento técnico.

## Estrutura de arquivos

```
Bestiario_dEd_python/
├── bestiario.py          # Ponto de entrada — menu interativo no terminal
├── banco_de_dados.py     # Camada de dados: criação do SQLite e inserção
├── analise_bestiario.py  # Relatórios prontos usando pandas + tabulate
├── bestiario_combate.db  # Banco SQLite com os dados já sincronizados
└── CLAUDE.md             # Este arquivo
```

## Tecnologias usadas

- **Python 3** (testado com 3.14 — veja __pycache__)
- **SQLite** via módulo `sqlite3` da stdlib
- **requests** — chamadas HTTP para a API Open5e
- **pandas** — manipulação de dados para relatórios
- **tabulate** — formatação de tabelas no terminal
- **API externa**: `https://api.open5e.com/v1/monsters/` (paginada, sem auth)

## Schema do banco de dados

### Tabela `monstros`
| Coluna | Tipo | Descrição |
|---|---|---|
| nome | TEXT PK | Nome do monstro (chave primária) |
| tamanho | TEXT | Tiny, Small, Medium, Large, Huge, Gargantuan |
| tipo | TEXT | beast, undead, dragon, humanoid, etc. |
| classe_armadura | INTEGER | AC |
| pontos_vida | INTEGER | HP máximo |
| nivel_desafio | REAL | CR como número decimal (ex: 0.25, 5.0, 30.0) — usa campo `cr` da API |
| forca | INTEGER | STR |
| destreza | INTEGER | DEX |
| constituicao | INTEGER | CON |
| inteligencia | INTEGER | INT |
| sabedoria | INTEGER | WIS |
| carisma | INTEGER | CHA |

### Tabela `acoes`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | Auto-incremento |
| monstro_nome | TEXT FK | Referência para monstros.nome |
| nome_acao | TEXT | Nome da ação/habilidade |
| descricao | TEXT | Texto completo da ação |
| bonus_ataque | INTEGER | Extraído da descrição via regex se ausente |
| dados_dano | TEXT | Ex: "2d6 + 4", extraído via regex |

Ações abrangem: `actions`, `special_abilities`, `legendary_actions`, `reactions` —
todas unificadas na mesma tabela com INSERT sem distinção de categoria.

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
- [x] `nivel_desafio` salvo como REAL usando o campo `cr` da API (ordenação numérica correta)
- [x] URLs atualizadas para `v1` após mudança de versionamento da Open5e
- [x] `DELETE FROM acoes` antes de reinserir — evita duplicar ações ao ressincronizar o mesmo monstro
- [x] `bestiario_combate.db` já ressincronizado com o schema/URLs corretos —
  verificado em 2026-07-08 via query direta: 2319 monstros, 14970 ações,
  `nivel_desafio` REAL com valores no range 0.0–30.0, 1244 ações já no formato
  combinado de `dados_dano`. Só 4 ações duplicadas, todas do mesmo monstro
  (`Bone Lord`) — parece ser a própria API do Open5e retornando a ação
  duplicada dentro da mesma resposta, não um bug do dedupe local.
- [x] `.gitignore` criado — `__pycache__/` e `*.pyc` fora do controle de versão

## O que está incompleto ou pode melhorar

- [ ] **Dados faltando no banco**: a API retorna muitos campos que não são
  salvos. Campos identificados como úteis para pesquisa: `damage_immunities`,
  `damage_resistances`, `damage_vulnerabilities`, `condition_immunities`,
  `environments`, `alignment`, `senses`, `speed`, `perception`,
  `strength_save`…`charisma_save`, `skills`.
- [ ] **Categoria das ações não é salva**: todas as ações vão para a mesma
  tabela sem coluna indicando se é `action`, `legendary_action`, etc.
  Além disso, `bonus_actions` não é capturado nem como categoria.
- [ ] **Sem pesquisa no banco local**: todas as buscas de tipo/CR vão para a
  API mesmo depois de sincronizar. Deveria consultar o SQLite primeiro.
- [ ] **Sem front-end**: a interface é 100% terminal.
- [ ] **Sem testes automatizados**.
- [ ] **Sem `requirements.txt`**: dependências não estão documentadas formalmente.

## Próximas melhorias planejadas (em ordem de prioridade sugerida)

1. **Enriquecer o schema** — adicionar colunas para imunidades, resistências,
   vulnerabilidades, imunidades a condições, ambientes, alinhamento, sentidos,
   velocidade e saving throws — fazendo uma coluna por vez para facilitar testes
2. **Adicionar coluna `categoria_acao`** na tabela `acoes` e capturar `bonus_actions`
3. **Consulta local primeiro** — checar o banco antes de chamar a API
4. **Criar `requirements.txt`**
5. **Expandir relatórios** — análises por ambiente, comparação entre tipos, etc.
6. **Front-end web** — Flask ou FastAPI + HTML simples para pesquisa sem terminal

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
- A API Open5e é **gratuita e sem autenticação** — basta HTTP GET, endpoint atual: `https://api.open5e.com/v1/monsters/`
- O banco `bestiario_combate.db` já está sincronizado com o schema atual (2319 monstros, 14970 ações)
- O código será lido por recrutadores — comentários claros e estrutura
  organizada são tão importantes quanto funcionalidade
- Preferência por **soluções simples e legíveis** em vez de over-engineering

## Como rodar

```bash
# Instalar dependências
pip install requests pandas tabulate

# Menu principal
python bestiario.py

# Só os relatórios
python analise_bestiario.py
```

## API Open5e — referência rápida

```
GET https://api.open5e.com/v1/monsters/          # lista paginada (50 por vez)
GET https://api.open5e.com/v1/monsters/{slug}/  # monstro específico
Paginação: campo "next" no JSON com a URL da próxima página
Sem autenticação necessária
```
