-- Aggregation SQL — TECH_STACK v2, patch v1.1 Amendment A.
-- Phase 3 drops these in behind app/aggregate.py. Plain parameterised SQL with GROUP BY;
-- no window functions beyond the latest-prediction pick, no CTEs deeper than one level.
-- Every statement here must be readable aloud in two sentences by any member.
--
-- Member 4's hostile question is "what does the SQL actually compute, and why does it replace
-- embeddings?" The answer is in `latest`: we count reports per site, count how many of those
-- the current model called precursors, and divide. Embeddings would cluster reports by
-- wording; this ranks locations by how often their reports carry fatal potential, which is the
-- decision an HSE manager actually makes.
--
-- Three rules are baked into every statement:
--   1. `latest` keeps ONE prediction per report, for the current model_version only.
--   2. `r.source <> 'osha'` — OSHA rows carry no site taxonomy.
--   3. HAVING count(*) >= :min_group_n — the small-denominator guard. The excluded groups are
--      fetched by the companion `_insufficient_volume` query, never silently dropped.

-- :model_version  text
-- :min_group_n    int


-- ---------------------------------------------------------------------------
-- name: latest_predictions
-- One row per report: its newest prediction under the current model version.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW latest_predictions AS
SELECT DISTINCT ON (p.report_id)
       p.report_id,
       p.hazard_assessment,
       p.lsr_rule,
       p.control_status,
       p.severity,
       p.is_sif_precursor,
       p.confidence,
       p.is_fallback,
       p.model_version,
       p.created_at AS classified_at
FROM predictions p
ORDER BY p.report_id, p.created_at DESC;


-- ---------------------------------------------------------------------------
-- name: latest_predictions_by_version
-- One row per report PER MODEL VERSION: that version's newest judgement.
--
-- `latest_predictions` above answers a different question. It picks the newest
-- prediction per report across ALL versions, which is right for the report list
-- (what do we currently think about this report?) and wrong for aggregation.
--
-- Every aggregate below filters `l.model_version = :model_version`. Against the
-- global-latest view that filter runs AFTER the newest row has been chosen, so a
-- report whose newest row belongs to some other version is never re-resolved to
-- its own row for the version asked for - it drops out of the result entirely.
--
-- That is not hypothetical. A classifier run that fell back to the baseline wrote
-- 111 `stub-0.1.0` rows; those became the newest rows for 111 reports, and every
-- one would have vanished from the site and activity rankings. No error, no
-- warning, just smaller numbers that still looked plausible.
--
-- Partitioning by version first means the filter selects among rows that are each
-- already the newest for their own version.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW latest_predictions_by_version AS
SELECT DISTINCT ON (p.report_id, p.model_version)
       p.report_id,
       p.hazard_assessment,
       p.lsr_rule,
       p.control_status,
       p.severity,
       p.is_sif_precursor,
       p.confidence,
       p.is_fallback,
       p.model_version,
       p.created_at AS classified_at
FROM predictions p
ORDER BY p.report_id, p.model_version, p.created_at DESC;


-- ---------------------------------------------------------------------------
-- name: summary
-- Totals, precursor rate, and the median seconds between a report arriving and
-- being classified — the monthly-triage-to-seconds headline.
-- ---------------------------------------------------------------------------
SELECT count(*)                                                     AS total_reports,
       count(*) FILTER (WHERE l.is_sif_precursor)                   AS precursor_count,
       coalesce(avg(l.is_sif_precursor::int), 0)                    AS precursor_rate,
       count(*) FILTER (WHERE l.hazard_assessment
                              = 'insufficient_information')         AS insufficient_information_count,
       coalesce(avg(l.confidence), 0)                               AS avg_confidence,
       coalesce(percentile_cont(0.5) WITHIN GROUP (
           ORDER BY extract(epoch FROM l.classified_at - r.created_at)), 0)
                                                                    AS median_triage_seconds,
       %(model_version)s                                            AS model_version,
       now()                                                        AS last_updated
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s;


