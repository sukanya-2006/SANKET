# Hand-off — Member 5 (Frontend)

Three screens. **The backend is finished and running** — start now, against real response shapes,
with no database and no API key.

```bash
cd backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Browse <http://localhost:8000/docs>. Generate your types from `/openapi.json` rather than hand-
writing them — then a backend field rename breaks your build instead of your demo.

React + Vite + TypeScript + Tailwind + Recharts. UI vocabulary mirrors the PS: "SIF-potential",
"barrier failure".

> **If you started against the old `/api/v1/*` paths, they are gone.** They pre-dated the master
> plan and used invented field names. Everything now uses the locked names in
> [NAMES.md](../../NAMES.md).

---

## Endpoints

| Screen | Endpoint |
|---|---|
| 1 — live analyse | `POST /analyze` `{"report_text": "..."}` |
| 2 — ranked queue | `GET /reports?limit&offset&is_sif_precursor&lsr_rule&site&source&q` |
| 2 — detail | `GET /reports/{report_id}` |
| 3 — stat cards | `GET /aggregate/summary` |
| 3 — site ranking | `GET /aggregate/sites` |
| 3 — activity ranking | `GET /aggregate/activities` |
| 3 — rule × barrier | `GET /aggregate/rules` |
| 3 — site × shift | `GET /aggregate/shifts` |
| 3 — trend line | `GET /aggregate/trend` |
| dropdowns, versions | `GET /meta` |

---

## Screen 1 — live analyse box, on the landing page

**Not behind a tab.** It is the first thing a judge sees and the first thing they will type into.

```json
{
  "result": {
    "hazard_assessment": "yes",
    "lsr_rule": "energy_isolation",
    "control_status": "absent",
    "severity": 4,
    "is_sif_precursor": true,
    "confidence": 0.82,
    "flagged_phrases": ["isolated", "no lockout"],
    "reasoning": "Hazard present (energy_isolation) with the direct control absent; ...",
    "recommended_check": "Verify energy isolation: sources identified, isolated, locked, ..."
  },
  "model_version": "stub-0.1.0",
  "is_fallback": false,
  "latency_ms": 1,
  "created_at": "2026-08-29T09:08:01Z"
}
```

Five things the UI must get right:

1. **Show all three gates, not just the verdict.** The two-field auditable judgement — hazard plus
   control status — is our innovation claim. A UI that shows only a red/green badge throws it away.
2. **`hazard_assessment` is three-valued.** `insufficient_information` is its own state, not a
   "no". Those reports go to a human. Render them differently from a clean negative.
3. **`control_status` is four-valued.** `present` means the barrier held, so the report is *not* a
   precursor even though the hazard was real. **This is the ambiguous demo case and the UI has to
   make it legible** — something like "Hazard present · Barrier held · Not a precursor". If a judge
   cannot see why we said no, the moment is wasted.
4. **`flagged_phrases` are verbatim substrings** of what was submitted. Highlight in place with
   `indexOf` — do not re-tokenise. A test guarantees the substring property.
5. **`recommended_check`** is non-null only for precursors. Label it as a standard checklist, not
   as advice the model wrote. If asked: "static, regulator-aligned checklists keyed to the rule —
   the model never generates safety advice."

### The degraded-mode banner

When `is_fallback` is `true`, show it plainly: **"Degraded mode — keyword baseline"**. Not a
tooltip, not a grey dot. It flips true when the Claude call fails or times out and the local
baseline answers.

Build this now. It is already in the contract, it is testable today by stopping the network, and
it is a strong answer to a resilience question — but only if a judge can see it working.

---

## Screen 2 — ranked report queue

`GET /reports` returns items **already ordered**: precursors first, then severity descending. The
ranked order is the product, so it lives in the API — do not re-sort client-side, and do not let a
column header silently override it.

Each item carries `report_id`, `report_text`, `site`, `activity`, `shift`, `report_date`,
`severity`, `lsr_rule`, `control_status`, `is_sif_precursor`, `confidence`. Clicking through to
`/reports/{report_id}` adds the full `result` with `reasoning` and `flagged_phrases`.

`total` is the unpaginated count — use it for the pager, not `items.length`.

---

## Screen 3 — density dashboard

**This is the actual product.** Protect it from being cut for time.

`GET /aggregate/sites` returns:

```json
{
  "ranked": [
    {"site": "Rig 4", "report_count": 20, "precursor_count": 11,
     "precursor_rate": 0.55, "top_rule": "energy_isolation"}
  ],
  "insufficient_volume": [
    {"site": "Naharkatiya Depot", "report_count": 4, "precursor_count": 1,
     "precursor_rate": 0.25, "top_rule": "work_at_height"}
  ],
  "min_group_n": 5
}
```

- **Rank by rate, but always show the count next to it.** Rate exists so a site that reports
  diligently is not punished for it — a judge will ask why. The count stays visible so nobody
  mistakes 2 of 6 for a crisis.
- **`insufficient_volume` gets rendered greyed out, never hidden.** These are sites with fewer
  than `min_group_n` reports, where a rate is noise. Hiding them looks like we are cherry-picking;
  greying them out with "too few reports to rank" looks like we thought about it.
- `/aggregate/activities` is the same shape with `activity` instead of `site`.
- `/aggregate/rules` gives `lsr_rule × control_status` counts — the barrier-failure view. A
  stacked bar works well: `energy_isolation × absent` is a supervision problem,
  `energy_isolation × failed` is an equipment problem, and they get different fixes.
- `/aggregate/trend` is monthly. **A display, not a model** — no trend line fitting, no forecast,
  no anomaly highlighting. We classify and aggregate what was reported; we do not extrapolate.
- `/aggregate/summary` gives the stat cards, including `median_triage_seconds`.

> `median_triage_seconds` is currently computed from **synthetic timestamps**. Render it, but it
> must not appear on a slide as a measured result until real timings exist.

---

## Deployment

Vercel, free tier. Point the API base URL at the Render deployment via an environment variable —
never a hard-coded localhost. Ask Member 6 for the URL, and ask Member 4 to add your Vercel domain
to `CORS_ORIGINS`.
