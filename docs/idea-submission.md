# SIH 2026 idea submission — draft

**PS SIH26165 · Oil India Limited** · Owner: Member 1

Drafted to the standard SIH idea structure. **Replace with the official format the moment the
nodal officer confirms word limits and sections** — section boundaries here are a guess, the
content is not.

Every claim traces to the problem statement text, IOGP Report 459, or something verifiable in our
repository. Placeholders stay placeholders until the evaluation runs.

---

## Problem

Safety programmes have been getting better at preventing the wrong things. Over fifteen years,
non-fatal accidents in the US fell 51% while fatalities fell only 25.5% — the two lines diverged
because low-severity incidents and fatalities do not share causes. Roughly 20–25% of safety
reports carry genuine fatal potential.

Oil India collects unsafe act, unsafe condition, near-miss and incident reports through its HSSE
platform. Triage is manual and periodic — monthly or quarterly. The reports are free text, there
are thousands of them, and the ones describing situations that could have killed someone do not
look different from the ones describing a wet floor. The warning is in the pile; nobody has time
to find it.

## Proposed solution

A classification and ranking layer that sits downstream of the existing HSSE reporting pipeline
and reorders the reading queue. It never closes a report.

Each report passes three gates, applied in order:

1. **Hazard** — is a high-energy hazard present, in one of the eight IOGP Life-Saving Rule
   categories? Answers `yes`, `no`, or `insufficient_information`.
2. **Control** — was the barrier `absent`, `failed`, `present`, or `unclear`? A barrier that held
   stops the assessment: the situation was hazardous but controlled.
3. **Plausible variation** — would a small realistic change in timing or position have produced
   death or life-altering injury? Scored 1–5.

All three yes produces a SIF precursor. Every judgement carries the rule it was tagged to, the
barrier status, a severity, a confidence, the exact phrases that drove the decision, and a written
justification — so a safety officer can disagree with it in ten seconds.

Above the classification sits the part that turns judgements into decisions: a density ranking of
sites and activities by precursor **rate**, cross-tabulated by Life-Saving Rule and barrier status.
"Rig 4 produced eleven Energy Isolation precursors this quarter, nine on night shift" is a place
to send an audit, not a chart.

## Technical approach

- **Backend** — Python 3.11, FastAPI, Pydantic v2. Pydantic validates every model response, which
  makes the schema-failure rate a measured number rather than an unbounded risk.
- **Classification** — two classifiers behind one interface. A TF-IDF and logistic regression
  baseline, built and scored first, and a structured LLM call returning the full schema. The
  backend does not know which answered.
- **Storage** — managed Postgres. Four tables: sites, reports, append-only predictions carrying a
  model version, and gold labels carrying an annotator. Database constraints encode the rubric
  directly, so a prompt change cannot silently redefine what "precursor" means.
- **Aggregation** — plain parameterised SQL with GROUP BY. No embeddings and no clustering: the
  question is which sites are dangerous, not which reports are similar, and every team member can
  read the query aloud and say what it computes.
- **Multilingual** — Hindi, Hinglish and code-mixed reports are handled inside the classification
  prompt, with no separate translation stage.
- **Resilience** — an SQLite cache keyed on the report text and prompt version, plus a local
  fallback: if the API fails or exceeds a ten-second timeout, the baseline answers and the
  interface says "degraded mode — keyword baseline" in those words.
- **Frontend** — React, with three screens: a live analysis box on the landing page, a ranked
  report queue, and the density dashboard.

## Innovation and uniqueness

We do not claim novelty for applying NLP to safety text; that is the problem statement's own
suggestion and commercial products already do it. Four things are ours:

1. **A two-field auditable judgement.** Hazard and barrier status are recorded separately rather
   than collapsed into one risk score. This is what lets the system distinguish a real hazard where
   the barrier held — not a precursor — from an identical-sounding report where it did not, and it
   is what makes a disagreement legible instead of a matter of trust.
2. **A rubric revised by measurement, not by argument.** Two annotators labelled all 180 reports
   against a written, versioned rubric. Round one was independent and agreed 52.2% on precursor
   status, Cohen's kappa 0.083 — severity was the gate that split us, disagreeing by three or four
   points on 76 of the 180. So we rewrote that gate: the one-change rule stated first, the severity
   bands rewritten from adjectives into observable outcomes. Round two agreed 96.1%, kappa 0.922,
   but it was **not run independently, so we do not quote it as a ceiling** — it is evidence the
   revision worked, not a bound on the system. Claiming a ceiling would take a fresh independent
   pass, and we would rather report that number than one we cannot defend. 173 of the 180 reports
   are agreed; 7 remain open.
