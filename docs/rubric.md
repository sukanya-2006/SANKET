# SIF Precursor Classification Rubric v1.0

**Owner:** Member 1 · **Status:** Phase 1 deliverable · **Used by:** Member 1 + Member 3 (independent labeling, Phase 2)

> Label using **this document only**. Do not discuss cases with the other annotator until both of you
> have finished all 180 reports. Disagreements go to Member 6 (tiebreaker).

---

## 1. What we are detecting

A **SIF precursor** is a situation where a *high-energy hazard* was present and a *direct control* was
absent, ineffective, or bypassed — such that a **realistic small change in circumstance** would have
produced a fatality or a life-altering injury.

The key move: **judge the situation, not the outcome.** A worker who fell 6 m onto concrete and walked
away with a bruise is still a SIF precursor. A worker who cut a finger on a box knife and needed four
stitches is not, no matter how much it bled.

---

## 2. The three gates

Apply the gates **in order**. A report is a **SIF PRECURSOR** only if **all three are YES**.

### Gate 1 — High-Energy Present

> Was a hazardous energy source of serious magnitude present in the work situation?

Use the energy-source list. The rough threshold is **1,500 foot-pounds** (~2,000 J) — about the energy
of a 250 kg object at rest 60 cm above you, or a person falling more than 1.2 m.

| Energy source | Counts as high-energy when… |
|---|---|
| **Gravity** | Fall of person >1.2 m; any dropped/suspended/falling object >~7 kg from >1.5 m; collapse of structure, trench, or stacked material |
| **Motion** | Vehicle or mobile equipment moving >5 km/h; person in the path of moving equipment; heavy swinging or rolling load |
| **Mechanical** | Rotating/reciprocating machinery, conveyors, augers, presses; stored spring or hydraulic-arm energy |
| **Electrical** | >50 V AC exposure, any arc-flash-capable panel, overhead or buried power line contact |
| **Pressure** | Pressurised gas/liquid >~7 bar, steam, hydraulic lines, pressure vessels, uncontrolled release |
| **Temperature** | Surfaces/liquids >60 °C, molten material, open flame, fire, cryogenic contact |
| **Chemical** | Toxic-by-inhalation, corrosive, flammable, or asphyxiant atmosphere (incl. oxygen deficiency) |
| **Biological** | Exposure to a pathogen with serious-illness potential |
| **Radiation** | Industrial radiography sources, high-power laser |

**NO** if the only energies present are hand tools, low-height slips/trips on the same level, manual
material handling, ergonomic strain, or minor sharps. Those may be real injuries — they are not
SIF precursors.

*Uncertain?* If the narrative does not let you name a specific energy source, Gate 1 is **NO**.

---

### Gate 2 — Direct Control Absent, Ineffective, or Bypassed

> Was there a **direct control** in place, and was it actually doing its job at the moment of the event?

A **direct control** is a safeguard that is (a) specifically targeted at the high-energy hazard from
Gate 1, (b) effective on its own even when a person makes a mistake, and (c) verifiably in place at
the time. Examples: a locked-out and verified isolation, a rated fall-arrest system that is actually
clipped in, a machine guard that is fitted and interlocked, a hard physical barricade, a rated
crane/rigging setup within its limits, a competent-person-designed trench protective system.

**Not** direct controls: training, toolbox talks, experience, warning signs, hi-vis clothing, "being
careful", pre-job briefs, procedures on paper, permits that were signed but not followed, or PPE that
does not stop the Gate 1 energy (hard hats and gloves do not stop a 6 m fall or 11 kV).

Gate 2 is **YES** (control failed) when the narrative shows any of:

- No direct control existed for that energy.
- A control existed but was **removed, bypassed, defeated, or disabled** (guard off, interlock jumped,
  lock cut, alarm muted).
- A control existed but was **not used** (harness worn but not clipped; LOTO not applied; barricade
  not set).
- A control was **present but inadequate or failed** (wrong-rated sling, un-shored trench, isolation
  not verified de-energised, anchor point failed).

Gate 2 is **NO** when a rated, targeted control was in place and functioning, and the event stayed
inside the protection it provides (e.g. worker fell but was arrested by a correctly rigged harness at
a correct anchor — *if* the narrative says so explicitly).

**Cross-check against the IOGP Life-Saving Rules.** IOGP Report 459 defines nine rules; **we use
eight**. "Bypassing Safety Controls" is deliberately excluded — barrier defeat is precisely what
Gate 2 measures, so carrying it as a hazard category as well would double-count the same signal.
A bypassed control is recorded as Gate 2 = YES with `lsr = none`.

If the narrative shows a breach of any of these eight, Gate 2 is almost always YES. Record which
rule in the `lsr` field:

1. **Confined Space** — entering without authorisation / gas test
2. **Driving** — seatbelt, speed, fitness, distraction
3. **Energy Isolation** — verified isolation before work
4. **Hot Work** — control of flammables and ignition sources
5. **Line of Fire** — position relative to moving, energised, or pressurised things
6. **Safe Mechanical Lifting** — planned and rigged lifts, no load overhead
7. **Work Authorisation** — valid permit, understood and followed
8. **Working at Height** — protection against falls

