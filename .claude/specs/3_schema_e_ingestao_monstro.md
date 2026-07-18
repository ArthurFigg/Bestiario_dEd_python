# Novo schema + ingestão dos campos do monstro

**Ordem:** 3 de 6
**Depende de:** Specs 1 (fundação) e 2 (cliente API v2)
**Revisão:** aprovada

## O que faz
Cria o schema relacional normalizado (tabela `monstros` enriquecida + tabelas de lista + tabelas de combate vazias) e persiste os campos de **nível monstro** vindos do dict estruturado da v2 (SRD 2014).

## Comportamento
- Quando `criar_base_de_dados` roda, todas as tabelas do modelo são criadas com `CREATE TABLE IF NOT EXISTS` (idempotente, seguro rodar a cada startup sem apagar dados).
- Quando um dict de criatura da v2 é ingerido, a tabela `monstros` recebe uma linha com `INSERT OR REPLACE` (chave `nome`), preenchendo as colunas atuais **e** as novas: sentidos, saves (de `saving_throws_all`), velocidades (de `speed_all`), alinhamento e idiomas.
- Quando o monstro tem sentido ausente (ex: sem visão no escuro), a coluna de alcance correspondente fica `NULL` — ausência real, não erro.
- Quando o monstro **não é proficiente** em um save, a coluna daquele save recebe o valor **derivado** de `saving_throws_all` (nunca `NULL` por falta de proficiência). Isso elimina o "NULL indevido".
- Quando o monstro tem imunidades/resistências/vulnerabilidades a dano, cada valor vira uma linha em `monstro_interacao_dano` com a coluna `relacao` indicando `imunidade`, `resistencia` ou `vulnerabilidade`.
- Quando o monstro tem imunidades a condição, cada uma vira uma linha em `monstro_imunidade_condicao`.
- Quando o monstro tem ambientes, cada um vira uma linha em `monstro_ambiente`.
- Quando o monstro tem perícias proficientes (`skill_bonuses`), cada uma vira uma linha em `monstro_pericia` com o bônus.
- Quando um monstro já existente é reingerido (re-sync), as linhas das tabelas de lista daquele monstro são apagadas antes de reinserir (`DELETE WHERE monstro_nome = ?`), evitando duplicatas — mesmo padrão já usado para `acoes`.
- Quando um campo de lista vem vazio (ex: `damage_resistances: []`), nenhuma linha é criada para aquela categoria — a ausência é representada pela falta de linhas, não por linha vazia.
- As tabelas `acoes`, `ataques` e `efeitos` são **criadas nesta spec, mas ficam vazias** — sua população é das Specs 4 e 5. Consequência consciente: após esta spec, ações deixam de ser gravadas até a Spec 4.
- Os valores das tabelas de lista são guardados como vêm da v2 (chaves canônicas em inglês: `fire`, `cold`, `prone`) — tradução para o usuário final é responsabilidade de camada de apresentação futura, não do banco.

## Critérios verificáveis
- [ ] `uv run pytest -v` passa, incluindo os testes desta spec e das Specs 1-2.
- [ ] Teste confirma que `criar_base_de_dados` cria todas as tabelas do schema (verificar via `sqlite_master`).
- [ ] Teste ingere um dict v2 de exemplo (ex: Adult Red Dragon) e confirma que `monstros` tem os sentidos corretos (`alcance_visao_cega=60`, `alcance_visao_penumbra=120`, `percepcao_passiva=23`).
- [ ] Teste confirma que um save de atributo **não proficiente** é gravado com o valor derivado (não `NULL`).
- [ ] Teste confirma que `speed_all` vira as colunas de velocidade corretas (`velocidade_voo=80`, `velocidade_escalada=40`).
- [ ] Teste confirma que `damage_immunities: ['fire']` gera uma linha em `monstro_interacao_dano` com `tipo_dano='fire'` e `relacao='imunidade'`.
- [ ] Teste confirma que reingerir o mesmo monstro não duplica linhas nas tabelas de lista.
- [ ] Teste confirma que as tabelas `acoes`, `ataques`, `efeitos` existem e estão vazias após ingerir um monstro (escopo respeitado).

