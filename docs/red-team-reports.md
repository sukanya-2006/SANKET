# Rubric red-team — 15 reports engineered to split the gates

**Purpose:** break [rubric v2.0](rubric.md) before it costs five days of labelling, not after.
**Owner:** Member 1. **Consumer:** Member 3, who folds these into the dataset.

The gates are **locked**. Nothing here restructures them. Every proposal below is an addition to
§7 Standing decisions, and none of it enters the rubric unless the day-4 agreement check fails —
at which point these are the pre-written answers rather than a panicked rewrite.

Each report is written to be genuinely ambiguous under the current wording. If you read one and
feel certain, note which gate you were certain about; if Member 3 felt equally certain the other
way, that is the finding.

---

## 1. Barrier held, but damaged

> Worker fell from the third-level platform. His lanyard arrested the fall, but the anchor point
> was visibly bent afterwards and had to be cut out and replaced.

Gate 1 `yes` / `work_at_height`. Gate 3 severity 5.
**Gate 2 splits.** The control did its job — that reads `present`, which stops the assessment.
It also deformed past reuse, which reads `failed`. Rubric §4 defines `failed` as "did not hold",
and this one held; but an annotator who reads "failed" as "was damaged" flips the whole label.

**Split point: Gate 2, `present` vs `failed`.**

---

## 2. Saved by the person, not the system

> A scaffolder stepped onto an unplanked bay and dropped through, catching the transom with both
> arms and pulling himself back up. He was not wearing a harness.

Gate 1 `yes` / `work_at_height`. Gate 2 `absent` — no harness.
**Gate 3 splits.** Rubric §5 says to remove the last-second intervention, which makes this a fall
through a scaffold bay: severity 5. But the phrase "caught the transom" reads to some annotators
as a control that worked, pulling them toward a lower severity or even Gate 2 `present`.

**Split point: Gate 3, and secondarily Gate 2.** This is the single most important case in the
set, because it tests whether the plausible-variation instruction is actually being applied.

---

## 3. Investigation ongoing

> Operator received an electric shock while working near the distribution panel. Investigation
> ongoing.

Gate 1 `yes` / `energy_isolation`. Gate 3 severity 4–5.
**Gate 2 splits.** The narrative says nothing about isolation, which is textbook `unclear` under
§4. But an annotator reasoning "he was shocked, so it clearly was not isolated" writes `absent` —
which is exactly the inference §4 forbids, and it flips `is_sif_precursor` from false to true.

**Split point: Gate 2, `unclear` vs `absent`.** Expect this pattern across many OSHA narratives.

---

## 4. The detector worked

> The gas detector alarmed during tank cleaning and the crew evacuated immediately. Entry had been
> permitted that morning.

Gate 1 `yes` / `confined_space`. Gate 3 severity 5.
**Gate 2 splits three ways.** `present` — the detector and permit both functioned. `failed` — the
atmosphere went bad inside a permitted entry, so something upstream did not hold. `unclear` —
we are not told whether ventilation was running.

**Split point: Gate 2, all four values reachable.**

---

## 5. Two hazards, one report

> While welding on a pipe rack four metres up, the fitter's harness was not clipped and no fire
> watch was posted.

Gate 2 `absent` either way. Gate 3 severity 5 either way. `is_sif_precursor` is **true** on both
readings — but the `lsr_rule` differs, which silently corrupts the dashboard's rule ranking even
though the headline label agrees.

**Split point: Gate 1, `work_at_height` vs `hot_work`.** Agreement on `is_sif_precursor` will hide
this; only per-field agreement catches it.

---

## 6. Four categories, one event

> A forklift struck a scaffold leg. A worker on the platform was thrown against the guardrail but
> was not injured.

`driving`, `lifting`, `line_of_fire`, and `work_at_height` are all defensible. §3 says pick the
one carrying the greatest potential to kill and name the tie-break in notes — which is guidance,
not a rule, so four annotators could produce four answers.

**Split point: Gate 1, four-way.**

---

## 7. Chemical splash — a category that does not exist

