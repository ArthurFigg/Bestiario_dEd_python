# Menu migrado para o núcleo

**Ordem:** 7c de 9
**Depende de:** Spec 7a (núcleo de consulta)
**Score:** 4
**Revisão:** pendente

## O que faz
Faz os filtros do menu do terminal consultarem o núcleo em vez das duas funções de consulta próprias de `banco.py`, que são removidas.

## Comportamento

- Quando o usuário filtra por tipo (opção 2), o menu chama o núcleo com o filtro `tipo` no modo `lista_monstros`, em vez de `consultar_por_tipo`.
- Quando o usuário filtra por desafio (opção 3), o menu chama o núcleo com `desafio_min` e `desafio_max` iguais ao valor digitado, em vez de `consultar_por_cr`.
- **O menu converte o texto digitado em número antes de chamar o núcleo.** A Spec 6 fazia essa conversão dentro de `consultar_por_cr`, que deixa de existir; sem alguém assumindo, o núcleo receberia texto. Conversão falha é tratada como sem resultado local e segue para o fallback.
- Os nomes passam a seguir o glossário: a função vira `consultar_desafio` e o rótulo impresso vira `Desafio:` no lugar de `CR:`. O `_dominio.md` marca "CR" como termo a evitar, e esta é a última spec que toca `main.py`.
- Quando a consulta local devolve resultado, o menu exibe com o rótulo `[local]`, como hoje.
- Quando a consulta local não devolve nada, o menu **continua caindo para a API v2** e exibe com o rótulo `[API]`. O comportamento de consulta local primeiro, decidido na Spec 6, não muda — só troca quem responde a parte local.
- Quando o usuário digita um tipo que não existe no vocabulário (ex: `dragão`), o núcleo levanta `ValorDeFiltroInvalido`. O menu **captura** a exceção e vai para o fallback da API, em vez de vazar erro na tela. Um tipo desconhecido localmente pode existir na API, e o usuário do terminal não deve ver rastro de exceção.
- Quando o usuário digita um desafio não numérico, o menu trata como sem resultado local e segue para o fallback, como já fazia.
- Quando nem o local nem a API devolvem nada, exibe "Nenhum monstro encontrado.", como hoje.
- As opções 1 (buscar e registrar por nome), 4 (sincronizar) e 5 (ver relatórios) **não mudam**.
- `consultar_por_tipo` e `consultar_por_cr` são removidas de `banco.py`, junto de suas re-exportações. Depois desta spec, `banco.py` volta a ter uma responsabilidade só: criar o schema e gravar dado.

## Critérios verificáveis

- [ ] `uv run pytest -v` passa, incluindo os testes das Specs 1-6, 7a e 7b.
- [ ] Busca por `consultar_por_tipo` e `consultar_por_cr` em `bestiario/`, `main.py` e `tests/` não encontra nenhuma ocorrência. O escopo é o código: os nomes continuam citados nas specs, que são registro histórico.
- [ ] Teste confirma que o rótulo impresso diz `Desafio:` e não `CR:`.
- [ ] Teste confirma que filtrar por tipo com o monstro já gravado devolve a linha local **sem** chamar a API — o dublê do cliente v2 não é invocado.
- [ ] Teste confirma que, sem correspondência local, o filtro por tipo chama o fallback da API e devolve o resultado remoto.
- [ ] Teste confirma que a saída rotula a origem: `[local]` para linha do banco, `[API]` para fallback.
- [ ] Teste confirma que tipo fora do vocabulário (`dragão`) não propaga exceção: cai no fallback da API.
- [ ] Teste confirma que desafio não numérico não quebra e segue para o fallback.
- [ ] Teste confirma que, sem resultado em lugar nenhum, a saída é "Nenhum monstro encontrado.".
- [ ] `python main.py` roda o menu de ponta a ponta com as opções 2 e 3 contra o banco real.

## Módulos afetados

- `bestiario/banco.py` — `consultar_por_tipo` e `consultar_por_cr` REMOVIDAS. O schema, a ingestão e a idempotência ficam intactos.
- `bestiario/__init__.py` — remove as re-exportações das duas funções removidas.
- `main.py` — `consultar_tipo` e `consultar_cr` (renomeada para `consultar_desafio`) passam a chamar `executar_consulta` do núcleo, a converter o desafio digitado em número e a capturar `ValorDeFiltroInvalido` antes do fallback. `_projetar_local` passa a receber dicionário do núcleo, cujas chaves seguem o contrato — lê `desafio`, **não** `nivel_desafio`. `_formatar_linha_filtro` troca o rótulo `CR:` por `Desafio:`. `_projetar_api` e `_exibir_resultados` ficam como estão.
- `.claude/specs/6_relatorios_e_consulta_local.md` — ganha nota de supersessão indicando que `consultar_por_tipo`/`consultar_por_cr` foram absorvidas pelo núcleo nesta spec. Sem a nota, uma spec concluída fica apontando para funções que não existem mais.
- `tests/test_banco.py` — ajustado: os testes das duas funções removidas saem daqui. Nada mais muda.
- `tests/test_main.py` — ajustado: a orquestração dos filtros passa a ser verificada contra o núcleo, mantendo os casos de local-primeiro, fallback e rótulo de origem, e ganhando o caso de valor fora do vocabulário.

## Não mexer

- `bestiario/consultas.py`, `calculos.py` e `excecoes.py` — criados na 7a e usados como estão.
- `bestiario/relatorios.py` — já migrado na 7b; esta spec não encosta.
- `bestiario/cliente_api.py` — o fallback continua chamando o mesmo cliente, sem alteração.
- `bestiario/extracao.py` e o schema do banco.
- A ordem "local primeiro, API como fallback" e os rótulos `[local]`/`[API]` — decisão da Spec 6, preservada.
- As opções 1, 4 e 5 do menu.

## Decisões tomadas

- Absorver `consultar_por_tipo` e `consultar_por_cr` em vez de deixá-las conviver com o núcleo → decisão do usuário em 2026-07-25. Duas funções fazendo consulta com um núcleo de consulta ao lado é a mesma duplicação que a 7b resolve nos relatórios, só que em outro arquivo. Ganho adicional: `banco.py` volta a ter responsabilidade única — criar schema e gravar —, que é o que o nome promete.
- Tipo fora do vocabulário cai no fallback em vez de exibir erro → o vocabulário é o do **banco local**, não o da API. Um tipo ausente localmente pode existir remotamente, então tratar como "não achei aqui" e perguntar lá é a leitura correta. Vazar `ValorDeFiltroInvalido` na tela do terminal seria expor detalhe interno de uma camada que o usuário não sabe que existe.
- Manter a Spec 6 intacta no comportamento → esta spec troca a implementação da consulta local, não a política de local-primeiro. Os testes da Spec 6 continuam valendo como rede de segurança.

## Impacto no CLAUDE.md

- **Estrutura de arquivos** → confirmar que a descrição de `banco.py` continua sendo só "criação do SQLite e inserção". A linha já está assim: a Spec 6 acrescentou consulta ao módulo sem nunca atualizar o CLAUDE.md, e esta spec devolve o arquivo ao que a documentação sempre disse.
- **O que já funciona** → o item de consulta local-primeiro (Spec 6) passa a citar o núcleo como quem responde a parte local; a política em si não muda.
- **Bloco em aberto — Specs 7 a 10** → marcar 7c como concluída e a Spec 7 inteira como fechada.
