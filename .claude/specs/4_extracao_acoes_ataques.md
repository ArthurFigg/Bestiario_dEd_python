# Extração de ações + ataques (núcleo híbrido)

**Ordem:** 4 de 6
**Depende de:** Specs 1 (fundação), 2 (cliente API v2) e 3 (schema + ingestão do monstro)
**Revisão:** aprovada

## O que faz
Percorre `actions` e `traits` do dict estruturado da v2 (SRD 2014) e popula as tabelas `acoes` e `ataques` (criadas vazias na Spec 3), usando `attacks[]` estruturado como enumerador dos ataques e a regex sobre o campo `desc` como gabarito do dano.

## Comportamento

### Ingestão de `acoes`
- Quando um monstro é ingerido, cada entrada de `actions` do dict vira uma linha em `acoes`, com `categoria` derivada de `action_type`: `ACTION`→`action`, `LEGENDARY_ACTION`→`legendary_action`, `REACTION`→`reaction`.
- Quando o monstro tem `traits` (habilidades especiais/passivas: Legendary Resistance, Regeneration, Magic Resistance, etc.), cada `trait` também vira uma linha em `acoes` com `categoria='special_ability'`, `nome_acao` e `descricao` preenchidos, e **nenhuma** linha em `ataques` (traits não têm estrutura de ataque na v2).
- `acoes` guarda `monstro_nome`, `categoria`, `nome_acao` (campo `name`) e `descricao` (campo `desc`).
- Quando um monstro já existente é reingerido (re-sync), as linhas de `acoes` e `ataques` daquele monstro são apagadas antes de reinserir (`DELETE WHERE monstro_nome = ?` em `acoes`, e as linhas de `ataques` associadas), evitando duplicatas — mesmo padrão da Spec 3.
- Quando uma action não tem ataque estruturado (`attacks: []`) — caso de Multiattack, Frightful Presence, Fire Breath, Wing Attack — a linha em `acoes` é criada normalmente e nenhuma linha em `ataques` é gerada para ela. Efeitos de save/condição/área dessas ações são responsabilidade da Spec 5, não desta.

### Ingestão de `ataques`
- O **enumerador** de ataques é o array `attacks[]` estruturado da v2: cada entrada de `attacks[]` de uma action vira uma linha em `ataques`, referenciando a `acao_id` da action pai. (Verificado no SRD: `attacks[]` sinaliza 100% dos ataques — não existe ação com `attacks: []` cujo `desc` contenha "to hit". A regex não precisa *descobrir* ataques, só corrigir o dano.)
- Quando uma action tem `attacks[]` com 2 entradas (18 casos "Melee **or** Ranged Weapon Attack", ex: Dagger, Javelin, Spear), gera **2 linhas** em `ataques`: a entrada com `reach` preenchido é rotulada como variante corpo-a-corpo; a entrada com `range`/`long_range` preenchido, como variante à distância. Ambas compartilham o mesmo dano parseado do `desc`.
- Campos vindos do **estruturado** (confiáveis na v2):
  - `nome_ataque` ← `name` da entrada de `attacks[]` (ex: "Bite attack")
  - `bonus_ataque` ← `to_hit_mod`
  - `alcance` ← `reach`
  - `alcance_longo` ← `long_range` (e `range` quando presente para a variante à distância)
  - `tipo_ataque` ← derivado do prefixo do `desc` ("Melee/Ranged Weapon/Spell Attack") normalizado para `melee_weapon`, `ranged_weapon`, `melee_spell` ou `ranged_spell`. Nos casos "Melee or Ranged", o desempate entre as 2 linhas usa a presença de `reach` (melee) vs `range` (ranged) no estruturado.
- Campos vindos da **regex sobre `desc`** (gabarito — o estruturado tem `damage_type` ~99% errado, sempre "thunder", e `damage_bonus` ~99% null):
  - `dano_dado` ← dado primário do bloco "Hit:" (ex: `"2d10"`)
  - `dano_bonus` ← bônus do dado primário (ex: `8`; `NULL` quando não há bônus)
  - `dano_tipo` ← tipo do dano primário (ex: `piercing`)
  - `dano_extra_dado`, `dano_extra_bonus`, `dano_extra_tipo` ← bloco de dano secundário ("plus X (NdM) tipo damage"), quando existir. Um único slot de extra é suficiente (0 ataques no SRD com 2+ danos secundários).
- Quando não há dano secundário no `desc`, os três campos `dano_extra_*` ficam `NULL`.

