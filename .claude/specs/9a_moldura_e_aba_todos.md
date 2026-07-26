# Moldura do site e aba "Todos os monstros"

**Ordem:** 9a de 9
**Depende de:** Specs 7a (núcleo) e 8 (API JSON)
**Score:** 6
**Revisão:** aprovada

## O que faz
Levanta o site: a moldura com as três abas e o botão de exibição, a identidade visual inteira, e a aba "Todos os monstros" funcionando de ponta a ponta.

## Comportamento

> **Revisada em 2026-07-25 após o `/spec-review`.** Corrigidos: o prefixo duplicado da API,
> o `/docs` que não existiria onde o rodapé aponta, a dependência circular com a 9c pelo
> bloco de estatísticas, e critérios de teste que misturavam banco em memória com contagens
> do banco real.

### Servidor e montagem

- Quando o servidor sobe por `web.app:app`, ele serve o site **e inclui o roteador da Spec 8 com o prefixo `/api/v1`**. Não monta a aplicação da Spec 8 como sub-aplicação: montar uma app que já prefixa dentro de outra que prefixa daria `/api/v1/api/v1/`. `api.app:app` continua subindo sozinho para os testes da Spec 8.
- Como o roteador é incluído e não montado, `/docs` fica na **raiz** e documenta a API — que é onde o link do rodapé aponta e onde o `CLAUDE.md` promete. As rotas de HTML ficam fora do esquema.
- `web/app.py` **registra os mesmos tratadores de erro que `api/app.py` registra** (os da Spec 8: `ValorDeFiltroInvalido` e `FiltroDesconhecido` viram 422 RFC 7807, base não sincronizada vira 503). Incluir o roteador traz as rotas, não os tratadores — e como o `CLAUDE.md` documenta `web.app:app` como a entrada real, sem isso `?resiste_a=fogo` responderia 500 em produção enquanto os testes da Spec 8, que rodam contra `api.app:app`, continuariam verdes. Para os dois não saírem de sincronia, a Spec 8 expõe uma função única de registro que as duas aplicações chamam.
- Quando alguém abre `/`, é redirecionado para `/relatorios`.
- Quando o banco não tem nenhum monstro, o site exibe uma página explicando que a base não foi sincronizada e indicando a opção 4 do menu — não uma tabela vazia sem explicação, nem o 503 cru que a API devolve.

### Moldura (`base.html`)

- Quando qualquer página renderiza, ela traz as três abas — Relatórios, Pesquisar, Todos os monstros — com a aba corrente destacada.
- Quando qualquer página renderiza, ela traz o botão **Resumida / Completa** no cabeçalho, com o estado corrente marcado.
- Quando o usuário troca de aba, o modo de exibição escolhido **viaja junto** pelo parâmetro `modo` da URL. Trocar de aba não perde o que ele escolheu.
- Quando o modo não vem na URL, vale `resumida`.
- Quando a página renderiza, o rodapé traz um link **API** apontando para `/docs`. É o único caminho pelo qual quem programa descobre que a API existe.

### Aba "Todos os monstros"

- Quando alguém abre `/monstros`, a página lista os 325 na forma enxuta: nome, tipo, tamanho, desafio, pontos de vida, classe de armadura.
- Quando o usuário clica num cabeçalho de coluna, a lista reordena por aquela coluna. A ordenação vai na URL (`?ordenar_por=desafio&sentido=decrescente`), então o estado sobrevive a recarregar e o link é compartilhável.
- Quando o usuário clica na primeira vez num cabeçalho, ordena crescente; na segunda, decrescente. Os valores de `sentido` são `crescente` e `decrescente` — não a abreviação inglesa `desc`, que ainda colidiria visualmente com o campo `desc` da Open5e usado nas Specs 4 e 5.
- Quando o usuário clica no nome de um monstro, vai para `/pesquisar?fixados={nome}`. O nome do parâmetro é fixado **aqui**, e a Spec 9c o consome — link emitido sem contrato divergiria de quem o recebe.
- Quando `ordenar_por` vem com coluna fora da lista permitida, cai na ordenação padrão por nome, sem erro. Quem aplica essa regra é o núcleo.
- Esta aba **não tem filtro**. Quem quer filtrar usa a aba Relatórios. A aba é para folhear.
- Nesta aba, o botão **Completa** não abre ficha nenhuma: o bloco de estatísticas nasce na Spec 9c, junto do `_ficha.html`. Até lá, alternar o modo aqui só afeta as outras abas. A 9c acrescenta o comportamento e tem permissão explícita para editar `todos.html`.

