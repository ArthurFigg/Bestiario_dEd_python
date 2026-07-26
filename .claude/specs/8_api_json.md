# API JSON

**Ordem:** 8 de 9
**Depende de:** Spec 7a (núcleo de consulta)
**Score:** 6
**Revisão:** aprovada

## O que faz
Expõe o bestiário como API HTTP de leitura, implementando o `openapi.yaml` já commitado, sem escrever nenhuma consulta própria — tudo passa pelo núcleo da Spec 7a.

> **Revisada em 2026-07-25 após o `/spec-review`.** A versão anterior registrava as rotas
> já sob `/api/v1` e a Spec 9a montava essa aplicação sob `/api/v1` de novo — o endereço
> viraria `/api/v1/api/v1/monstros`. Também deixava de fora o filtro `nome` por trecho (do
> qual a 9c depende), a ordenação e as regras de serialização que o contrato promete.

## Comportamento

### Montagem e prefixo

- As rotas vivem num **roteador sem prefixo** em `api/rotas.py`. Quem aplica `/api/v1` é a aplicação que o inclui — `api/app.py` quando roda sozinha nos testes desta spec, e `web/app.py` na Spec 9a. **O roteador é incluído, não montado como sub-aplicação**; assim o prefixo é aplicado uma vez só, e a documentação fica na raiz.
- A documentação navegável fica em **`/docs`**, na aplicação, documentando os endpoints da API. As rotas de HTML da Spec 9 ficam fora do esquema, para a documentação não misturar página com recurso.
- O `openapi.yaml` declara os caminhos sem prefixo e põe `/api/v1` em `servers`. O teste de contrato compara **`servers[0].url` + caminho do contrato** contra os caminhos gerados. Sem essa normalização o teste falharia por construção.

### Regra que atravessa a spec inteira

- **Nenhuma rota escreve SQL.** Toda rota traduz parâmetros de consulta em filtros, chama o núcleo e serializa o que voltou. Rota que monte query própria é violação de camada, mesmo que funcione.
- O contrato **já existe** em `openapi.yaml`. Esta spec o implementa; não o redefine. Divergência entre código e contrato se resolve corrigindo o código, ou alterando o contrato de propósito e num commit que diga isso.

### Endpoints

- Quando chega `GET /api/v1/monstros`, responde 200 com o envelope de paginação (`total`, `limite`, `deslocamento`, `itens`), cada item na forma enxuta.
- Quando chega `GET /api/v1/monstros/{nome}`, responde 200 com a ficha completa, com as ações aninhadas e, dentro de cada ação, seus ataques e efeitos.
- Quando o nome não existe, responde **404** com corpo RFC 7807.
- A busca por nome no caminho é exata e não diferencia maiúsculas — `/monstros/adult red dragon` acha o mesmo que `/monstros/Adult%20Red%20Dragon`. Usa `buscar_monstro` do núcleo, **não** o filtro `nome`.
- Quando chega `GET /api/v1/monstros?nome=drag`, responde 200 com todos os monstros cujo nome contém o trecho, sem diferenciar maiúsculas. É este parâmetro que a busca incremental do site consome — e é diferente da busca exata do caminho.
- Quando chega `ordenar_por` em `/monstros` ou `/ataques`, o resultado sai ordenado por aquela coluna. Valor fora do enum **não** é erro: cai na ordenação padrão, como o núcleo define.
- **`sentido` existe só em `/monstros`.** Em `/ataques` a ordenação é sempre decrescente, como o contrato declara na descrição de `ordenar_por` — maior bônus e maior dano primeiro é a única leitura útil de uma lista de ataques. Aceitar `sentido` ali criaria parâmetro não documentado.
- Quando chega `GET /api/v1/ataques`, responde 200 com envelope de paginação, cada item sendo um ataque com o monstro e a ação donos.
- Quando chega `GET /api/v1/comparacoes?por=tipo`, responde 200 com uma lista de linhas agregadas.
- Quando `por` está ausente em `/comparacoes`, responde **422** — é o único parâmetro **de consulta** obrigatório da API (o `nome` do caminho de `/monstros/{nome}` também é obrigatório).
- Quando chega `GET /api/v1/resumo`, responde 200 com uma linha só, mesmo que nenhum monstro atenda aos filtros (nesse caso, contagem zero e médias nulas).
- Quando chega `GET /api/v1/vocabulario`, responde 200 com as listas de valores aceitos, lidas do banco. O núcleo devolve **uma entrada por filtro, com contagem**; a rota **remapeia** para as seis chaves do schema `Vocabulario` (`tipos`, `tamanhos`, `alinhamentos`, `ambientes`, `tipos_dano`, `condicoes`) e descarta as contagens. Remapear dicionário não é escrever SQL — a regra de camadas continua valendo. Decisão do usuário em 2026-07-26.