-- ---------------------------------------------------------------------------
-- name: sites_ranked
-- Reports per site, how many were precursors, and the rate. Ranked by rate so a
-- site is not punished for reporting diligently; count stays visible alongside.
-- ---------------------------------------------------------------------------
SELECT r.site,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate,
       mode() WITHIN GROUP (ORDER BY l.lsr_rule)
           FILTER (WHERE l.is_sif_precursor)      AS top_rule
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
  AND r.site IS NOT NULL
GROUP BY r.site
HAVING count(*) >= %(min_group_n)s
ORDER BY precursor_rate DESC, precursor_count DESC;


-- ---------------------------------------------------------------------------
-- name: sites_insufficient_volume
-- The same groups that fell below the guard, so the UI greys them out instead of
-- hiding them. Identical to sites_ranked except the HAVING flips.
-- ---------------------------------------------------------------------------
SELECT r.site,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate,
       mode() WITHIN GROUP (ORDER BY l.lsr_rule)
           FILTER (WHERE l.is_sif_precursor)      AS top_rule
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
  AND r.site IS NOT NULL
GROUP BY r.site
HAVING count(*) < %(min_group_n)s
ORDER BY report_count DESC;


-- ---------------------------------------------------------------------------
-- name: activities_ranked
-- Same shape as sites_ranked, grouped by activity.
-- ---------------------------------------------------------------------------
SELECT r.activity,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate,
       mode() WITHIN GROUP (ORDER BY l.lsr_rule)
           FILTER (WHERE l.is_sif_precursor)      AS top_rule
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
  AND r.activity IS NOT NULL
GROUP BY r.activity
HAVING count(*) >= %(min_group_n)s
ORDER BY precursor_rate DESC, precursor_count DESC;


-- ---------------------------------------------------------------------------
-- name: activities_insufficient_volume
-- The activities that fell below the guard, so the UI greys them out.
-- ---------------------------------------------------------------------------
SELECT r.activity,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate,
       mode() WITHIN GROUP (ORDER BY l.lsr_rule)
           FILTER (WHERE l.is_sif_precursor)      AS top_rule
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
  AND r.activity IS NOT NULL
GROUP BY r.activity
HAVING count(*) < %(min_group_n)s
ORDER BY report_count DESC;


-- ---------------------------------------------------------------------------
-- name: rules
-- Which Life-Saving Rule, crossed with what the barrier was doing. This is the
-- barrier-failure view: energy_isolation x absent is a different problem from
-- energy_isolation x failed.
-- ---------------------------------------------------------------------------
SELECT l.lsr_rule,
       l.control_status,
       count(*) AS count
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
GROUP BY l.lsr_rule, l.control_status
ORDER BY count DESC;


-- ---------------------------------------------------------------------------
-- name: shifts
-- Site crossed with shift. This is the query behind "eleven at Rig 4 this
-- quarter, nine of them on night shift".
-- ---------------------------------------------------------------------------
SELECT r.site,
       r.shift,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
  AND r.site IS NOT NULL
  AND r.shift IS NOT NULL
GROUP BY r.site, r.shift
ORDER BY precursor_count DESC, r.site, r.shift;


-- ---------------------------------------------------------------------------
-- name: trend
-- Reports and precursors per calendar month of report_date. A display, not a
-- model: no forecasting, no anomaly detection on this line.
-- ---------------------------------------------------------------------------
SELECT to_char(date_trunc('month', r.report_date), 'YYYY-MM') AS month,
       count(*)                                   AS report_count,
       count(*) FILTER (WHERE l.is_sif_precursor) AS precursor_count,
       avg(l.is_sif_precursor::int)               AS precursor_rate
FROM reports r
JOIN latest_predictions_by_version l ON l.report_id = r.report_id
WHERE r.source <> 'osha'
  AND l.model_version = %(model_version)s
GROUP BY date_trunc('month', r.report_date)
ORDER BY month ASC;
