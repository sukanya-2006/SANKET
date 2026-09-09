# SIF Precursor Classification Rubric v2.2

**Owner:** Member 1 · **Annotators:** Member 1 + Member 3, independently · **Tiebreak:** Member 6

Gates and field names are locked by [TECH_STACK.md](TECH_STACK.md) §Ground truth and
[NAMES.md](../NAMES.md). This document says how to *apply* them. It does not restructure them.

> **Label using this document only.** No discussion with the other annotator until both of you
> have finished. If the rubric does not answer your question, write the question in `notes` and
> make your best call — do not ask. The questions you write are the evidence that revises v2.2.

---

## 1. What we are detecting

A **SIF precursor** is a situation where a high-energy hazard was present and the control meant
to stop it was not doing its job — such that a small, realistic change in circumstance would have
killed someone or changed their life permanently.

**Judge the situation, not the outcome.** A worker who fell 6 m and walked away with a bruise is a
precursor. A worker who needed four stitches from a box knife is not, however much it bled.

---

## 2. What you record for every report

Use these exact names. They are the columns in `gold_labels` and the fields the classifier must
produce, so a synonym here becomes a bug three files away.

| Field | Values |
|---|---|
| `hazard_assessment` | `yes` · `no` · `insufficient_information` |
| `lsr_rule` | one of the eight rules below, or `none` |
| `control_status` | `absent` · `failed` · `present` · `unclear` (leave blank if Gate 1 is not `yes`) |
| `severity` | 1–5 |
| `is_sif_precursor` | true / false — **computed** from §6. See the warning below |
| `notes` | one line of rationale; **mandatory** for every `insufficient_information`, every `unclear`, and every call where you hesitated between severity 3 and 4 |
| `rubric_version` | `2.2` |

### `is_sif_precursor` is computed, not judged

In round one, one annotator typed this field by hand on **138 of 180 rows in a way that
contradicted their own three gate answers** — always resolving to "hazard yes and control failed,
therefore true", with severity ignored. The two annotators were not applying the same rule at all,
and the headline agreement number was measuring typing rather than the rubric.

Two safeguards, both mandatory:

1. **Use the tool.** `python label_reports.py --annotator <you>` computes this field from your
   three gate answers. It cannot get it wrong.
2. **If you label in a spreadsheet, validate before handing the file over:**
   `python label_reports.py --annotator <you> --validate` — it reports every row where the typed
   value disagrees with §6, with line numbers matching Excel.

A file that fails this check must not be merged. An invalid value raises no error downstream;
`merge_labels.py` simply reads it as a disagreement with the other annotator, so it silently
lowers the kappa we then quote on stage.

---

## 3. Gate 1 — Hazard

> Is a high-energy hazard present, in one of the eight IOGP Life-Saving Rule categories?

`no` or `insufficient_information` → **stop. Not a precursor.** Do not fill in Gate 2 or 3.

IOGP Report 459 defines nine rules. **We use eight.** *Bypassing Safety Controls* is deliberately
excluded, because barrier defeat is exactly what `control_status` measures at Gate 2 — carrying it
here as well would count the same signal twice. A bypassed control is recorded as
`control_status = absent`, with `lsr_rule` set to whatever hazard the control was protecting against.

| `lsr_rule` | Answer `yes` when the report involves… |
|---|---|
| `energy_isolation` | Work on or near equipment that should have been isolated and proven dead: electrical systems, stored pressure, stored mechanical or hydraulic energy, live process fluid |
| `work_at_height` | A person, tool, or material able to fall far enough to kill or maim — scaffolds, derricks, roofs, ladders, open edges, gratings, dropped objects from height |
| `lifting` | Cranes, hoists, rigging, slings, forklifts, suspended or swinging loads |
| `line_of_fire` | A person in the path of something moving, energised, or pressurised — vehicles, machinery, released pressure, breaking containment, recoiling lines |
| `confined_space` | Entry into a tank, vessel, pit, sewer, or any space with restricted egress or a potentially hazardous atmosphere |
| `hot_work` | Welding, cutting, grinding, or any ignition source where flammables may be present |
| `driving` | Operating a vehicle on site or public road, including passenger exposure |
| `permit_to_work` | Work that required an authorisation which was not raised, not valid, or not followed — used when no other category names the hazard better |

**One report, one rule.** If several apply, use this precedence — it exists so two annotators
reading the same multi-hazard report land on the same rule, which a shared "pick the worst one"
instruction does not guarantee:

