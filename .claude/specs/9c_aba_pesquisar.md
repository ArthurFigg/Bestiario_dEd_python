# Aba "Pesquisar"

**Ordem:** 9c de 9
**Depende de:** Specs 7a (núcleo), 8 (API JSON), 9a (moldura) e 9b (aba Relatórios)
**Score:** 5
**Revisão:** pendente

## O que faz
Entrega a aba de busca e comparação: o campo que sugere nomes consumindo a API, as fichas acumuladas na tela em bloco de estatísticas, e o link JSON de cada uma.

## Comportamento

### Busca

- Quando o usuário digita no campo de busca, sugestões de nome aparecem, buscadas em `GET /api/v1/monstros?nome=…` com `fetch`. Sem framework nem etapa de compilação.
- Quando o usuário escolhe uma sugestão, o monstro é acrescentado às fichas da tela.
- Quando a busca não encontra nada, a tela diz que nenhum monstro corresponde, sem apagar o que já estava fixado.
- Quando o JavaScript está desligado ou falha, o campo continua funcionando como formulário comum enviado ao servidor. A busca é conveniência, não requisito.

### Fichas acumuladas

- Quando um monstro é acrescentado, ele se junta aos que já estão na tela. **Não há limite de quantidade** — a aba pode conter desde um até os 325.
- Quando o usuário quer tirar um, cada ficha tem um controle de remoção.
- Quando não há nenhum monstro na tela, ela mostra o convite para pesquisar, e não uma área em branco.

### Estado na URL

- Quando os monstros foram escolhidos um a um, a URL os carrega por nome: `?fixados=Adult+Red+Dragon,Vampire`.
- Quando o recorte veio da aba Relatórios, a URL carrega **os filtros**, não os nomes: `?tipo=dragon&desafio_min=15`. A aba refaz a consulta e exibe todos os que casam. Ela aceita **os mesmos nomes de parâmetro** que a 9b emite, incluindo `combinar` — sem ele, um recorte feito com "qualquer um dos filtros" seria reavaliado como "todos" e exibiria um conjunto diferente do que o relatório mostrou, sem erro nenhum.
- O motivo da distinção é tamanho: 325 nomes passariam de seis mil caracteres na URL, e navegador e servidor cortam antes disso. Com filtro, o tamanho não depende da quantidade de resultados.
- Quando a URL traz nomes e filtros ao mesmo tempo, os dois conjuntos são unidos, sem repetir monstro.
- Quando um nome na URL não existe no banco, ele é ignorado e os demais são exibidos, com aviso de quantos não foram encontrados. Link velho não deve derrubar a página.

### O bloco de estatísticas

- Quando o modo é **Resumida**, cada ficha traz nome, tipo e tamanho, alinhamento, classe de armadura, pontos de vida, desafio e os seis atributos com o modificador entre parênteses.
- Quando o modo é **Completa**, a ficha ganha deslocamento, testes de resistência, perícias, sentidos, idiomas, os selos de imunidade e ambiente, e a lista de ações com ataques e efeitos.
- Quando os testes de resistência são exibidos, aparecem **apenas os proficientes**, deduzidos pelo núcleo. O bloco impresso do livro faz assim, e mostrar os seis contradiria a fonte.
- Quando o deslocamento é exibido, modos com valor **zero ou nulo** são omitidos. A Spec 3 nunca fixou qual dos dois a ingestão grava para "não possui" — ela só definiu NULL para sentidos —, então a regra cobre os dois. A omissão vem pronta do núcleo.
- Quando as ações são exibidas, são **separadas por categoria** — ações, ações lendárias, reações e habilidades especiais —, como o bloco impresso do livro faz. O dado existe desde a Spec 4 e não usá-lo contradiria a referência visual declarada.
- Quando um ataque é exibido, mostra o bônus, o alcance, o dado de dano e a **média já calculada**.
- Quando uma ação tem efeito, mostra os selos de CD de resistência, condição e área.
- Quando o efeito tem CD mas **não tem condição** — o caso do Fire Breath, e de outros 81 no SRD —, o selo de condição é omitido. A Spec 5 grava condição nula de propósito nesses casos.
- Quando uma ação impõe **duas ou mais condições**, a Spec 5 grava uma linha por condição, todas repetindo a mesma CD e a mesma área. A ficha exibe **um** selo de CD e **um** de área, com um selo por condição — repetir a CD em cada linha faria parecer que são saves diferentes.
- Quando o modo Completa é pedido com mais de 30 monstros na tela, a página avisa que o volume é grande antes de renderizar tudo. Com centenas de fichas inteiras o navegador engasga.

