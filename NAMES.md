# NAMES.md — locked field names, one set, everywhere

Per master plan §2. **Members 2 and 4 read this before writing a line of code**, and Member 5
reads it before naming a prop. These names are identical in SQL, Pydantic, and the UI. Field
names drifted across three drafts of the plan before this version; they do not drift again.

Changing anything here requires agreement from Members 2, 4, and 5 in the same conversation.

## Classification output

| Field | Type | Notes |
|---|---|---|
| `hazard_assessment` | `yes` \| `no` \| `insufficient_information` | Gate 1 |
| `lsr_rule` | `LSRRule` | Gate 1 hazard category — the eight IOGP rules, or `none` |
| `control_status` | `absent` \| `failed` \| `present` \| `unclear` \| `null` | Gate 2 |
| `severity` | int 1–5 | Gate 3 magnitude; drives the sorted queue |
| `is_sif_precursor` | bool | the decision |
| `confidence` | float 0–1 | makes PR-AUC computable |
| `flagged_phrases` | list[str] | explainability; verbatim substrings of the report text |
| `reasoning` | str | one paragraph, per-field justification |
| `recommended_check` | str \| null | **static lookup, never model output** — see below |

`recommended_check` (added by backend patch v1.1, Amendment B) is a fixed, conservative
verification prompt keyed to `lsr_rule`, from `backend/app/api/recommendations.py`. It is populated
only when `is_sif_precursor` is true, and is `null` otherwise. It is a lookup table, not generated
text: **the model never generates safety advice.**

## Banned synonyms

These keep creeping back. They are wrong everywhere — SQL, Pydantic, and the UI:

- ~~`category`~~, ~~`hazard_category`~~ → the field is `lsr_rule`
- ~~`barrier_status`~~ → the field is `control_status`. The UI **may display** "barrier failure"
  as a label; the field name does not change.
- ~~`offline_fallback`~~ → the field is `is_fallback`
- ~~`contractor`~~ → the field is `is_contractor`

## Enums

```
HazardAssessment : yes | no | insufficient_information
ControlStatus    : absent | failed | present | unclear
LSRRule          : energy_isolation | hot_work | confined_space | line_of_fire
                   work_at_height | lifting | driving | permit_to_work | none
```

Eight IOGP Life-Saving Rules plus `none`. "Bypassing Safety Controls" is not among them —
barrier defeat is what `control_status` already measures, so carrying it as a hazard category
would double-count the same signal.

## Report metadata

Per master plan §6. Without these, `aggregate.py` has nothing to group by.

| Field | Type | Notes |
|---|---|---|
| `report_id` | str | |
| `report_text` | str | the narrative |
| `site` | str \| null | one of ten fixed sites; `null` for OSHA rows |
| `activity` | str \| null | `null` for OSHA rows |
| `shift` | `day` \| `night` \| null | `null` for OSHA rows |
| `report_date` | date | grouping key for `/aggregate/trend` |
| `is_contractor` | bool \| null | contractor vs own-workforce |
| `source` | `synthetic` \| `osha` | **OSHA rows are excluded from every aggregate** — no site taxonomy |
| `created_at` | timestamp | report received; with `predictions.created_at` gives triage latency |

## Prediction / label rows

`predictions` is append-only and carries `model_version` and `is_fallback`. `gold_labels`
carries `annotator`. `is_fallback` is true when the Claude call failed or timed out (10s) and
the local TF-IDF baseline answered instead; the UI shows that plainly as
"degraded mode — keyword baseline". Aggregates read the
**latest prediction per report for the current `model_version` only** — never mix versions in one
aggregate.

## Aggregation

`MIN_GROUP_N = 5` — a site or activity with fewer than 5 reports is excluded from rate-ranked
output and returned in `insufficient_volume` instead, so the frontend greys it out rather than
hiding it. A site with 1 report and 1 precursor is not "100% risk"; it is noise.

Every aggregate returns **both count and rate**. The frontend ranks by rate; the count stays
visible so nobody mistakes 2 of 6 for a crisis. Rate, not raw count, because raw counts penalise
sites that report diligently — the opposite of the incentive a safety system should create.