> `confined_space` → `work_at_height` → `energy_isolation` → `line_of_fire` → `lifting` →
> `driving` → `hot_work` → `permit_to_work`

Override the precedence only when the narrative makes a lower rule clearly the thing that would
have caused the death, and say so in `notes`.

**Chemical hazards.** The eight rules contain no chemical category, and oil and gas work is full
of them. Resolve as follows:

- Released from a system that should have been isolated, drained, or depressurised first →
  `energy_isolation`.
- Released and the person was in its path, with no isolation failure described →
  `line_of_fire`.
- A splash or exposure with **no release from a system** — only a missing PPE item →
  Gate 1 is `no`. A missing PPE item never creates a hazard the narrative does not otherwise
  contain.

### Answer `no` when

The report describes only same-level slips and trips, manual handling and ergonomic strain, hand
tools, minor sharps, heat stress, housekeeping, or property damage with nobody exposed. These can
be genuine injuries. They are not what this system is for.

### Answer `insufficient_information` when

The text does not let you name a hazard category at all — "Employee was injured at the facility.
Hospitalized." This is a real, reportable state, **not** a soft `no`: these reports go to a human,
they are not dismissed. Target **under 10%** of reports. It is for text that genuinely does not
say what happened, not for cases you find difficult. If careful reading gets you to a confident
call, make the call.

---

## 4. Gate 2 — Control status

> Was there a control targeting the Gate 1 hazard, and was it doing its job at that moment?

`present` → **stop. Not a precursor.**

A **direct control** is a safeguard that (a) targets the Gate 1 hazard specifically, (b) works even
when a person makes a mistake, and (c) was verifiably in place at the time. A locked and proven
isolation. A rated fall-arrest system actually clipped to a rated anchor. A fitted interlocked
guard. A hard barricade. A trench protective system. A lift inside its load chart.

**These are not direct controls:** training, experience, toolbox talks, signage, hi-vis, pre-job
briefs, procedures on paper, a permit that was signed but not followed, "being careful", or PPE
that cannot stop the Gate 1 energy. A hard hat is not a control for an 8 m fall.

| Value | Choose it when |
|---|---|
| `absent` | No direct control existed, or one existed and was **not used, removed, bypassed, defeated, or disabled** — harness worn but not clipped; guard taken off; isolation never applied; no permit raised; interlock jumped |
| `failed` | A control was in place and **did not hold** — sling parted, anchor pulled out, shoring collapsed, brake failed, isolation was applied but the system was still live |
| `present` | A rated, targeted control **was in place and did its job**, and the event stayed inside the protection it gives. The narrative must say so — you may not infer it |
| `unclear` | A hazard is clearly present but the text does not say what the control was doing |

### `absent` versus `failed`

Ask **was it there and doing its job?** If the answer is no because nobody put it there or somebody
took it away, that is `absent`. If the answer is no because it was there and broke, that is
`failed`. This distinction is a dashboard axis, not bookkeeping: `energy_isolation × absent` is a
planning and supervision problem; `energy_isolation × failed` is an equipment problem. They get
different fixes.

### A person is not a control — with one exception

§4 says training, supervision and "being careful" are not direct controls. §7.4 says a crew that
recognised and controlled a hazard before exposure is `present`. Both are right, and the line
between them is **whether anyone was exposed**:

- The intervention happened **before exposure began** — a supervisor stops entry because the gas
  test lapsed, a crew halts on noticing a missing guard → `control_status = present`. The hazard
  was recognised and controlled. Not a precursor.
- Exposure **had already begun** and a person intervened, caught themselves, or was pulled clear
  → `control_status = absent` or `failed`, whichever the narrative supports. A last-second rescue
  is not a barrier; §5 explicitly tells you to remove it before scoring severity.

Self-rescue is never a control. A worker who falls and grabs a handrail was not protected by
anything — record what the barrier was doing, which is `absent` if nothing was in place.

### A control that stopped the event is `present`, even if it broke doing so

`failed` means the event was **not stopped**. A lanyard that arrested a fall and had to be scrapped
afterwards did its job: `present`. An anchor that pulled out and let the person hit the ground:
`failed`.

### `unclear` does not become `absent`

If the narrative is silent about controls, record `unclear`. Do **not** reason "the person got hurt,
so the control must have failed" — that is a conclusion the text does not support, and it would
convert every vague report into a precursor.

---

## 5. Gate 3 — Plausible variation, and severity

### The one-change rule

