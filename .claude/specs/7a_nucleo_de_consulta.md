# Núcleo de consulta

**Ordem:** 7a de 9
**Depende de:** Specs 1-6 (concluídas) e da **reabertura da Spec 4**, que acrescenta `ataques.dano_medio` e `ataques.dano_extra_medio`
**Score:** 4
**Revisão:** aprovada

> **Reescrita em 2026-07-25 após o `/spec-review`.** A primeira versão prometia menos do
> que o contrato e as telas consomem: faltavam ordenação, leitura de ficha completa, busca
> por nome exato, contagem para paginação e resolução de lista de nomes. Sem isso, `api/` e
> `web/` — que têm SQL proibido — não teriam de onde tirar o dado. As adições abaixo vêm
> todas de consumidor real já especificado, nenhuma é especulativa.

## O que faz
Cria a camada que monta e executa consultas sobre o SQLite a partir de filtros nomeados, devolvendo dicionários, e as derivações de regra de D&D que a apresentação precisa. Nada existente é modificado — esta spec só acrescenta.

## Comportamento

### Derivações puras (`bestiario/calculos.py`)

- Quando recebe um valor de atributo, `modificador` devolve `(valor - 10) // 2` — 27 vira 8, 10 vira 0, 7 vira -2.
- Quando recebe a linha de um monstro, `saves_proficientes` devolve os atributos em que o teste de resistência **difere** do modificador do atributo. O schema guarda os seis testes já derivados e nunca nulos, mas o bloco de estatísticas só lista os proficientes; a diferença é o que denuncia a proficiência. No Adult Red Dragon o resultado é exatamente `destreza`, `constituicao`, `sabedoria` e `carisma` — que bate com o SRD.
- Quando recebe um dado e um bônus, `media_de_dado` devolve a média: `n × (faces + 1) / 2 + bonus`. `("2d10", 8)` dá 19,0.
- Quando não há dado válido **mas há bônus**, `media_de_dado` devolve o próprio bônus: dano fixo (`1 piercing damage`, 15 ataques do SRD) é uma constante, e uma constante é a sua própria média. Corrigido na Revisão 1 da Spec 4, ao implementar — a redação anterior devolvia `None` aqui e perderia esses 15.
- Quando não há dado válido **nem bônus**, devolve `None` — ausência de dano não é erro. São 4 ataques no SRD.
- `tests/test_calculos.py` já cobre `media_de_dado`; esta spec acrescenta os casos das outras duas funções.

### Vocabulário das chaves devolvidas

- Todo dicionário devolvido usa **os nomes do contrato e do glossário**, não os nomes das colunas: `desafio` (não `nivel_desafio`), `pontos_vida`, `classe_armadura`, `media_dano`, `dano_medio`. A tradução acontece aqui, uma vez, e não em cada consumidor.
- Isto é contrato desta spec, não detalhe: a 7c projeta esses dicionários no menu e a 8 os serializa em JSON. Divergência de chave quebraria as duas em silêncio.

### Montagem da consulta (`bestiario/consultas.py`)

- Quando recebe filtros e um modo de saída, `montar_consulta` devolve a tupla `(sql, parametros)`. É **função pura, sem conexão** — o teste verifica o SQL montado sem tocar em banco.
- Filtros aceitos, todos opcionais: `tipo`, `tamanho`, `alinhamento`, `desafio_min`, `desafio_max`, `ambiente`, `resiste_a`, `imune_a`, `vulneravel_a`, `imune_a_condicao`, `impoe`, `nome`, `relacao`. Filtro ausente ou vazio não restringe nada.
- O filtro `relacao` aceita `imunidade`, `resistencia` ou `vulnerabilidade` e restringe a coluna `relacao` de `monstro_interacao_dano`. Combinado com a dimensão `tipo_dano`, é o que produz o relatório de imunidade/resistência da 7b — sem ele, agrupar por tipo de dano misturaria as três relações numa contagem sem sentido. Acrescentado por decisão do usuário em 2026-07-26.
- Quando o filtro é `nome`, a comparação é por trecho, sem diferenciar maiúsculas — é o que a busca incremental do site consome. **Busca exata é outra função** (ver abaixo), não este filtro.
- Quando o filtro mora em tabela filha (`ambiente`, `resiste_a`, `imune_a`, `vulneravel_a`, `imune_a_condicao`, `impoe`), a cláusula vira subconsulta `EXISTS`, **nunca `JOIN`**. `JOIN` multiplicaria linhas e estragaria qualquer contagem.
- Quando `combinar` é `todos`, as cláusulas se juntam com `AND`; quando é `qualquer`, com `OR`. Ausente, vale `todos`.