> A worker sustained a caustic splash to the face while breaking a line. Goggles were available on
> the rack but he was not wearing them.

**This one found a real gap.** The eight IOGP rules we use contain no chemical category. An
annotator must either force it into `line_of_fire` (person in the path of a released substance),
`energy_isolation` (line not drained or isolated before breaking), `permit_to_work` (fallback), or
answer Gate 1 `no` — which throws away a genuine SIF hazard.

**Split point: Gate 1, and the rubric currently gives no answer.** Fix this before labelling
regardless of the agreement number.

---

## 8. PPE only, low hazard

> Employee cut his hand on sheet metal while deburring. Cut-resistant gloves were not worn.

Gate 1 should be `no` — §3 excludes hand tools and minor sharps. But "gloves not worn" pattern-
matches to a control failure, and an annotator working bottom-up from Gate 2 will manufacture a
Gate 1 `yes` to justify it.

**Split point: Gate 1, `no` vs a forced `line_of_fire`.**

---

## 9. The pure one-liner

> Near miss reported at Rig 7.

`insufficient_information`, unanimously — this one is in the set as a consistency check, not a
trap. If annotators disagree here, the problem is attention, not the rubric.

**Split point: none expected.**

---

## 10. The one-liner that names a hazard

> Crane issue during lift.

Five words, under any reasonable thinness bar, so §3 says `insufficient_information`. But it
plainly names a hazard category, so an annotator may answer `yes` / `lifting` with
`control_status = unclear`.

**Split point: Gate 1, `insufficient_information` vs `yes`.** The rubric does not say whether
naming a hazard is enough to clear Gate 1 when nothing else is known.

---

## 11. Positive observation

> A supervisor stopped the crew from entering the vessel after noticing the gas test had expired.
> Entry was rescheduled for the afternoon.

§7.4 says a recognised-and-controlled hazard is `present` and not a precursor.
**But it splits anyway.** "Gas test had expired" is a control that lapsed — `absent` — and the
supervisor is a person, not a direct control under §4. An annotator following §4 strictly reaches
`absent`; one following §7.4 reaches `present`.

**Split point: Gate 2, and §4 and §7.4 genuinely conflict here.**

---

## 12. Adversarial tone

> Another day, another genius decides the guard is optional. Nobody died, so I suppose that counts
> as a win.

Gate 1 `yes` / `energy_isolation` — a removed guard. Gate 2 `absent`. Gate 3 severity 4.
**Splits on whether an event occurred at all.** The sarcasm describes a practice rather than an
incident, and it is not clear anyone was exposed. Some annotators will mark
`insufficient_information` because no event is described; others will label the hazard.

**Split point: Gate 1, plus a risk that annotators penalise tone rather than assess content.**

---

## 13. Code-mixed — Hinglish

> Height pe kaam kar rahe the, harness pehna tha but hook nahi lagaya. Neeche gir sakta tha.
>
> *(Working at height; harness was worn but the hook was not attached. He could have fallen.)*

Gate 1 `yes` / `work_at_height`. Gate 2 `absent` — worn but not clipped, which §4 lists
explicitly. Gate 3 severity 5. Clean **true** once read.

**Split point: language comprehension, not judgement.** §7 requires "language" in notes if you
cannot read it, so a disagreement here is diagnosable rather than mysterious.

---

## 14. Code-mixed, and a supervisor intervened

> Tanker driver ne seatbelt nahi pehna tha aur speed bhi zyada thi. Supervisor ne dekh kar turant
> roka.
>
> *(Tanker driver was not wearing a seatbelt and was over-speeding. The supervisor saw it and
> stopped him immediately.)*

Gate 1 `yes` / `driving`. Gate 3 severity 5.
**Gate 2 splits**, the same conflict as #11: `absent` because no seatbelt, or `present` because
it was caught and stopped. Two of the fifteen splitting on the same conflict is the signal that
this is a rubric hole, not annotator noise.

**Split point: Gate 2, `absent` vs `present`.**

---

## 15. A real fatality that is not a precursor

> A worker suffered a fatal heart attack while operating a valve in the process area.