> Change **exactly one** thing. The timing by a few seconds, **or** the position by a metre,
> **or** remove one last-second intervention. Then score what happens.

**One change. Not two, not a chain.** This is the single most important sentence in the rubric,
because it is where round one fell apart: one annotator changed one thing, the other imagined a
sequence of unlucky events, and their severities diverged by three or four points on 76 of 180
reports. If you find yourself thinking "and then, if he had also…", stop — you have made a second
change. Score the version with one.

Ask it as a question with a yes/no answer: **"Name the one thing that would have to be different,
and say in one sentence how the person dies or is permanently injured."** If you cannot say it in
one sentence without a second "and if", the answer is not 5 or 4.

### The bands

Anchored to **observable outcomes**, not adjectives. "Life-altering" meant different things to
two careful people; "cannot return to the same job" does not.

| `severity` | Test — apply it literally |
|---|---|
| **5** | **Someone dies.** You can name the mechanism in one sentence, after one change. |
| **4** | **The person cannot return to the same job.** Amputation, loss of an eye, spinal cord injury, burn needing grafts, permanent restriction. Not "was badly hurt" — permanently unable. |
| **3** | **Off work, then back to the same job.** Fracture, laceration needing surgery, concussion. Full recovery expected, no permanent restriction. |
| **2** | **Seen by a doctor, back at work the same or next shift.** Stitches, sprain, minor burn. |
| **1** | **First aid from the site kit.** Nothing more. |

The line that decides the label sits between **3 and 4**, and it is one question:
**would this person be permanently unable to do the same job again?** Yes → 4 or 5. No → 3 or below.
If you are genuinely torn between 3 and 4, the honest answer is 3 — and say so in `notes`.

**Gate 3 passes when `severity` is 4 or 5.**

### Worked calibration

Apply these before you start. If your answer differs, re-read the one-change rule.

| Report | One change | Score | Why |
|---|---|---|---|
| Plank tipped at 8 m, he caught the handrail | remove the catch | **5** | One change; he falls 8 m; name the mechanism — head strike on grade |
| Bolt fell from waist height, someone nearby | move him under it | **1** | A bolt from waist height does not kill or maim |
| Sling parted, load dropped on an empty deck | move a person under the load | **5** | One change — position |
| Finger caught in a running conveyor, bruised | a moment later | **4** | Degloving or amputation; cannot return to the same job |
| Slipped on a wet floor, wrist fracture | none available that kills | **3** | Off work, then back. There is no one change that makes this fatal |
| Arc flash at 480 V, burns to the face | stand closer | **5** | One change — position |
| Vehicle rollover, seatbelt not worn | none needed | **5** | Already ejection-capable; actual outcome was spinal |

**An actual fatality, amputation, or permanent restriction in the report scores 5 or 4 by
definition.** Do not talk yourself down from an outcome that already happened.

**An actual fatality, amputation, or ICU admission in the report scores 4 or 5 by definition.**
Do not talk yourself down from an outcome that already happened.

**This is a rule about `severity`, not about Gate 1.** A death with no Life-Saving Rule hazard —
a fatal heart attack at a valve, say — is Gate 1 `no` with `severity` 5. The outcome was fatal;
the situation was not a precursor. §7.1 and this paragraph do not conflict: severity records how
bad the plausible variation is, and Gate 1 records whether a hazard was present at all.

Record `severity` for **every** report, including the ones that fail Gate 1 or 2. The queue sorts
on it, and it is the input to the severity MAE table.

---

## 6. The decision

| `hazard_assessment` | `control_status` | `severity` | `is_sif_precursor` |
|---|---|---|---|
| `yes` | `absent` or `failed` | 4 or 5 | **true** |
| `yes` | `absent` or `failed` | 1–3 | false |
| `yes` | `present` | any | false |
| `yes` | `unclear` | any | false — see below |
| `no` | — | — | false |
| `insufficient_information` | — | — | false |

### Why `unclear` does not produce a precursor

We chose recall over precision deliberately, so this looks like the wrong call. It is not, and the
reasoning needs to be sayable out loud:

Marking every `unclear` as a precursor would flag most vaguely-written high-hazard reports, push the
positive class far past the 20–25% the data actually carries, and make the ranking useless — the
dashboard would say every site is on fire. Recall is preserved a different way: **`severity` is
still recorded, so a severity-5 `unclear` report sits near the top of the queue and gets read.**
`is_sif_precursor = false` means "not confirmed as a precursor", never "closed" or "ignored". The
system never closes a report; it reorders the reading queue.

