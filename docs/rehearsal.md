# Rehearsal drills

**Owner:** Member 1. Run these this week, before the build is finished — a team that can explain
the project can also build it, and the reverse is not true.

Three drills, in increasing difficulty: the stranger test, the random-person drill, and the
three-why chain from [hostile-qa.md](hostile-qa.md).

---

## 1. The stranger test

Find someone outside computer science — a friend from another branch, a family member, anyone who
has not heard you talk about this. Explain it in 90 seconds. Then ask them three questions.

**If they cannot answer all three, the explanation failed, not the listener.**

### The 90-second script (~200 words)

> Every workplace collects safety reports. Somebody nearly fell, a machine was left running while
> being cleaned, a truck reversed too fast. Thousands of them, written in whatever words the
> person had.
>
> Most are minor. But about one in four describes a situation where somebody could genuinely have
> died — and it does not look different on the page from the one about a wet floor.
>
> Right now a safety officer reads through them by hand, once a month. The dangerous ones are in
> there. Nobody has time to find them.
>
> So we built something that reads every report and asks three questions. Was there something
> present that could kill someone — electricity, a fall, a moving vehicle? Was the safety
> protection actually working at that moment? And if one small thing had gone differently — a
> second later, a step to the left — would someone be dead?
>
> If all three are yes, it flags it. And it shows you which words made it decide, so a human can
> disagree.
>
> Then it tells you which locations produce the most of these. Which is where you send someone
> to look.

### The three comprehension questions

1. **"What does the system actually decide?"**
   Looking for: whether a report describes a situation that could have killed someone. *Not*
   "whether an accident happened" or "how dangerous a workplace is".
2. **"Does it fix the problem, or does a person still do something?"**
   Looking for: a person still does everything. It changes what they read first.
3. **"Why not just count the accidents that already happened?"**
   Looking for: because the serious ones are rare, so by the time you have counted enough to see a
   pattern, people have already been hurt.

If they answer 1 and 2 but not 3, your problem section is too thin. If they cannot answer 1, start
over — that is the whole product.

---

## 2. The random-person drill

**The lead picks who answers, not the owner.** Rotate a member number 1–6 and a question; that
person answers alone, out loud, with no rescue from anyone.

This exists because judges do it. If only Member 2 can discuss the model, you have one person who
understands the project and five who are decoration — and it is obvious in about forty seconds.

### Procedure

1. Draw a question from [hostile-qa.md](hostile-qa.md), any section.
2. Draw a member number 1–6.
3. That member answers out loud. **Nobody else speaks.** Not to correct, not to add.
4. Compare against the model answer. Score 1–5:
   - **5** — answers the actual question, four sentences or fewer, concedes what should be conceded
   - **3** — correct but rambling, defensive, or answering a nearby easier question
   - **1** — hedged, invented a number, or used a banned phrase
5. Then three whys on whatever they said.
6. Anything under 4 goes on that member's study list.

Run twenty rounds. Twenty minutes. Do it twice before demo day.

### The banned-phrase buzzer

Anyone saying one of these loses the round instantly, whatever else they said:

> "it's a black box" · "our accuracy is X percent" · "it's 100% accurate" · "AI-powered" used
> instead of saying what it does · any claim that we *prevent* fatalities · **any specific number
> that has not been measured yet**

The last one matters most. Inventing a number under pressure is the single easiest way to lose a
panel, because the follow-up question is always "how did you measure that".

---

## 3. Per-member cheat sheets

One page each. Everyone knows the shared five in
[hostile-qa.md](hostile-qa.md); this is what *you specifically* will be asked, and what everyone
must be able to explain regardless of role.

### What all six must be able to explain

Not optional, not role-specific. If any member cannot do these in three sentences, fix it before
anything else.

| | Three-sentence answer |
|---|---|
| **Why not accuracy** | About one in four reports is serious, so answering "no" to everything scores 78%. That number would look good and mean nothing. We report F1 and PR-AUC. |
| **Precision vs recall** | Precision: of what we flagged, how much was real. Recall: of what was real, how much we caught. We chose recall deliberately — missing a fatal precursor costs a life, a false alarm costs twenty minutes. |
| **Why we don't quote a ceiling** | Our first round was independent and agreed 52%, kappa 0.083 — severity was the gate that split us, so we rewrote it. The second round agreed 96% but was not run independently, so it is evidence the revision worked, not a bound on the system. A ceiling needs a fresh independent pass, and we would rather report that number than one we cannot defend. |
| **Kappa vs raw agreement** | Kappa subtracts the agreement you would expect from chance alone. At a 22% positive rate, two people guessing still agree often, so raw agreement flatters us. |
| **When it is wrong** | It never closes a report — it reorders the reading queue, so a low-ranked report is still read. Every judgement is logged with the gate and the phrases. A human overrules it. |
| **Where the data came from** | 150 synthetic reports we wrote, plus 30 real public OSHA narratives. We never had Oil India data and we say so before being asked. |

