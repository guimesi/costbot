# Demo da POC — texto falado

**Para quem:** Guilherme, apresentando ao David e ao time, com o app aberto no Databricks.

É um texto corrido, para ler em voz alta ou decorar o fio. As indicações entre colchetes
são o que você faz na tela enquanto fala. Nenhum número de acurácia é dito; os números
ficam na aba **Reported accuracy** e a conversa sobre eles fica para o David puxar.
Dura uns 12 minutos. A versão em inglês está logo depois da versão em português.

O que você precisa ter pronto: o app aberto na página Estimator, formulário vazio
(botão **Reset**), e esta folha. O que explica cada modelo e cada termo está em
`docs/DEMO_BACKGROUND.md`, para ler antes, não durante.

---

## Em português

**[App aberto, página Estimator, formulário vazio]**

Deixa eu mostrar o que a gente montou. Isso aqui é o estimador de triagem, construído em
cima do pacote que você mandou em setembro. São os seus modelos, reescritos num código
nosso e conferidos contra os arquivos que você compartilhou. Roda aqui no Databricks, lendo
os arquivos do pacote. Não tem inteligência artificial no meio, não tem banco de dados.
É determinístico: mesma entrada, mesmo resultado.

A tela é simples. Do lado esquerdo eu descrevo o projeto. Do lado direito, o app me diz
quais modelos conseguem opinar com o que eu já preenchi. Nada roda até eu apertar o botão,
mas essa lista da direita vai mudando conforme eu preencho. É a ideia de divulgação
progressiva do brief: quanto mais eu conto, mais modelos acordam.

Vou começar pelo caso mais simples.

**[Archetype: Petrochemical (onshore). Location: US Gulf Coast.]**

Uma planta petroquímica na costa do Golfo. Só com isso, olha a lista da direita: o
Benchmark, o modelo de análogos, já está pronto. Os outros estão dizendo o que falta para
cada um.

**[Rough size: Substantial ($500M to $1,000M)]**

Esse campo é a ordem de grandeza. Não é um custo, é uma faixa: estou dizendo que é um
projeto na casa de 500 milhões a 1 bilhão. O Benchmark usa isso para procurar projetos do
mesmo porte. O brief fala em "size provided"; é esse campo.

**[Facility type: polypropylene. Primary capacity: 450. Unit: KTA.]**

Agora eu disse o que é a planta: polipropileno, 450 mil toneladas por ano. Com isso o
calculador onshore acorda, e o OSBL, utilidades e offsites, acende como automático, porque
ele roda sozinho quando o calculador produz um ISBL.

**[Run screening estimate]**

Pronto. Em cima, os três números: a melhor estimativa, que é o P50; a faixa, de P20 a P80;
e a confiança, que diz quantos modelos concordaram. Logo abaixo tem uma linha explicando
por que a confiança é essa.

**[Aponta para o gráfico Model estimates]**

Aqui cada barra é um modelo. O comprimento da barra é a faixa que o próprio modelo deu, e a
linha tracejada é a mediana, que vira o número do topo. O calculador fez a conta de
engenharia: custo de referência, escala pela capacidade, ajuste de local, multiplicador
para custo total. O Benchmark foi na base dos 503 projetos e trouxe os dez mais parecidos.

**[Abre a aba Onshore calculator]**

Cada modelo tem a aba dele com a conta aberta. Aqui dá para ver a correlação usada, o
índice de localidade, o multiplicador. Tem até uma nota dizendo com quantos projetos essa
correlação foi calibrada.

**[Abre a aba Benchmark (analogues), depois rola até Comparable projects]**

E aqui os análogos que o Benchmark usou, com a aderência de cada um. Embaixo, a tabela de
projetos comparáveis, que é o que o estimador vai querer ver primeiro: "parecido com o quê?"

Uma coisa que vale notar: o OSBL aparece ao lado, como linha indireta. Ele não entra na
mediana. O mesmo vale para o SURF, que eu mostro daqui a pouco.

**[Reset]**

Segundo caso: modificação em refinaria. Esse é importante por dois motivos.

**[Archetype: Refinery brownfield. Location: US Gulf Coast. Scope type: Modification.
Rough size: Moderate ($75M to $200M). Facility type: hydrotreater. Capacity: 40000 BPD.]**

Primeiro motivo: olha a lista da direita. O calculador onshore está marcado como excluído
para esse arquétipo. É a regra do seu API: em modificação de refinaria ele exagera, então
fica de fora. O app mostra isso antes de rodar, não esconde.