### Identidade visual (`estilo.css`)

- O CSS sai do esboço aprovado, que é a fonte da verdade visual. Ele vive hoje em pasta temporária e **precisa ser copiado para o repositório** nesta spec: se a pasta for limpa antes, as fontes em base64 se perdem.
- **Onde o esboço está** (verificado íntegro em 2026-07-26): `%LOCALAPPDATA%\Temp\claude\C--Users-Arthur-OneDrive-Imagens-Documentos-projetos-treino-Bestiario-dEd-python\29d573de-3f99-419d-a4b1-f5a29d66fab8\scratchpad\`, com `bestiario-mockup.html` (a tela aprovada), `fontes.css` e `fontes_embutidas.css` (Cinzel e EB Garamond em `data:font/woff2;base64`). Se a pasta já não existir quando esta spec for implementada, **pare e avise** — reinventar o CSS produz outra coisa, e o esboço foi aprovado como está.
- As duas fontes (Cinzel e EB Garamond, ambas SIL OFL) ficam embutidas em base64 no próprio CSS. Sem CDN: a origem externa é bloqueada e o recuo silencioso para outra fonte destruiria a semelhança com o livro.
- Tema único claro. A página ignora a preferência de tema do sistema de propósito, porque o livro não tem versão escura.
- Elementos que vêm do livro e não podem sumir na conversão para Jinja: a cunha vermelha afilada como separador, a listra verde-salva das tabelas, a moldura com volutas nos cantos e fio dourado, o grão de papel, e zero canto arredondado.

### A fixture compartilhada

- A fixture de banco em memória é a **de `tests/conftest.py`, criada na Spec 8** — esta spec a amplia, não cria outra. Duas fixtures do mesmo schema com pressupostos independentes divergiriam em silêncio. O conjunto é pequeno e conhecido, e cobre os casos das três abas: tipos variados, monstro com vários ambientes, monstro com imunidade, monstro com ataque e efeito, monstro sem ataque nenhum.
- O site recebe a conexão pela **mesma dependência do FastAPI** que a Spec 8 define, e o teste a substitui por `app.dependency_overrides`. É o que torna testáveis tanto a listagem quanto o caso de banco vazio.
- **Nenhum teste do site usa `bestiario_combate.db`.** O arquivo está fora do git e não existe no CI, que só roda `uv sync` e `pytest`. Critério que dependa dele falha em máquina limpa.
- As Specs 9b e 9c ampliam esta mesma fixture em vez de criarem a sua. Três fixtures com pressupostos diferentes no mesmo arquivo de teste colidiriam.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-8.
- [ ] Teste confirma que `GET /` redireciona para `/relatorios`.
- [ ] Teste confirma que `GET /monstros` responde 200 e o HTML traz uma linha para **cada monstro da fixture**.
- [ ] Teste confirma que `GET /api/v1/monstros` responde 200 pela aplicação em `web.app:app`, com o prefixo aplicado uma vez só.
- [ ] Teste confirma que `GET /docs` responde 200 em `web.app:app`.
- [ ] Teste confirma que `GET /api/v1/monstros?resiste_a=fogo` **pela aplicação `web.app:app`** responde 422 com `application/problem+json` — os tratadores da Spec 8 valem também aqui, não só em `api.app:app`.
- [ ] Teste confirma que `?ordenar_por=desafio&sentido=decrescente` devolve o monstro de maior desafio da fixture em primeiro.
- [ ] Teste confirma que `?ordenar_por=` com coluna fora da lista permitida não quebra nem vaza erro: cai na ordenação padrão por nome.
- [ ] Teste confirma que `?modo=completa` aparece nos links das outras abas — o modo viaja entre abas.
- [ ] Teste confirma que o rodapé contém link para `/docs`.
- [ ] Teste confirma que, com banco sem monstros, `/monstros` responde 200 com a mensagem de base não sincronizada, e **não** com tabela vazia.
- [ ] Busca por `SELECT`, `execute` e `sqlite3` em `web/` não encontra ocorrência.
- [ ] Busca por `http://` e `https://` em `web/static/estilo.css` não encontra ocorrência — nenhuma fonte ou recurso vem de fora.
- [ ] `web/static/estilo.css` contém `@font-face` com `src: url(data:font/woff2;base64,` para **Cinzel** e para **EB Garamond**. Sem este critério, um CSS vazio ou reescrito do zero passaria no critério anterior — e é exatamente o artefato sob risco de perda.
- [ ] `uv run uvicorn web.app:app` sobe, `/monstros` abre no navegador e `/docs` também.

