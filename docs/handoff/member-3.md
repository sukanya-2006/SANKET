# Hand-off — Member 3 (Data)

You own report generation with metadata, the OSHA pull, the labelling tool, the evaluation
script, and you are the first annotator. **You gate Members 2 and 4** — everything downstream is
meaningless without labels, so labels come first.

**Generate the reports without reading [docs/rubric.md](../rubric.md).** Member 1 wrote it
without seeing your reports. That independence is what makes the agreement number mean anything,
and a judge will ask whether you had it.

---

## 1. The dataset — 150 synthetic + 30 OSHA

**150, not 90.** At ~22% positives, a 90-report set leaves roughly six positives in a held-out
split, and one flipped prediction swings F1 by about eight points. Your headline number becomes
noise.

**Positive class stays 20–25%.** Never rebalance to 50/50 — it flatters every model and convinces
nobody experienced.

Every synthetic report carries metadata. Without it, `aggregate.py` has nothing to group by, which
is the most likely silent failure in the project.

`data/reports_metadata.csv` — these column names exactly, from [NAMES.md](../../NAMES.md):

```
report_id, report_text, source, site, activity, shift, report_date, is_contractor
```

- `source` — `synthetic` or `osha`
- `site` — one of the ten in [backend/app/sql/schema.sql](../../backend/app/sql/schema.sql).
  **Distribute unevenly on purpose.** If every site has three precursors, the "Rig 4 had eleven
  this quarter" demo moment does not exist.
- `shift` — `day` or `night`
- `site`, `activity`, `shift` may be blank **only** when `source` is `osha`. The loader and the
  database both refuse a synthetic row without them, with a line number.

Include a handful of **Hindi / Hinglish / code-mixed** reports. They prove the multilingual claim,
and the rubric §7 tells annotators how to handle them.

The seeded stub in `backend/app/stub.py` shows the shape and distribution that works — treat it
as a worked example, then delete nothing: the moment your CSV lands, the stub stops being used.

### The 30 OSHA reports

Real OSHA Severe Injury Reports, public and downloadable. Be precise about what they prove: that
the classifier handles real-world writing nobody on the team produced — **not** that it detects
precursors in near-miss reports. OSHA records describe injuries that already happened, a different
population. Someone in the room may know that.

They carry no site taxonomy, so they are excluded from every aggregate. That is a stated
limitation, not a gap to hide.

---

## 2. Labelling — days 1–6

You and Member 1 label all 180 independently against rubric v2.1, **no discussion until both
finish**. Batched: first 90 by day 4 so a broken gate surfaces while there is time to fix it,
the rest by day 6. Member 6 tiebreaks.

That instruction is right and it stays. Round one kept it. Round two — the re-label after the
rubric revision — did not: it was worked through together rather than blind. Read **What the two
rounds actually measured** below before you quote either number.

`data/gold_labels.csv`:

```
report_id, annotator, hazard_assessment, lsr_rule, control_status,
severity, is_sif_precursor, notes, gate_split, rubric_version, is_tiebreak
```

- `control_status` blank unless `hazard_assessment` is `yes`
- `gate_split` — 1, 2 or 3, **filled only on Member 6's tiebreak rows**. This column is the whole
  diagnostic: if agreement lands under 70%, it tells you which gate to revise instead of
  rewriting the rubric wholesale.
- `rubric_version` — `2.1`. A label made under one rubric version and one made under another
  are not the same measurement, so this column is not optional.
- `notes` — mandatory for every `insufficient_information`, every `unclear`, and every hard call.

### Agreement

```python
from sklearn.metrics import cohen_kappa_score
kappa = cohen_kappa_score(annotator_1, annotator_3)
```

Report **both** raw agreement and kappa — kappa subtracts the agreement chance alone would
produce. Compute it on `is_sif_precursor` first, then per gate, because the per-gate numbers are
what identify the culprit.

**Below 70%:** the rubric is ambiguous, not the annotators. Member 1 revises only the offending
gate, bumps the version, and you both re-label only the reports that turned on that gate.

### What the two rounds actually measured

**Round one was independent, and it failed: 52.2% on `is_sif_precursor`, kappa 0.083.** Severity
was the gate that split us — 14.4% agreement, 3–4 points apart on 76 of the 180. That is
`gate_split` doing exactly the job described above.

It bought the revision it was supposed to buy. v2.1 → v2.2 targeted the failing gate and nothing
else: the one-change rule was stated first, and the severity bands were rewritten from adjectives
into observable outcomes.

**Round two scored 96.1%, kappa 0.922 — but it was not run independently, so it is not a
ceiling.** "No discussion until both finish" was the rule and round two did not keep it. A kappa
computed after two annotators have reconciled measures how well they agree once they already
agree; it says nothing about how hard the task is. It cannot be credited to the rubric revision - both rounds used v2.1 - and
nothing stronger. Wherever it appears, it appears labelled **not independent — not a ceiling**.

The labels are still good: 173 agreed, 7 open (10, 20, 51, 60, 96, 139, 149). Adjudicated labels
are perfectly sound gold for training and evaluation. What round two cost us is the
agreement-ceiling claim, not the data.

**To get a real ceiling:** re-label a fresh ~40-report subset independently, no contact between
annotators, and report that kappa. A couple of hours. Do that rather than defend a number you
cannot.

---

## 3. Loading it

```bash
cd backend
./.venv/Scripts/python.exe scripts/ingest.py --apply-schema
./.venv/Scripts/python.exe scripts/ingest.py --reports ../data/reports_metadata.csv
./.venv/Scripts/python.exe scripts/ingest.py --labels  ../data/gold_labels.csv
./.venv/Scripts/python.exe scripts/ingest.py --classify
```

The loader validates column names against NAMES.md and refuses a mismatched file rather than
silently importing nulls. Needs `SUPABASE_DB_URL` in `backend/.env` — ask Member 4.

---

## 4. `eval/run_eval.py` — artifact #1

One output table. **Two tables plus one line, never a single merged table:**

1. **Synthetic held-out split** — baseline F1/PR-AUC vs LLM F1/PR-AUC. The fair, apples-to-apples
   fight. ~30 reports for prompt tuning; the held-out set opens exactly **once**, at the end.
2. **OSHA set — LLM only.** A generalisation check on real writing. Testing the baseline here
   would measure domain transfer, not model quality: an unfair fight we do not stage.
3. **Severity MAE** on precursor cases against adjudicated human severity.

Plus annotator agreement % and kappa for each round, each one labelled with whether it was run
independently. Round two's 96.1% / kappa 0.922 carries **not independent — not a ceiling** or it
does not go in the table at all. Saying which of your own numbers you cannot defend is the most
sophisticated thing a student team can say.

**F1 and PR-AUC, never accuracy.** At ~22% positives, "always say no" scores 78%.

State that you tuned for recall over precision as a deliberate choice: missing a fatal precursor
costs a life, a false alarm costs twenty minutes.

---

## Your hostile questions

- *"You wrote the reports and graded yourself."* — Intent labels are discarded. Two annotators
  labelled against a written rubric neither of them could negotiate, the first round blind — it
  agreed 52%, which is what forced the revision — and a sixth of the set is real OSHA text nobody
  on the team wrote.
- *"What is your inter-annotator agreement?"* — First round was independent: 52%, kappa 0.083,
  and severity was the gate that split us, so we rewrote it. Second round agreed 96%, but it was
  not run independently, so we do not quote it as a ceiling — it cannot be credited to the revision,
  not a bound on the system. A fresh independent pass would give us a real number, and we would
  rather report that one.
- *Why hold out a test set* — tuning against your test score fits the model to the answers rather
  than to the problem.
