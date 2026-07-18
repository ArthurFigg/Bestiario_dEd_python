# Relatórios enriquecidos + consulta local primeiro

**Ordem:** 6 de 6
**Depende de:** Specs 1 (fundação), 2 (cliente API v2), 3 (schema + ingestão), 4 (ações + ataques) e 5 (efeitos)
**Revisão:** aprovada

## O que faz
Faz os filtros de tipo/CR do menu consultarem o SQLite antes de chamar a API (com fallback para a v2 quando não há dado local) e reescreve os relatórios para o novo schema, somando quatro relatórios ricos que exploram as tabelas normalizadas das Specs 3-5.

## Comportamento

### Consulta local primeiro (filtros do menu)
- Quando o usuário filtra por tipo (opção 2), o menu consulta primeiro o SQLite (`banco.py`) e lista os monstros daquele tipo gravados localmente.
- Quando o usuário filtra por CR (opção 3), o menu consulta primeiro o SQLite pelo `nivel_desafio` (REAL) correspondente.
- Quando a consulta local não retorna nada (banco vazio/nunca sincronizado, ou aquele tipo/CR ausente), o filtro cai para a API v2 (função de filtro do cliente da Spec 2) e mostra o resultado remoto.
- Quando o filtro exibe resultados, cada linha projeta um conjunto comum mínimo (`nome`, `tipo`, `challenge_rating`/`nivel_desafio`) e é rotulada com a origem: `[local]` para linhas do SQLite, `[API]` para resultados de fallback. Isso evita que a troca silenciosa de fonte confunda o usuário.
- Quando nem o local nem a API retornam resultado, exibe "Nenhum monstro encontrado."
- Quando o input de CR não é numérico válido (ex: texto vazio ou não parseável), o filtro trata como sem resultado local e segue o fluxo de fallback/mensagem, sem quebrar.
- A busca individual por nome (opção 1) e a sincronização (opção 4) **não mudam** — opção 1 continua buscando e registrando via API; só os filtros 2 e 3 ganham a consulta local.

### Relatórios (baseline reescrito para o novo schema)
- Quando os relatórios rodam, "os N mais resistentes" lista monstros por `pontos_vida`/`classe_armadura` da tabela `monstros` (inalterado no schema).
- Quando os relatórios rodam, "top ataques mais precisos" passa a usar `ataques.bonus_ataque` (JOIN `monstros`→`acoes`→`ataques`), **não** mais `acoes.bonus_ataque`/`acoes.dados_dano` (colunas eliminadas nas Specs 3-4).
- Quando os relatórios rodam, "letalidade média por tipo" passa a agregar `ataques.bonus_ataque` por `monstros.tipo`, **não** mais `acoes.bonus_ataque`.

### Relatórios ricos novos
- **Por ambiente**: contagem/listagem de monstros por ambiente, via JOIN com `monstro_ambiente` (322/325 monstros têm ambiente).
- **Comparação entre tipos**: CR médio, HP médio e AC médio agrupados por `monstros.tipo`.
- **Imunidade/resistência a dano**: contagem de monstros por `tipo_dano` e `relacao`, via `monstro_interacao_dano` (ex: quantos são imunes a `fire`).
- **Condições impostas**: contagem das condições mais causadas e quais monstros as impõem, via JOIN `efeitos`→`acoes`→`monstros` (usa a tabela `efeitos` da Spec 5).

### Estrutura e execução dos relatórios
- Cada relatório é uma **função independente** em `relatorios.py` (uma query + exibição via pandas/tabulate), orquestradas por uma função que roda todos em sequência. Isso mantém o conjunto extensível — novos relatórios entram como funções novas sem tocar as existentes.
- Os relatórios continuam executáveis de forma standalone (rodar `relatorios.py` como módulo produz todos), e ganham uma opção "Ver relatórios" no menu.
- Quando o banco está vazio (nenhum monstro sincronizado), cada relatório exibe tabela vazia sem quebrar — ausência de dado não é erro.

## Critérios verificáveis
- [ ] `uv run pytest -v` passa, incluindo os testes desta spec e das Specs 1-5.
- [ ] Teste confirma que o filtro por tipo, com o monstro já gravado no SQLite, retorna a linha local **sem** chamar a API (mock do cliente v2 não é invocado).
- [ ] Teste confirma que, com o SQLite sem match, o filtro por tipo chama o fallback da API v2 (mock do cliente invocado) e retorna o resultado remoto.
- [ ] Teste confirma que a saída do filtro rotula a origem (`[local]` para linha do banco, `[API]` para fallback).
- [ ] Teste confirma que o relatório "top ataques" consulta `ataques.bonus_ataque` (não `acoes.bonus_ataque`), rodando contra um banco de teste populado no schema novo sem erro de coluna inexistente.
- [ ] Teste confirma que o relatório "por ambiente" agrega a partir de `monstro_ambiente` e retorna as contagens esperadas para um banco de teste.
- [ ] Teste confirma que o relatório "imunidade/resistência a dano" conta corretamente a partir de `monstro_interacao_dano` (ex: 1 monstro imune a `fire`).
- [ ] Teste confirma que o relatório "condições impostas" agrega a partir de `efeitos` e lista o monstro que impõe a condição.
- [ ] Teste confirma que rodar todos os relatórios contra um banco **vazio** não lança exceção (tabelas vazias exibidas).
- [ ] Teste confirma que CR de input inválido no filtro não quebra (sem resultado local → fluxo de fallback/mensagem).