---

## 7. Standing decisions

Apply these consistently. They exist because two people reading the same sentence otherwise split.

1. **Outcome never decides the label.** It informs `severity` only. Gates 1 and 2 are about the
   situation.
2. **Controls are not inferred.** `present` requires the text to say the control worked. Silence is
   `unclear`, not `absent` and not `present`.
3. **Near-misses count fully.** No injury does not mean no precursor. A load swung over a crew and
   was set down safely is a precursor if Gates 1–3 pass.
4. **Positive safety observations** — "crew stopped the job when they noticed the missing guard" —
   are **not** precursors when the hazard was recognised and controlled before exposure. Record
   `hazard_assessment = yes`, `control_status = present`, and say so in `notes`.
5. **Work at height has no trigger height.** Judge whether the fall could kill or maim at Gate 3
   rather than looking for a number. **We have no sourced threshold and will not invent one.**
6. **Vehicle incidents on public roads** are in scope — `lsr_rule = driving`.
7. **`permit_to_work` is the fallback category**, not the first choice. Use it when the failure is
   the authorisation itself, or when no other rule names the hazard.
8. **Multiple people exposed** raises `severity` toward 5, never lowers it.
9. **Contractor or own-workforce makes no difference** to any gate. It is metadata, not evidence.
10. **Naming a hazard is not enough to clear Gate 1.** "Crane issue during lift" names a category
    but says nothing about what happened or what the controls were — that is
    `insufficient_information`, not `yes` with `control_status = unclear`.
11. **Label the hazard the text describes, whatever its tone.** Sarcasm, blame, and frustration are
    not evidence about the hazard. A report describing an ongoing practice rather than a single
    event is still labelled on that hazard.
12. **A detection-and-evacuation system that worked is `present`.** An alarm that sounded and a
    crew that got out is a barrier doing its job, even though the atmosphere or condition
    degraded to make it sound.
13. **Work the gates in order, top down.** Do not start from a control failure you noticed and
    reverse-engineer a hazard to justify it. If Gate 1 is `no`, stop — whatever the report says
    about PPE or procedure.

### Code-mixed reports

Some reports are in Hindi, Hinglish, or code-mixed English. **Label them by the same gates.** If you
can read the report well enough to name the hazard, do so; if you genuinely cannot, that is
`insufficient_information` and you must say "language" in `notes` — so we can tell a language
failure apart from a thin-narrative failure when we compute agreement.

---

## 8. Worked examples

| # | Report (abridged) | `hazard_assessment` / `lsr_rule` | `control_status` | `severity` | `is_sif_precursor` |
|---|---|---|---|---|---|
| 1 | Technician opened a pump starter panel to clear a fault; circuit not isolated, no lockout applied. | `yes` / `energy_isolation` | `absent` | 5 | **true** |
| 2 | Fitter on a 5 m scaffold with no guardrail fitted; harness worn but not clipped. Fell, fractured pelvis. | `yes` / `work_at_height` | `absent` | 4 | **true** |
| 3 | Fitter slipped on the scaffold; harness was clipped to a rated anchor and the fall arrest functioned. Unhurt. | `yes` / `work_at_height` | `present` | 4 | false |
| 4 | Crane load swung over the crew because taglines were not used. Set down without contact, nobody hurt. | `yes` / `lifting` | `absent` | 5 | **true** |
| 5 | Sling parted during a routine lift; load dropped onto an empty deck. | `yes` / `lifting` | `failed` | 5 | **true** |
| 6 | Worker slipped on a wet floor in the break room, fractured wrist. | `no` / `none` | — | 3 | false |
| 7 | Worker strained back lifting a 20 kg box; hospitalised overnight for observation. | `no` / `none` | — | 2 | false |
| 8 | "Employee was injured at the facility and taken to hospital." | `insufficient_information` / `none` | — | 2 | false |
| 9 | Two workers entered a storage tank to clean it. No gas test recorded, no attendant posted. | `yes` / `confined_space` | `absent` | 5 | **true** |
| 10 | Welding on a flare line; fire watch posted, area gas-tested and cleared, no incident. | `yes` / `hot_work` | `present` | 4 | false |
| 11 | Driver ejected during a rollover on the haul road; seatbelt not worn. Spinal injuries. | `yes` / `driving` | `absent` | 5 | **true** |
| 12 | "Crew reported hydraulic leak near the pump during shift handover." Nothing further. | `yes` / `line_of_fire` | `unclear` | 4 | false — flagged by severity, not by label |
| 16 | Caustic splash to the face while breaking a line; goggles available but not worn. | `yes` / `energy_isolation` | `absent` | 4 | **true** — line not drained before breaking (§3 chemical ruling) |
| 17 | Supervisor stopped entry after noticing the gas test had expired; entry rescheduled. | `yes` / `confined_space` | `present` | 5 | false — intervention before exposure (§4) |
| 18 | Worker suffered a fatal heart attack while operating a valve. | `no` / `none` | — | 5 | false — fatal outcome, no LSR hazard (§5) |
| 13 | Crew stopped work on noticing the conveyor guard was missing and raised it before starting. | `yes` / `energy_isolation` | `present` | 4 | false — positive observation, §7.4 |
| 14 | Worker struck his thumb with a hammer while framing; fracture. | `no` / `none` | — | 2 | false |
| 15 | Contractor began hydrojetting with no permit raised; area owner not informed. | `yes` / `permit_to_work` | `absent` | 4 | **true** |

