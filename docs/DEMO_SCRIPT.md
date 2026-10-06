# Roteiro da demo — GP Screening Cost Estimator

**Para quem:** Guilherme, apresentando a POC ao David e ao time, ao vivo, no app publicado
no Databricks.

**Como usar.** A Parte 1 explica a ferramenta para você, em português, sem pressupor nada.
Leia uma vez com calma. A Parte 2 é o roteiro da apresentação: o que falar, o que clicar, o
que vai aparecer. Cada fala vem em português e logo abaixo em inglês, para ler em voz alta
se a reunião for em inglês. A Parte 3 tem as perguntas que devem vir e as respostas prontas.

**Tempo.** Apresentação completa: 25 minutos. Curta: abertura, Caso 1, Caso 2 e a parte de
acurácia, 12 minutos.

---

# PARTE 1 — Entenda a ferramenta antes de apresentar

## 1.1 O que ela faz, em uma frase

Você descreve um projeto de capital com poucos campos (tipo de projeto, lugar, tamanho
aproximado, capacidade) e a ferramenta responde quanto ele deve custar, com uma faixa de
incerteza, e mostra os projetos parecidos do passado que sustentam o número. É uma
estimativa de triagem ("screening", classe 5), para decidir se vale seguir, não para orçar.

## 1.2 Como ela chega no número: a mesa de especialistas

Pense em uma mesa com dez especialistas. Cada um tem um jeito próprio de estimar. Cada um
só dá opinião se tiver os dados que o método dele precisa. No fim, a ferramenta pega as
opiniões que apareceram, descarta quem ficou muito fora, e fica com a mediana.

Os dez, com o nome que aparece na tela:

| Na tela | O que faz, em uma frase | Do que precisa | Como se comporta |
|---|---|---|---|
| **Benchmark (analogues)** | Procura, entre 503 projetos passados, os mais parecidos e usa o custo deles. "Quanto custou da última vez que fizemos algo assim." | Tipo de projeto e lugar. Melhora muito com o tamanho aproximado. | Sem tamanho, acerta pouco; com tamanho, é o que mais ajuda. |
| **Equipment vector** | Compara a lista de equipamentos do seu projeto com a de 593 projetos. "Me diga o que tem dentro e eu acho o projeto com a mesma receita." | Lista de equipamentos com quantidades (pelo menos dois itens de processo: bombas, trocadores, torres...). | O David chama de "melhor modelo amplo". |
| **Onshore calculator** | Fórmula de engenharia: custo de referência × (capacidade / capacidade de referência)^0,6, ajustado pelo índice do local, vezes um multiplicador que leva ao custo total. | Tipo de instalação e capacidade. | Boa para plantas novas; exagera em modificações de refinaria, por isso é desligado nesse caso. |
| **Offshore calculator** | Estima a partir do peso do topsides (a parte de cima da plataforma). | Peso do topsides ou produção em KBPD, profundidade da água, tipo de casco. | Só dois projetos de calibração; tratar com cautela. |
| **Pipeline calculator** | Diâmetro × comprimento, trecho a trecho: tubo, construção, travessias, estações. | Comprimento e diâmetro. | O próprio David marcou como "não verificado"; o app avisa na tela. |
| **LNG calculator** | Equações por subsistema de uma planta de GNL. | Capacidade em MTPA. | O David diz que está descalibrado e fora do escopo de novembro. |
| **Unconventional lookup** | Tabela de projetos não convencionais por tipo de instalação (estação de compressão, ponto de entrega...), interpolando pela capacidade. | Tipo de instalação. | Foi a família mais certeira nos dados reais. |
| **Composite (scope chips)** | Monta o projeto por pedaços (uma unidade de processo, um pacote de utilidades, um trecho de duto) e soma o custo de cada pedaço, buscado em uma biblioteca de 857 "chips" de custo. | Pelo menos um item de escopo. | Veio do wireframe do David; o brief de setembro não o lista. |
| **SURF subsea (component)** | Custo do sistema submarino: árvores, linhas, risers, manifolds, umbilicais. | Árvores ou linhas, profundidade. | É um componente: fica fora da mediana, aparece ao lado. |
| **OSBL overlay (indirect)** | Utilidades e offsites como proporção do custo das unidades de processo. | Roda sozinho quando o Onshore calculator produz um ISBL. | Também fica fora da mediana. |