### Selos clicáveis

- A ficha completa exibe selos de **cinco** categorias, e cada uma leva a um filtro próprio da aba Relatórios: imunidade a dano (`imune_a`), resistência a dano (`resiste_a`), **vulnerabilidade a dano** (`vulneravel_a`), **imunidade a condição** (`imune_a_condicao`) e ambiente (`ambiente`). Os dois do meio foram acrescentados ao contrato em 2026-07-25 — sem eles, parte dos selos não teria destino, e "alguns selos clicam e outros não" é pior que nenhum clicar.
- Os selos de **efeito** (CD, condição imposta, área) descrevem o que o monstro faz, não o que ele é. O selo de condição imposta leva ao filtro `impoe`; CD e área não são clicáveis, porque não existe filtro por CD nem por área — e nem faria sentido.
- É o que transforma a ficha em navegação, e é o caminho inverso do botão que traz o resultado do relatório para cá.

### Link JSON

- Quando uma ficha é exibida, abaixo dela há um link discreto **JSON** apontando para `/api/v1/monstros/{nome}` daquele monstro.
- É o que impede a API de ficar decorativa: junto com a busca por `fetch`, dá à API dois consumidores dentro do próprio projeto.
- O jogador comum nunca clica; quem clica é quem entende o que é, e é esse o público que o link serve.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-9b.
- [ ] Teste confirma que `GET /pesquisar?fixados=Adult Red Dragon,Vampire` responde 200 e renderiza duas fichas.
- [ ] Teste confirma que `GET /pesquisar?tipo=dragon` renderiza os 43 dragões — o caminho vindo do relatório não depende de lista de nomes.
- [ ] Teste confirma que nomes e filtros na mesma URL se unem sem repetir monstro.
- [ ] Teste confirma que nome inexistente em `fixados` é ignorado, os demais aparecem e a página avisa quantos faltaram.
- [ ] Teste confirma que `?modo=completa` renderiza os blocos que a resumida omite, e que `?modo=resumida` não os traz.
- [ ] Teste confirma que a ficha do Adult Red Dragon exibe exatamente quatro testes de resistência — Des, Con, Sab e Car —, e não seis.
- [ ] Teste confirma que a ficha omite o modo de deslocamento tanto quando a coluna vale zero quanto quando vale nulo.
- [ ] Teste confirma que o ataque Bite exibe a média 19 junto de `2d10+8`.
- [ ] Teste confirma que a ação Fire Breath exibe os selos de CD 21 e cone de 60 pés, e **não** exibe selo de condição, já que ela é nula nesse caso.
- [ ] Teste confirma que ação com duas condições exibe um selo de CD, um de área e dois de condição — e não a CD repetida duas vezes.
- [ ] Teste confirma que a ficha separa as ações por categoria, com seção própria para ações lendárias.
- [ ] Teste confirma que os selos de vulnerabilidade e de imunidade a condição levam a `/relatorios` com `vulneravel_a` e `imune_a_condicao`.
- [ ] Teste confirma que `?combinar=qualquer` vindo do relatório é respeitado, e não silenciosamente trocado por `todos`.
- [ ] Teste confirma que cada ficha traz link para `/api/v1/monstros/{nome}` com o nome daquele monstro.
- [ ] Teste confirma que o selo de imunidade a fogo aponta para `/relatorios` com `imune_a=fire`.
- [ ] Teste confirma que `?modo=completa` com mais de 30 monstros exibe o aviso de volume.
- [ ] Teste confirma que a busca funciona sem JavaScript: envio do formulário responde 200 com o monstro fixado.
- [ ] Busca por `SELECT`, `execute` e `sqlite3` em `web/` não encontra ocorrência.
- [ ] Com o servidor no ar, digitar no campo de busca dispara chamada a `/api/v1/monstros?nome=` e exibe sugestões.

## Módulos afetados

