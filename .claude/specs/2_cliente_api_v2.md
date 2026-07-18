# Cliente da API v2

**Ordem:** 2 de 6
**Depende de:** Spec 1 (fundação)
**Revisão:** aprovada

## O que faz
Reescreve `bestiario/cliente_api.py` para consumir a API Open5e v2 (`https://api.open5e.com/v2/creatures/`) em vez da v1, fixado no documento SRD 2014, retornando os dados estruturados da v2 sem persistir nem transformar em entidades.

## Comportamento
- Quando o usuário busca uma criatura por nome, o cliente retorna o dict estruturado da v2 correspondente **dentro do SRD 2014**; se nenhuma corresponder, retorna `None`.
- Quando o usuário busca por nome que casa com criaturas de outros documentos (ex: `bfrd_`, `a5e-mm_`), essas são ignoradas — só SRD 2014 é considerado (o mesmo nome não pode voltar duplicado entre fontes).
- Quando o usuário filtra por tipo, o cliente retorna a lista de criaturas do SRD 2014 daquele tipo (`document__key=srd-2014` + `type`).
- Quando o usuário filtra por CR, o cliente retorna a lista de criaturas do SRD 2014 com aquele challenge rating (`document__key=srd-2014` + `challenge_rating`).
- Quando o usuário sincroniza, o cliente percorre **todas** as páginas do SRD 2014 seguindo o campo `next`, até `next` ser `null`, e devolve/entrega cada criatura estruturada.
- Quando a requisição HTTP falha por erro de conexão, o cliente trata com `try/except` (padrão herdado da v1): busca individual retorna `None`; filtro/sincronização retornam o que já obtiveram (ou vazio) e exibem mensagem de erro, sem propagar exceção.
- Quando a resposta HTTP tem status diferente de 200, o cliente não quebra: busca individual retorna `None`, filtro/sync interrompem a paginação.
- O cliente retorna o **dict cru estruturado da v2** (com `type`, `size`, `speed_all`, `saving_throws_all`, `resistances_and_immunities`, `actions` com `attacks`, `traits`, etc.). Não converte em entidades de `modelos.py` nem extrai ataques/efeitos — isso é responsabilidade das Specs 3-5.

## Critérios verificáveis
- [ ] `uv run pytest -v` passa, incluindo os testes desta spec e os da Spec 1.
- [ ] Teste com `requests` mockado confirma que a busca por nome retorna o dict da criatura quando a API responde 200, e `None` quando responde 404.
- [ ] Teste com `requests` mockado confirma que a paginação percorre múltiplas páginas: dado um mock que devolve `next` na primeira página e `null` na segunda, a sincronização acumula criaturas das duas páginas.
- [ ] Teste confirma que as chamadas de filtro/sync incluem `document__key=srd-2014` na URL/params (escopo SRD garantido).
- [ ] Teste com `requests.get` lançando `RequestException` confirma que nenhuma exceção vaza e o retorno é `None`/lista vazia (tratamento de erro preservado).
- [ ] Nenhum teste faz chamada HTTP real (mock na fronteira `requests`).

## Módulos afetados
- `bestiario/cliente_api.py` — reescrito: URLs passam de `/v1/monsters/` para `/v2/creatures/`; adiciona constante de módulo com o documento fixo (`srd-2014`) aplicada a todas as chamadas; `buscar_monstro`, `filtrar_monstros`, `sincronizar_base_completa` reescritas para a v2, retornando os dicts estruturados; paginação via campo `next` mantida; `try/except` de conexão preservado.
- `tests/test_cliente_api.py` — reescrito/expandido: mocks de `requests` para 200/404/erro de conexão e para paginação de múltiplas páginas; asserção do escopo `document__key=srd-2014`.

## Não mexer
- `bestiario/banco.py` — persistência e schema são a Spec 3; o cliente não grava nada.
- `bestiario/extracao.py` — extração de ataques/efeitos é Specs 4-5.
- `bestiario/modelos.py` — conversão em entidades não acontece aqui; o cliente devolve dict cru.
- `bestiario/relatorios.py` — não é tocado.
- `main.py` — o menu continua chamando as mesmas funções do cliente; assinaturas públicas (`buscar_monstro`, `filtrar_monstros`, `sincronizar_base_completa`) preservadas para não quebrar o menu.
- `bestiario_combate.db` — não recriar nem alterar.
- Escolha de fontes: apenas SRD 2014. Não incluir srd-2024 nem documentos de terceiros.

## Decisões tomadas
- Fonte de dados → migrar da v1 para a v2 (`/v2/creatures/`). Motivo: v2 entrega ataques, sentidos, saves e resistências já estruturados (decisão de projeto tomada antes das specs).
- Escopo de documentos → **apenas SRD 2014** (`document__key=srd-2014`, ~325 monstros). Motivo: a v2 mistura ~10 fontes (SRD, A5E, Tome of Beasts, etc.) e repete o mesmo monstro entre elas; restringir ao SRD oficial elimina duplicatas na origem e permite manter `nome` como PRIMARY KEY. Descartadas "todas as fontes" (forçaria trocar a PK para `key`) e "SRD + terceiros".
- Edição do SRD → **2014** (não 2024). Motivo: é o D&D 5e clássico que a maioria das mesas e conteúdos usa, e bate com os dados que o banco já tinha. As duas edições têm o mesmo monstro, então escolher uma evita colisão de `nome`.
- Retorno do cliente → dict cru estruturado da v2, sem conversão em entidades. Motivo: separar comunicação (esta spec) de modelagem/persistência (Specs 3+); `modelos.py` só ganha corpo depois.
- Filtro de CR → parâmetro `challenge_rating` da v2 (confirmado: `?challenge_rating=17` retorna 36; `?cr=` é ignorado pela API).
- Casos negativos → herdados da v1: nome não encontrado/status ≠ 200 → `None`; erro de conexão → `None`/lista vazia + mensagem via `try/except`; filtro sem resultado → lista vazia.
- Escopo desta spec → só a camada de comunicação HTTP e o parsing da resposta; persistência (Spec 3) e extração de ações/ataques/efeitos (Specs 4-5) ficam de fora.

## Impacto no CLAUDE.md
Seção adicionada retroativamente (spec anterior à regra "spec declara e /spec-close sincroniza o CLAUDE.md"). Esta spec muda só a camada de código HTTP — a contagem de monstros no banco (2319) só muda na Spec 3 (re-sync); não editar contagem aqui.
- Tecnologias usadas → "API externa: `https://api.open5e.com/v1/monsters/`" passa para v2 `https://api.open5e.com/v2/creatures/` (SRD 2014, `document__key=srd-2014`).
- API Open5e — referência rápida → substituir o bloco v1 (`/v1/monsters/`, `/{slug}/`) pelos endpoints v2 (`/v2/creatures/`, filtro `document__key=srd-2014`, paginação por `next`).
- O que é esse projeto → o escopo deixa de ser "todos os monstros do D&D 5e" e passa a "SRD 2014 (~325 criaturas)"; endpoint base atualizado para a v2.
- Contexto para decisões futuras → "endpoint atual: `https://api.open5e.com/v1/monsters/`" → v2 `/v2/creatures/` (SRD 2014).

---
**Status:** concluida em 2026-07-18