## 1.3 Como as opiniões viram um número: o ensemble

Regras que o app aplica, copiadas do `cost_bot_api` do David:

1. Só entram os modelos de custo total. SURF e OSBL aparecem ao lado, nunca na mediana.
2. **Portão de dispersão:** enquanto a maior e a menor estimativa sobreviventes diferirem
   mais de 3 vezes, a mais distante da mediana é descartada. Nenhum modelo tem prioridade
   sobre outro.
3. **Melhor estimativa (P50)** = mediana dos sobreviventes.
4. **Faixa (P20 a P80)** = da menor "baixa" à maior "alta" entre as faixas dos próprios
   modelos, limitada a 5 vezes a mediana para cada lado.
5. **Confiança:** HIGH se 3 ou mais sobreviventes estão a ±30% da mediana; MEDIUM-HIGH se 2
   estão; MEDIUM se há 2 ou mais mas discordam; LOW com um só modelo; COMPONENT_ONLY quando só
   o SURF rodou (há custo submarino, não há custo total).
6. Projetos abaixo de US$ 20 milhões ganham um aviso: estão fora do piso de triagem.

Quando um modelo é descartado, a tela diz "Gated out of the ensemble" com o motivo.

## 1.4 Os termos que vão aparecer

| Termo | Em português simples |
|---|---|
| **TEC** | Total erected cost: o custo total instalado do projeto. É o número que o app estima. |
| **ISBL / OSBL** | Dentro e fora dos limites de bateria: as unidades de processo versus utilidades e offsites. |
| **P50, P20, P80** | Mediana e os percentis 20 e 80 da faixa. "P80 = há 80% de chance de custar menos que isso." |
| **Class 5** | Estimativa de triagem, alvo de ±50%. Não serve de base para orçamento. |
| **Archetype** | O tipo de projeto (refinaria brownfield, FPSO, duto...). Decide quais modelos podem rodar. |
| **CP30** | Índice de custo por local e ano. Todo custo é trazido para dólares de 2024 com ele. |
| **EMMA** | Índice de custo por localidade usado pelos calculadores. Costa do Golfo = 414; a base GOM 2000 = 202; o fator é 414/202 = 2,05. |
| **Análogos** | Os projetos parecidos que o Benchmark usou. Aparecem em "Comparable projects". |
| **Greenfield / brownfield** | Planta nova em terreno novo / obra em planta existente. Expansion e modification são tipos de brownfield. |
| **Rough size** | Sua ordem de grandeza para o projeto: "entre 500 milhões e 1 bilhão". Não é um custo; é uma faixa. |
| **LOOCV** | Como medimos a acurácia: para cada projeto conhecido, escondemos ele da base, estimamos, e comparamos com o custo real. |

## 1.5 De onde veio e o que fizemos

- Em 16 de setembro o David mandou o pacote: dados (503 projetos, 593 vetores de
  equipamento, 857 chips, 53 linhas de custo real), o código de referência dele e o brief.
- Reconstruímos os modelos dele em código nosso, módulo a módulo, e conferimos contra os
  arquivos dele que foram compartilhados: `cost_bot_api.py`, `analogue_estimator.py`,
  `onshore_calculator.py`, `evaluation_harness.py`. Os 25 casos de teste "golden" onshore
  do pacote dele dão o mesmo número no nosso código, centavo a centavo.
- O app roda no Databricks como App, lendo arquivos CSV. Sem IA, sem banco de dados.
- Faltam quatro arquivos dele para fechar a paridade completa: SURF, OSBL, pipeline, LNG e
  offshore. Até lá esses modelos seguem a primeira versão, com as entradas no formato do
  `cost_bot_api`.

## 1.6 A acurácia, para você saber responder

**Como medimos.** Pegamos os 52 projetos cujo custo real é conhecido. Para cada um,
escondemos o projeto da base, rodamos a ferramenta como um usuário faria e comparamos.
"Acertou" quer dizer que a estimativa ficou a ±30% do custo real.

**Os números (dados reais, 30 de setembro):**

| O que foi medido | Resultado |
|---|---:|
| O número que o app mostra (P50), sem informar o tamanho | 29% dos projetos (15 de 52) |
| O número que o app mostra, informando o tamanho aproximado | **63%** (33 de 52); refinaria brownfield 14 de 17 |
| A regra de medição do próprio David, sem o modelo que olha a resposta | 48% (24 de 50) |
| O número que o David reporta | 77% (40 de 52) |

