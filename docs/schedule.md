# Schedule — 20 days to 20 September

**Answered:** 20 September 2026 is the **build deadline**, not the submission-form date.
That closes master plan §14. Owner: Member 1.

Today is **Tue 1 September**, day 1. **20 days inclusive.** The master plan assumed ~22, so we
are two days tighter than it was written for — not a crisis, but it removes the slack that plan
was quietly relying on.

**The one number that matters:** labelling is at **0 of 180 for both annotators** on day 1. The
plan budgets days 1–6 for it. Every day it slips costs a day at the far end, where there is
nothing left to cut except rehearsal — and an unrehearsed pitch loses to a rehearsed one
regardless of what the software does.

---

## Working backwards from the deadline

| Days | Dates | What must be true by the end |
|---|---|---|
| **1–6** | Tue 1 – Sun 6 Sep | **Labelling done.** Both annotators, all 180, independently. Kappa computed |
| **7–9** | Mon 7 – Wed 9 Sep | Baseline trained and scored. Prompt tuned on the dev split. Supabase live, reports loaded |
| **10–13** | Thu 10 – Sun 13 Sep | Real pipeline end to end. `batch_classify.py` run. Dashboard showing real numbers |
| **14–16** | Mon 14 – Wed 16 Sep | Frontend wired to real endpoints. Eval table produced. Deployed to Vercel + Render |
| **17–18** | Thu 17 – Fri 18 Sep | Offline fallback verified live. Full demo run-through. Hostile Q&A drill |
| **19** | Sat 19 Sep | **Buffer.** Deliberately empty |
| **20** | Sun 20 Sep | Final rehearsal, submission |

Day 19 is buffer on purpose. A twenty-day plan with no slack is a nineteen-day plan that fails on
day twenty.

---

## Day-by-day, week one

Week one is the only week with a hard dependency chain. After labelling lands, work parallelises.

| Day | Date | M1 (lead) | M3 (data) | M2 (ML) | M4 (backend) | M5 (frontend) | M6 (devops) |
|---|---|---|---|---|---|---|---|
| 1 | Tue 1 | **Label 45** · EHS review booked | **Label 45** | Prompt tuning setup | **Supabase live** | Screen 1 | Render deploy |
| 2 | Wed 2 | **Label 45** (→90) | **Label 45** (→90) | Prompt tuning | Load reports | Screen 1 | Vercel deploy |
| 3 | Thu 3 | — | **Early agreement check on the first 90** | Prompt tuning | Verify SQL path live | Screen 2 | Literature check |
| 4 | Fri 4 | **Label 45** (→135) | **Label 45** (→135) | — | — | Screen 2 | — |
| 5 | Sat 5 | **Label 45** (→180) | **Label 45** (→180) | — | — | Screen 3 | — |
| 6 | Sun 6 | Adjudicate with M6 | **Run `merge_labels.py`. Kappa.** | **Train baseline** | Batch classify | Screen 3 | **Tiebreak** |

**45 reports a day is the target.** At roughly a minute a report that is under an hour of focused
work — but only if the rubric is open beside you and you are not re-deciding settled questions.
`label_reports.py` saves after every row, so it splits across sittings without losing anything.

### The day-3 checkpoint is not optional

Run `merge_labels.py` on the **first 90** on day 3, before labelling the rest. If agreement is
below 70% there, the rubric is ambiguous and we revise the offending gate and re-label only its
reports — a one-day loss. Discovering the same thing on day 6 costs three days and lands in the
week we need for the pipeline.

This is the single highest-leverage checkpoint in the schedule.

---

## What is already done, and what it buys us

The backend, rubric, and all pitch documents are finished. That is worth being explicit about,
because it means **week two is integration rather than construction**:

- API, schema, aggregation, classifier seam, cache, fallback, 36 tests — done
- Rubric v2.1, red-team, demo script, hostile Q&A, submission draft, drills — done
- Dataset: 150 synthetic + 30 OSHA — done

So the 20 days are not 20 days of building. They are 6 days of labelling, then roughly 8 days of
wiring things that already exist to data that will exist, then 4 days of rehearsal and buffer.
That is a comfortable shape **if and only if labelling finishes on time.**

---

## Slip triggers, decided now rather than at 2am

Deciding these in advance is the difference between a considered cut and a panic.

| If, by… | Then |
|---|---|
| **End of day 2**, either annotator is under 60 labelled | Drop to 120 reports (100 synthetic + 20 OSHA). Say so in the pitch; a smaller set honestly labelled beats a larger one rushed |
| **Day 3**, agreement is under 70% | Revise only the splitting gate, re-label only its reports. Do not re-label all 180 |
| **End of day 6**, labelling is not finished | Labelling continues and everything else starts anyway on the partial gold set. Retrain when it completes |
| **Day 13**, the real pipeline is not end to end | Demo on seeded data and say so plainly. The API already degrades honestly — that is why it was built that way |
| **Day 16**, deployment is not live | Demo locally. Rehearsed and local beats deployed and unrehearsed |
| **Any point**, the eval numbers do not exist | The demo script already uses placeholders. Cut the numbers slide rather than inventing a figure |

**The rehearsal days are not cuttable.** If something has to give, it is scope, never rehearsal.
Member 1's stranger test and the random-person drill catch problems no amount of code review will.

---

## Standing risks

1. **Labelling is one person's evening away from slipping**, twice over, and it gates everything.
   Nothing else on this schedule has that property.
2. **The external EHS review** (rubric §9) has no date yet. It should happen this week — it is
   15 minutes, and it is the entire answer to *"who decided what counts as serious?"*
3. **Free-tier services sleep.** Render idles after inactivity, Supabase pauses after a week.
   Both need waking before any demo. Member 6's checklist covers it.
4. **The 25s LLM timeout** is untested under demo conditions. 25 seconds of silence on stage is
   worse than showing the fallback we plan to demo anyway.

---

## Changelog

- **1 Sep 2026** — created. Master plan §14 answered: 20 September is the build deadline. Schedule
  compressed from the plan's assumed ~22 days to 20, with day 19 held as buffer.
