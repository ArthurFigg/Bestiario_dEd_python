# Aba "Relatórios"

**Ordem:** 9b de 9
**Depende de:** Specs 7a (núcleo) e 9a (moldura)
**Score:** 4
**Revisão:** pendente

## O que faz
Entrega a aba de análises: os filtros nomeados, a escolha única entre ver a lista ou comparar, a faixa de resumo sempre visível e a tabela de resultado.

## Comportamento

### Princípio que rege a tela

- **Quando faltar um dado, a resposta não é mais um botão — é o dado já estar lá.** A primeira versão desta tela foi reprovada por exigir raciocínio antes de servir. Toda decisão abaixo segue disso.

### Filtros

- Quando a aba abre, os filtros já estão na tela, cada um com nome em português claro: Tipo, Tamanho, **Alinhamento**, Ambiente, Resiste a, Imune a, **Vulnerável a**, **Imune à condição**, Impõe, e Desafio como faixa de/até. A tela expõe **todos** os filtros que o núcleo aceita — filtro que exista no núcleo e não tenha campo na tela sumiria da URL no próximo envio do formulário.
- Não há "adicionar filtro" nem linha genérica de campo e operador.
- Quando um filtro fica vazio, ele não restringe nada.
- Quando cada filtro é montado, suas opções vêm do vocabulário lido do banco, com a contagem ao lado (`dragon (43)`). Opção escrita à mão sairia de sincronia no próximo re-sync.
- Quando o usuário escolhe como combinar, a frase é "mostrar quem atende **todos os filtros** / **qualquer um deles**". Vale para todos de uma vez; não há como misturar os dois.

### A escolha única

- Quando a aba abre, há **uma** escolha embaixo dos filtros: `( ) Ver os monstros` ou `(•) Comparar por [tipo]`. Nada mais.
- Não existe seletor de métrica. As colunas vêm prontas.
- Quando o usuário escolhe "Comparar por", a dimensão sai de um menu com **as sete** que o núcleo aceita: tipo, tamanho, alinhamento, **desafio**, ambiente, tipo de dano, condição imposta.
- A escolha entre as duas saídas viaja na URL como **`saida`**, com valores `monstros` e `comparacao`. O nome não pode ser `modo`: `modo` já é o botão Resumida/Completa da moldura, que atravessa todas as abas. Duas semânticas na mesma chave se anulariam.
- Quando a aba abre pela primeira vez, já vem com resposta na tela — comparação por tipo, sem filtro. Ninguém encara formulário vazio.

### A faixa de resumo

- Quando qualquer resultado é exibido, uma faixa acima dele mostra o conjunto filtrado condensado: quantos monstros, média de pontos de vida, de classe de armadura, de desafio e de dano.
- Quando o usuário muda um filtro e gera de novo, a faixa recalcula.
- A faixa **não é opcional** e não tem botão que a ligue. É o que responde "qual a média de dano desses monstros" sem o usuário precisar pedir.

### A tabela

- Quando a saída é "Ver os monstros", cada linha traz nome, tipo, tamanho, desafio, pontos de vida, classe de armadura e **dano médio** — esta última sempre presente, sem seletor.
- Quando a saída é "Comparar por", cada linha traz o valor da dimensão, quantos monstros, e as médias de pontos de vida, classe de armadura, desafio e dano.
- Quando a coluna é uma média, o cabeçalho diz **"Média de…"** por extenso. Sem isso, `202` na linha do dragão lê como o total de pontos de vida de um dragão, e não como a média dos 43.
- Quando a dimensão é multivalorada (ambiente, tipo de dano, condição imposta), a tela avisa que a soma da coluna de contagem pode passar do total, porque um monstro conta em mais de um grupo. Sem o aviso, o usuário conclui que a conta está errada.
- Quando nenhum monstro atende aos filtros, a tabela aparece vazia com a mensagem de que nada foi encontrado, e a faixa mostra zero. Não é erro.

### Estado e navegação