### Modos de saída

| modo | uma linha é |
|---|---|
| `lista_monstros` | um monstro, na forma enxuta, com `dano_medio` |
| `lista_ataques` | um ataque, com o monstro e a ação donos |
| `comparacao` | um valor da dimensão pedida em `por` |
| `resumo` | o conjunto inteiro, sempre uma linha só |

- O modo se chama `comparacao`, **não `agregado`** — o glossário manda usar "comparação" e evitar "agrupamento"; o contrato expõe `/comparacoes` e o schema `LinhaDeComparacao`.
- Quando o modo é `comparacao`, a dimensão `por` é obrigatória e aceita `tipo`, `tamanho`, `alinhamento`, `desafio`, `ambiente`, `tipo_dano` e `condicao_imposta`.
- Quando o modo é `comparacao`, o resultado sai ordenado da maior contagem para a menor, como o contrato promete.
- Quando o modo é `comparacao`, o valor da dimensão sai **sempre como texto**, porque `LinhaDeComparacao.valor` é `string` no contrato. `desafio` vem de `nivel_desafio REAL` e precisa de conversão; `alinhamento` é anulável no schema e o valor nulo vira a string `sem alinhamento`, já que o campo é obrigatório no contrato e uma linha faltando esconderia monstros da contagem.

### Ordenação, paginação e contagem

- Quando o modo é `lista_monstros` ou `lista_ataques`, aceita `ordenar_por` e `sentido` (`crescente`/`decrescente`), além de `limite` e `deslocamento`.
- `ordenar_por` é resolvido por lista branca: para monstros, `nome`, `tipo`, `tamanho`, `desafio`, `pontos_vida`, `classe_armadura`, `dano_medio`; para ataques, `bonus_ataque` e `dano_medio`. `tipo` e `tamanho` entraram porque a aba Todos (9a) oferece os seis cabeçalhos como ordenáveis — sem eles, dois cabeçalhos clicariam e não fariam nada, que é a mesma inconsistência reprovada nos selos da 9c. Valor fora da lista **não** levanta erro — cai na ordenação padrão (`nome` para monstros, `bonus_ataque` decrescente para ataques). Link editado à mão não deve derrubar página.
- O núcleo **não impõe limite padrão**: sem `limite`, devolve tudo. Quem impõe teto é a API, porque teto é política de superfície pública, não de leitura. É o que permite a aba "Todos os monstros" listar as 325 numa página.
- Quando recebe conexão, filtros e um grão (`monstros` ou `ataques`), `contar` devolve quantas linhas atendem aos filtros **ignorando paginação**. É a fonte do campo `total` do envelope de paginação do contrato.

### Execução

- Quando recebe conexão, filtros e modo, `executar_consulta` devolve **lista de dicionários** — nunca DataFrame. A camada não conhece pandas: pandas é ferramenta de apresentação, e devolver DataFrame obrigaria a API a importá-lo só para desmontar de volta.
- O `dano_medio` **vem lido da coluna `ataques.dano_medio`**, gravada pela ingestão. Não é calculado aqui. Decisão do usuário em 2026-07-26: como `dano_medio` é coluna de ordenação em `/monstros` e `/ataques` e convive com `limite`/`deslocamento`, calcular em Python depois do `LIMIT` devolveria a página errada em silêncio. Com a média gravada, `ORDER BY` e paginação acontecem no SQL como em qualquer outra coluna. `media_de_dado` continua existindo em `calculos.py` — é ela que a ingestão usa, e ela segue testável isoladamente.
- O `dano_medio` **de um monstro** é a média das médias dos ataques dele, obtida por subconsulta de agregação sobre `ataques`; monstro sem ataque com dado válido recebe `None`. O `dano_medio` **de um ataque** é a coluna daquele ataque, e `dano_extra_medio` a do dano secundário.
- Essa dependência é o que torna esta spec **bloqueada pela reabertura da Spec 4**, que acrescenta as duas colunas e re-popula o banco.
- Toda média sai arredondada em duas casas. Sem regra fixa, o mesmo número sairia diferente em cada consumidor.
- Quando nenhum monstro atende aos filtros, devolve lista vazia. Ausência de resultado não é erro.
- Quando o modo é `resumo` e nada atende, devolve uma linha com contagem zero e médias nulas — o site precisa exibir "0 monstros", não uma tela em branco.