**[Run screening estimate]**

Com só o Benchmark, a confiança fica baixa, e o app diz isso.

Segundo motivo: a sua orientação no brief era que, em brownfield, o escopo é a lista de
equipamentos. Então vamos dar a lista.

**[Equipment list: exchanger 6, pump 8, tower 1, drum 3, compressor 1, clicando Add a cada um]**

Reparem que só o card atualiza; a página não recarrega. E agora o Equipment vector está
pronto. Ele compara a lista de equipamentos com a de 593 projetos e acha os que têm a mesma
receita, independente do nome da unidade.

**[Run screening estimate]**

Dois modelos agora, a confiança subiu, e na aba do Equipment vector estão os cinco perfis
de equipamento mais parecidos.

**[Reset]**

Terceiro caso, offshore, rápido.

**[Archetype: Offshore FPSO. Location: Guyana. Rough size: Very large ($2,500M to $5,000M).
Topsides weight: 25000. Water depth: 1800. Hull type: Fpso newbuild.]**

Para FPSO o seu API exclui o Benchmark, e a lista já mostra. O calculador offshore trabalha
a partir do peso do topsides. E apareceu um card novo, o de escopo submarino.

**[Subsea scope: trees 12, flowlines 6, risers 4, manifolds 2, umbilicals 3. Run.]**

O SURF estima o sistema submarino à parte. Ele aparece no gráfico na cor de componente e
não entra no custo total. Se só ele rodasse, o app não inventaria um total: a confiança
viraria COMPONENT_ONLY, como o brief pede. Dá para ver isso apagando o peso do topsides e
rodando de novo.

**[Volta ao último resultado, rola até o fim]**

Três coisas que ficam embaixo de qualquer resultado. O ano-base: a base está em dólares de
2024, e se eu escolho 2025 ou 2026 o app aplica o índice CP30 e avisa o fator. O bid check:
chegou uma proposta, eu digito o valor e ele diz se cai dentro, acima ou abaixo da faixa.
E o what-if: mudo um número, a capacidade por exemplo, e ele reroda todos os modelos e
mostra a diferença, modelo a modelo.

**[Download HTML report]**

Tudo isso sai num relatório de uma página, que dá para anexar num pacote de gate.

**[Página Models]**

Para fechar, duas páginas de referência. Em Models, um card por modelo com o método e o
algoritmo; a aba de roteamento, que diz quais modelos cada arquétipo pode usar e as
exclusões; e a aba Reported accuracy.

**[Aba Reported accuracy]**

Aqui estão os números medidos nos 52 projetos de custo conhecido, com a tabela do seu brief
ao lado e as notas de como uma coisa se compara com a outra. Eu preferia que você olhasse
isso com calma e me desse a sua leitura antes de a gente tirar conclusão, porque a forma de
contar faz diferença, e isso é decisão sua.

**[Página Data]**

E em Data, as tabelas que o app carregou, com a contagem de linhas ao vivo e qual modelo
lê cada uma. Tudo rastreável.

Para terminar: o que está aí é o seu pacote de setembro rodando como app. Para fechar a
paridade completa eu preciso dos arquivos que ainda não vieram: SURF, OSBL, pipeline, LNG e
offshore. Com eles, a última parte fica igual ao seu código também.

Perguntas?

---

## In English

**[App open, Estimator page, empty form]**

Let me show you what we put together. This is the screening estimator, built on the
package you sent in September. These are your models, rewritten in our code and checked
against the files you shared. It runs here on Databricks, reading the package files.
There's no AI in the loop and no database. It's deterministic: same input, same answer.

The screen is simple. On the left I describe the project. On the right, the app tells me
which models can weigh in with what I've filled so far. Nothing runs until I press the
button, but that list on the right changes as I type. That's the progressive disclosure
idea from the brief: the more I say, the more models wake up.

I'll start with the simplest case.

**[Archetype: Petrochemical (onshore). Location: US Gulf Coast.]**

A petrochemical plant on the Gulf Coast. With just that, look at the list on the right:
the Benchmark, the analogue model, is already ready. The others are saying what they need.

**[Rough size: Substantial ($500M to $1,000M)]**

This field is the order of magnitude. It's not a cost, it's a band: I'm saying this is a
500 million to 1 billion kind of project. The Benchmark uses it to look for projects of
the same size. The brief calls it "size provided"; this is that field.

**[Facility type: polypropylene. Primary capacity: 450. Unit: KTA.]**