## Módulos afetados
- `bestiario/banco.py` — reescrito. `criar_base_de_dados` passa a criar o schema de ~9 tabelas (schema completo abaixo). A função de ingestão de monstro é reescrita para ler o dict v2 e gravar `monstros` + as tabelas de lista; **não** grava mais em `acoes` (isso volta na Spec 4). A lógica de regex de ataque/dano que estava embutida sai daqui (fica em `extracao.py`, usada só a partir da Spec 4).
- `tests/test_banco.py` — reescrito para o novo schema, com um dict v2 de exemplo como fixture.

### Schema completo
```
monstros (
  nome TEXT PRIMARY KEY,
  tamanho, tipo TEXT,
  classe_armadura, pontos_vida INTEGER,
  nivel_desafio REAL,
  forca, destreza, constituicao, inteligencia, sabedoria, carisma INTEGER,
  -- sentidos
  alcance_visao_cega, alcance_visao_penumbra, alcance_sentido_tremor,
  alcance_visao_verdadeira, percepcao_passiva INTEGER,
  -- saves (saving_throws_all — derivados, nunca NULL por falta de proficiência)
  forca_save, destreza_save, constituicao_save,
  inteligencia_save, sabedoria_save, carisma_save INTEGER,
  -- velocidade (speed_all)
  velocidade_caminhada, velocidade_voo, velocidade_natacao,
  velocidade_escalada, velocidade_escavacao INTEGER,
  pode_pairar INTEGER,   -- 0/1
  -- lore
  alinhamento TEXT,
  idiomas TEXT
)

monstro_interacao_dano (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monstro_nome TEXT,  tipo_dano TEXT,  relacao TEXT,  -- imunidade|resistencia|vulnerabilidade
  FOREIGN KEY (monstro_nome) REFERENCES monstros(nome)
)
monstro_imunidade_condicao (id PK, monstro_nome FK, condicao TEXT)
monstro_ambiente          (id PK, monstro_nome FK, ambiente TEXT)
monstro_pericia           (id PK, monstro_nome FK, pericia TEXT, bonus INTEGER)

-- criadas vazias; populadas nas Specs 4-5
acoes   (id PK, monstro_nome TEXT FK, categoria TEXT, nome_acao TEXT, descricao TEXT)
ataques (id PK, acao_id INTEGER FK, nome_ataque TEXT, tipo_ataque TEXT,
         bonus_ataque INTEGER, alcance INTEGER, alcance_longo INTEGER,
         dano_dado TEXT, dano_bonus INTEGER, dano_tipo TEXT,
         dano_extra_dado TEXT, dano_extra_bonus INTEGER, dano_extra_tipo TEXT)
efeitos (id PK, acao_id INTEGER FK, cd_resistencia INTEGER, atributo_resistencia TEXT,
         condicao TEXT, area_tipo TEXT, area_tamanho INTEGER)
```

## Não mexer
- `bestiario/cliente_api.py` — a ingestão consome o dict que o cliente já retorna; não altera o cliente.
- `bestiario/extracao.py` — a regex de ataque/dano só é usada a partir da Spec 4; aqui ela apenas deixa de ser chamada (dados de ação não são gravados nesta spec).
- `bestiario/relatorios.py` — as queries de relatório são ajustadas na Spec 6, não aqui.
- `bestiario/modelos.py` — segue placeholder; a ingestão lê o dict v2 diretamente, sem entidade intermediária.
- `main.py` — o menu não muda; a função de sync continua chamando a ingestão (que agora grava só nível monstro).
- População de `acoes`, `ataques`, `efeitos` — Specs 4 e 5.
- Tradução dos valores para português — camada de apresentação futura; o banco guarda as chaves canônicas em inglês.