### Leitura de um monstro (`ficha`)

- Quando recebe conexão e um nome, `buscar_monstro` devolve **a ficha completa** daquele monstro: dados do nível monstro, atributos com modificador, testes de resistência **apenas os proficientes**, sentidos, deslocamento, perícias, as listas de interação com dano, imunidades a condição e ambientes, e as **ações aninhadas**, cada uma com seus ataques e efeitos dentro.
- A busca é por **nome exato, sem diferenciar maiúsculas**. Não usa o filtro `nome`, que é por trecho: "Goblin" por trecho casaria "Goblin Boss", e o contrato promete uma criatura ou nada.
- Quando o nome não existe, devolve `None`. Quem chama decide se isso vira 404, aviso ou silêncio.
- Quando um sentido não existe para o monstro, a chave é **omitida** do dicionário, não devolvida como nula.
- Quando um modo de deslocamento vale **zero ou nulo**, a chave é **omitida**. A Spec 3 não fixou qual dos dois a ingestão grava, e a ficha não pode depender disso — a regra cobre os dois casos.
- **`pode_pairar` não é modo de deslocamento** e nunca é omitido: sai sempre, convertido de `INTEGER` 0/1 para booleano, porque `Deslocamento.pode_pairar` é `boolean` no contrato. Aplicar a regra de omissão a ele apagaria o campo em vez de devolver `false`.
- Cada ataque aninhado na ficha traz `dano_medio` e `dano_extra_medio` prontos, lidos das colunas. O contrato os exige no schema `Ataque`, que aparece dentro de `Monstro.acoes[].ataques[]`, e a Spec 8 declara que nenhuma regra de cálculo mora na rota.
- Sem esta função, `/monstros/{nome}` do contrato e a ficha do site não teriam de onde sair, já que `api/` e `web/` têm SQL proibido.

### Resolução de lista de nomes

- Quando recebe conexão e uma lista de nomes, `resolver_nomes` devolve as fichas encontradas **e** a lista dos nomes que não existem.
- É o que a aba Pesquisar consome em `?fixados=Adult+Red+Dragon,Vampire` para exibir os achados e avisar quantos faltaram. O filtro `nome` não serve: é valor único e por trecho.

### Vocabulário e validação de valor

- Quando recebe uma conexão, `vocabulario` devolve, para cada filtro, os valores distintos **com a contagem de monstros de cada um** — `dragon` com 43, `forest` com 151. Uma entrada por filtro, chaveada pelo nome do filtro.
- **Esta é a forma canônica; o contrato expõe uma redução dela.** O schema `Vocabulario` do `openapi.yaml` tem seis chaves fixas (`tipos`, `tamanhos`, `alinhamentos`, `ambientes`, `tipos_dano`, `condicoes`) e nenhuma contagem. Quem faz o remapeamento é a rota da Spec 8 — remapear dicionário não é escrever SQL, então a regra de camadas continua de pé. A aba Relatórios (9b) consome a forma rica direto do núcleo, porque é dela que sai o `dragon (43)` no rótulo das opções. Decisão do usuário em 2026-07-26.
- É lido do banco, não escrito à mão: vocabulário fixo em código sairia de sincronia no próximo re-sync.
- Quando um filtro recebe valor fora do vocabulário (ex: `resiste_a="fogo"`, sendo que o banco guarda `fire`), levanta `ValorDeFiltroInvalido` informando o parâmetro e o valor recebido.
- Quando `desafio_min` é maior que `desafio_max`, **não** é erro: devolve vazio. `"fogo"` é engano de quem escreveu, e devolver vazio esconderia o erro; "de 20 até 5" é pergunta coerente sem resposta. O `BETWEEN` do SQL já se comporta assim.