### Filtros

- Os quatro endpoints que aceitam filtro aceitam **os mesmos doze filtros de domínio**, com os mesmos nomes: `tipo`, `tamanho`, `alinhamento`, `desafio_min`, `desafio_max`, `ambiente`, `resiste_a`, `imune_a`, `vulneravel_a`, `imune_a_condicao`, `impoe`, `relacao` — mais o `combinar`. Filtro que mude de nome entre endpoints é defeito, não variação.
- `relacao` (`imunidade`/`resistencia`/`vulnerabilidade`) foi acrescentado ao contrato em 2026-07-26. Combinado com `por=tipo_dano` em `/comparacoes`, é o que produz a contagem por tipo de dano dentro de uma relação — sem ele o agrupamento misturaria as três.
- Os parâmetros **de apresentação** não são uniformes, e o contrato diz onde cada um vale: `nome` só em `/monstros`; `limite` e `deslocamento` só em `/monstros` e `/ataques`; `ordenar_por` e `sentido` só onde há lista. `/comparacoes` e `/resumo` não paginam — a resposta já é o agregado.
- Quando um filtro é omitido, ele não restringe nada.
- Quando `combinar` é omitido, vale `todos`.

### Serialização — o que o contrato promete e a rota tem de cumprir

- Quando um monstro não tem um sentido, a chave **não aparece** no JSON.
- Quando um modo de deslocamento vale zero ou nulo, a chave **não aparece**. Zero significa "não possui", e a Spec 3 não fixou qual dos dois a ingestão grava.
- Quando a ficha traz testes de resistência, traz **apenas os proficientes**, como o núcleo os deduz.
- Quando um ataque é serializado, traz `dano_medio` e `dano_extra_medio` já calculados.
- Quando `/comparacoes` responde, as linhas saem da maior contagem para a menor.

Nenhuma dessas regras é implementada na rota: todas vêm prontas do núcleo. Estão listadas aqui porque o teste de contrato, que só verifica existência de campo, não as pegaria — e a Spec 9c depende de três delas.

### Erros

- **A conexão SQLite chega às rotas por dependência do FastAPI**, não por import de módulo nem por variável global. É o único ponto de substituição que permite ao teste apontar para a fixture em memória via `app.dependency_overrides` — sem ele, ou o teste toca o `bestiario_combate.db` real (proibido: está fora do git e não existe no CI) ou os critérios de banco vazio e de erro não fecham. A mesma dependência serve à Spec 9a, que roda o site sobre a mesma aplicação.
- Todo erro sai em `application/problem+json` no formato RFC 7807, com `type`, `title`, `status`, `detail` e `instance`.
- Quando o núcleo levanta `ValorDeFiltroInvalido`, responde **422** e o `detail` nomeia o parâmetro, o valor recebido e remete a `/vocabulario`. Quem errou `resiste_a=fogo` precisa saber onde descobrir que o certo é `fire`.
- Quando o núcleo levanta `FiltroDesconhecido`, responde **422**.
- Quando o FastAPI rejeita um parâmetro por tipo ou intervalo (ex: `limite=500`, acima do máximo de 200), a resposta também sai em RFC 7807 — o formato padrão do FastAPI é substituído, para a API ter **um** formato de erro só.
- Quando `desafio_min` é maior que `desafio_max`, responde **200** com lista vazia. Não é erro: é pergunta coerente sem resposta, conforme decidido na Spec 7a.

### Banco não sincronizado

- Quando o banco não tem nenhum monstro, **todo** endpoint responde **503** com corpo RFC 7807 dizendo que a base não foi sincronizada e indicando a opção 4 do menu.
- A verificação é uma contagem barata, feita por requisição.
- O contrato documenta esse caso pela resposta `default` de cada operação, acrescentada ao `openapi.yaml` na revisão de 2026-07-25. Antes disso a spec prometia um código que o contrato não previa.

### Contrato e documentação

