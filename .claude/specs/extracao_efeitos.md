# Extração de efeitos (save / condição / área)

**Ordem:** 5 de 6
**Depende de:** Specs 1 (fundação), 2 (cliente API v2), 3 (schema + ingestão do monstro) e 4 (ações + ataques)
**Revisão:** aprovada

## O que faz
Parseia o campo `desc` de cada linha de `acoes` (via regex) e popula a tabela `efeitos` (criada vazia na Spec 3) com save DC, atributo do save, condição imposta e área de efeito. É a parte assumidamente **lossy** da ingestão — a v2 não estrutura nada disso, tudo vem do texto livre.

## Comportamento

### Fonte e escopo
- A extração roda sobre o `desc` de **todas** as linhas de `acoes` (categorias `action`, `legendary_action`, `reaction` e `special_ability`). É desc-driven: só gera linha em `efeitos` quando um padrão casa; ações/traits sem efeito não produzem nada.
- A v2 **não** fornece nenhum campo estruturado de save/condição/área nas actions (verificado: as chaves são só `name`, `desc`, `attacks`, `action_type`, `order_in_statblock`, `legendary_action_cost`, `limited_to_form`, `usage_limits`). Toda a informação é extraída do `desc` por regex.
- Cada linha de `efeitos` referencia a `acao_id` da ação de origem (FK para `acoes.id`, populada na Spec 4).

### Save (DC + atributo)
- Quando o `desc` contém "DC N <atributo> saving throw", extrai `cd_resistencia=N` e `atributo_resistencia=<atributo>` (`strength`, `dexterity`, `constitution`, `intelligence`, `wisdom` ou `charisma`, chave canônica em inglês minúsculo).
- Quando o `desc` contém "escape DC N" (agarrar/prender), extrai `cd_resistencia=N` e `atributo_resistencia=NULL`. O `NULL` sinaliza que é um teste de escape (FOR/DES à escolha do alvo), não um saving throw contra o DC do monstro.
- O save considerado é o **primeiro** DC encontrado no `desc` (o save principal da ação). Ações com múltiplos saves distintos são raras e ficam como limitação lossy: as condições da ação herdam o save principal.

### Condição (uma por linha)
- Quando o `desc` menciona uma das 15 condições canônicas do SRD (`blinded`, `charmed`, `deafened`, `exhaustion`, `frightened`, `grappled`, `incapacitated`, `invisible`, `paralyzed`, `petrified`, `poisoned`, `prone`, `restrained`, `stunned`, `unconscious`), cada condição detectada vira **uma linha** em `efeitos`. "knocked prone" normaliza para `prone`.
- Quando uma ação impõe 2+ condições (54 ações no SRD, ex: Behir/Constrict → `grappled` + `restrained`), gera uma linha por condição, **todas compartilhando** o mesmo `cd_resistencia`, `atributo_resistencia`, `area_tipo` e `area_tamanho` da ação.
- Quando a ação tem save mas **nenhuma** condição (ex: breath weapon que só causa dano — 82 casos), gera **uma** linha com `condicao=NULL` e os campos de save/área preenchidos. Preserva o save do dano em área como dado analisável.
- Quando a ação não tem save, nem condição, nem área, **nenhuma** linha de `efeitos` é criada.

### Área
- Quando o `desc` contém uma área geométrica nomeada ("N-foot cone/line/cube/sphere/radius"), extrai `area_tipo` (`cone`, `line`, `cube`, `sphere` ou `radius`, chave canônica em inglês) e `area_tamanho=N` (em pés).
- Quando o `desc` contém "within N ft/feet" (emanação ao redor do monstro, ex: Frightful Presence, Wing Attack — 96 casos), extrai `area_tipo='emanation'` e `area_tamanho=N`.
- Quando há mais de uma área no mesmo `desc`, considera a **primeira**. Ausência de área → `area_tipo=NULL`, `area_tamanho=NULL`.

### Idempotência
- Quando um monstro já existente é reingerido (re-sync), as linhas de `efeitos` daquele monstro são apagadas antes de reinserir (`DELETE FROM efeitos WHERE acao_id IN (SELECT id FROM acoes WHERE monstro_nome = ?)`), evitando duplicatas — mesmo padrão das Specs 3 e 4. A ordem importa: apagar `efeitos` antes de apagar/reinserir `acoes`, para não deixar linhas órfãs.

### Valores e idioma
- `condicao`, `atributo_resistencia` e `area_tipo` são guardados em inglês/chaves canônicas — tradução é camada de apresentação futura, conforme Spec 3.

## Critérios verificáveis
- [ ] `uv run pytest -v` passa, incluindo os testes desta spec e das Specs 1-4.
- [ ] Teste extrai efeitos de "Each creature ... must make a DC 21 Dexterity saving throw, taking 63 (18d6) fire damage ..." (Fire Breath, sem condição) e confirma **uma** linha com `cd_resistencia=21`, `atributo_resistencia='dexterity'`, `condicao=NULL`, `area_tipo='cone'`, `area_tamanho=60`.
- [ ] Teste extrai de "must succeed on a DC 19 Wisdom saving throw or become frightened ..." (Frightful Presence) e confirma uma linha com `cd_resistencia=19`, `atributo_resistencia='wisdom'`, `condicao='frightened'`, `area_tipo='emanation'`, `area_tamanho=120`.
- [ ] Teste com ação de 2 condições (ex: Behir/Constrict → `grappled` + `restrained`) confirma **2 linhas** em `efeitos`, ambas com o mesmo `cd_resistencia`/`atributo_resistencia`/`area` e `condicao` distintos.
- [ ] Teste com "grappled (escape DC 14)" confirma `cd_resistencia=14` e `atributo_resistencia=NULL` (escape, não saving throw).
- [ ] Teste confirma que "knocked prone" normaliza `condicao='prone'`.
- [ ] Teste confirma que uma ação sem save/condição/área (ex: Multiattack) **não** gera nenhuma linha em `efeitos`.
- [ ] Teste confirma que "within 10 ft" gera `area_tipo='emanation'`, `area_tamanho=10`.
- [ ] Teste confirma idempotência: reingerir o mesmo monstro não duplica linhas em `efeitos` e não deixa linhas órfãs.
- [ ] Teste confirma que a extração de efeito é pura (recebe `desc`/dados, devolve estrutura) sem I/O de rede.