**Por que o David fala 77% e nós 48% na mesma regra.** Três motivos, em linguagem simples:

1. A regra dele conta um projeto como acerto se **qualquer** modelo, sozinho, chegou perto.
   Não é um número final; é "algum dos dez acertou". O app entrega um número só.
2. Um dos modelos dele, o Composite, usa o custo real do projeto para se corrigir. O próprio
   código dele chama isso de "oracle ceiling", teto teórico. Isso não existe para um projeto
   novo que alguém digita.
3. Ele pontua o SURF contra um custo só do submarino, para quatro projetos.

**O que mais mexe no resultado:** o tamanho aproximado informado pelo usuário. Leva de 29%
para 63%. É uma entrada legítima: quem faz triagem sabe se o projeto é de 50 ou de 500
milhões.

**Onde ainda é zero:** oil sands, GNL e petroquímica integrada. Dependem dos calculadores
de GNL e offshore, cujos arquivos ainda não vieram, e de uma correlação para oil sands.

## 1.7 O que é igual e o que é diferente do wireframe do David

| No wireframe (agosto) | No app | Por quê |
|---|---|---|
| Cinco páginas: Estimator, Data Package, Code Inventory, Dependencies, Model Specs | Três: Estimator, Models, Data | "Code Inventory" listava arquivos que o pacote de setembro removeu. "Dependencies" e "Model Specs" viraram abas da página Models. |
| Modelos chamados A, A.1, B, B.1, Bottom-Up | Os nove nomes do brief de 15 de setembro, mais o Composite | O brief renomeou os modelos. O A.1 "Calculator Plus (ADR)" saiu do pacote, então não existe no app. |
| Benchmark precisa de tipo + lugar + ano; "tamanho, se informado" | Benchmark roda com tipo + lugar; o tamanho é o campo "Rough size" | O código do David aceita uma faixa de tamanho, não um custo. O ano já vem como 2024. |
| "Nenhuma entrada de custo pelo usuário" | Mantido. "Rough size" é uma ordem de grandeza, nunca um número | Mesma regra. |
| Composite monta o projeto por itens de escopo | Mesmo card, mesmos tipos de item | Mantido do wireframe. |
| OSBL "roda sempre que algum modelo roda" | Roda quando há um ISBL, isto é, quando o Onshore calculator rodou | É o que o `cost_bot_api` faz. A frase do brief é mais solta que o código. |
| Um modelo de análogos | Dois, selecionáveis: o do David ("Reference") e uma variante nossa com banda de tamanho ("Engine"), que é o padrão | Nos dados reais, empatam sem tamanho; com tamanho a variante acerta mais (63% contra 44%). O app sempre mostra o que o outro daria. |
| Calculador offshore com fator de localidade EMMA | EMMA desligado no offshore | As tabelas de taxa já estão em dólares de 2024; aplicar EMMA de novo dobrava o ajuste. Está documentado. |
| Não existia | Bid check, What-if, relatório HTML | Adicionados na primeira versão para uso em gate review. |
| Página "Data Package" com manifesto de 74 projetos | Página Data com as tabelas reais do pacote de setembro (503 projetos etc.) | O pacote de setembro substituiu o manifesto. |

---

# PARTE 2 — O roteiro

## Antes de começar

- Abra o app no Databricks. O topo mostra **GP screening cost estimator**, o selo azul
  **POC v1.1** e a frase *Class 5 screening estimate (±50% target). Deterministic models, no
  AI. Not a basis of estimate.*
- Três páginas no menu de cima: **Estimator**, **Models**, **Data**.
- O topo **não** pode mostrar aviso de dados sintéticos. Se mostrar, o app está lendo o
  pacote de exemplo; pare e corrija (`docs/DEPLOY_DATABRICKS.md`).
- Clique em **Reset** (embaixo da coluna de entradas) para começar com o formulário vazio.
- Na primeira vez que ensaiar, anote na margem os números que aparecerem em cada caso. Eles
  não mudam enquanto os dados não mudarem.

## Abertura (1 minuto)