Examples 3, 12, and 13 are the ones that separate reading from keyword-hunting. Expect the
disagreements to cluster there.

---

## 9. Sources, and what is ours

Being precise about this is a defence, not a disclaimer. The hostile question is
*"who decided what counts as serious?"* — and the answer is that we did, in writing, before we
labelled anything.

**Sourced.** The high-energy-hazard / direct-control structure of Gates 1 and 2 comes from the
precursor literature the problem statement itself cites — DEKRA (Martin & Black 2015), the EEI SIF
Precursor model, and VelocityEHS 2024. The eight hazard categories are IOGP Report 459
Life-Saving Rules; 459 defines nine and our exclusion of the ninth is explained in §3.

**Ours, and stated as ours.** The `severity` 1–5 anchors in §5, the `severity ≥ 4` threshold for
Gate 3, the decision that `unclear` does not produce a precursor (§6), and every standing decision
in §7 are this team's calibration choices. They are not quoted from any source and must never be
presented as if they were.

**Deliberately absent.** No energy thresholds in joules, volts, bar, or metres appear anywhere in
this rubric. An earlier draft carried them; they were removed because we could not verify them
against a source we actually hold. Gate 3 does that work instead.

**External review.** Before labelling starts, this rubric gets a 15-minute review from an
EHS or industrial-engineering contact outside the team. Record the reviewer's name and date here:

> Reviewed by: ________________  Date: __________  Changes made: ________________

---

## 10. Labelling protocol

1. **Independence.** Members 1 and 3 label all 180 reports — 150 synthetic, 30 OSHA — with no
   contact until both finish. Member 3 generated the synthetic reports without seeing this rubric;
   Member 1 wrote this rubric without seeing the reports.
2. **Batched, for an early signal.** First 90 by **day 3 (Thu 3 Sep)**, remainder by **day 5
   (Sat 5 Sep)** — pulled forward from the plan's day 4/6 because the build deadline is 20 Sep,
   two days tighter than the plan assumed. The early batch exists so a broken gate surfaces while
   there is still time to fix it. See [schedule.md](schedule.md).
3. **Tiebreak.** Member 6 adjudicates every disagreement and records **which gate split** — not
   just the final label. That column is the whole diagnostic.
4. **Agreement.** Member 3 computes raw agreement and Cohen's kappa (`cohen_kappa_score`).
   Report both: kappa subtracts the agreement chance alone would produce.
5. **If agreement is below 70%**, the rubric is ambiguous — not the annotators. Revise **only the
   gate that split**, bump to v2.1, and re-label **only the reports that turned on that gate**.
   Losing a day here is cheaper than building everything downstream on labels nobody trusts.
6. **Every label records `rubric_version`.** A label made under v2.0 and one made under v2.1 are
   not the same measurement.

Agreement is also the ceiling on every number we report afterwards. If two humans applying this
document agree 88% of the time, no classifier can honestly claim 95%.

---

## Changelog