## Módulos afetados

- `web/__init__.py` — NOVO. Vazio.
- `web/app.py` — NOVO. Cria a aplicação, configura o Jinja2, serve os estáticos, **inclui o roteador da Spec 8** com o prefixo `/api/v1`, **chama a função de registro de tratadores de erro da Spec 8** e registra as rotas do site, essas fora do esquema da documentação.
- `tests/conftest.py` — amplia a fixture criada na Spec 8 com o que as três abas exigem. Não cria fixture nova.
- `web/rotas.py` — NOVO. Rota raiz com redirecionamento e rota `/monstros`. As rotas de `/relatorios` e `/pesquisar` entram nas Specs 9b e 9c; aqui existem apenas como destino de link, podendo responder uma página mínima.
- `web/templates/base.html` — NOVO. Moldura: cabeçalho, abas, botão de exibição, rodapé com link da API, bloco de conteúdo.
- `web/templates/todos.html` — NOVO. Tabela dos 325 com cabeçalhos ordenáveis.
- `web/static/estilo.css` — NOVO. Portado do esboço aprovado, com as fontes em base64.
- `tests/web/test_rotas.py` — NOVO. Via `TestClient`, contra banco de teste em memória.
- `pyproject.toml` — acrescenta `jinja2` com teto de versão, se a Spec 8 ainda não o trouxe.

## Não mexer

- `api/` — o roteador da Spec 8 é **incluído** como está. Se o site precisar de algo que a API não dá, isso se resolve no núcleo ou numa rota do site, nunca alterando o contrato da API.
- `openapi.yaml` — o contrato não muda por causa do site.
- `bestiario/` inteiro — nenhum módulo do núcleo é tocado.
- `main.py` — o menu do terminal continua idêntico.
- Os templates das abas Relatórios e Pesquisar — são das Specs 9b e 9c.
- A identidade visual do esboço — cores, fontes, cunha, volutas e listra são para portar, não para reinterpretar.

## Decisões tomadas

- A aba "Todos" não ganha filtro → é a aba de folhear, para quem não sabe o que procura. Filtrar é a função da aba Relatórios, e duplicar filtro nas duas criaria dois lugares para fazer a mesma coisa de jeitos diferentes.
- Ordenação na URL, e não só no navegador → sobrevive a recarregar e vira link compartilhável, pelo mesmo motivo que o resto do estado do site vive na URL.
- Modo "Completa" nesta aba **não abre ficha nenhuma nesta spec** → o bloco de estatísticas nasce na 9c, junto do `_ficha.html`. Quando a 9c o acrescentar, ele abrirá só a linha clicada: 325 blocos empilhados dariam uma página que ninguém lê e que o navegador sofreria para montar.
- `web.app:app` como entrada única, **incluindo** o roteador da API em vez de montar a aplicação → montar daria prefixo duplicado e jogaria a documentação para `/api/v1/docs`, onde o link do rodapé não a acharia. Incluir resolve os dois. `api.app:app` continua de pé para os testes da Spec 8 rodarem isolados.
- O bloco de estatísticas sai desta spec e vai inteiro para a 9c → a 9a precisava dele para abrir a linha clicada, mas quem o cria é a 9c: era dependência circular. Com a criação concentrada na 9c, que ganha permissão de editar `todos.html`, o `_ficha.html` existe num lugar só e ninguém duplica.
- Fixture de teste única em `conftest.py`, sem tocar no banco real → o `.db` está fora do git e não existe no CI; critério que dependa dele falha em máquina limpa. Três fixtures separadas colidiriam no mesmo arquivo de teste.
- Banco vazio mostra página explicativa em vez do 503 da API → quem abre o site é pessoa, não programa. O 503 está certo para a API e errado para uma tela.
- O CSS é portado do esboço, que fica em pasta temporária → risco real de perda. A cópia para o repositório é parte do escopo desta spec, não detalhe de implementação.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → remover a marca `(9)` de `web/`, `templates/` e `static/`.
- **Tecnologias usadas** → remover a marca `(9)` de Jinja2.
- **Como rodar** → a entrada volta a ser `web.app:app`, como já documentado; remover a nota de que vale a partir das Specs 8-9.
- **O que está incompleto** → o item "Sem front-end e sem API HTTP" perde mais uma parte; sobra até a 9c.
- **Bloco em aberto — Specs 7 a 10** → marcar 9a como concluída.