Now I've said what the plant is: polypropylene, 450 thousand tonnes a year. That wakes up
the onshore calculator, and OSBL, utilities and offsites, lights up as automatic, because
it runs on its own whenever the calculator produces an ISBL.

**[Run screening estimate]**

There it is. At the top, the three numbers: the best estimate, which is the P50; the range,
P20 to P80; and the confidence, which tells you how many models agreed. Right below there's
a line explaining why the confidence is what it is.

**[Point at the Model estimates chart]**

Each bar is a model. The length of the bar is the range that model gave on its own, and
the dashed line is the median, which becomes the number at the top. The calculator did
the engineering math: reference cost, scaled by capacity, location factor, multiplier up
to total cost. The Benchmark went into the pool of 503 projects and brought back the ten
closest.

**[Open the Onshore calculator tab]**

Every model has its own tab with the math shown. Here you can see the correlation used,
the location index, the multiplier. There's even a note saying how many projects that
correlation was calibrated on.

**[Open the Benchmark (analogues) tab, then scroll to Comparable projects]**

And here are the analogues the Benchmark used, with how well each one matches. Below,
the comparable projects table, which is what an estimator wants to see first: "similar to
what?"

One thing worth noting: OSBL sits beside the total, as an indirect line. It's not in the
median. Same for SURF, which I'll show in a minute.

**[Reset]**

Second case: a refinery modification. This one matters for two reasons.

**[Archetype: Refinery brownfield. Location: US Gulf Coast. Scope type: Modification.
Rough size: Moderate ($75M to $200M). Facility type: hydrotreater. Capacity: 40000 BPD.]**

First reason: look at the list on the right. The onshore calculator is marked as excluded
for this archetype. That's your API's rule: on refinery modifications it overshoots, so it
stays out. The app shows that before running; it doesn't hide it.

**[Run screening estimate]**

With only the Benchmark, confidence is low, and the app says so.

Second reason: your guidance in the brief was that for brownfield, the scope is the
equipment list. So let's give it the list.

**[Equipment list: exchanger 6, pump 8, tower 1, drum 3, compressor 1, clicking Add each time]**

Notice only the card refreshes; the page doesn't reload. And now the Equipment vector is
ready. It compares the equipment list with 593 projects and finds the ones with the same
recipe, regardless of what the unit is called.

**[Run screening estimate]**

Two models now, confidence went up, and in the Equipment vector tab you have the five
closest equipment profiles.

**[Reset]**

Third case, offshore, quickly.

**[Archetype: Offshore FPSO. Location: Guyana. Rough size: Very large ($2,500M to $5,000M).
Topsides weight: 25000. Water depth: 1800. Hull type: Fpso newbuild.]**

For an FPSO your API excludes the Benchmark, and the list already shows it. The offshore
calculator works from the topsides weight. And a new card appeared, the subsea scope.

**[Subsea scope: trees 12, flowlines 6, risers 4, manifolds 2, umbilicals 3. Run.]**

SURF prices the subsea system separately. It shows in the chart in the component colour
and doesn't go into the total. If it were the only one running, the app wouldn't make up
a total: confidence would say COMPONENT_ONLY, as the brief asks. You can see that by
clearing the topsides weight and running again.

**[Back to the last result, scroll to the bottom]**

Three things that sit under any result. The basis year: the pool is in 2024 dollars, and
if I pick 2025 or 2026 the app applies the CP30 index and tells you the factor. The bid
check: a bid comes in, I type the amount and it says whether it falls inside, above or
below the range. And the what-if: I change one number, capacity for example, it reruns
every model and shows the difference, model by model.

**[Download HTML report]**

All of that comes out as a one-page report you can attach to a gate package.

**[Models page]**

To wrap up, two reference pages. In Models, one card per model with the method and the
algorithm; the routing tab, which says which models each archetype can use and the
exclusions; and the Reported accuracy tab.

**[Reported accuracy tab]**

Here are the figures measured on the 52 projects with known cost, with the table from your
brief next to them and notes on how one compares with the other. I'd rather you looked at
this with some time and gave me your read before we draw conclusions, because how you count
makes a difference, and that's your call.

**[Data page]**

And in Data, the tables the app loaded, with live row counts and which model reads each
one. All traceable.

To close: what's here is your September package running as an app. To complete the parity
I need the files that haven't come yet: SURF, OSBL, pipeline, LNG and offshore. With those,
the last part matches your code too.

Questions?
