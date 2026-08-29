# Hand-off — Member 6 (DevOps / QA / Research)

You own deployment, secrets, the test suite, the literature check, and you are the tiebreak
annotator. Two of those are on the critical path in week one.

---

## 1. Tiebreak annotator — week one, blocking

Members 1 and 3 label all 180 reports independently against [rubric v2.0](../rubric.md). You
adjudicate every disagreement.

**Record which gate split, not just the final label.** `gold_labels.gate_split` takes 1, 2, or 3.
That column is the entire diagnostic: if agreement lands below 70%, it says which gate to revise
rather than forcing a rewrite of the whole rubric and a re-label of all 180.

Read the rubric before you adjudicate. You are applying their document, not your own judgement —
if you find yourself disagreeing with the rubric rather than with an annotator, that is a note for
Member 1, not a label change.

---

## 2. Deployment

**API → Render.** [render.yaml](../../render.yaml) is written. Free tier, `rootDir: backend`,
health check at `/health`.

```
Environment variables — set in the Render dashboard, never in the repo:
  SUPABASE_DB_URL     from Supabase > Project Settings > Database > Connection string (URI)
  ANTHROPIC_API_KEY   once Member 2's classifier lands
  CORS_ORIGINS        the Vercel URL, comma-separated
```

**Frontend → Vercel.** Member 5's app, with the API base URL as an environment variable.

Two free-tier facts worth knowing before demo day:

- **Render free instances sleep.** First request after idle takes ~30–60 seconds. Hit the API
  once a few minutes before you present. This is the single most likely way the demo dies.
- **Supabase free projects pause after a week of inactivity.** Check it the day before.

The API is built to survive both: with no database it serves the seeded stub rather than
erroring, and `/health` reports `data_source` so you can see which one you are looking at.

**Never commit keys.** `.env` is gitignored from commit one. Judges read repos, and a leaked key
in git history is a bad look that no amount of good architecture recovers from.

---

## 3. Tests

`backend/tests/test_api.py` has **34 passing tests, no skips**. They cover the ten named in
[TECH_STACK v2](../TECH_STACK.md) §Testing:

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

`/analyze` contract · 422 on malformed input · schema-validation retry · fallback trigger ·
timeout behaviour · both-classifiers-down → 503 · cache hit · prompt-version cache invalidation ·
rate correctness · small-denominator guard · trend bucketing · OSHA exclusion ·
`recommended_check` behaviour · vocabulary drift between SQL, Pydantic and NAMES.md.

The resilience tests register deliberately broken classifiers and drive the real machinery —
nothing is faked. One of them caught a genuine bug: a timeout that fired but still blocked for
the full duration of the slow call.

**The pitch may claim a test suite only because it exists.** It does. You can say "thirty-four
tests" and open the file.

No CI — invisible on stage relative to setup cost.

---

## 4. Literature check

Member 1's [rubric §9](../rubric.md) separates what is sourced from what is our own calibration.
Your job is to confirm the sourced half actually says what we claim, and to flag anything that
does not.

Specifically worth verifying:

- **IOGP Report 459** defines nine Life-Saving Rules, and the eight we use are named correctly.
- The PS's own citations — DEKRA (Martin & Black 2015), the EEI SIF Precursor model, VelocityEHS
  2024 — support the high-energy / direct-control precursor structure we built Gates 1 and 2 on.
- The PS's own statistics (51% fall in non-fatal, 25.5% in fatalities; 20–25% of reports carrying
  fatal potential) are quoted from the PS text, not from us.

**If a source does not say what we claim, we cut the claim.** No fabricated citations, ever. An
earlier rubric draft carried numeric energy thresholds that were removed for exactly this reason.

Also help Member 3 pull the 30 real OSHA Severe Injury Reports.

---

## 5. Pre-demo checklist

Run this the morning of, in order:

```bash
curl https://<render-url>/health          # wakes the instance; check data_source
curl https://<render-url>/meta            # check primary_classifier is not stub-0.1.0
curl -X POST https://<render-url>/analyze -H 'Content-Type: application/json' \
     -d '{"report_text":"Technician opened the pump starter panel. The circuit was not isolated and no lockout was applied."}'
```

- [ ] Render awake, `/health` returns 200
- [ ] `primary_classifier` is the real one, not `stub-0.1.0`
- [ ] Supabase project not paused
- [ ] Vercel frontend loads and points at the right API
- [ ] The ambiguous barrier-held case returns *not a precursor* — see [demo-script.md](../demo-script.md)
- [ ] Degraded-mode banner verified by killing the network once
- [ ] `/aggregate/sites` still puts the high-density site first