- O `openapi.yaml` commitado continua sendo o contrato; `/docs` é a vista dele gerada pelo código. O teste de contrato é o que impede os dois de divergirem.
- **Cada rota declara explicitamente `responses` para o `404` (só em `/monstros/{nome}`) e para a resposta `default` em `application/problem+json`.** O FastAPI gera sozinho apenas `200` e `422`; sem a declaração, o `404` e o `default` — que é onde mora o `503` de base não sincronizada — existiriam no contrato e não no gerado, e o teste de contrato passaria sem cobrir justamente as respostas que o projeto mais depende de não perder.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-7c.
- [ ] Teste de contrato confirma que o conjunto de caminhos do `openapi.yaml`, **prefixado com o `url` de `servers`**, é exatamente igual ao conjunto de caminhos do OpenAPI gerado — endpoint criado sem documentar quebra o teste.
- [ ] Teste confirma que `GET /api/v1/monstros` responde 200 — ou seja, o prefixo é aplicado **uma vez só**, e não `/api/v1/api/v1/`.
- [ ] Teste confirma que `?nome=drag` devolve mais de um monstro, e que `/monstros/Goblin` devolve exatamente um — busca por trecho e busca exata são caminhos diferentes.
- [ ] Teste confirma que `?ordenar_por=pontos_vida&sentido=decrescente` devolve o de maior vida primeiro, e que valor fora do enum não quebra.
- [ ] Teste confirma que a ficha omite sentido ausente e deslocamento zero, e traz só os testes de resistência proficientes.
- [ ] Teste confirma que `/docs` responde 200 e que nenhuma rota de HTML aparece no esquema.
- [ ] Teste de contrato confirma que, para cada operação do `openapi.yaml`, todo parâmetro e todo campo de resposta prometidos **existem** no gerado. O gerado pode ter mais; não pode ter menos.
- [ ] Teste de contrato confirma que **todo status code prometido** por cada operação existe no gerado — incluindo o `default` das seis e o `404` de `/monstros/{nome}`.
- [ ] Teste confirma que `/ataques` **não** aceita `sentido`: a ordenação é sempre decrescente.
- [ ] Teste confirma que `GET /api/v1/vocabulario` responde com exatamente as seis chaves do schema `Vocabulario`, sem contagem, apesar de o núcleo devolver onze entradas com contagem.
- [ ] Teste confirma `GET /api/v1/monstros` responde 200 e o corpo tem `total`, `limite`, `deslocamento` e `itens`.
- [ ] Teste confirma `GET /api/v1/monstros/Adult Red Dragon` responde 200 e traz ações aninhadas com ataques dentro.
- [ ] Teste confirma que nome inexistente responde 404 com `content-type: application/problem+json`.
- [ ] Teste confirma que `resiste_a=fogo` responde 422 e o `detail` cita `resiste_a` e `/vocabulario`.
- [ ] Teste confirma que `/comparacoes` sem `por` responde 422.
- [ ] Teste confirma que `limite=500` responde 422 em formato RFC 7807, e **não** no formato padrão do FastAPI.
- [ ] Teste confirma que `desafio_min=20&desafio_max=5` responde 200 com `itens` vazio.
- [ ] Teste confirma que, com banco sem monstros, `/monstros` responde 503 citando a sincronização.
- [ ] Teste confirma que os mesmos filtros funcionam nos quatro endpoints que os aceitam.
- [ ] Teste confirma que nenhuma rota executa SQL: busca por `SELECT`, `execute` e `sqlite3` em `api/` não encontra ocorrência.
- [ ] `uv run uvicorn api.app:app` sobe e `/docs` abre a documentação navegável.

## Módulos afetados

- `api/__init__.py` — NOVO. Vazio.
- `api/app.py` — NOVO. Cria a aplicação FastAPI, **inclui** o roteador com o prefixo `/api/v1`, registra os tratadores de erro e configura título e versão a partir do contrato. Executável sozinho, para esta spec fechar sem depender da Spec 9.
- `api/modelos.py` — NOVO. Modelos Pydantic que materializam os schemas do contrato: `MonstroResumido`, `Monstro`, `Acao`, `Ataque`, `AtaqueComMonstro`, `Efeito`, `Atributos`, `Atributo`, `TesteDeResistencia`, `Sentidos`, `Deslocamento`, `Pericia`, `ListaDeMonstros`, `ListaDeAtaques`, `LinhaDeComparacao`, `Resumo`, `Vocabulario`, `Problema`.
- `api/rotas.py` — NOVO. Um roteador **sem prefixo** com os 6 endpoints. Cada um monta filtros, chama o núcleo e serializa. Os parâmetros de filtro ficam numa dependência compartilhada, para os quatro endpoints filtráveis não repetirem a lista.
- `api/erros.py` — NOVO. Tratadores que convertem `ValorDeFiltroInvalido`, `FiltroDesconhecido`, o erro de validação do FastAPI e a base vazia em respostas RFC 7807. Expõe **`registrar_tratadores(app)`**, uma função única que `api/app.py` e `web/app.py` chamam. Incluir o roteador leva as rotas, não os tratadores: sem essa função, `web.app:app` — que o CLAUDE.md documenta como a entrada real — devolveria 500 onde a API devolve 422, e os testes desta spec, que rodam contra `api.app:app`, não pegariam a regressão.
- `tests/conftest.py` — NOVO. A fixture de banco em memória no schema da Spec 3, **compartilhada com o site**. Nasce aqui porque esta spec vem antes da 9a; a 9a e as demais a ampliam em vez de criar a sua. Duas fixtures do mesmo schema com pressupostos independentes divergem em silêncio, e os critérios desta spec exigem monstros nomeados (`Adult Red Dragon`, `Goblin`, dois nomes contendo "drag") que a fixture do site também precisa ter.
- `tests/api/test_rotas.py` — NOVO. Via `TestClient`, contra a fixture compartilhada de `tests/conftest.py`.
- `tests/api/test_contrato.py` — NOVO. Compara o `openapi.yaml` com o OpenAPI gerado pelo app.
- `pyproject.toml` — acrescenta `fastapi`, `uvicorn` de produção e `httpx`, `pyyaml` de desenvolvimento, com teto de versão.