**Fala.** "Isso aqui é o estimador de triagem construído em cima do pacote de 16 de
setembro. São os seus modelos, reescritos em código nosso e conferidos contra os seus
arquivos. Roda no Databricks lendo arquivos CSV, sem IA, sem banco. Vou mostrar um caso por
família de modelo e, no final, a acurácia que medimos nos 52 projetos reais, com a mesma
régua do seu harness."

> EN: "This is the screening estimator built on the September 16 package. These are your
> models, rewritten in our code and checked against your files. It runs on Databricks from
> CSV files, no AI, no database. I'll show one case per model family and, at the end, the
> accuracy we measured on the 52 real projects, with the same yardstick as your harness."

## A tela (1 minuto)

**Fala.** "Lado esquerdo, o escopo. Lado direito, o que os modelos fazem com ele. Nada roda
até eu apertar o botão, mas a lista de prontidão à direita vai se atualizando conforme eu
preencho: ela diz qual modelo já tem o que precisa."

> EN: "Left side is the scope. Right side is what the models make of it. Nothing runs until
> I press the button, but the readiness list on the right updates as I fill things in: it
> tells me which model already has what it needs."

**O que mostrar com o mouse, de cima para baixo na esquerda:** o card **Project**
(Archetype, Location, Basis year, Scope type, Rough size, Project name), **Equipment list**,
**Facility and capacity**, **Scope items**, e o botão **Run screening estimate**. À direita,
**Model readiness**.

---

## Caso 1 — Planta petroquímica: o caso simples, dois modelos

**Contexto para você.** É o caminho mais curto. Com tipo, lugar, tamanho aproximado e
capacidade, dois modelos conseguem opinar: o de análogos e o calculador onshore. Serve para
mostrar a mecânica inteira sem complicação.

**Fala.** "Vou começar pelo caso mais simples. Eu só sei que é uma planta de polipropileno
de 450 mil toneladas por ano, na costa do Golfo, e que é um projeto na casa de 500 milhões
a 1 bilhão. Isso basta para dois modelos."

> EN: "Let me start with the simplest case. All I know is: a polypropylene plant, 450
> thousand tonnes a year, Gulf Coast, and that it's a 500 million to 1 billion kind of
> project. That's enough for two models."

**Clique.**

| Campo | Escolha / digite |
|---|---|
| Archetype | **Petrochemical (onshore)** |
| Location (CP30 region) | **US Gulf Coast** |
| Basis year | **2024** (já vem marcado) |
| Scope type | **Greenfield** |
| Rough size | **Substantial ($500M to $1,000M)** |
| Project name | `Demo polypropylene` |
| Facility type | **polypropylene** |
| Primary capacity | `450` |
| Unit | **KTA** |

Antes de apertar Run, aponte para **Model readiness**: Benchmark (analogues) *Ready*,
Onshore calculator *Ready*, OSBL overlay (indirect) *Ready automatic*, Equipment vector
*Needs at least one equipment item*, Composite (scope chips) *Needs at least one scope item*.

**Fala.** "Reparem que antes de rodar a tela já diz quem pode opinar e o que falta para os
outros. É a divulgação progressiva do brief."

> EN: "Notice that before running, the screen already says who can weigh in and what the
> others are missing. That's the progressive disclosure from the brief."

Aperte **Run screening estimate**.

**O que aparece.**

- Três cartões: **Best estimate (P50)**, **Range (P20 to P80)** e **Confidence**
  (MEDIUM-HIGH ou HIGH), com uma linha explicando o porquê.
- Uma linha *Other analogue variant, Reference (analogue_estimator v3): $…*: é o que o
  modelo de análogos do David daria com as mesmas entradas.
- **Model estimates**: uma barra por modelo, com a faixa de cada um, e a linha tracejada da
  mediana. Uma aba por modelo.
- Na aba **Onshore calculator**: a correlação polypropylene (136 milhões a 450 KTA), o
  índice EMMA 414 (fator 2,05), o multiplicador 2,58 de greenfield, 6% de escalação. Conta
  fechada: 136 × 2,05 = 279; × 2,58 = 719; × 1,06 = **762 milhões**. Também aparece a nota de
  calibração: esse coeficiente foi ajustado com um único projeto.
- Na aba **Benchmark (analogues)**: a variante usada, o sinal de tamanho (*size_bucket*,
  700 milhões) e os dez análogos com a similaridade.
- **Comparable projects**: os dez projetos mais próximos, com custo, aderência, país,
  capacidade.