## Decisões tomadas
- Campos de lista (imunidades/resistências/vulnerabilidades a dano, imunidades a condição, ambientes) → **tabelas normalizadas**, não texto com vírgulas. Motivo: análise exata ("quantos monstros imunes a fogo") via COUNT/JOIN, alinhado ao objetivo "tudo vira dado analisável". LIKE em texto seria frágil.
- Decomposição do dano → **uma tabela `monstro_interacao_dano` com coluna `relacao`** em vez de três tabelas idênticas. Motivo: imunidade/resistência/vulnerabilidade são o mesmo conceito; `relacao` é modelagem legítima e evita repetição. (Usuário delegou a escolha.)
- Perícias → tabela normalizada `monstro_pericia` com bônus. Motivo: permite análise por perícia (ex: furtividade alta).
- Idiomas → coluna TEXT em `monstros`, não tabela. Motivo: raramente se filtra por um idioma isolado; payload analítico baixo não justifica outra tabela (exceção pragmática à regra de normalizar listas).
- Velocidade → colunas separadas (`velocidade_*` + `pode_pairar`). Motivo: SQL trivial ("WHERE velocidade_voo >= 60"), decisão de projeto tomada antes das specs.
- Sentidos → colunas de alcance inteiras separadas (a v2 já entrega `blindsight_range` etc. como int). `NULL` quando o sentido não existe.
- Saves → 6 colunas de `saving_throws_all` (valores derivados). Motivo: elimina o "NULL indevido" quando o monstro não é proficiente.
- Idempotência → `INSERT OR REPLACE` em `monstros`; `DELETE` das linhas de lista do monstro antes de reinserir. Mesmo padrão já usado em `acoes`.
- Migração do banco → o `.db` é artefato regenerável; a migração é apagar o `bestiario_combate.db` uma vez e re-sincronizar. `CREATE TABLE IF NOT EXISTS` mantido (não destrói dados no startup).
- Escopo → só schema + persistência de nível monstro. `acoes`/`ataques`/`efeitos` criadas vazias; população nas Specs 4-5. Ações deixam de ser gravadas temporariamente até a Spec 4 (regressão consciente de meio de migração).
- Valores em inglês no banco → chaves canônicas da v2 (`fire`, `prone`) preservadas; tradução é camada de apresentação futura.

## Impacto no CLAUDE.md
Seção adicionada retroativamente (spec anterior à regra "spec declara e /spec-close sincroniza o CLAUDE.md").
- Schema do banco de dados → substituir a seção de 2 tabelas pelo schema relacional de ~9 tabelas: `monstros` enriquecida (sentidos, saves, velocidade, alinhamento, idiomas); tabelas de lista `monstro_interacao_dano`, `monstro_imunidade_condicao`, `monstro_ambiente`, `monstro_pericia`; `acoes` reescrita (ganha `categoria`, perde `bonus_ataque`/`dados_dano`); `ataques` e `efeitos` novas (criadas vazias, populadas nas Specs 4-5). Usar o bloco "Schema completo" desta spec como fonte.
- O que já funciona → remover/atualizar os itens que descrevem o estado v1 do banco: "2319 monstros, 14970 ações", "1244 ações no formato combinado de `dados_dano`", a dup do Bone Lord, `INSERT OR REPLACE`/`DELETE FROM acoes` sobre o schema antigo. Após o re-sync: ~325 monstros do SRD 2014; `acoes`/`ataques`/`efeitos` vazias até as Specs 4-5.
- O que está incompleto ou pode melhorar → item "Dados faltando no banco" (imunidades, resistências, vulnerabilidades, imunidades a condição, ambientes, alinhamento, sentidos, velocidade, saves, perícias) resolvido — agora persistidos.
- Contexto para decisões futuras → "banco já sincronizado (2319 monstros, 14970 ações)" → ~325 do SRD 2014, com `acoes`/`ataques`/`efeitos` vazias até as Specs 4-5.