3. **Density aggregation by site, activity and barrier**, reported as a rate rather than a count.
   Raw counts penalise sites that report diligently, which is the opposite of the incentive a
   safety system should create. Groups below a minimum volume are shown but not ranked, so a site
   with one report is never presented as "100% risk".
4. **A tested degraded mode.** The offline fallback is wired early and covered by tests that drive
   the real failure path, not promised in a slide.

## Feasibility and viability

**Data honesty, stated upfront.** Our dataset is 150 synthetic reports we generated plus 30 real
OSHA Severe Injury Reports, which are public. **We have never had Oil India operational data and
we do not imply otherwise.** Two consequences we disclose rather than hide: the OSHA records
describe injuries that already occurred, which is a different population from near-misses, so they
serve only as a check that the classifier handles real writing nobody on the team wrote; and OSHA
narratives carry no site taxonomy, so the density dashboard runs on synthetic data only.

**What makes it feasible.** The whole system runs on free tiers with roughly 500 model calls
across development and demonstration — a build budget near ₹1,000. It requires no change to
existing reporting workflows because it sits downstream of them. The LLM path needs no training
data at all. The baseline fallback does train — on our own 180 labelled reports — so putting it in
front of an operator's vocabulary would mean re-labelling a comparable set in that vocabulary,
which is a labelling exercise rather than a data collection programme.

**Known limitations.** A site that under-reports cannot be ranked; rate-based ranking protects
against uneven honest reporting, not against silence. The rubric's severity thresholds are our own
calibration rather than a sourced standard, though they were reviewed by an EHS professional
outside the team. And we do not currently quote a human agreement ceiling: the round that was run
independently predates the rubric revision, and the round that scored 96.1% was not independent.
A fresh independent re-label of a ~40-report subset would settle it in a couple of hours; until
that runs, we claim no bound.

**Risks and mitigations.** Model output drifting between versions — every prediction row stores its
model version, and aggregates never mix versions. API unavailability — the local baseline answers
and says so. Annotator disagreement — if agreement falls below 70% the rubric is revised and the
affected reports re-labelled, because at that point the document is ambiguous, not the people. That
mitigation has already fired once, taking the rubric from v2.1 to v2.2.

## Impact and benefits

The operational change is triage latency: from a monthly or quarterly manual read to a ranked
queue available as reports arrive. The value is not that a machine reads faster — it is that the
scarce resource, a safety professional's attention, gets spent on the 20–25% of reports that carry
fatal potential rather than distributed evenly across everything.

Second-order benefits follow from the aggregation. Recurring barrier failures become visible at the
site and activity level, which converts one-off report handling into a pattern a manager can act
on. Because the reasoning is recorded per field, disagreements between the system and a safety
officer are themselves data about where the rubric is wrong.

**What we do not claim.** We do not prevent fatalities. We surface warnings earlier and more
consistently than a monthly manual read; people act.

## References

Cited by the problem statement:

- DEKRA — Martin & Black (2015), on serious injury and fatality precursors.
- Edison Electric Institute — SIF Precursor model.
- VelocityEHS (2024) — PSIF classifier.

External:

- IOGP Report 459 — Life-Saving Rules. Nine rules are defined; we use eight, excluding *Bypassing
  Safety Controls* because barrier defeat is what our second gate measures and including it as a
  hazard category would double-count the same signal.
- OSHA Severe Injury Reports — public dataset, used as a generalisation check on real narratives.

---

### Pre-submission checklist

- [ ] Official SIH format confirmed with the nodal officer; sections and word limits matched
- [ ] Every `[PLACEHOLDER]` replaced with a real evaluated number, or the sentence cut
- [ ] Data-honesty paragraph still present in Feasibility and not softened
- [ ] No innovation claim outside the four listed above
- [ ] No agreement number presented as a ceiling unless a fresh independent pass produced it
- [ ] No reference added that we have not read
- [ ] EHS reviewer's name recorded in rubric §9
