# Costbot POC — demo script

---

## 1. Open — why we're here (45 s)

[Share the screen with the app open. Don't click anything yet.]

Thanks for joining. I'll give a brief demo of Costbot, our new cost estimation tool.

Basically, this tool gives you a first screening number in a couple of minutes, from a few inputs, 
and shows you where the number came from.

It's built on the cost models we've been developing over the last months, now as a
standalone app. It runs here on Databricks, reading flat files. So, its a deterministic model, meaning same inputs, same answer, every time.

## 2. The screen (45 s)

[Hover over the left column, then the right.]

The layout is very simple. On the left, I describe the project. On the right, the app tells me
which models can give an opinion with what I've filled in so far.

Nothing runs until I press the "Run" button at the bottom. But watch the list on the right: it
updates as I type. The more I say about the project, the more models wake up.

## 3. Case one — a petrochemical plant (3 min)

Let me start with simple examples to show how it works. 
I'll start with a petrochemical plant on the Gulf Coast.
Two fields selected. And already, on the right, the Benchmark model says it's ready. That's the
model that looks for similar past projects. And the others are telling me what they still need to be ready.

[Archetype: **Petrochemical (onshore)**. Location: **US Gulf Coast**.]

Now, for the Rough Size, this one is the order of magnitude. Its not a cost, its a band. 
Basically I'm saying "this is a half-billion to one-billion kind of project", 
and the Benchmark uses it to look for projects of similar size.

[Rough size: **Substantial ($500M to $1,000M)**.]

Well. we selected archetype, location. size....
Now I add what the plant is: for example a polyethylene plant, 450 thousand tonnes a year. 
That wakes up the onshore calculator, which is the engineering-formula model. And see the OSBL line here, marked automatic, because it runs on its own whenever the calculator gives
it a process cost to work from.

[Facility type: **polyethylene**. Primary capacity: **450**. Unit: **KTA**.]

[Press **Run screening estimate**.]

There it is. We have three numbers at the top. First, the best estimate, which is the median of the
models. Second, the range, from P20 to P80. And the confidence, which is really "how many models agreed".
This line under them explains the confidence in words.

[Point at the **Model estimates** chart.]

We have this chart with each model's estimate. Each bar is one model. The length of the bar is that model's own range. The dashed line is
the median, which becomes the number at the top. So you can always see who said what.

[Open the **Onshore calculator** tab.]

We have for each model a tab with the math open. For example, for the calculator we can see the correlation it used, the
location index, the multiplier up to total cost. There's even a note on how many projects
that correlation was calibrated on.

[Open the **Benchmark (analogues)** tab, then scroll to **Comparable projects**.]

And for the Benchmark, we have the projects it matched on, with a similarity score. And further down,
the comparable projects table, which helps answer the question "similar to what?"

Ok, let's reset and run a few more cases, with different characteristics to show different situations.

## 4. Case two — a refinery modification (3 min)

Second case, and with this one I want to show two things.

[Press **Reset**. Archetype: **Refinery brownfield**. Location: **US Gulf Coast**. Scope
type: **Modification**. Rough size: **Moderate ($75M to $200M)**. Facility type:
**hydrotreater**. Capacity: **40000**, unit **BPD**.]

First, look at the right. The onshore calculator is now marked "excluded for this archetype".
That's a rule that comes with the models: on refinery modifications it overshoots badly, so
it stays out. And the app tells you that before you run.

[Press **Run screening estimate**.]

Well, and with only one model running, confidence is low, and it says so.

Second thing. For brownfield work, the scope really is the equipment list, meaning what gets
replaced or added. 

Let's give it one.

[In **Equipment list**: exchanger **6**, Add. pump **8**, Add. tower **1**, Add. drum **3**,
Add. compressor **1**, Add.]

And now the Equipment vector is
ready. Basically it compares this list with almost six hundred past projects and finds the ones with
the same mix of equipment.

[Press **Run screening estimate**.]

Now we have two models running now. Confidence went up. And in the Equipment vector tab you can see the five
closest equipment profiles it found.

Cool, now lets run one more case, offshore.

## 5. Case three — an FPSO (2 min)

[Press **Reset**. Archetype: **Offshore FPSO**. Location: **Guyana**. Rough size: **Very
large ($2,500M to $5,000M)**. Topsides weight: **25000**. Water depth: **1800**. Hull
type: **Fpso newbuild**.]

For an FPSO the Benchmark is excluded, and the list shows it.
The offshore calculator works from the topsides weight. And what I wanna show is that with this selection of inputs, we have a new card appeared down here, for the
subsea scope. We can add here the number of subsea trees, flowlines, risers, umbilicals, etc. basically anything related to the SURF package.

[**Subsea scope (SURF)**: Subsea trees **12**, Flowlines **6**, Risers **4**, Manifolds
**2**, Umbilicals **3**. Press **Run screening estimate**.]

And heres the result...

## 6. Under every result (1.5 min)

[Scroll to the bottom of the results.]

What else,

Basis year. Everything in the pool is in 2024 dollars. If I pick 2025 or 2026, the app
applies the CP30 index and tells me the factor it used.

We have a Bid check. A bid comes in, I type the amount, and it tells me whether it falls inside,
above or below the range.

We have a What-if. I change one number, say the capacity, and it reruns every model and shows the
difference model by model.

[Press **Download HTML report**.]

And we have a one-page report that you can download here.

## 7. Models and Data pages (1.5 min)

I think thats it, one last thing actually.

[Open **Models**.]

Two reference pages to finish. On Models: we have the card models, with the method and what it
needs in it. Then there's a routing tab, which tells which models each project type can use, and the
exclusions. And a tab called Reported accuracy.

[Open the **Reported accuracy** tab. Don't read the numbers out.]

That tab has the figures we measured on the fifty-two projects with known cost, with notes
on how they were counted. 

[Open **Data**.]

And Data: we have all tables the app loaded, with live row counts and which model reads it.

## 8. Close (30 s)

[Back to the **Estimator** page.]

So, this is our cost estimator, with a few inputs, models
wake up as you add more detail, we always give you a number with a range, and the evidence behind it.

That's it. Now, any questions? Any thing else I can show you?

---

## If someone asks

**"Is this the same code as the original models?"**
It's a rewrite as a standalone app, checked module by module against the original. The
onshore test cases match to the digit. A few model families are still being brought up
to date.

**"Can I use it today?"**
You can open it with the link in the invite. It's a POC: a screening number, Class 5, not a
basis of estimate. Use it to get a first order of magnitude and the comparable projects.

**"What does the confidence mean?"**
How many models agreed. High means three or more within thirty percent of each other.
Low means only one model could run. "Component only" means we have a subsea cost but no
total.

**"Why was a model excluded?"**
Rules that come with the models: where one is known to overshoot for a project type, it
stays out, and the app says so before you run.

**"How accurate is it?"**
The measured figures are on the Models page, Reported accuracy tab. How you count makes a
real difference, so I'd rather review them with the team before quoting a single number.
Happy to walk anyone through that tab afterwards.

**"Can it estimate X?"** (a project type not in the list)
The archetypes in the dropdown are the ones the models cover. Anything else, not yet.

**"Where did the data come from?"**
Our own project history: 503 past projects, about 600 equipment profiles, 857 cost
chips, and the cost indices. The Data page lists every table.
