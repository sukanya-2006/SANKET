# Tiebreak sheet — 7 open disagreements

Generated from `data/labeling_disagreements.csv`. One person decides each of these, applying the rubric. Nothing here suggests an answer.

**How to record a decision.** Write the winning value in the DECISION line, add one sentence of reasoning, then append the row to `data/gold_labels.csv` with `annotator` set to `agreed`.

Split by gate — gate 2: 1, gate 3: 6.

---

## Gate 2 — 1 report

GATE 2 - was there a control targeting that hazard, and was it doing its job?
> `absent`: no control existed, or one existed and was not used, removed, bypassed.
> `failed`: a control was in place and did not hold.
> `present`: a rated, targeted control held, and the text explicitly says so.
> `unclear`: the narrative says nothing either way. Silence is `unclear`.
>
> A report that states a control was not done IS `absent` - that is reading, not
> inferring. Reserve `unclear` for narratives that simply do not mention controls.


### Report 96

> At the Pipeline Yard D during the day shift, a contractor was walking down the access lane without his hard hat or high‑visibility vest. When he passed the gas line inspection point, a loose pipe cap fell and landed on the ground. The contractor quickly ducked to avoid injury, but the lack of PPE meant he could not see the falling debris and almost got hit. The incident was logged as a near miss.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | line_of_fire | line_of_fire |
| control | unclear | failed |
| severity | 5 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

## Gate 3 — 6 reports

GATE 3 - the 3/4 boundary, which is the one that decides the label:
>     "Would this person be permanently unable to do the same job again?"
>     Yes -> 4 or 5.   No -> 3 or below.
>
> THE ONE-CHANGE RULE. Change EXACTLY ONE thing: the timing by a few seconds, OR the
> position by a metre, OR remove one last-second catch or rescue. Not two, not a
> chain. If you catch yourself thinking "and then, if he had also...", go back.
>
> 3 = off work for a while, THEN BACK TO THE SAME JOB.
> 4 = cannot return to the same job. Amputation, lost eye, permanent restriction.
> 5 = someone dies, and you can name the mechanism in one sentence after ONE change.
>
> If you are genuinely torn between 3 and 4, answer 3 and say why.


### Report 10

> On the day shift at Pipeline Yard D, a company employee was stepping down from a 4‑meter high loading dock when the guard rail snapped, sending him to the concrete floor. He slipped and twisted his ankle, but no serious injury occurred; the incident was flagged as a near‑miss and the broken rail was replaced immediately.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | work_at_height | work_at_height |
| control | failed | failed |
| severity | 3 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

### Report 149

> Day shift at Refinery B, a company employee was going into the tank house for a routine inspection. The ladder had been propped up by a temporary bar, but it slid off when the worker moved, so the employee slipped and nearly fell into the tank. He stopped the entry, called for help, and the safety barrier was then put in place before anyone else entered.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | confined_space | confined_space |
| control | absent | absent |
| severity | 4 | 3 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

### Report 60

> During the day shift at Refinery B, a contractor was climbing a 12‑meter ladder to replace a burner vent. The ladder's guardrail was missing on the right side, so the contractor slipped but caught himself on the side rail, landing on his back but not hitting the platform. No injuries were reported, but the incident showed a clear lapse in safety equipment.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | work_at_height | work_at_height |
| control | absent | absent |
| severity | 3 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

### Report 139

> At Rig 4, during the day shift, a company employee was walking around the drill floor without wearing a hard hat or safety vest, despite the hard‑hat zone signs. The employee was nearly struck by a falling drill pipe that slipped from a nearby rigging rig. No one was injured, but the incident highlighted a clear PPE noncompliance that could have caused serious injury.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | line_of_fire | line_of_fire |
| control | absent | absent |
| severity | 3 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

### Report 20

> During the night shift at Refinery B, a company employee was walking through the chemical storage area without wearing the required hard hat and safety goggles. The worker walked right next to a leaking pipe; the exposed skin could have come into contact with the corrosive fluid, but the employee stopped just before the spray reached them. The incident was logged as a near‑miss because the PPE omission could have caused a serious burn if the leak had worsened.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | line_of_fire | line_of_fire |
| control | absent | absent |
| severity | 3 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---

### Report 51

> At Pipeline Yard D on the night shift, a contractor was working on the rooftop of the storage tank when a handrail that was supposed to support him slid off the steel bracket. He nearly fell but caught himself on the edge of the tank, and no one was injured. The handrail was found to be improperly installed and the safety guard was missing. The incident was reported to the safety officer immediately.

| | akanksha | sukanya |
|---|---|---|
| hazard | yes | yes |
| rule | work_at_height | work_at_height |
| control | absent | absent |
| severity | 3 | 4 |

**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`

**WHY:** ______________________________________________

---
