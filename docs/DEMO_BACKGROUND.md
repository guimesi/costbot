# Costbot — material de apoio para quem apresenta (português)

**Para quem:** Guilherme, antes de apresentar. Explica a ferramenta sem pressupor nada:
o que cada modelo faz, como as opiniões viram um número, os termos, de onde veio, a
acurácia medida e como ela se compara com a reportada, e o que é igual ou diferente do
wireframe. O texto falado da demo está em `docs/DEMO_SCRIPT.md`; a versão em inglês deste
material está em `docs/DEMO_BACKGROUND_EN.md`.

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

---

# PARTE 2 — Perguntas prováveis e respostas

| Pergunta | Resposta em português |
|---|---|---|
| "Isso está chamando o meu código?" | Não. É uma reescrita, módulo a módulo, conferida contra os seus arquivos. Os casos golden batem centavo a centavo. Faltam quatro arquivos seus: SURF, OSBL, pipeline, LNG e offshore. |
| "Por que dois modelos de análogos?" | O seu é a referência e aparece sempre. A variante filtra por faixa de tamanho; nos dados reais ela acerta mais quando há tamanho. Você decide qual fica. |
| "Por que 10 modelos e não 9?" | O Composite do wireframe foi mantido. Nunca é escolhido pelo arquétipo; só roda quando o usuário adiciona itens de escopo. |
| "Por que o brownfield usa 2,61?" | Porque o `cost_bot_api` manda BF-expansion para todo brownfield; 1,30 só com modification ou conversion no nome. Copiado como está, anotado. |
| "E oil sands, GNL, petroquímica integrada?" | Ainda zero em qualquer configuração. Dependem dos arquivos de GNL e offshore e de uma correlação para oil sands. |
| "Por que o EMMA está desligado no offshore?" | As tabelas de taxa offshore já estão em dólares de 2024; aplicar EMMA de novo dobrava o ajuste. Os casos golden Payara, Liza e Jacket mostram isso. |
| "Roda no Databricks?" | Está rodando agora, como App, a partir de arquivos. |
| "O que é o número de confiança?" | Quantos modelos concordam. HIGH: três ou mais a ±30% da mediana. MEDIUM-HIGH: dois. MEDIUM: dois ou mais, discordando. LOW: um só. |
| "O que acontece se os modelos discordam muito?" | Enquanto o maior e o menor diferirem mais de 3 vezes, o mais distante da mediana é descartado, e a tela diz qual e por quê. |
| "Posso digitar o custo que eu acho?" | Não. A regra do brief é não ter entrada de custo. O "Rough size" é uma ordem de grandeza. |