- **v2.2** — revised after the first agreement check failed. Severity was the broken gate:
  annotators agreed on it **14.4%** of the time, splitting by three or four points on 76 of 180
  reports, and because Gate 3 keys on `severity >= 4` that fed straight into the label. Derived
  agreement on `is_sif_precursor` was **52.2%, Cohen's kappa 0.083**.

  Two causes, both addressed here rather than by adjudicating the disputed rows:

  1. **The plausible-variation instruction did not bound the number of changes.** One annotator
     changed one thing; the other imagined a chain. §5 now states the one-change rule first and
     gives a one-sentence test for it.
  2. **The bands were adjectives.** "Life-altering" calibrated differently for two careful
     people. The bands are now observable outcomes, the 3/4 boundary is a single question —
     *can this person return to the same job?* — and seven worked calibration examples are
     included to be read before labelling starts.

  §2 additionally makes explicit that `is_sif_precursor` is computed, never typed, after one
  annotator's typed values contradicted their own gate answers on 138 of 180 rows.

  **Measured on the final pair, 9 Sep**, from the raw annotator rows now in the `gold_labels`
  table rather than from a merged CSV. Run `python agreement.py` to reproduce.

  | | round one | final pair |
  |---|---|---|
  | `is_sif_precursor` | 52.2%, kappa 0.083 | **96.1%, kappa 0.922** |
  | `severity` exact | 14.4% | 60.0%, kappa 0.452 |
  | `severity` within one band | split by 3-4 points on 76 of 180 | **100% — 180 of 180** |
  | Gate 1 `hazard_assessment` | — | 100%, kappa 1.000 |
  | Gate 2 `control_status` | — | 98.8%, kappa 0.978 |

  The revision worked, and it worked on the gate it was aimed at. Severity now never disagrees
  by more than one band on any report in the set. Six of the seven remaining headline
  disagreements straddle the 3/4 line, which is the boundary the label is defined on — that is
  the residue you would expect from two careful people, not a broken instruction.

  Read Gate 1's perfect agreement with the enrichment caveat: every synthetic report was
  generated centred on a hazard category, so both annotators answered `yes` almost every time.
  A kappa of 1.000 there reflects how the set was built.

  Three figures have circulated for this pair and they are all real measurements of different
  things. Quote the first and say which it is:

  | what is compared | result |
  |---|---|
  | `is_sif_precursor` alone — the label the product predicts | 96.1%, kappa 0.922 |
  | all four fields matching exactly | 58.3% |
  | the three gates matching exactly, ignoring `lsr_rule` | 59.4% |

  Note these are computed after `load_gold_labels.py` derives `is_sif_precursor` from the gates
  instead of reading the annotators' typed column, per §2. That changed the disagreement set in
  both directions: report 56 stopped being a disagreement, and 51 and 96 became one where a
  typed value had been masking a genuine Gate 3 split. **Open tiebreaks: 10, 20, 51, 60, 96,
  139, 149.**

  > **STILL TO BE ANSWERED BY MEMBER 1 — the one thing no script can check.**
  > Did akanksha and sukanya each label all 180 reports without seeing the other's file, and
  > was neither file edited to match afterwards? Independent re-labelling against a revised
  > rubric gives a ceiling. Adjudication into both files does not, however similar the numbers
  > look. `agreement.py` cannot tell the two apart and neither can anything else.
  > **Until this is answered, 0.922 is not quotable as a ceiling.**

- **v2.1** — applied the three defects found by the [rubric red-team](red-team-reports.md) before
  labelling began, so no re-labelling is required. Added a chemical-hazard ruling (the eight IOGP
  categories contain none, and a caustic splash previously had four defensible answers); added an
  explicit precedence order for multi-hazard reports; resolved the §4 / §7.4 conflict on human
  intervention with the before-or-after-exposure line, which split two of the fifteen adversarial
  cases; clarified that a control which stopped the event is `present` even if damaged; and made
  explicit that §5's fatality rule governs `severity` only, never Gate 1. Four standing decisions
  added covering thin-but-named hazards, adversarial tone, working detection systems, and gate
  order. **No gate was restructured.**
- **v2.0** — rebuilt against the locked three gates. Gate 1 is now `yes`/`no`/
  `insufficient_information` over the eight IOGP categories, replacing v1.0's nine-source energy
  wheel. Gate 2 is now four-valued (`absent`/`failed`/`present`/`unclear`), replacing a boolean;
  `present` stops the assessment and `unclear` no longer collapses into "control failed". Gate 3
  now carries a 1–5 severity scale, needed for the severity MAE table and the queue ordering.
  All unsourced numeric energy thresholds removed. Field names aligned to NAMES.md. Revision
  protocol narrowed from "re-label all 180" to "re-label the reports that turned on the offending
  gate".
- **v1.0** — superseded. Built before the master plan; used an energy-wheel taxonomy, a boolean
  Gate 2, no severity scale, and carried numeric thresholds we could not source.
