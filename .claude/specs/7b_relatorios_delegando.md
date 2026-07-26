# Relatórios delegando ao núcleo

**Ordem:** 7b de 9
**Depende de:** Spec 7a (núcleo de consulta)
**Score:** 2
**Revisão:** pendente

> **Revisada em 2026-07-25 após o `/spec-review`.** A versão anterior prometia saída
> idêntica à atual em todos os 7 relatórios, o que é impossível: três deles têm formato
> que o núcleo não expressa. A promessa foi escopada e as três mudanças estão declaradas.

## O que faz
Faz os 7 relatórios do terminal chamarem a camada de consulta em vez de carregarem SQL próprio. Quatro mantêm o resultado idêntico; três mudam de formato de forma declarada.

## Comportamento

### A delegação

- Quando um relatório roda, ele monta os parâmetros e chama o núcleo. **Nenhuma query fica escrita em `relatorios.py`.**
- Cada uma das 7 funções mantém **nome, assinatura e retorno**: recebem conexão, devolvem DataFrame, imprimem via tabulate. Os testes existentes seguem valendo como rede de segurança da própria refatoração.
- Como o núcleo devolve dicionários, cada função converte com `pd.DataFrame(linhas)` antes de exibir. Pandas fica no lado da apresentação, que é onde deve viver.
- `gerar_todos_relatorios` continua abrindo a conexão e, portanto, `relatorios.py` **continua importando `sqlite3`**. O que sai do arquivo é a construção de query, não a conexão.
- Cada relatório **renomeia as colunas para exibição** antes de imprimir. O núcleo devolve `media_pontos_vida`; o cabeçalho impresso é decisão da apresentação.
- Os cabeçalhos passam a seguir o glossário: `pontos_vida` e `classe_armadura` no lugar de `hp` e `ac`, que o `_dominio.md` marca como termos a evitar. É mudança visível no terminal, e é intencional.
- O núcleo arredonda toda média em duas casas. Onde o relatório atual usava uma casa, o número passa a sair com duas.
- A orquestradora e a lista `TODOS_OS_RELATORIOS` não mudam — o ponto único de registro fica de pé.
- Quando o banco está vazio, cada relatório continua exibindo tabela vazia sem quebrar.
- Continuam executáveis isolados (`python bestiario/relatorios.py`) e pela opção "Ver relatórios" do menu.

### Os quatro que ficam idênticos

- "Os N mais resistentes" — `lista_monstros` ordenado por pontos de vida, decrescente, com limite 5.
- "Top ataques mais precisos" — `lista_ataques` ordenado por bônus de ataque, decrescente, limite 5.
- "Monstros por ambiente" — `comparacao` por ambiente.
- "Comparação entre tipos" — `comparacao` por tipo.

Nesses quatro, os valores impressos são os mesmos de hoje, salvo o arredondamento e os nomes de cabeçalho descritos acima.

### Os três que mudam, e por quê

- **"Letalidade por tipo"** — usa a métrica de média de bônus de ataque, acrescentada à lista branca do núcleo na 7a. Perde a coluna de contagem de ataques, que vira contagem de monstros. É a menor das três mudanças.
- **"Imunidade/resistência a dano"** — hoje é uma tabela de duas dimensões (tipo de dano × relação). Passa a ser **uma comparação por tipo de dano executada uma vez para cada relação**, com a relação indicada no título de cada bloco. O núcleo não ganha agrupamento por duas dimensões.
- **"Condições impostas"** — hoje traz a coluna `quais`, com os nomes de quem impõe cada condição, via concatenação no SQL. Passa a trazer só a contagem. Quem quiser os nomes filtra por `impoe` e lista os monstros.

