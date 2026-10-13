# Costbot POC — demo script

**Audience:** the stakeholders on the thread (David, Pedro, Giovanni, Lokesh, Prasanth and
his team, Caroline). Most of them have not seen the tool. Some know the models, most don't.

**Format:** numbered beats. Each beat starts with what you click, in brackets, then the
words. Short sentences, your voice. Total about 12 minutes plus questions. No accuracy
figures are spoken; they live in the app, on the Models page, and you point there.

**Before you start:** app open on the **Estimator** page, form empty (press **Reset**),
this page on a second screen. Rehearse once with the app so the numbers you see are
familiar; they don't change unless the data package changes.

---

## 1. Open — why we're here (45 s)

[Share the screen with the app open. Don't click anything yet.]

Thanks for joining. I'll keep this to about twelve minutes and then take questions.

Here's the problem we're working on. Early in a project, before there's any engineering,
someone needs a first cost number. Today that takes an estimator, a few days, and a lot of
judgment. This tool gives you a first screening number in a couple of minutes, from a
handful of inputs, and shows you where the number came from.

It's built on David's September package: the cost models his team developed, rewritten
as a standalone app. It runs here on Databricks, reading flat files. No AI involved, no
database. Same inputs, same answer, every time.

## 2. The screen (45 s)

[Hover over the left column, then the right.]

The layout is simple. On the left, I describe the project. On the right, the app tells me
which models can give an opinion with what I've filled in so far.

Nothing runs until I press the button at the bottom. But watch the list on the right: it
updates as I type. The more I say about the project, the more models wake up. That's the
"progressive disclosure" idea from the brief.

## 3. Case one — a petrochemical plant (3 min)

[Archetype: **Petrochemical (onshore)**. Location: **US Gulf Coast**.]

Let me start with the simplest thing you can do. A petrochemical plant on the Gulf Coast.
Two fields. And already, on the right, the Benchmark model says it's ready. That's the
model that looks for similar past projects. The others are telling me what they still need.

[Rough size: **Substantial ($500M to $1,000M)**.]

This one is the order of magnitude. Not a cost, a band. I'm saying "this is a half-billion
to one-billion kind of project". The Benchmark uses it to look for projects of similar size.
Whoever does screening usually knows this much.

[Facility type: **polypropylene**. Primary capacity: **450**. Unit: **KTA**.]

Now I've said what the plant is: polypropylene, 450 thousand tonnes a year. That wakes up
the onshore calculator, the engineering-formula model. And see the OSBL line, utilities and
offsites: it's marked automatic, because it runs on its own whenever the calculator gives
it a process cost to work from.

[Press **Run screening estimate**.]

There it is. Three numbers at the top. The best estimate, which is the median of the
models. The range, P20 to P80. And the confidence, which is really "how many models agreed".
The line under them explains the confidence in words.

[Point at the **Model estimates** chart.]

Each bar is one model. The length of the bar is that model's own range. The dashed line is
the median, which becomes the number at the top. So you can always see who said what.

[Open the **Onshore calculator** tab.]

Every model has a tab with the math open. For the calculator: the correlation it used, the
location index, the multiplier up to total cost. There's even a note on how many projects
that correlation was calibrated on, because some are thin.

[Open the **Benchmark (analogues)** tab, then scroll to **Comparable projects**.]

And for the Benchmark, the projects it matched on, with a similarity score. Further down,
the comparable projects table. In my experience that's the first thing an estimator wants:
"similar to what?"

## 4. Case two — a refinery modification (3 min)

[Press **Reset**. Archetype: **Refinery brownfield**. Location: **US Gulf Coast**. Scope
type: **Modification**. Rough size: **Moderate ($75M to $200M)**. Facility type:
**hydrotreater**. Capacity: **40000**, unit **BPD**.]

Second case, and this one shows two things the brief asked for.

First, look at the right. The onshore calculator is marked "excluded for this archetype".
That's a rule from the package: on refinery modifications it overshoots badly, so it stays
out. The app tells you that before you run, instead of hiding it.

[Press **Run screening estimate**.]

With one model only, confidence is low, and it says so.

Second thing. The brief says that for brownfield work, the scope *is* the equipment list.
So let's give it one.

[In **Equipment list**: exchanger **6**, Add. pump **8**, Add. tower **1**, Add. drum **3**,
Add. compressor **1**, Add.]

Notice only this card refreshes; the page doesn't reload. And now the Equipment vector is
ready. It compares this list with almost six hundred past projects and finds the ones with
the same mix of equipment, whatever the unit was called.

[Press **Run screening estimate**.]

Two models now. Confidence went up. And in the Equipment vector tab you can see the five
closest equipment profiles it found.

## 5. Case three — an FPSO (2 min)

[Press **Reset**. Archetype: **Offshore FPSO**. Location: **Guyana**. Rough size: **Very
large ($2,500M to $5,000M)**. Topsides weight: **25000**. Water depth: **1800**. Hull
type: **Fpso newbuild**.]

Offshore, quickly. For an FPSO the package excludes the Benchmark, and the list shows it.
The offshore calculator works from the topsides weight. And a new card appeared, for the
subsea scope.

[**Subsea scope (SURF)**: Subsea trees **12**, Flowlines **6**, Risers **4**, Manifolds
**2**, Umbilicals **3**. Press **Run screening estimate**.]

SURF prices the subsea system separately. It shows in the chart in the component colour
and it is *not* added into the total. If SURF were the only model that ran, the app would
not invent a total; the confidence would read "component only". Honest by design.

## 6. Under every result (1.5 min)

[Scroll to the bottom of the results.]

Three things sit under any result.

Basis year. Everything in the pool is in 2024 dollars. If I pick 2025 or 2026, the app
applies the CP30 index and tells me the factor it used.

Bid check. A bid comes in, I type the amount, and it tells me whether it falls inside,
above or below the range.

What-if. I change one number, say the capacity, and it reruns every model and shows the
difference model by model.

[Press **Download HTML report**.]

And all of this comes out as a one-page report you can drop into a gate package.

## 7. Models and Data pages (1.5 min)

[Open **Models**.]

Two reference pages to finish. On Models: one card per model, with the method and what it
needs. A routing tab, which says which models each project type can use, and the
exclusions. And a tab called Reported accuracy.

[Open the **Reported accuracy** tab. Don't read the numbers out.]

That tab has the figures we measured on the fifty-two projects with known cost, next to the
figures from David's brief, with notes on how the two compare. I'd rather not go through
them live; how you count makes a real difference, and I'd like David's read on it first.
It's all there for anyone who wants to look.

[Open **Data**.]

And Data: every table the app loaded, with live row counts and which model reads it.
Everything is traceable back to a file.

## 8. Close (30 s)

[Back to the **Estimator** page.]

So, what you've seen is the September package running as an app: a few inputs, models
waking up as you add detail, a number with a range, and the evidence behind it.

What's next is finishing the parity with David's code. A few of his files haven't reached
me yet, the SURF, OSBL, pipeline, LNG and offshore calculators. Once they do, those parts
match his code too.

That's it. Questions?

---

## If someone asks

**"Is this David's code running?"**
It's a rewrite of his models in our code, checked module by module against the files he
shared. The onshore test cases match to the digit. A few files are still to come.

**"Can I use it today?"**
You can open it with the link in the invite. It's a POC: a screening number, Class 5, not a
basis of estimate. Use it to get a first order of magnitude and the comparable projects.

**"What does the confidence mean?"**
How many models agreed. High means three or more within thirty percent of each other.
Low means only one model could run. "Component only" means we have a subsea cost but no
total.

**"Why was a model excluded?"**
Rules from the package: where a model is known to overshoot for a project type, it stays
out, and the app says so before you run.

**"How accurate is it?"**
The measured figures are on the Models page, Reported accuracy tab, next to the ones in
the brief. I'd like David's read on how we count before we quote a single number. Happy to
walk anyone through that tab afterwards.

**"Can it estimate X?"** (a project type not in the list)
The archetypes in the dropdown are the ones the package covers. Anything else, not yet.

**"Where did the data come from?"**
The September package: 503 past projects, about 600 equipment profiles, 857 cost chips,
and the cost indices. The Data page lists every table.