### Erros de domínio (`bestiario/excecoes.py`)

- `FiltroDesconhecido` — chave de filtro, dimensão ou métrica fora da lista branca.
- `ValorDeFiltroInvalido` — chave válida, valor fora do vocabulário. Carrega o parâmetro e o valor.
- Ambas herdam de uma exceção base do projeto, para a API capturar as duas de uma vez ao traduzir para RFC 7807.

### Métricas e presets

- `METRICAS` é a lista branca das colunas calculadas do modo `comparacao` e do `resumo`, com **estes nomes exatos de chave**, iguais aos do contrato: `monstros` (contagem), `media_pontos_vida`, `media_classe_armadura`, `media_desafio`, `media_dano` e `media_bonus_ataque`. Fixar os nomes aqui é o que torna verificáveis os testes de valor da 7b e a serialização da 8.
- As métricas **saem sempre todas**, em bloco — não são escolhidas por parâmetro. A tela mostra o conjunto pronto, e foi essa a decisão de produto que podou o construtor. A lista branca existe para `FiltroDesconhecido` proteger a dimensão `por`, não para o usuário escolher colunas.
- `media_dano` de um grupo é a média dos `dano_medio` dos monstros do grupo; `media_bonus_ataque` é a média dos bônus dos ataques dos monstros do grupo. As duas são **médias por monstro**, não por linha de ataque — monstro com seis ataques não pesa seis vezes na média do tipo dele.
- `PRESETS` é um dicionário de nome para conjunto de filtros mais modo de saída, cobrindo os relatórios de `relatorios.py`. Não é código: é parâmetro.
- **Dois presets não reproduzem o formato atual do relatório correspondente**, e isso é deliberado — ver a 7b. "Imunidade a dano" vira **três comparações por tipo de dano, uma por relação** (via o filtro `relacao` + dimensão `tipo_dano`), em vez de uma tabela de duas dimensões; "condições impostas" perde a coluna com a lista de nomes de cada grupo. O núcleo não ganha agrupamento por duas dimensões nem concatenação de nomes, porque nenhum outro consumidor do projeto precisa disso — o motor cresce pelo que vem, não pelo que já foi.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os 65 testes anteriores.
- [ ] Teste confirma `media_de_dado("2d10", 8) == 19.0` e `None` para dado fora do padrão.
- [ ] Teste confirma `modificador(27) == 8`.
- [ ] Teste confirma que `saves_proficientes` do Adult Red Dragon devolve exatamente destreza, constituição, sabedoria e carisma.
- [ ] Teste confirma que `montar_consulta` é pura: chamada sem conexão devolve `(sql, parametros)` sem tocar em banco.
- [ ] Teste confirma que filtro de tabela filha gera `EXISTS` e não `JOIN`, e que filtrar por ambiente não duplica monstro de vários ambientes.
- [ ] Teste confirma que `combinar="qualquer"` gera `OR` e `"todos"` gera `AND`.
- [ ] Teste confirma que todo valor de filtro entra por marcador e nenhum é interpolado no texto do SQL.
- [ ] Teste confirma que chave de filtro fora da lista branca levanta `FiltroDesconhecido` sem montar SQL.
- [ ] Teste confirma que `resiste_a="fogo"` levanta `ValorDeFiltroInvalido`.
- [ ] Teste confirma que `desafio_min=20, desafio_max=5` devolve lista vazia sem exceção.
- [ ] Teste confirma que `executar_consulta` devolve lista de dicionários com as chaves do contrato — `desafio`, e **não** `nivel_desafio`.
- [ ] Teste confirma que `ordenar_por="pontos_vida"` com `sentido="decrescente"` devolve o monstro de maior vida primeiro.
- [ ] Teste confirma que `ordenar_por` fora da lista branca cai na ordenação padrão, sem levantar exceção.
- [ ] Teste confirma que `contar` devolve o total ignorando `limite` — com `limite=2` sobre 5 monstros, a lista tem 2 e a contagem diz 5.
- [ ] Teste confirma que sem `limite` a consulta devolve todas as linhas, sem teto implícito.
- [ ] Teste confirma que `buscar_monstro("adult red dragon")` acha o monstro apesar da caixa, e traz ações com ataques e efeitos aninhados.
- [ ] Teste confirma que `buscar_monstro` de nome inexistente devolve `None`.
- [ ] Teste confirma que `buscar_monstro("Goblin")` devolve o Goblin, e **não** casa "Goblin Boss".
- [ ] Teste confirma que a ficha omite a chave de um sentido que o monstro não tem.
- [ ] Teste confirma que a ficha omite o modo de deslocamento tanto quando vale zero quanto quando vale nulo.
- [ ] Teste confirma que `resolver_nomes` devolve as fichas achadas e a lista dos nomes inexistentes.
- [ ] Teste confirma que o modo `resumo` sem resultado devolve uma linha com contagem zero.
- [ ] Teste confirma que o modo `comparacao` sai ordenado da maior contagem para a menor.
- [ ] Teste confirma que `vocabulario` devolve cada valor com sua contagem, uma entrada por filtro.
- [ ] Teste confirma que `relacao="imunidade"` com `por="tipo_dano"` conta só imunidades, e que trocar para `resistencia` muda o resultado.
- [ ] Teste confirma que `ordenar_por="dano_medio"` com `limite=2` devolve os **dois de maior dano médio do conjunto inteiro** — não os dois primeiros de uma página já cortada.
- [ ] Teste confirma que `ordenar_por="tipo"` e `ordenar_por="tamanho"` ordenam de fato, e não caem no padrão.
- [ ] Teste confirma que o modo `comparacao` por `desafio` devolve `valor` como texto, e que monstro sem alinhamento aparece agrupado em `sem alinhamento`.
- [ ] Teste confirma que a ficha traz `pode_pairar` como booleano mesmo quando vale 0 — a chave não é omitida.
- [ ] Teste confirma que os ataques aninhados na ficha trazem `dano_medio` preenchido.
- [ ] Teste confirma que toda média sai com duas casas decimais.
- [ ] Teste confirma que cada preset roda contra banco de teste sem erro de coluna inexistente.