- Mais abaixo: **Bid check**, **What-if**, **Download HTML report**.

**Fala.** "O calculador faz a conta de engenharia: custo de referência, escala pela
capacidade com expoente 0,6, ajuste de local, multiplicador para custo total. O Benchmark
foi buscar os dez projetos mais parecidos na base. A mediana dos dois é o número do topo. E
o OSBL, utilidades e offsites, rodou sozinho porque o calculador produziu um ISBL; ele
aparece ao lado, não entra na mediana."

> EN: "The calculator does the engineering math: reference cost, scaled by capacity with a
> 0.6 exponent, location factor, multiplier to total cost. The Benchmark went and found the
> ten most similar projects in the pool. The median of the two is the number at the top. And
> OSBL, utilities and offsites, ran on its own because the calculator produced an ISBL; it
> sits beside the total, it's not in the median."

**Se perguntarem "e esse 'other analogue variant'?"** "O app tem dois modelos de análogos:
o seu, e uma variante nossa que também filtra a base por faixa de tamanho. Sem tamanho
informado eles empatam; com tamanho, a variante acerta mais. O app usa a variante e sempre
mostra o que o seu daria. A escolha de qual fica é sua."

> EN: "The app has two analogue models: yours, and a variant of ours that also filters the
> pool by size band. Without a size they tie; with a size the variant does better. The app
> uses the variant and always shows what yours would give. Which one stays is your call."

---

## Caso 2 — Refinaria brownfield: a exclusão e "o escopo é a lista de equipamentos"

**Contexto para você.** Em modificação de refinaria o calculador onshore exagera muito (o
brief fala em 7 vezes), então o `cost_bot_api` o desliga para esse tipo de projeto. O David
disse no brief que, em brownfield, o escopo *é* a lista de equipamentos. Este caso mostra
as duas coisas: o modelo desligado e o Equipment vector entrando quando a lista aparece.

**Fala.** "Agora uma modificação em refinaria. Aqui o calculador exagera, e o seu API o
desliga para esse arquétipo. O app mostra isso antes mesmo de rodar. E a sua orientação
era: em brownfield, pergunte quais equipamentos estão envolvidos. Vamos dar a lista."

> EN: "Now a refinery modification. Here the calculator overshoots, and your API switches it
> off for this archetype. The app shows that before I even run. And your guidance was: for
> brownfield, ask which equipment is involved. Let's give it the list."

**Clique.** Aperte **Reset**, depois:

| Campo | Escolha / digite |
|---|---|
| Archetype | **Refinery brownfield** |
| Location (CP30 region) | **US Gulf Coast** |
| Scope type | **Modification** |
| Rough size | **Moderate ($75M to $200M)** |
| Facility type | **hydrotreater** |
| Primary capacity | `40000` |
| Unit | **BPD** |

Aponte para **Model readiness**: Onshore calculator com o selo vermelho **Excluded for this
archetype**. Aperte **Run screening estimate** e mostre o resultado só com o Benchmark.

Depois, em **Equipment list**, adicione um por vez (tipo, quantidade, **Add**; só o card
atualiza, a página não recarrega):

| Equipment type | Count |
|---|---:|
| exchanger | 6 |
| pump | 8 |
| tower | 1 |
| drum | 3 |
| compressor | 1 |

A prontidão passa a mostrar Equipment vector *Ready*. Aperte **Run screening estimate** de
novo.

Opcional: em **Scope items**, tipo **process_unit**, nome `Hydrotreater revamp`, **Add**, e
rode de novo para ligar o Composite (scope chips).

**O que aparece.**

- Primeira rodada: só o Benchmark, confiança LOW, e a exclusão listada.
- Segunda rodada: o Equipment vector entra, com os cinco projetos de perfil de equipamento
  mais parecido na aba dele; a mediana passa a juntar dois modelos; a confiança sobe.
- Terceira rodada (se fizer): o Composite entra, mostrando os chips casados por item.

**Fala.** "Com a lista de equipamentos o Equipment vector acha os projetos com a mesma
receita de equipamentos, independente do nome da unidade. É o modelo que o seu brief chama
de melhor modelo amplo."

> EN: "With the equipment list, the Equipment vector finds the projects with the same
> equipment recipe, regardless of what the unit is called. That's the model your brief calls
> the best broad model."

