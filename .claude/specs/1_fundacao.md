# Fundação (setup + reestrutura)

**Ordem:** 1 de 6
**Depende de:** nenhuma
**Revisão:** aprovada

## O que faz
Introduz `uv` + `pyproject.toml` com dependências travadas por teto de versão e `pytest`, e reestrutura os três arquivos flat atuais em um pacote `bestiario/` organizado por responsabilidade, preservando 100% o comportamento atual (ainda usando a API v1).

## Comportamento
- Quando o usuário roda `python main.py`, o mesmo menu interativo de hoje aparece e funciona idêntico (buscar por nome, filtrar por tipo, filtrar por CR, sincronizar, sair).
- Quando o código é importado como pacote (`from bestiario.cliente_api import buscar_monstro`), as funções movidas continuam com a mesma assinatura e o mesmo comportamento de antes.
- Quando `main.py` é importado (não executado), o menu não roda — o guard `if __name__ == "__main__"` é preservado.
- Quando o usuário roda os relatórios, o resultado é idêntico ao `analise_bestiario.py` atual.
- A sincronização e a inserção continuam apontando para a API v1 e para o schema atual de 2 tabelas — nada de v2 nem schema novo nesta spec.
- `modelos.py` nasce como placeholder (sem entidades ainda) — só ganha corpo nas specs seguintes.

## Critérios verificáveis
- [ ] `uv run pytest -v` roda e a suite passa.
- [ ] `uv sync` instala as dependências a partir do `pyproject.toml` sem erro.
- [ ] Existe teste que importa cada módulo do pacote (`cliente_api`, `banco`, `relatorios`, `extracao`) e confirma que os símbolos públicos existem.
- [ ] Existe teste que exercita `criar_base_de_dados` + `registrar_monstro` (com um dict de monstro fake) e confirma que a linha foi gravada — provando que o comportamento de persistência foi preservado após a mudança de arquivo.
- [ ] Existe teste que exercita a extração de `bonus_ataque`/`dados_dano` (a regex movida) com uma descrição de exemplo e confirma o valor extraído.
- [ ] `python main.py` abre o menu (execução manual — smoke).

## Módulos afetados
- `main.py` — NOVO na raiz; recebe o conteúdo do `bestiario.py` atual (menu + guard `__main__`). Importa as funções do pacote em vez de definir tudo localmente. Roda com `python main.py`.
- `bestiario/__init__.py` — NOVO; só re-exportações explícitas da API pública do pacote (sem lógica).
- `bestiario/cliente_api.py` — NOVO; recebe `buscar_monstro`, `filtrar_monstros`, `sincronizar_base_completa` (movidas de `bestiario.py`), ainda com URLs v1.
- `bestiario/banco.py` — NOVO; recebe `criar_base_de_dados` e `registrar_monstro` (movidas de `banco_de_dados.py`), schema atual de 2 tabelas inalterado.
- `bestiario/extracao.py` — NOVO; recebe a lógica de regex de `bonus_ataque`/`dados_dano` hoje embutida em `registrar_monstro`, isolada em função(ões) próprias e chamada por `banco.py`.
- `bestiario/relatorios.py` — NOVO; recebe `gerar_relatorio_perfeito` (movida de `analise_bestiario.py`).
- `bestiario/modelos.py` — NOVO; placeholder vazio/comentado, sem entidades ainda.
- `pyproject.toml` — NOVO; projeto gerenciado por `uv`, deps `requests`, `pandas`, `tabulate` com teto de versão (`>=x,<major+1`), `pytest` como dep de desenvolvimento.
- `tests/` — NOVO; espelha a estrutura do pacote (`test_cliente_api.py`, `test_banco.py`, `test_extracao.py`, `test_relatorios.py`).
- `bestiario.py`, `banco_de_dados.py`, `analise_bestiario.py` — REMOVIDOS após a migração do conteúdo para o pacote.

## Não mexer
- Lógica de negócio das chamadas à API — a migração v1→v2 é a Spec 2. Aqui as URLs continuam `/v1/`.
- Schema do banco (2 tabelas) — o schema de 4 tabelas é a Spec 3.
- `bestiario_combate.db` — não recriar nem alterar nesta spec.
- Comportamento observável do menu e dos relatórios — só muda a organização dos arquivos, não o que o usuário vê.
- Conteúdo de `modelos.py` e `extracao.py` além do necessário para preservar o comportamento atual — enriquecimento vem nas specs 2-5.

## Decisões tomadas
- Layout dos módulos → pacote `bestiario/` com `__init__.py` de re-exportações; entrada na raiz (padrão do CLAUDE.md global, projeto de portfólio).
- Nome do ponto de entrada → `main.py` (roda com `python main.py`). Motivo: pacote e arquivo não podem ambos se chamar `bestiario` no mesmo diretório — colisão de nome de import no Python. Descartadas `cli.py` e `bestiario/__main__.py`.
- Profundidade desta spec → mover o código atual para os módulos certos, preservando comportamento; `modelos.py` nasce placeholder e `extracao.py` só com a regex atual. Enriquecimento fica para specs posteriores.
- Fonte de dados nesta spec → permanece API v1 e schema de 2 tabelas; migração v2 e schema novo são specs seguintes (evita acoplar reestrutura com mudança de comportamento).
- Deps → `uv` + `pyproject.toml` com teto de versão em todas as deps de produção (regra do CLAUDE.md global). `pytest` como dependência de desenvolvimento.

## Impacto no CLAUDE.md
Seção adicionada retroativamente (a spec é anterior à regra "spec declara e /spec-close sincroniza o CLAUDE.md").
- Estrutura de arquivos → substituir o bloco flat (`bestiario.py`, `banco_de_dados.py`, `analise_bestiario.py`) pelo pacote `bestiario/` (`__init__.py`, `cliente_api.py`, `banco.py`, `extracao.py`, `relatorios.py`, `modelos.py`) + `main.py` na raiz como ponto de entrada; `tests/` espelhando o pacote.
- Como rodar → trocar `pip install requests pandas tabulate` por `uv sync`; `python bestiario.py` por `python main.py`; `python analise_bestiario.py` por `python bestiario/relatorios.py`.
- Tecnologias usadas → "Python 3 (testado com 3.14 — veja __pycache__)" passa a Python 3.13 gerenciado por `uv` (alinhado à seção "Setup do ambiente").

---
**Status:** concluida em 2026-07-18