- Quando o usuário gera um resultado, todos os filtros, a saída escolhida e o `combinar` vão para a URL. Recarregar reproduz a tela, e o link pode ser enviado a outra pessoa.
- Quando os links da moldura são montados, eles **preservam o `modo`** da exibição, para o botão Resumida/Completa não se perder ao gerar um relatório.
- Quando um valor de filtro chega inválido pela URL, a tela exibe o aviso de valor não reconhecido e mantém os demais filtros, em vez de mostrar erro de servidor.
- Quando uma **chave** de filtro ou uma dimensão desconhecida chega pela URL (ex: `?por=cor`), a tela ignora o parâmetro e avisa, em vez de devolver erro de servidor. Só valor inválido não basta: chave inválida é igualmente alcançável por link editado à mão.
- Quando o usuário clica num preset, o formulário é **preenchido** com aqueles filtros e aquela saída — não abre uma tela pronta e fechada. Ele vê como a análise foi montada e pode mexer.
- Quando o resultado é uma lista de monstros, um botão manda esse mesmo recorte para a aba Pesquisar, **levando os filtros na URL**, não a lista de nomes. O `combinar` vai junto: sem ele, um recorte montado com "qualquer um dos filtros" chegaria na outra aba avaliado como "todos" e exibiria um conjunto diferente, sem erro nenhum.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-9a.
- [ ] Teste confirma que `GET /relatorios` sem parâmetro nenhum responde 200 e já traz a comparação por tipo preenchida.
- [ ] Teste confirma que a faixa de resumo aparece no HTML em toda resposta de resultado.
- [ ] Teste confirma que a faixa recalcula ao filtrar: com `imune_a=fire`, mostra a contagem de imunes a fogo **da fixture**, e sem filtro mostra o total dela. Os testes usam a fixture de `tests/web/conftest.py` criada na 9a — nunca o `bestiario_combate.db`, que está fora do git e não existe no CI.
- [ ] Teste confirma que `?combinar=qualquer` chega íntegro no link que leva para a aba Pesquisar.
- [ ] Teste confirma que `?modo=completa` sobrevive a gerar um relatório.
- [ ] Teste confirma que `?por=cor` responde 200 com aviso, e não 500.
- [ ] Teste confirma que a tela oferece campo para **todos** os filtros do núcleo, incluindo alinhamento, vulnerável a e imune à condição.
- [ ] Teste confirma que os cabeçalhos de coluna de agregado contêm o texto "Média de".
- [ ] Teste confirma que a lista de monstros traz coluna de dano médio.
- [ ] Teste confirma que `?por=ambiente` exibe o aviso de contagem que pode ultrapassar o total.
- [ ] Teste confirma que os selects de filtro são preenchidos a partir do vocabulário do banco, e não de lista fixa no template — a quantidade de opções acompanha a fixture.
- [ ] Teste confirma que cada opção traz a contagem ao lado, vinda do vocabulário do núcleo.
- [ ] Teste confirma que filtro sem resultado devolve 200 com mensagem de nada encontrado e faixa zerada, sem erro.
- [ ] Teste confirma que `?resiste_a=fogo` responde 200 com aviso de valor não reconhecido, e não 500.
- [ ] Teste confirma que clicar num preset devolve o formulário com aqueles parâmetros marcados.
- [ ] Teste confirma que o botão de mandar para Pesquisar gera link com os **filtros**, não com nomes de monstro.
- [ ] Busca por `SELECT`, `execute` e `sqlite3` em `web/` não encontra ocorrência.

## Módulos afetados

- `web/rotas.py` — ganha a rota `/relatorios`. Lê os parâmetros, chama o núcleo nos modos `agregado`, `lista_monstros` e `resumo`, e passa tudo ao template. Captura `ValorDeFiltroInvalido` e transforma em aviso na tela.
- `web/templates/relatorios.html` — NOVO. Presets, cartão único de busca, a escolha única, faixa de resumo e tabela.
- `web/static/estilo.css` — ajustado com o que a aba precisa e que ainda não veio do esboço na 9a.
- `tests/web/test_rotas.py` — ampliado com os casos desta aba.

## Não mexer

- `bestiario/consultas.py` — o núcleo é consumido como está. Se a tela precisar de algo que ele não oferece, é sinal de que a 7a ficou incompleta.
- `api/` e `openapi.yaml` — esta aba renderiza HTML no servidor e não consome a API. Quem consome é a 9c.
- `web/templates/base.html` — a moldura é da 9a; aqui só se preenche o bloco de conteúdo.
- `web/templates/todos.html` — é da 9a.
- `main.py` e `bestiario/relatorios.py` — os relatórios do terminal continuam como estão.
- A identidade visual — cores, fontes, cunha, volutas e listra vêm do esboço.

## Decisões tomadas

- Sem seletor de métrica; colunas fixas → veredito do usuário testando o esboço: *"no geral está confuso demais — se tem que pensar para entender, já mostra que está ruim."* Os filtros são concretos, mas escolher dimensão de agrupamento e marcar nove métricas é montar uma consulta com o mouse. Ficou uma escolha só.
- Faixa de resumo sempre visível, sem botão → responde "qual a média de dano desses monstros" sem custar nenhuma decisão ao usuário. É a aplicação direta do princípio de que dado faltando não se resolve com mais um botão.
- Cabeçalho com "Média de" por extenso → sem isso o número lido isolado engana, e engana em silêncio.
- Aviso na dimensão multivalorada → o mesmo cuidado já está registrado na descrição de `/comparacoes` no `openapi.yaml`; a tela repete porque o usuário do site não lê contrato.
- Preset preenche o formulário em vez de abrir tela pronta → resolve a tela em branco e ensina a ferramenta usando ela mesma.
- Valor de filtro inválido vindo da URL vira aviso na tela, não erro → link velho ou editado à mão não deve derrubar a página.
- Mandar filtros, e não nomes, para a aba Pesquisar → a aba não tem limite de monstros, e uma lista de nomes longa estouraria o tamanho da URL. Com filtro, o tamanho não depende da quantidade de resultados.
- A "lista de ataques" não aparece nesta tela → seria uma terceira escolha, e a poda existiu justamente para deixar uma. O preset "Top ataques" continua produzindo essa lista.

## Impacto no CLAUDE.md

- **O que já funciona** → acrescentar a aba de relatórios com construtor de análises, faixa de resumo e presets.
- **Bloco em aberto — Specs 7 a 10** → marcar 9b como concluída.