## Módulos afetados
- `bestiario/extracao.py` — ampliado. Ganha o parser de efeito a partir do `desc`: extrai save (DC + atributo, incluindo escape DC), lista de condições canônicas e área (geométrica ou emanação). Funções puras (string → dados), sem I/O. Reutiliza padrões de regex já introduzidos na Spec 4 quando aplicável.
- `bestiario/banco.py` — a ingestão (que na Spec 4 popula `acoes` e `ataques`) passa a também popular `efeitos`: para cada linha de `acoes` inserida, chama o parser de efeito de `extracao.py` e insere as linhas resultantes com a `acao_id` correta. `DELETE` das linhas de `efeitos` do monstro antes de reinserir (idempotência), antes do delete de `acoes`.
- `tests/test_extracao.py` — ampliado com casos do parser de efeito (save com/sem condição, escape DC, multi-condição, emanação vs área geométrica, ausência de efeito).
- `tests/test_banco.py` — ampliado com fixture de dict v2 validando a população de `efeitos` na ingestão e a idempotência.

## Não mexer
- `bestiario/cliente_api.py` — a extração consome o dict/`desc` que o cliente já retorna; não altera o cliente.
- `bestiario/relatorios.py` — queries de relatório são a Spec 6.
- `bestiario/modelos.py` — segue placeholder.
- `main.py` — o menu não muda.
- **Tabelas `acoes` e `ataques`** e sua extração — responsabilidade da Spec 4. Esta spec só lê `acoes` (para obter `acao_id` e `desc`); não altera suas linhas nem sua extração.
- **Tabelas de nível monstro** (`monstros`, `monstro_interacao_dano`, `monstro_imunidade_condicao`, `monstro_ambiente`, `monstro_pericia`) — Spec 3, não tocadas.
- **Schema** da tabela `efeitos` — fixado na Spec 3. Esta spec só popula; não altera colunas.
- Tradução dos valores para português — camada de apresentação futura; o banco guarda chaves canônicas em inglês.

## Decisões tomadas
- Multiplicidade → **1 linha por condição**, todas compartilhando o save/área da ação; ação com save-só-dano (breath) = 1 linha com `condicao=NULL`; ação sem save/cond/área = nenhuma linha. Motivo: 54 ações do SRD impõem 2+ condições e a coluna `condicao` guarda uma só; N linhas resolvem o schema single-column sem perda e mantêm "tudo vira dado analisável" (ex: contar quantos monstros causam `restrained`). Descartado "1 linha por ação" (perderia as condições extras das 54 ações multi).
- Escape DC (agarrar, 29 casos) → grava em `cd_resistencia` com `atributo_resistencia=NULL`. Motivo: preserva a dificuldade de escapar como dado analisável; o `NULL` em `atributo_resistencia` distingue escape de saving throw. Descartado ignorar o escape DC (perderia a dificuldade da agarrada).
- Emanação "within X ft" (96 casos) → `area_tipo='emanation'`, `area_tamanho=X`, junto de cone/line/cube/sphere/radius. Motivo: torna pesquisável o alcance dos efeitos de presença/asa (a maioria dos saves de emanação); cobre ~96 casos a mais. Descartado capturar só áreas geométricas nomeadas.
- Fonte de dados → 100% regex sobre `desc`. Motivo: verificado que a v2 não tem nenhum campo estruturado de save/condição/área nas actions; não há alternativa estruturada.
- Vocabulário controlado → 15 condições canônicas do SRD, `atributo_resistencia` ∈ {strength…charisma}, `area_tipo` ∈ {cone, line, cube, sphere, radius, emanation}, valores em inglês. Motivo: coerente com "banco em inglês" da Spec 3; permite COUNT/GROUP BY exatos.
- Escopo do scan → todas as linhas de `acoes` (actions + traits), não só actions com save. Motivo: extração é desc-driven; traits sem efeito não geram linha, então varrer tudo é consistente e não custa.
- Save principal por ação → primeiro DC do `desc`; múltiplos saves distintos herdam o principal. Limitação lossy consciente: condições vindas de cláusulas com DCs diferentes (ex: Chuul/Tentacles) herdam o save principal da ação, podendo associar o DC errado a uma condição secundária. Aceito como custo da parte lossy — bindar cada condição à sua cláusula seria regex frágil e over-engineered.
- Risco de falso-positivo → uma condição citada como pré-condição ("if the target is grappled") ou negação pode gerar linha indevida. Aceito como limitação lossy documentada; não se tenta análise semântica do texto.
- Idempotência → `DELETE` de `efeitos` do monstro (via join em `acoes`) antes de reinserir, antes do delete de `acoes` para não deixar órfãos. Mesmo padrão das Specs 3-4.