Gate 1 `no` — no Life-Saving Rule hazard. §7.1 says the outcome never decides the label.
**But §5 says an actual fatality scores 4 or 5 by definition**, and an annotator who scores
severity 5 will feel enormous pull to answer Gate 1 `yes`.

**Split point: Gate 1, and §5 and §7.1 appear to contradict each other.**

---

## Summary table

| # | Type | Expected split point | Proposed clarifying sentence for §7 |
|---|---|---|---|
| 1 | Barrier held but damaged | Gate 2 `present` vs `failed` | A control that stopped the event is `present` even if it was damaged doing so; `failed` means the event was not stopped. |
| 2 | Self-rescue | Gate 3, and Gate 2 | A person catching, grabbing, or recovering themselves is not a control. Remove it and score the outcome without it. |
| 3 | Investigation ongoing | Gate 2 `unclear` vs `absent` | *(already §4)* — reinforce: an injury occurring is not evidence about the control. If controls are not described, the answer is `unclear`. |
| 4 | Detector alarmed | Gate 2, four-way | When a detection-and-evacuation system works as designed, `control_status` is `present` even though the atmosphere degraded. |
| 5 | Height + hot work | Gate 1 rule choice | With two hazards, tag the rule matching the energy that would cause the death, not the task being performed. |
| 6 | Four-category collision | Gate 1, four-way | Order of precedence when several rules apply: `confined_space` → `work_at_height` → `energy_isolation` → `line_of_fire` → `lifting` → `driving` → `hot_work` → `permit_to_work`. |
| 7 | Chemical splash | **Gate 1 — no category exists** | Chemical release from a system is `energy_isolation` if the line was not isolated or drained, otherwise `line_of_fire`. A splash with no release from a system and only a PPE gap is Gate 1 `no`. |
| 8 | PPE-only, low hazard | Gate 1 forced `yes` | Work the gates in order. A missing PPE item never creates a Gate 1 hazard that the narrative does not otherwise contain. |
| 9 | Pure one-liner | none expected | — |
| 10 | One-liner naming a hazard | Gate 1 `insufficient_information` vs `yes` | Naming a hazard is not enough to clear Gate 1. If the text does not say what happened or what the controls were, it is `insufficient_information`. |
| 11 | Positive observation | Gate 2 `absent` vs `present` | A person intervening before exposure counts as `present` for Gate 2 only when the intervention happened *before* anyone was exposed. If exposure had already begun, the lapsed control is `absent`. |
| 12 | Adversarial tone | Gate 1 event vs practice | Label the hazard the text describes, whatever its tone. A report describing an ongoing practice rather than a single event is still labelled on that hazard. |
| 13 | Hinglish | comprehension only | *(already §7)* — no change. |
| 14 | Hinglish + intervention | Gate 2, same as #11 | Covered by the #11 ruling. |
| 15 | Fatality, no LSR hazard | Gate 1, §5 vs §7.1 | §5's "a fatality scores 4 or 5" applies to `severity` only, and only once Gate 1 has answered `yes`. A death with no Life-Saving Rule hazard is Gate 1 `no`. |

---

## Three findings that should change the rubric before labelling, not after

Most of the table is contingency. These three are defects now:

1. **#7 — there is no chemical category.** Eight IOGP rules cover no chemical hazard, and oil and
   gas operations are full of them. Without a ruling, annotators will scatter across four
   different answers on every chemical report in the set.
2. **#11 and #14 — §4 and §7.4 contradict each other** on human intervention. Two of fifteen
   reports split on the same conflict; in a 180-report set that is not noise.
3. **#15 — §5 and §7.1 appear to contradict each other** on fatalities. The rule is coherent as
   written, but it reads as a contradiction, and an annotator resolving it under time pressure
   will resolve it inconsistently.

Fixing these three costs an hour. Discovering them through a failed kappa costs a day.

---

## Hand-off to Member 3

These fifteen go into the dataset as-is, marked as adversarial so they can be analysed separately.
They are deliberately harder than the population, so **do not read the agreement rate on these
fifteen as the project's agreement rate** — report it separately if you report it at all.