## Módulos afetados

- `bestiario/calculos.py` — **já existe** com `media_de_dado`, criado na Revisão 1 da Spec 4 (a ingestão precisava da fórmula para gravar `dano_medio`). Esta spec acrescenta `modificador` e `saves_proficientes`. Funções puras, sem I/O, sem pandas nem sqlite.
- `bestiario/consultas.py` — NOVO. `montar_consulta` (pura), `executar_consulta`, `contar`, `buscar_monstro`, `resolver_nomes`, `vocabulario`, as listas brancas `FILTROS`/`DIMENSOES`/`METRICAS`/`ORDENACOES` e o `PRESETS`.
- `bestiario/excecoes.py` — NOVO. Exceção base mais `FiltroDesconhecido` e `ValorDeFiltroInvalido`.
- `bestiario/__init__.py` — acrescenta as re-exportações da API pública nova. Só re-exportação. **`cliente_api.buscar_monstro` é renomeada para `buscar_monstro_na_api`** aqui e em `cliente_api.py`, `main.py` e `tests/test_cliente_api.py`: sem isso as duas funções de mesmo nome se re-exportam no mesmo `__init__.py` e a segunda sobrescreve a primeira **sem erro de import**. Depois da 7a, `buscar_monstro` sem qualificador significa a consulta local, que é o caminho principal; o nome novo diz de onde o dado vem. Decisão do usuário em 2026-07-26.
- `tests/test_calculos.py` — NOVO. Sem mock: é tudo função pura.
- `tests/test_consultas.py` — NOVO. Montagem testada sem banco; execução contra SQLite em memória no schema da Spec 3.

## Não mexer

- `bestiario/banco.py` — schema e ingestão intactos. `consultar_por_tipo` e `consultar_por_cr` continuam existindo aqui; quem as remove é a 7c.
- `bestiario/relatorios.py` — os 7 relatórios continuam com SQL próprio nesta spec. Quem delega é a 7b.
- `main.py` — o menu não muda aqui.
- `bestiario/extracao.py`.
- `bestiario/cliente_api.py` — só a renomeação de `buscar_monstro` para `buscar_monstro_na_api`. Nenhuma mudança de comportamento.
- `openapi.yaml` — esta spec não é de endpoint; ela existe para que a 8 consiga cumprir o contrato sem escrever SQL.
- O banco `bestiario_combate.db` — só leitura.

