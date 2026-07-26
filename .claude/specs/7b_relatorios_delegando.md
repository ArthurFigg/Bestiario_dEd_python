# Relatórios delegando ao núcleo

**Ordem:** 7b de 9
**Depende de:** Spec 7a (núcleo de consulta)
**Score:** 2
**Revisão:** aprovada

> **Revisada em 2026-07-25 após o `/spec-review`.** A versão anterior prometia saída
> idêntica à atual em todos os 7 relatórios, o que é impossível: cinco deles têm formato
> ou ordenação que o núcleo não reproduz. A promessa foi escopada e as cinco mudanças estão
> declaradas. **Revisada de novo em 2026-07-26:** eram "três", mas a ordenação fixa do modo
> `comparacao` atinge outros dois.

## O que faz
Faz os 7 relatórios do terminal chamarem a camada de consulta em vez de carregarem SQL próprio. Dois mantêm o resultado idêntico; cinco mudam de formato ou de ordenação, de forma declarada.

## Comportamento

### A delegação

- Quando um relatório roda, ele monta os parâmetros e chama o núcleo. **Nenhuma query fica escrita em `relatorios.py`.**
- Cada uma das 7 funções mantém **nome, assinatura e retorno**: recebem conexão, devolvem DataFrame, imprimem via tabulate. Quatro dos seis testes existentes seguem valendo como rede de segurança da própria refatoração; os outros dois são substituídos — ver abaixo.
- Como o núcleo devolve dicionários, cada função converte com `pd.DataFrame(linhas)` antes de exibir. Pandas fica no lado da apresentação, que é onde deve viver.
- `gerar_todos_relatorios` continua abrindo a conexão e, portanto, `relatorios.py` **continua importando `sqlite3`**. O que sai do arquivo é a construção de query, não a conexão.
- Cada relatório **renomeia as colunas para exibição** antes de imprimir. O núcleo devolve `media_pontos_vida`; o cabeçalho impresso é decisão da apresentação.
- Os cabeçalhos passam a seguir o glossário: `pontos_vida` e `classe_armadura` no lugar de `hp` e `ac`, que o `_dominio.md` marca como termos a evitar. É mudança visível no terminal, e é intencional.
- O núcleo arredonda toda média em duas casas. Onde o relatório atual usava uma casa, o número passa a sair com duas.
- A orquestradora e a lista `TODOS_OS_RELATORIOS` não mudam — o ponto único de registro fica de pé.
- Quando o banco está vazio, cada relatório continua exibindo tabela vazia sem quebrar.
- Continuam executáveis isolados (`python bestiario/relatorios.py`) e pela opção "Ver relatórios" do menu.

### Regra que vale para todos: seleção de colunas

O núcleo devolve **sempre o conjunto pronto** — a forma enxuta inteira em `lista_monstros`, as seis métricas em `comparacao`. Nenhum relatório imprime tudo isso. Cada função **seleciona as colunas que hoje imprime** antes de exibir, e é isso que a delegação preserva. Renomear não é selecionar: as duas coisas acontecem, nesta ordem.

### Os dois que ficam idênticos

- **"Os N mais resistentes"** — `lista_monstros` ordenado por pontos de vida, decrescente, limite 5. Imprime `nome`, `tipo`, `pontos_vida`, `classe_armadura`; descarta o resto da forma enxuta. O filtro atual `WHERE pontos_vida IS NOT NULL AND classe_armadura IS NOT NULL` deixa de existir: nenhum dos 325 tem esses campos nulos, e o núcleo não oferece filtro de nulidade.
- **"Top ataques mais precisos"** — `lista_ataques` ordenado por bônus de ataque, decrescente, limite 5.

Nesses dois, os valores impressos são os mesmos de hoje, salvo o arredondamento e os nomes de cabeçalho descritos acima.

### Os cinco que mudam, e por quê

Ordenação é a causa de três deles: o modo `comparacao` do núcleo **sai sempre da maior contagem para a menor**, como o contrato promete, e hoje três relatórios ordenam por outra coisa.

- **"Monstros por ambiente"** — só muda o nome da coluna de contagem, de `total` para `monstros`. A ordenação já era por contagem decrescente.
- **"Comparação entre tipos"** — hoje ordena por desafio médio decrescente; passa a ordenar por **contagem de monstros** decrescente. As colunas seguem as mesmas.
- **"Letalidade por tipo"** — usa `media_bonus_ataque`, publicada no núcleo e no contrato por decisão de 2026-07-26. Muda em três pontos: a contagem de ataques vira **contagem de monstros**; a ordenação por bônus médio decrescente vira **contagem decrescente**; e a média passa a ser **por monstro**, não por linha de ataque — hoje um monstro com seis ataques pesa seis vezes na média do tipo dele, o que infla tipos com muitas ações. Os números impressos mudam por causa disso, e a mudança é uma correção, não um efeito colateral.
- **"Imunidade/resistência a dano"** — hoje é uma tabela de duas dimensões (tipo de dano × relação). Passa a ser **uma comparação por tipo de dano executada uma vez para cada relação**, usando o filtro `relacao` acrescentado à 7a, com a relação no título de cada bloco. O núcleo não ganha agrupamento por duas dimensões.
- **"Condições impostas"** — hoje traz a coluna `quais`, com os nomes de quem impõe cada condição, via concatenação no SQL. Passa a trazer só a contagem. Quem quiser os nomes filtra por `impoe` e lista os monstros.