**Se perguntarem "por que o brownfield mostra multiplicador 2,61 e não 1,30?"** "Porque o
`cost_bot_api` manda 'BF-expansion' para qualquer brownfield, e 2,61 é o valor dessa chave
no seu `onshore_calculator`. O 1,30 só é usado quando o nome da instalação diz modification
ou conversion. Copiamos como está e deixamos anotado como pendência."

> EN: "Because `cost_bot_api` sends 'BF-expansion' for any brownfield, and 2.61 is that key's
> value in your `onshore_calculator`. The 1.30 is used only when the facility name says
> modification or conversion. We copied it as is and flagged it."

---

## Caso 3 — FPSO: o calculador offshore e o componente submarino

**Contexto para você.** No FPSO o Benchmark é excluído (regra do brief), o calculador
offshore trabalha a partir do peso do topsides, e o SURF estima o sistema submarino como um
componente separado, que não entra no custo total.

**Fala.** "Offshore agora. Para FPSO o seu API exclui o Benchmark. O calculador offshore
parte do peso do topsides, e o SURF estima o submarino à parte, como componente."

> EN: "Offshore now. For an FPSO your API excludes the Benchmark. The offshore calculator
> works from the topsides weight, and SURF prices the subsea scope separately, as a
> component."

**Clique.** Aperte **Reset**, depois:

| Campo | Escolha / digite |
|---|---|
| Archetype | **Offshore FPSO** |
| Location (CP30 region) | **Guyana** |
| Scope type | **Greenfield** |
| Rough size | **Very large ($2,500M to $5,000M)** |
| Topsides weight (t) | `25000` |
| Water depth (m) | `1800` |
| Hull type | **Fpso newbuild** |

Em **Subsea scope (SURF)**: Subsea trees `12`, Flowlines `6`, Risers `4`, Manifolds `2`,
Umbilicals `3`. Aperte **Run screening estimate**.

**O que aparece.**

- Prontidão: Benchmark **Excluded for this archetype**, Offshore calculator *Ready*, SURF
  subsea (component) *Ready*.
- Resultado: o Offshore calculator como estimativa de custo total; o SURF na cor de
  componente, com a aba dele (linhas, risers, umbilicais, árvores, instalação); o valor do
  SURF **não** está no P50.
- Se você apagar o peso do topsides e rodar de novo, a confiança vira **COMPONENT_ONLY**:
  existe custo submarino, não existe custo total. Diga isso em voz alta: é a regra do brief.

**Fala.** "O SURF aparece ao lado, na cor de componente. Se só ele rodar, o app não inventa
um total: diz COMPONENT_ONLY, como o brief pede."

> EN: "SURF shows up beside the total, in the component colour. If it's the only one that
> runs, the app doesn't make up a total: it says COMPONENT_ONLY, as the brief asks."

**Se perguntarem "o SURF pede as mesmas entradas do meu?"** "O seu brief fala em número de
poços, profundidade e peso do topsides. O card pede árvores, linhas, risers, manifolds e
umbilicais, e lê a profundidade do card de cima. Quando o seu `surf_estimator.py` vier,
alinhamos."

> EN: "Your brief mentions well count, water depth and topsides weight. The card asks for
> trees, flowlines, risers, manifolds and umbilicals, and reads the water depth from the card
> above. When your `surf_estimator.py` arrives, we align it."

---

## Caso 4 — Duto: o calculador não verificado

**Contexto para você.** O próprio brief marca o calculador de dutos como "não verificado",
porque os custos reais de dutos divergem entre as fontes dele. O app mostra esse aviso na
tela. É um caso curto.

**Fala.** "Dutos são o ponto fraco do próprio brief: o calculador está marcado como não
verificado porque os valores reais divergem entre fontes. O app diz isso na cara."

> EN: "Pipelines are the weak spot in the brief itself: the calculator is marked unverified
> because the truth values disagree between sources. The app says so right on screen."

**Clique.** Aperte **Reset**, depois:

| Campo | Escolha / digite |
|---|---|
| Archetype | **Pipeline (mainline)** |
| Location (CP30 region) | **US Gulf Coast** |
| Scope type | **Greenfield** |
| Rough size | **Medium ($200M to $500M)** |
| Length (km) | `200` |
| Diameter (in) | `24` |

Aperte **Run screening estimate**.