---

### Gate 3 — Serious Injury Plausible

> If one small, realistic thing had gone differently, would this have killed someone or
> changed their life permanently?

Ask: **shift the timing by a few seconds, or the position by a metre — what happens?**

Gate 3 is **YES** if that shifted version produces death, amputation, permanent disability, severe burn,
blindness, spinal or serious head injury, or admission to intensive care.

Constrain yourself to **plausible** changes, not imaginative ones. "The scaffold plank flipped and he
caught the rail" → had he not caught it, an 8 m fall — **YES**. "A bolt fell from a shelf at waist
height and there happened to be a person nearby" → no realistic version of this kills anyone — **NO**.

Gate 3 is **YES by default** for any *actual* fatality, amputation, or hospitalisation in the report.

---

## 3. Deciding the label

| Gate 1 | Gate 2 | Gate 3 | Label |
|---|---|---|---|
| YES | YES | YES | **SIF_PRECURSOR** |
| NO | — | — | **NOT_SIF** |
| — | NO | — | **NOT_SIF** |
| — | — | NO | **NOT_SIF** |
| Narrative too thin to judge a gate | | | **UNCLEAR** |

Use **UNCLEAR** sparingly — target under 10% of reports. It is for narratives that genuinely do not
say what happened ("Employee was injured at facility. Hospitalized."), not for cases you find hard.
If you can make a confident judgement by reading carefully, make it.

**Also record for every report:**

- `energy_source` — the single dominant Gate 1 energy (or `none`)
- `lsr` — the IOGP Life-Saving Rule breached (or `none`)
- `notes` — one line of rationale; mandatory for `UNCLEAR` and for any close call

---

## 4. Standing decisions (apply consistently)

1. **Outcome does not decide the label.** Severity of the actual injury informs Gate 3 but never
   overrides Gates 1 and 2.
2. **Absence of evidence is evidence of absence for controls.** OSHA narratives rarely mention
   controls that worked. If a high-energy event reached a person, the direct control did not hold —
   Gate 2 is YES unless the narrative explicitly says a control functioned.
3. **One report, one label.** If a narrative describes several hazards, label on the most severe one.
4. **Motor-vehicle incidents on public roads** still count if Gate 1 motion is met — record LSR
   *Driving*.
5. **Heat stress, repetitive strain, and slips on the same level** are Gate 1 NO.
6. **Falls between 1.2 m and 1.8 m** are Gate 1 YES — do not require the OSHA 1.8 m trigger height.
7. **Struck-by a powered hand tool** (nail gun, grinder wheel burst) is Gate 1 YES via mechanical.

---

## 5. Worked examples

| # | Narrative (abridged) | G1 | G2 | G3 | Label | Why |
|---|---|---|---|---|---|---|
| 1 | Worker on 5 m scaffold, no guardrail installed, stepped back and fell to grade. Fractured pelvis. | Y (gravity) | Y (WAH — no fall protection) | Y | **SIF_PRECURSOR** | Textbook |
| 2 | Worker cleaning conveyor while running; sleeve caught in pinch point; finger amputated. | Y (mechanical) | Y (Energy Isolation — no LOTO) | Y | **SIF_PRECURSOR** | Amputation → G3 by default |
| 3 | Worker slipped on wet floor in break room, fractured wrist. | N | — | — | **NOT_SIF** | Same-level slip, no high energy |
| 4 | Worker lifting 20 kg box, strained lower back, hospitalised for observation. | N | — | — | **NOT_SIF** | Ergonomic; hospitalisation alone is not SIF |
| 5 | Crane load swung over crew during lift; taglines not used; load set down without contact. | Y (motion/gravity) | Y (Lifting — load overhead) | Y | **SIF_PRECURSOR** | No injury; still a precursor |
| 6 | Electrician opened 480 V panel to troubleshoot, arc flash, second-degree burns to face. | Y (electrical) | Y (Energy Isolation) | Y | **SIF_PRECURSOR** | |
| 7 | Worker fell 4 m from steel; harness and lanyard arrested the fall at a rated anchor; no injury. | Y (gravity) | **N** (control held) | Y | **NOT_SIF** | Gate 2 closes it — control worked as designed |
| 8 | Employee was injured and taken to hospital. No further detail. | ? | ? | ? | **UNCLEAR** | Narrative too thin |
| 9 | Worker in 2.5 m unshored trench; wall sloughed, buried to waist; freed by crew. | Y (gravity) | Y (no protective system) | Y | **SIF_PRECURSOR** | |
| 10 | Worker struck thumb with hammer, fracture. | N | — | — | **NOT_SIF** | Hand-tool energy |

---

## 6. Revision protocol

Member 3 computes raw agreement and Cohen's kappa after both annotators finish. **If kappa < 0.70**,
the two annotators review disagreement patterns *without* re-litigating individual cases, Member 1
revises this rubric — bumping the version and appending to §4 — and both annotators **re-label all 180
reports** from scratch against the new version. Record the version used in the `rubric_version` field
on every label.

**Changelog**

- **v1.0** — initial rubric. Gates derived from the high-energy / direct-control SIF model; control
  breaches cross-referenced to the nine IOGP Life-Saving Rules.