- `web/rotas.py` — ganha a rota `/pesquisar`. Resolve os monstros a partir de nomes, de filtros ou dos dois, e monta a ficha completa chamando o núcleo, inclusive as derivações de `calculos.py`.
- `web/templates/pesquisa.html` — NOVO. Campo de busca, área das fichas, estado vazio.
- `web/templates/_ficha.html` — NOVO. O bloco de estatísticas, com resumida e completa no mesmo arquivo.
- `web/templates/todos.html` — ampliado: passa a abrir a ficha da linha clicada no modo Completa, reutilizando o `_ficha.html`. **Esta spec tem permissão explícita para editá-lo**; a 9a o criou sem esse comportamento justamente porque o bloco de estatísticas nasce aqui.
- `tests/web/conftest.py` — a fixture da 9a é ampliada, não substituída, com os casos que a ficha exige: ação com duas condições, ação com CD e sem condição, monstro sem ataque.
- `web/static/busca.js` — NOVO. Só a busca incremental por `fetch` e o preenchimento das sugestões. Poucas linhas, sem framework nem compilação.
- `web/static/estilo.css` — ajustado com o que a ficha precisa.
- `tests/web/test_rotas.py` — ampliado com os casos desta aba.

## Não mexer

- `api/` e `openapi.yaml` — a API é consumida como está. Se a busca precisar de algo que ela não dá, isso muda o contrato de propósito, em commit próprio, e não por conveniência da tela.
- `bestiario/` inteiro — o núcleo é consumido, não alterado. As derivações de teste de resistência, modificador e média de dano já existem em `calculos.py` e não se refazem aqui.
- `web/templates/base.html` — a moldura é da 9a.
- `web/templates/relatorios.html` — é da 9b.
- A invariante do CSS da 9a: **nenhuma origem externa**. As fontes ficam embutidas em base64; ajustar o `estilo.css` aqui não é licença para trazer recurso de fora, que a política de segurança da página bloquearia e faria a semelhança com o livro cair em silêncio.
- `main.py` — o menu do terminal não muda.
- A identidade visual do bloco de estatísticas — tarja no topo e no pé, cunha entre seções, rótulos em vermelho: tudo vem do esboço aprovado.

## Decisões tomadas

- Sem limite de fichas na tela → decisão do usuário em 2026-07-25, corrigindo o desenho anterior de três. A aba passa a comportar desde um monstro até os 325.
- Estado por nome quando escolhido a um, por filtro quando vindo do relatório → consequência direta de tirar o limite. Guardar 325 nomes na URL passaria de seis mil caracteres e a página não carregaria; carregando o filtro, o tamanho não depende da quantidade.
- Aviso de volume acima de 30 fichas no modo completa → sem limite de quantidade, o modo completa pode montar centenas de blocos e travar o navegador. Avisar é preferível a impor um teto que contradiria a decisão acima.
- Link JSON embaixo de cada ficha → decisão do usuário sobre onde colocá-lo. É, junto com a busca por `fetch`, o que dá à API consumidores reais dentro do projeto — API que nada consome é pior que API nenhuma, e num projeto de portfólio isso conta contra.
- Busca degrada para formulário comum sem JavaScript → a busca incremental é conveniência; a aba não pode depender dela para funcionar.
- Testes de resistência só os proficientes → é o que o bloco impresso do livro mostra. O schema guarda os seis já derivados, e a dedução por comparação com o modificador está em `calculos.py`, feita na 7a.
- Nome inexistente é ignorado com aviso, em vez de erro → a URL é compartilhável e editável à mão; link velho não deve derrubar a página.

## Impacto no CLAUDE.md

- **Sessão 6 do histórico** → corrigir "Pesquisar — busca que acumula **até 3 monstros**". O limite foi eliminado por decisão do usuário em 2026-07-25; a aba comporta de um a 325.
- **O que está incompleto** → remover o item "Sem front-end e sem API HTTP": fecha aqui.
- **O que já funciona** → acrescentar a aba Pesquisar com fichas acumuladas, navegação em dois sentidos entre ficha e relatório, e a API consumida pela própria busca do site.
- **Bloco em aberto — Specs 7 a 10** → marcar 9c como concluída e o bloco do front como fechado; sobra a Spec 10 (tradução).
- **Sobre o desenvolvedor / Contexto para decisões futuras** → o projeto deixa de ser "interface 100% terminal".