## Decisões tomadas

- Retorno em **dicionários**, não DataFrame → a camada não deve conhecer pandas, que é ferramenta de apresentação. Consequência aceita: `media_dano` vira Python puro, o que tira pandas do núcleo por completo.
- Chaves com **os nomes do contrato**, não os das colunas → traduzir uma vez aqui evita que 7c, 8, 9b e 9c tenham cada uma a sua tradução, e que a divergência apareça só em produção.
- Validação de valor de filtro na camada → `"fogo"` é engano; vazio em silêncio esconderia o erro. Por isso a camada lê o vocabulário do banco, que é o mesmo dado do endpoint `/vocabulario`.
- Intervalo de desafio invertido devolve vazio → pergunta coerente sem resposta, diferente de valor digitado errado.
- Filtros de tabela filha por `EXISTS` → `JOIN` corromperia contagens e médias.
- **Ordenação, `contar`, `buscar_monstro` e `resolver_nomes` acrescentados após o `/spec-review`** → cada um tem consumidor já especificado: ordenação (7b, `/ataques` do contrato, aba Todos), contagem (envelope de paginação do contrato), ficha (`/monstros/{nome}` e a aba Pesquisar), lista de nomes (`?fixados=`). Sem eles, `api/` e `web/` precisariam escrever SQL, o que as duas specs proíbem.
- Sem limite padrão no núcleo → teto é política de superfície pública. A API impõe o dela; a aba Todos precisa das 325.
- `agregado` renomeado para `comparacao` → o glossário manda evitar "agrupamento"; o contrato já expõe `/comparacoes`.
- Ordenação inválida cai no padrão em vez de levantar erro, ao contrário de valor de filtro inválido → ordenação é preferência de exibição, e ignorá-la ainda responde a pergunta certa. Valor de filtro errado responderia **outra** pergunta, e por isso precisa reclamar.
- Média de bônus de ataque entra em `METRICAS`, mas agrupamento por duas dimensões e concatenação de nomes **não** entram → a primeira é uma linha a mais numa lista branca; as outras duas são mudanças estruturais que só os relatórios antigos usariam. O motor cresce pelo que vem, não pelo que já foi.
- Divisão da Spec 7 em 7a, 7b e 7c → o conjunto somava score 10, acima do limite de 8.
- **`dano_medio` gravado no banco em vez de calculado em Python** (usuário, 2026-07-26) → é coluna de ordenação no contrato e convive com paginação; calcular depois do `LIMIT` devolveria a página errada sem nenhum sinal de erro. Custo aceito: reabrir a Spec 4 e re-sincronizar o banco. Princípio: **dado que participa de `ORDER BY` precisa existir onde o `ORDER BY` acontece** — o mesmo motivo pelo qual índices não funcionam sobre valor calculado na aplicação.
- **Vocabulário rico no núcleo, reduzido na API** (usuário, 2026-07-26) → a tela precisa da contagem e o contrato não a promete; a forma mais rica mora embaixo e cada superfície corta o que não usa. O caminho inverso — núcleo pobre — obrigaria a 9b a contar por fora, e contar por fora significa SQL em `web/`.
- **`relacao` e `media_bonus_ataque` publicados** (usuário, 2026-07-26) → os dois relatórios que dependiam deles sobrevivem inteiros, e o que o núcleo calcula a API publica. Métrica calculada e não exposta é trabalho que ninguém vê.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → remover a marca `(7)` de `calculos.py`, `consultas.py` e `excecoes.py`. A marca `(7)` da linha de `relatorios.py` só sai na 7b, quando a delegação acontece.
- **O que já funciona** → acrescentar item de camada de consulta parametrizada com lista branca, validação de vocabulário, ordenação e leitura de ficha.
- **O que está incompleto** → o item "SQL espalhado" **continua aberto**: a camada existe, mas `relatorios.py` só delega na 7b.
- **Bloco em aberto — Specs 7 a 10** → marcar 7a como concluída e registrar que a 7 virou três specs.