## Não mexer

- `openapi.yaml` — é o contrato, e esta spec o implementa. Se algo nele estiver errado, isso é conserto deliberado em commit próprio, não ajuste silencioso para o teste passar. Ele **já foi corrigido** em 2026-07-25, antes da implementação, para cobrir a resposta `default` (que absorve o 503), os filtros `vulneravel_a` e `imune_a_condicao`, a ordenação de `/monstros` e o `dano_medio` da forma enxuta — tudo que as Specs 9b e 9c consomem e que o contrato não prometia.
- `bestiario/consultas.py`, `calculos.py`, `excecoes.py` — criados na 7a e consumidos como estão. Se um endpoint precisar de algo que o núcleo não oferece, é sinal de que a 7a ficou incompleta, e não licença para consultar o banco daqui.
- `bestiario/banco.py`, `cliente_api.py`, `extracao.py`, `relatorios.py` — nenhum é tocado.
- `main.py` — o menu do terminal não muda.
- `web/` — não existe ainda; é a Spec 9. Esta spec não cria template, CSS nem rota de HTML.
- O schema do banco e o arquivo `bestiario_combate.db` — a API só lê.

## Decisões tomadas

- Teste de contrato **contido, com os caminhos por igualdade exata** → igualdade estrita no arquivo inteiro quebraria por ordem de chave e por campo que o FastAPI acrescenta sozinho; teste que dá alarme falso acaba sendo apagado, e aí não sobra proteção nenhuma. Comparar a lista de caminhos por igualdade fecha o buraco da abordagem contida: endpoint não documentado quebra o teste. Estrito onde a promessa mora, tolerante no detalhe. Decisão delegada ao assistente por falta de base do usuário, com o raciocínio registrado aqui.
- Banco vazio responde **503**, não 200 vazio → lista vazia é ambígua: quem consome não distingue "meu filtro não achou nada" de "o servidor não tem dado". O consumidor depuraria o próprio filtro por um bom tempo. 503 é o código correto porque a falha não é do pedido (não é 4xx) e o servidor está genuinamente incapaz de servir até alguém sincronizar. Também delegada ao assistente.
- Erro de validação do FastAPI convertido para RFC 7807 → API com dois formatos de erro obriga quem consome a tratar os dois. O contrato promete um.
- Roteador sem prefixo, **incluído** e não montado → montar sub-aplicação já prefixada dentro de outra que também prefixa dava `/api/v1/api/v1/`, e ainda jogava a documentação para `/api/v1/docs`, onde o link do rodapé da Spec 9a não a acharia. Incluir o roteador resolve os dois de uma vez: prefixo aplicado uma única vez, `/docs` na raiz.
- `api/app.py` executável sozinho → a spec precisa fechar com teste próprio sem depender da Spec 9. Depois da Spec 9, a entrada passa a ser `web.app:app`, que inclui o mesmo roteador.
- Gerar a spec inteira em vez de dividir (score 6) → os modelos Pydantic isolados não teriam critério verificável que preste: "o modelo existe" não prova nada, só ganha sentido quando um endpoint devolve dado por ele. A divisão criaria uma parte que não fecha sozinha.
- Fatia do contrato implementada: os operationIds `listarMonstros`, `buscarMonstro`, `listarAtaques`, `compararMonstros`, `resumirMonstros` e `obterVocabulario`, com todos os schemas de `components`.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → remover a marca `(8)` de `api/` e de `openapi.yaml`; passam a existir.
- **Tecnologias usadas** → remover a marca `(8/9)` de FastAPI e uvicorn.
- **Como rodar** → a seção já prevê o servidor; ajustar a entrada para `api.app:app` enquanto a Spec 9 não existir.
- **O que está incompleto** → o item "Sem front-end e sem API HTTP" perde a parte da API; a parte do site continua aberta até a Spec 9.
- **Setup do ambiente** → mover `fastapi`, `uvicorn`, `httpx` e `pyyaml` de "dependências das Specs 8-9" para instaladas.
- **Bloco em aberto — Specs 7 a 10** → marcar a 8 como concluída.