---

### Member 1 — Lead / Product

**You own:** the rubric, the pitch, the honesty line.

- *"Who decided what counts as serious?"* → We did, in writing, before labelling. The gate
  structure is from the PS's own cited sources and IOGP 459; the severity thresholds are our
  calibration and the rubric says so. An EHS professional outside the team reviewed it.
- *"Why can't ChatGPT do this?"* → It can classify one report. The product is a consistent schema
  across thousands, a ranked aggregation, and a measured agreement number.
- *"Why do 20–25% of reports carry fatal potential?"* → It is the problem statement's own figure,
  and the divergence supports it: non-fatal fell 51% while fatalities fell 25.5%. Shared causes
  would have meant both fell together.
- *"What would you do with six more months?"* → Re-label a real operator's reports to see whether
  the rubric survives contact with their vocabulary. Everything else is downstream of that.

### Member 2 — ML

**You own:** both classifiers, the prompt, the schema.

- *Understanding vs pattern-matching* → Sophisticated pattern-matching, and that is enough for a
  reading-comprehension task. Do not overclaim.
- *Why not fine-tune* → 180 examples would overfit; prompting wins at this scale and keeps the
  per-gate reasoning inspectable.
- *What TF-IDF actually does* → Counts weighted words, no meaning. That is exactly why the gap to
  the LLM is evidence rather than a benchmark.
- *On hallucination* → Schema-constrained by Pydantic, retry once, then the baseline answers and
  the rate is logged. Point at `/meta`.

### Member 3 — Data

**You own:** the dataset, the labelling, the evaluation.

- *"You wrote the reports and graded yourself."* → Concede it first. Then: intent labels
  discarded, two annotators against a written rubric we revised after measuring where it failed,
  a sixth of the set real OSHA text nobody here wrote.
- *Why hold out a test set* → Tuning against your test score fits the model to the answers, not
  the problem.
- *Why 150 and not 90* → At 22% positives, 90 leaves about six positives in a held-out split and
  one flipped prediction swings F1 by roughly eight points.
- *Why not rebalance to 50/50* → It flatters every model and convinces nobody experienced.

### Member 4 — Backend

**You own:** the API, the schema, the aggregation.

- *"What does the SQL aggregation actually compute, and why does it replace embeddings?"* → It
  counts reports per site, counts how many the current model called precursors, and divides.
  Embeddings cluster reports by wording; this ranks locations by how often their reports carry
  fatal potential — which is the decision an HSE manager makes.
- *Why rate and not count* → Raw counts punish sites that report honestly. Rate does not. Both are
  always shown.
- *Why the small-denominator guard* → A site with one report and one precursor is not 100% risk,
  it is noise. Under five reports we show the group but do not rank it.
- *Why append-only predictions* → So "every judgement is logged and reviewable" is a property of
  the schema rather than a promise.

### Member 5 — Frontend

**You own:** the three screens and what a judge actually sees.

- *Why the analyse box is on the landing page* → It is the first thing a judge wants to try, and
  burying it in a tab reads as hiding it.
- *Why show three gates instead of a risk score* → The auditable judgement is the point. A single
  score cannot be disagreed with; "hazard yes, barrier present" can.
- *What the degraded-mode banner means* → The API failed or timed out and a local keyword model
  answered. We show it in plain words rather than serving a worse answer silently.
- *Why greyed-out sites instead of hidden ones* → Hiding low-volume sites looks like
  cherry-picking. Showing them unranked shows we thought about it.

### Member 6 — DevOps / QA / Research

**You own:** deployment, tests, sources, and the tiebreak.

- *"Do you actually have tests?"* → Thirty-seven, no skips. They cover the contract, the retry,
  the fallback, the timeout, the cache, and the aggregation rules. Offer to open the file.
- *How the tiebreak worked* → Every disagreement is on a worksheet with the gate that split it
  recorded — one Gate 2, six Gate 3 — so a low agreement number tells us which gate to fix
  rather than forcing a full rewrite. What is *not* done is the adjudication: all seven are
  still open, and the gold set is the 173 rows the annotators already agreed on, with the
  disputed reports held out rather than decided.
- *What happens if the demo deployment is asleep* → We wake it before presenting; and if it is
  gone entirely the API still answers without a database, on seeded data, and says so.
- *Where the sources come from* → The PS's own citations plus IOGP Report 459. Anything we could
  not verify was cut — an earlier rubric draft had numeric energy thresholds that were removed for
  exactly that reason.

---

## Schedule

| When | Drill |
|---|---|
| This week, before more code | Stranger test — Member 1, then one other member separately |
| After the rubric red-team | Random-person drill, 20 rounds |
| Day before submission | Random-person drill again, plus a full run of the 5-minute script |
| Demo morning | One timed run, then Member 6's pre-demo checklist |

The stranger test comes first for a reason. If someone outside CS cannot follow the 90-second
version, the problem is not the panel — the explanation is not finished.