O motivo comum das duas últimas: agrupar por duas dimensões e concatenar nomes de grupo são mudanças estruturais no núcleo que **nenhum outro consumidor do projeto usaria**. O motor cresce pelo que vem, não pelo que já foi.

### Os testes atuais que deixam de valer

Dois dos seis testes de `tests/test_relatorios.py` não sobrevivem à mudança de formato, e isso é esperado, não regressão:

- `test_condicoes_impostas_lista_o_monstro_que_impoe` afirma `poisoned["quais"] == "Giant Poison Snake"`. A coluna deixa de existir; o teste é **substituído** por um que verifica a contagem.
- `test_por_ambiente_agrega_de_monstro_ambiente` depende do nome de coluna `total`, que passa a ser `monstros`.

Os outros quatro continuam servindo de rede de segurança da refatoração.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-6 e 7a.
- [ ] Teste confirma, para cada um dos **dois** relatórios de saída preservada, que o resultado contra banco de teste é igual ao esperado antes da refatoração — valores fixos no teste, escritos à mão, **não** recalculados com a implementação nova. Teste que recalcula passaria mesmo se o resultado mudasse, que é exatamente o risco desta spec.
- [ ] Teste confirma, para cada um dos **cinco** relatórios de formato alterado, o formato novo declarado acima.
- [ ] Teste confirma que "comparação entre tipos" e "letalidade por tipo" saem ordenados por **contagem de monstros** decrescente, e não pela média que ordenava antes.
- [ ] Teste confirma que a média de bônus de ataque de um tipo é **por monstro**: um monstro com vários ataques não pesa mais de uma vez.
- [ ] Teste confirma que "monstros por ambiente" usa a coluna `monstros`, e não `total`.
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
- `tests/test_relatorios.py` — ajustado. Valores esperados fixos e explícitos para os dois preservados; casos novos para os cinco alterados; os dois testes listados acima substituídos.
- `.claude/specs/6_relatorios_e_consulta_local.md` — ganha nota de supersessão registrando que "condições impostas" perdeu a coluna de nomes e que "comparação entre tipos" mudou de ordenação. Sem a nota, uma spec concluída fica prometendo um formato que não existe mais — o mesmo tratamento que a 7c dá às funções que remove.

## Não mexer

- `bestiario/consultas.py`, `calculos.py` e `excecoes.py` — criados na 7a e usados como estão. Se um relatório precisar de algo que o núcleo não oferece, isso é sinal de que a 7a ficou incompleta, e não licença para escrever SQL aqui.
- `bestiario/banco.py` — `consultar_por_tipo` e `consultar_por_cr` continuam de pé; quem as remove é a 7c.
- `main.py` — inclusive a chamada de "Ver relatórios", idêntica.
- `bestiario/cliente_api.py` e `bestiario/extracao.py`.
- O formato de saída no terminal — tabulate com `tablefmt="psql"`.

## Decisões tomadas

- Refatorar em vez de conviver com SQL duplicado → decisão do usuário em 2026-07-25, para o SQL existir num lugar só. Sem isso, o mesmo `SELECT` viveria em dois arquivos e uma correção não chegaria ao outro; os números do terminal passariam a divergir dos do site sem ninguém perceber.
- **Cinco relatórios mudam de formato ou ordenação** → decisão do usuário em 2026-07-25 (formato) e 2026-07-26 (o núcleo ganha `relacao` e publica `media_bonus_ataque`, mas mantém a ordenação fixa do modo `comparacao`). Preservar os sete exigiria agrupamento por duas dimensões, concatenação de nomes e ordenação configurável por métrica. Nenhum outro consumidor precisaria disso.
- Escopar a promessa de "resultado idêntico" a dois relatórios → a promessa anterior era inverificável, e critério que não se pode cumprir é pior que critério ausente: dá falsa segurança.
- Manter as assinaturas das 7 funções → os testes existentes continuam servindo de rede de segurança. Trocar assinatura junto tiraria a trava que torna a mudança segura.
- Cabeçalhos migram para o glossário → a 7b é a última oportunidade natural de corrigir `hp` e `ac` sem uma spec só para isso.
- Isolar esta refatoração numa spec própria, mesmo com score 2 → é a única parte do bloco que mexe em código já commitado e coberto por teste. Commit próprio significa reversão barata.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → remover a marca `(7)` da linha de `relatorios.py`.
- **O que está incompleto** → remover o item "SQL espalhado": resolve-se aqui.
- **O que já funciona** → registrar que os relatórios do terminal passam pela camada de consulta única, e que três deles mudaram de formato.
- **Bloco em aberto — Specs 7 a 10** → marcar 7b como concluída.