**O que aparece.** Pipeline calculator *Ready* e Benchmark *Ready*; um aviso amarelo do
calculador de dutos dizendo que está "UNVERIFIED"; na aba dele, a decomposição: tubo,
construção da linha, travessias, estações, engenharia, contingência.

---

## Caso 5 — Não convencional: o modelo de tabela

**Contexto para você.** Para projetos não convencionais de ciclo curto (estações de
compressão, pontos de entrega) existe um modelo de tabela por tipo de instalação. Foi a
família mais certeira nos dados reais: 7 de 11 só com ele, 8 de 11 com o ensemble.

**Fala.** "Para não convencional existe um modelo de tabela por tipo de instalação, que
interpola pela capacidade. Foi a família que mais acertou nos dados reais."

> EN: "For unconventional there's a lookup model by facility type that interpolates by
> capacity. It was the most accurate family on the real data."

**Clique.** Aperte **Reset**, depois:

| Campo | Escolha / digite |
|---|---|
| Archetype | **Onshore unconventional** |
| Location (CP30 region) | **New Mexico** |
| Scope type | **Expansion** |
| Facility type | **compressor_station** |
| Primary capacity | `70` |
| Unit | **MMSCFD** |

Aperte **Run screening estimate**.

**O que aparece.** Prontidão: Benchmark **Excluded**, Onshore calculator *Ready*,
Unconventional lookup *Ready*, OSBL overlay *Ready*. Na aba do Unconventional lookup, os
projetos-pares usados e a interpolação entre eles. Na aba do Onshore calculator, a correlação
`compressor_station`, com a nota de que foi ajustada com um único projeto.

---

## Caso 6 — Ano-base, bid check, what-if, relatório (em qualquer caso)

**Clique.** No último resultado, mude **Basis year** para **2026** e rode de novo.

**O que aparece.** A linha *Pool-based estimates escalated from 2024 to 2026 USD (CP30
factor 1.2019; +20.2%)*.

**Fala.** "Os números da base são dólares de 2024. Para outro ano o app usa o índice CP30 da
costa do Golfo. 2025 é o último ano da tabela; 2026 é extrapolado, e o app avisa."

> EN: "The pool numbers are 2024 dollars. For another year the app uses the Gulf Coast CP30
> index. 2025 is the last year in the table; 2026 is extrapolated, and the app says so."

**Clique.** Em **Bid check**, digite um valor (no Caso 1, `700`), deixe **TEC**, aperte
**Check bid**. Em **What-if**, escolha **Primary capacity**, digite outro valor (no Caso 1,
`600`), aperte **Run what-if**.

**O que aparece.** Bid check: *Within range*, *Above range* ou *Below range*, com a distância
até o limite. What-if: três cartões (P50 base, P50 novo com a variação, o parâmetro) e uma
tabela por modelo, base contra novo.

**Fala.** "O bid check é para gate review: chegou uma proposta, confere se cai na faixa. O
what-if muda um número e reroda todos os modelos."

> EN: "Bid check is for gate reviews: a bid comes in, you check whether it sits in the range.
> What-if changes one number and reruns every model."

**Clique.** Aperte **Download HTML report** e abra o arquivo.

**O que aparece.** Uma página só: escopo, os três cartões, avisos (inclusive qual variante
de análogos foi usada e o que a outra daria), o gráfico, a tabela de status dos modelos, os
análogos, o aviso legal.

---

## Páginas Models e Data (2 minutos)

**Clique.** Abra **Models**. Três abas: **Model specs** (um card por modelo: método,
algoritmo, acurácia medida), **Routing and inputs** (quais modelos cada arquétipo pode usar,
as exclusões, a tabela de entrada por modelo e as regras do ensemble em texto), **Reported
accuracy** (os três números medidos e, ao lado, a tabela do brief).

**Clique.** Abra **Data**: as tabelas carregadas com contagem de linhas ao vivo e qual
modelo lê cada uma, uma prévia, e a base por arquétipo.

**Fala.** "Tudo é rastreável: a tabela, a linha, a correlação, a regra."

> EN: "Everything is traceable: the table, the row, the correlation, the rule."

---

## A conversa sobre acurácia (3 minutos)

Essa pergunta vai vir. Tenha a tabela da seção 1.6 à mão.