O motivo comum: agrupar por duas dimensões e concatenar nomes de grupo são mudanças estruturais no núcleo que **nenhum outro consumidor do projeto usaria**. O motor cresce pelo que vem, não pelo que já foi.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-6 e 7a.
- [ ] Teste confirma, para cada um dos **quatro** relatórios de saída preservada, que o resultado contra banco de teste é igual ao esperado antes da refatoração — valores fixos no teste, escritos à mão, **não** recalculados com a implementação nova. Teste que recalcula passaria mesmo se o resultado mudasse, que é exatamente o risco desta spec.
- [ ] Teste confirma, para cada um dos **três** relatórios de formato alterado, o formato novo declarado acima.
- [ ] Busca por `read_sql_query` em `bestiario/relatorios.py` não encontra ocorrência.
- [ ] Busca por `SELECT` e `FROM` em caixa alta em `bestiario/relatorios.py` não encontra ocorrência. A busca precisa distinguir caixa: o módulo tem `from tabulate import tabulate`.
- [ ] Teste confirma que "top ataques" continua ordenando por bônus de ataque decrescente e devolvendo 5 linhas.
- [ ] Teste confirma que "imunidade a dano" produz um bloco por relação — imunidade, resistência e vulnerabilidade.
- [ ] Teste confirma que "condições impostas" agrupa por condição a partir de `efeitos` e **não** traz coluna de nomes.
- [ ] Teste confirma que, com banco vazio, cada relatório devolve DataFrame vazio sem exceção.
- [ ] Teste confirma que os cabeçalhos impressos usam `pontos_vida` e `classe_armadura`, e não `hp` e `ac`.
- [ ] `python bestiario/relatorios.py` roda de ponta a ponta contra o banco real sem erro.

## Módulos afetados

- `bestiario/relatorios.py` — reescrito por dentro. As 7 funções perdem a query e passam a montar parâmetros, chamar o núcleo, renomear colunas e exibir. Continua importando `sqlite3` (a orquestradora abre a conexão), pandas e tabulate.
- `tests/test_relatorios.py` — ajustado. Valores esperados fixos e explícitos para os quatro preservados; casos novos para os três alterados.

## Não mexer

- `bestiario/consultas.py`, `calculos.py` e `excecoes.py` — criados na 7a e usados como estão. Se um relatório precisar de algo que o núcleo não oferece, isso é sinal de que a 7a ficou incompleta, e não licença para escrever SQL aqui.
- `bestiario/banco.py` — `consultar_por_tipo` e `consultar_por_cr` continuam de pé; quem as remove é a 7c.
- `main.py` — inclusive a chamada de "Ver relatórios", idêntica.
- `bestiario/cliente_api.py` e `bestiario/extracao.py`.
- O formato de saída no terminal — tabulate com `tablefmt="psql"`.

## Decisões tomadas

- Refatorar em vez de conviver com SQL duplicado → decisão do usuário em 2026-07-25, para o SQL existir num lugar só. Sem isso, o mesmo `SELECT` viveria em dois arquivos e uma correção não chegaria ao outro; os números do terminal passariam a divergir dos do site sem ninguém perceber.
- **Três relatórios mudam de formato** → decisão do usuário em 2026-07-25, depois de o `/spec-review` mostrar que preservar os sete exigiria agrupamento por duas dimensões, concatenação de nomes e arredondamento configurável no núcleo. Nenhum outro consumidor precisaria disso.
- Escopar a promessa de "resultado idêntico" a quatro relatórios → a promessa anterior era inverificável, e critério que não se pode cumprir é pior que critério ausente: dá falsa segurança.
- Manter as assinaturas das 7 funções → os testes existentes continuam servindo de rede de segurança. Trocar assinatura junto tiraria a trava que torna a mudança segura.
- Cabeçalhos migram para o glossário → a 7b é a última oportunidade natural de corrigir `hp` e `ac` sem uma spec só para isso.
- Isolar esta refatoração numa spec própria, mesmo com score 2 → é a única parte do bloco que mexe em código já commitado e coberto por teste. Commit próprio significa reversão barata.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → remover a marca `(7)` da linha de `relatorios.py`.
- **O que está incompleto** → remover o item "SQL espalhado": resolve-se aqui.
- **O que já funciona** → registrar que os relatórios do terminal passam pela camada de consulta única, e que três deles mudaram de formato.
- **Bloco em aberto — Specs 7 a 10** → marcar 7b como concluída.
