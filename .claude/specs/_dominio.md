# Domínio — Bestiário de D&D 5e

> Gerado por `/dominio` em 2026-07-25. Lido automaticamente pelo `/spec` antes de
> gerar qualquer spec de feature, e pelo `/contrato` ao nomear recursos da API.

**Este documento descreve o domínio que já existe, não propõe um novo.** Ele foi
escrito depois de 6 specs entregues, com schema estável e código em produção. Se
uma revisão futura sugerir renomear entidade consagrada, isso é sinal de alerta,
não de melhoria — o custo de renomear passa por banco, testes e, a partir da
Spec 8, pelo contrato público da API.

## Entidades

### Persistidas — têm identidade e vivem no SQLite

| Entidade | O que é |
|---|---|
| Monstro | A criatura do SRD 2014. Única com identidade própria: `nome` é chave primária e todo o resto pende dela. São 325. |
| Ação | Algo que um monstro faz, em quatro categorias: ação, ação lendária, reação e habilidade especial. Não existe sem o monstro dono. |
| Ataque | A parte de uma ação que acerta alguém — bônus de acerto, alcance, dano. Uma ação tem zero, um ou dois ataques (dois quando é "corpo a corpo ou à distância"). |
| Efeito | A parte de uma ação que não é ataque — CD de resistência, condição imposta, área atingida. Também pende da ação. |

### Calculadas — nascem de uma pergunta e morrem na resposta

Nunca são gravadas. A distinção é deliberada: confundir "coisa gravada" com "coisa
calculada" leva alguém a criar tabela para guardar comparação.

| Entidade | O que é |
|---|---|
| Consulta | Um conjunto de filtros mais um modo de saída. É o que o construtor da tela monta e o que a API recebe por query string. |
| Comparação | O resultado agrupado — uma linha por tipo, por ambiente, por tamanho. |
| Resumo | O conjunto filtrado condensado em uma linha só: quantos, médias de pontos de vida, classe de armadura, desafio e dano. |

### O que deliberadamente não é entidade

Imunidade a dano, resistência, vulnerabilidade, imunidade a condição, ambiente,
perícia, sentidos, velocidade e atributos. Todos têm tabela ou coluna própria, mas
nenhum existe sozinho — "resistência a frio" sem o monstro não é coisa nenhuma. São
características dele: aparecem **dentro** do monstro e **como filtro**, nunca como
coleção própria na API.

Ações e efeitos, embora sejam entidades, **não viram recurso de API** pelo mesmo
tipo de razão: "Fire Breath" sem saber de quem é não serve a ninguém. Vêm aninhados
na ficha do monstro.

## Glossário de termos

Apenas termos que hoje aparecem com mais de um nome no projeto.

### Sobre o monstro

| Usar sempre | Evitar | Motivo |
|---|---|---|
| desafio | CR, nível de desafio, challenge rating | O campo tem quatro nomes hoje: coluna `nivel_desafio`, API externa `challenge_rating`, terminal "CR", tela "Desafio". Na API pública vira `desafio`. |
| monstro | criatura | A Open5e chama de `creatures`; o projeto chama de monstro desde o início. A tradução fica na fronteira de ingestão. |
| pontos de vida | HP, vida | `relatorios.py` hoje faz `pontos_vida AS hp` e a abreviação vaza para o terminal. |
| classe de armadura | CA, AC, armadura | Mesmo caso: `classe_armadura AS ac`. |

### Sobre o combate

| Usar sempre | Evitar | Motivo |
|---|---|---|
| ação | habilidade, trait | O que a API chama de `traits` vira ação de categoria "habilidade especial". Um conceito, um nome. |
| ataque | golpe, investida | Termo já fixado no schema. |
| efeito | consequência | É a linha inteira da tabela: CD, condição e área juntas. |
| condição | estado, status | É **um campo** do efeito, não sinônimo dele. Confundir faz "impõe efeito" e "impõe condição" parecerem a mesma pergunta — não são. |
| bônus de ataque | to hit, acerto | Decidido na Sessão 5, quando as colunas de combate foram traduzidas. |
| CD de resistência | save DC, DC | Idem. |

### Sobre a consulta

| Usar sempre | Evitar | Motivo |
|---|---|---|
| consulta | query, busca, pesquisa | Termo técnico do núcleo (`consultas.py`, "montar consulta"). |
| filtro | critério, condição | "Condição" já é termo de combate; usá-lo para filtro cria colisão dentro do próprio glossário. |
| comparação | agrupamento, group by | O usuário escolhe "comparar por tipo" — não deveria ver a palavra agrupamento em lugar nenhum. |
| relatório | análise, dashboard | Nome da aba e já em uso no código. |

### Regra estrutural

**Nome de coisa em português, valor de dado em inglês canônico.** A coluna se chama
`tipo_dano`; o que está gravado nela é `fire`, não `fogo`. Vale para o schema inteiro
e para a API pública.

O motivo é que os valores vêm da Open5e e funcionam como **chave**, não como texto:
traduzir na ingestão quebraria a correspondência com a fonte e tornaria o re-sync
ambíguo. A tradução é camada de apresentação — é exatamente o que a Spec 10 faz, e
o dicionário dela nasce deste glossário.

## Bounded Contexts

**Contexto único** — todo o projeto é um domínio coeso.

O teste aplicado não foi contar módulos, e sim perguntar se alguma palavra muda de
significado ao atravessar a fronteira. "Monstro" significa a mesma coisa no cliente
da Open5e, no banco, na camada de consulta, na API e no site. Enquanto isso valer,
separar em contextos só criaria tradução entre partes que já se entendem.

Há uma costura que parece fronteira: a ingestão (regex sobre `desc`, payload da v2)
fala uma língua bem diferente da consulta (filtros, comparações). Mas é fronteira
**técnica**, não de domínio — as duas falam de monstro, ação e efeito com o mesmo
sentido. Módulo separado resolve; contexto separado seria exagero.