**Fala.** "O seu pacote reporta 40 de 52 dentro de ±30%. Nós medimos de dois jeitos. O
primeiro é o número que o app mostra: sem tamanho informado, 29%; com o usuário informando
a ordem de grandeza, 63%. O segundo é a sua régua, do harness: qualquer modelo sozinho
chegando perto. Nessa régua, sem o Composite que se corrige com o valor real, dá 48%. A
diferença para os 77% é esse Composite e o SURF pontuado contra custo só de submarino.
Nada disso existe para um projeto novo que alguém digita."

> EN: "Your package reports 40 of 52 within ±30%. We measured two ways. First, the number the
> app shows: with no size given, 29%; with the user giving the order of magnitude, 63%.
> Second, your yardstick, from the harness: any single model landing close. On that
> yardstick, without the Composite that corrects itself with the actual value, it's 48%. The
> gap to 77% is that Composite and SURF being scored against a subsea-only truth. None of
> that exists for a new project someone types in."

**Fala.** "O que mais mexe no resultado é o tamanho aproximado. É uma entrada legítima: quem
faz triagem sabe se é um projeto de 50 ou de 500 milhões. Por isso o campo está em destaque."

> EN: "What moves the number most is the rough size. It's a legitimate input: whoever does
> screening knows whether it's a 50 million or a 500 million project. That's why the field is
> up front."

---

# PARTE 3 — Perguntas prováveis e respostas

| Pergunta | Resposta em português | Em inglês |
|---|---|---|
| "Isso está chamando o meu código?" | Não. É uma reescrita, módulo a módulo, conferida contra os seus arquivos. Os casos golden batem centavo a centavo. Faltam quatro arquivos seus: SURF, OSBL, pipeline, LNG e offshore. | "No. It's a rewrite, module by module, checked against your files. The golden cases match to the digit. Four of your files are still to come: SURF, OSBL, pipeline, LNG and offshore." |
| "Por que dois modelos de análogos?" | O seu é a referência e aparece sempre. A variante filtra por faixa de tamanho; nos dados reais ela acerta mais quando há tamanho. Você decide qual fica. | "Yours is the reference and always shows. The variant adds a size band; on the real data it does better when a size is given. Your call which stays." |
| "Por que 10 modelos e não 9?" | O Composite do wireframe foi mantido. Nunca é escolhido pelo arquétipo; só roda quando o usuário adiciona itens de escopo. | "The composite from the wireframe was kept. It's never routed by archetype; it only runs when the user adds scope items." |
| "Por que o brownfield usa 2,61?" | Porque o `cost_bot_api` manda BF-expansion para todo brownfield; 1,30 só com modification ou conversion no nome. Copiado como está, anotado. | "Because `cost_bot_api` sends BF-expansion for any brownfield; 1.30 only with modification or conversion in the name. Copied as is, flagged." |
| "E oil sands, GNL, petroquímica integrada?" | Ainda zero em qualquer configuração. Dependem dos arquivos de GNL e offshore e de uma correlação para oil sands. | "Still zero in every configuration. They depend on the LNG and offshore files and on an oil sands correlation." |
| "Por que o EMMA está desligado no offshore?" | As tabelas de taxa offshore já estão em dólares de 2024; aplicar EMMA de novo dobrava o ajuste. Os casos golden Payara, Liza e Jacket mostram isso. | "The offshore rate tables are already in 2024 dollars; applying EMMA again doubled the adjustment. The Payara, Liza and Jacket golden cases show it." |
| "Roda no Databricks?" | Está rodando agora, como App, a partir de arquivos. | "It's running now, as an App, from flat files." |
| "O que é o número de confiança?" | Quantos modelos concordam. HIGH: três ou mais a ±30% da mediana. MEDIUM-HIGH: dois. MEDIUM: dois ou mais, discordando. LOW: um só. | "How many models agree. HIGH: three or more within ±30% of the median. MEDIUM-HIGH: two. MEDIUM: two or more, disagreeing. LOW: a single one." |
| "O que acontece se os modelos discordam muito?" | Enquanto o maior e o menor diferirem mais de 3 vezes, o mais distante da mediana é descartado, e a tela diz qual e por quê. | "While the highest and lowest differ by more than 3x, the one furthest from the median is dropped, and the screen says which and why." |
| "Posso digitar o custo que eu acho?" | Não. A regra do brief é não ter entrada de custo. O "Rough size" é uma ordem de grandeza. | "No. The brief's rule is no cost input. Rough size is an order of magnitude." |