### Fallback quando a regex falha
- Quando a regex não consegue parsear o bloco de dano de um ataque (desc malformado — raríssimo, os descs do SRD são padronizados), a linha de ataque é gravada mesmo assim: `dano_dado` é montado a partir dos campos estruturados `damage_die_count` + `damage_die_type` (ex: `2` + `D10` → `"2d10"`); `dano_bonus` e `dano_tipo` ficam `NULL` (não inventa valor a partir do estruturado, que é sabidamente errado). O ataque nunca é perdido.

### Valores e idioma
- Os valores de `categoria`, `tipo_ataque` e `dano_tipo` são guardados em inglês/chaves canônicas (`action`, `melee_weapon`, `fire`) — tradução é camada de apresentação futura, conforme decidido na Spec 3.

## Critérios verificáveis
- [ ] `uv run pytest -v` passa, incluindo os testes desta spec e das Specs 1-3.
- [ ] Teste ingere o dict v2 do Adult Red Dragon e confirma que a action "Bite" gera 1 linha em `acoes` (`categoria='action'`) e 1 em `ataques` com `nome_ataque='Bite attack'`, `bonus_ataque=14`, `alcance=10`, `dano_dado='2d10'`, `dano_bonus=8`, `dano_tipo='piercing'`, `dano_extra_dado='2d6'`, `dano_extra_tipo='fire'` — provando que a regex corrige o `damage_type='thunder'` e o `damage_bonus=null` do estruturado.
- [ ] Teste confirma que um `trait` (ex: Legendary Resistance) vira linha em `acoes` com `categoria='special_ability'` e **nenhuma** linha em `ataques`.
- [ ] Teste confirma que uma action sem ataque (ex: Multiattack, `attacks: []`) gera linha em `acoes` e **nenhuma** linha em `ataques`.
- [ ] Teste confirma que uma action "Melee or Ranged Weapon Attack" (ex: Dagger, `attacks[]` com 2 entradas) gera 2 linhas em `ataques`, uma `tipo_ataque='melee_weapon'` (com `alcance`) e outra `ranged_weapon` (com `alcance_longo`), ambas com o mesmo dano.
- [ ] Teste confirma que um ataque sem bônus e sem dano secundário (ex: Claw sem "+") grava `dano_bonus=NULL` e `dano_extra_*=NULL`.
- [ ] Teste de fallback: dado um attack cujo `desc` não casa com a regex, a linha é gravada com `dano_dado` derivado de `damage_die_count`/`damage_die_type` e `dano_bonus`/`dano_tipo` NULL.
- [ ] Teste confirma que reingerir o mesmo monstro não duplica linhas em `acoes` nem em `ataques`.
- [ ] Teste confirma que a extração é pura (recebe dict, devolve estrutura) sem chamada HTTP nem I/O de rede.

## Módulos afetados
- `bestiario/extracao.py` — ampliado. Ganha o parser do bloco de ataque a partir do `desc`: extrai `dano_dado`, `dano_bonus`, `dano_tipo` do dano primário e `dano_extra_*` do secundário; deriva `tipo_ataque` do prefixo do `desc`. A regex de `bonus_ataque`/`dados_dano` da Spec 1 é generalizada/substituída aqui para produzir os campos do novo schema. Funções puras (dict/string → dados), sem I/O.
- `bestiario/banco.py` — a função de ingestão (que na Spec 3 grava só nível monstro) passa a também popular `acoes` e `ataques`: itera `actions` + `traits`, insere em `acoes`, e para cada entrada de `attacks[]` chama o parser de `extracao.py` e insere em `ataques` com a `acao_id` correta. `DELETE` das linhas de `acoes`/`ataques` do monstro antes de reinserir (idempotência).
- `tests/test_extracao.py` — ampliado com casos do parser de ataque (dano primário com/sem bônus, dano secundário, fallback, derivação de `tipo_ataque`).
- `tests/test_banco.py` — ampliado com fixtures de dict v2 (Adult Red Dragon e um monstro com trait) validando a população de `acoes` e `ataques` e a idempotência.

## Não mexer
- `bestiario/cliente_api.py` — a ingestão consome o dict que o cliente já retorna; não altera o cliente.
- `bestiario/relatorios.py` — queries de relatório são a Spec 6.
- `bestiario/modelos.py` — segue placeholder; a ingestão lê o dict v2 diretamente.
- `main.py` — o menu não muda; a função de sync continua chamando a ingestão.
- **Schema** das tabelas `acoes` e `ataques` — fixado na Spec 3. Esta spec só popula; não altera colunas nem cria tabelas.
- **Tabela `efeitos`** e a extração de save DC / condição / área — responsabilidade da Spec 5. Ações com save (Fire Breath, Wing Attack) têm sua linha em `acoes` criada aqui, mas seus efeitos não são extraídos nesta spec.
- **Tabelas de nível monstro** (`monstros`, `monstro_interacao_dano`, `monstro_imunidade_condicao`, `monstro_ambiente`, `monstro_pericia`) — populadas na Spec 3, não tocadas aqui.
- Tradução dos valores para português — camada de apresentação futura; o banco guarda chaves canônicas em inglês.