## Módulos afetados
- `bestiario/relatorios.py` — reescrito e ampliado. As 3 queries baseline passam para o schema novo (`ataques.bonus_ataque`/`ataques.dano_*` em vez das colunas mortas de `acoes`). Adiciona 4 funções de relatório rico (por ambiente, comparação entre tipos, imunidade/resistência, condições impostas). Uma função orquestradora roda todos. Mantém pandas + tabulate e execução standalone.
- `bestiario/banco.py` — ganha funções de consulta local (`consultar_por_tipo`, `consultar_por_cr`) que leem o SQLite e devolvem as linhas dos monstros. Só leitura; não altera schema nem ingestão.
- `main.py` — os handlers dos filtros (opções 2 e 3) passam a chamar as funções de consulta local de `banco.py` primeiro e cair para o cliente v2 no fallback, exibindo com rótulo de origem. Ganha a opção de menu "Ver relatórios" chamando a orquestradora de `relatorios.py`.
- `tests/test_relatorios.py` — ampliado com um banco de teste no schema novo validando cada relatório (baseline + ricos) e o caso de banco vazio.
- `tests/test_banco.py` — ampliado com testes das funções de consulta local (match e ausência de match).

## Não mexer
- `bestiario/cliente_api.py` — apenas **consumido** no fallback (a função de filtro da Spec 2 é chamada como está); não é alterado.
- `bestiario/extracao.py` — extração de ações/ataques/efeitos (Specs 4-5) não é tocada.
- `bestiario/modelos.py` — segue placeholder.
- **Schema** das tabelas (Specs 3-5) — esta spec só consulta; não cria nem altera colunas.
- **Ingestão** (`registrar_monstro`/população das tabelas) — Specs 3-5; aqui `banco.py` só ganha funções de leitura.
- Busca por nome (opção 1) e sincronização (opção 4) do menu — comportamento preservado; só os filtros 2 e 3 mudam.
- Tradução dos valores para português — camada de apresentação futura; relatórios exibem as chaves canônicas em inglês do banco.

## Decisões tomadas
- Consulta dos filtros → **local primeiro, API como fallback**. Motivo: fiel ao "consultar o SQLite primeiro" do CLAUDE.md e robusto (funciona mesmo sem sync). Custo aceito: local (linha do banco) e API (dict v2) têm formatos diferentes, resolvido projetando um conjunto comum mínimo na exibição. Descartado "só local" (mais simples, mas perde o fallback quando o banco está vazio).
- Rótulo de origem na saída do filtro → `[local]`/`[API]`. Motivo: o fallback troca a fonte de dados silenciosamente; rotular evita confundir o usuário sobre a procedência do resultado (consequência de UX da decisão de fallback).
- Relatórios baseline → **reescritos** para o schema novo (obrigatório, não opcional). Motivo: as colunas `acoes.bonus_ataque`/`acoes.dados_dano` foram eliminadas nas Specs 3-4; as queries antigas quebrariam. Dados de ataque agora vêm de `ataques`.
- Relatórios ricos → **todos os quatro** (por ambiente, comparação entre tipos, imunidade/resistência a dano, condições impostas). Motivo: projeto de portfólio ("impressionar recrutadores"); "por ambiente" e "comparação entre tipos" são citados no CLAUDE.md, e imunidade/resistência + condições demonstram o valor do schema normalizado das Specs 3 e 5. Todos nascem com dado real no SRD (322 com ambiente, 160 com resistência, 266 ações com efeito). Conjunto extensível — mais relatórios podem ser adicionados depois como funções novas.
- Estrutura de `relatorios.py` → uma função por relatório + orquestradora. Motivo: extensibilidade (novo relatório = função nova, sem tocar as existentes) e testabilidade (cada relatório testado isolado).
- Invocação dos relatórios → standalone (rodar o módulo) **e** opção "Ver relatórios" no menu. Motivo: preserva o modo de execução atual e melhora usabilidade a custo baixo.
- Funções de consulta local em `banco.py` → seguem a camada de dados (repositório) do CLAUDE.md; `main.py` (UI) só orquestra, não faz SQL. Motivo: separação de responsabilidades (regra "nunca misturar lógica de negócio/UI com acesso a dados").
- Banco vazio nos relatórios → exibe tabela vazia, não erro. Motivo: ausência de dado (sem sync) é estado válido, não falha.

## Impacto no CLAUDE.md
Seção adicionada retroativamente (spec anterior à regra "spec declara e /spec-close sincroniza o CLAUDE.md").
- O que está incompleto ou pode melhorar → itens "Sem pesquisa no banco local" e "Expandir relatórios (por ambiente, comparação entre tipos, imunidade/resistência, condições)" resolvidos.
- O que já funciona → adicionar consulta local-primeiro nos filtros de tipo/CR (opções 2 e 3) com fallback para a API v2 e rótulo de origem `[local]`/`[API]`; relatórios baseline reescritos para o schema novo (`ataques.bonus_ataque` no lugar de `acoes.bonus_ataque`); 4 relatórios ricos (por ambiente, comparação entre tipos, imunidade/resistência a dano, condições impostas).
- Como rodar → o menu ganha a opção "Ver relatórios"; os relatórios seguem executáveis standalone via `python bestiario/relatorios.py`.
- Contexto para decisões futuras → o pressuposto "todas as buscas de tipo/CR vão para a API mesmo depois de sincronizar" deixa de valer (agora é local primeiro, API como fallback).