## Decisões tomadas
- Ingerir `traits` → **sim**, como linhas em `acoes` com `categoria='special_ability'`, sem linha em `ataques`. Motivo: a v1 já salvava `special_abilities` na tabela de ações; deixá-las de fora seria regressão de dados, e o objetivo do projeto é "tudo vira dado analisável". Habilidades passivas ficam pesquisáveis.
- Categorias de ação → `action`, `legendary_action`, `reaction`, `special_ability`. Motivo: mapeamento direto de `action_type` da v2 + `special_ability` para traits. `BONUS_ACTION` não existe no SRD 2014 (verificado: 0 ocorrências em 944 ações), então não é previsto.
- Fonte da verdade do dano → **regex parseia o bloco "Hit:" inteiro** (`dano_dado`, `dano_bonus`, `dano_tipo`, `dano_extra_*`); estruturado fornece só `bonus_ataque`, `alcance`, `alcance_longo`, `tipo_ataque`. Motivo: no SRD, `damage_type` estruturado é ~99% "thunder" (lixo constante) e `damage_bonus` ~99% null; parsear o dano todo de uma fonte única (o `desc`) evita dessincronizar dado-do-estruturado com tipo-da-regex. Descartada a opção de misturar `dano_dado` estruturado com tipo/bônus da regex.
- Enumerador de ataques → `attacks[]` estruturado, não a regex. Motivo: verificado que `attacks[]` sinaliza 100% dos ataques (0 ações com `attacks: []` e "to hit" no `desc`); a regex só corrige o dano, não descobre ataques.
- Fallback de regex → cair para o estruturado: `dano_dado` de `damage_die_count`/`damage_die_type`, `dano_bonus`/`dano_tipo` NULL. Motivo: nunca perder o ataque nem inventar tipo/bônus a partir de campos sabidamente errados. Deve ser acionado em ~0 casos (descs do SRD padronizados), mas o comportamento fica definido.
- "Melee or Ranged" (18 casos) → **2 linhas** em `ataques` (uma `melee_weapon` com `alcance`, uma `ranged_weapon` com `alcance_longo`), ambas com o mesmo dano. Motivo: preserva a estrutura da v2 (que já separa em 2 entradas de `attacks[]`) e mantém as duas variantes analisáveis; desempate melee/ranged via `reach` vs `range` do estruturado.
- `tipo_ataque` → derivado do prefixo do `desc` (`melee_weapon`/`ranged_weapon`/`melee_spell`/`ranged_spell`), não do `attack_type` cru (que só distingue WEAPON/SPELL). Motivo: captura as duas dimensões (corpo-a-corpo/distância + arma/magia) numa string pesquisável, coerente com "desc é o gabarito".
- Slot único de dano extra → suficiente. Motivo: verificado 0 ataques no SRD com 2+ danos secundários; o schema da Spec 3 (`dano_extra_*` único) cobre 100% dos casos.
- Idempotência → `DELETE` de `acoes`/`ataques` do monstro antes de reinserir, mesmo padrão da Spec 3 e da v1.

## Impacto no CLAUDE.md
Seção adicionada retroativamente (spec anterior à regra "spec declara e /spec-close sincroniza o CLAUDE.md").
- O que está incompleto ou pode melhorar → item "Categoria das ações não é salva" resolvido: coluna `categoria` populada (`action`/`legendary_action`/`reaction`/`special_ability`; `BONUS_ACTION` não existe no SRD 2014).
- O que já funciona → adicionar população de `acoes` (com `categoria`) e `ataques` via extração híbrida (array `attacks[]` estruturado como enumerador + regex do `desc` como gabarito do dano; fallback para o estruturado quando a regex falha).
- Schema do banco de dados → garantir que a observação antiga "Ações abrangem `actions`/`special_abilities`/`legendary_actions`/`reactions` — todas unificadas na mesma tabela sem distinção de categoria" não sobreviva (agora há `categoria` e os ataques ficam em tabela própria). Se a Spec 3 já reescreveu a seção, aqui é só conferir.
