-- Supabase schema — TECH_STACK v2 §Database. Column names are NAMES.md verbatim.
--
-- Five tables: sites, reports, predictions (append-only), gold_labels,
-- report_status_events (append-only). No pgvector, no
-- embeddings, no clustering — the aggregation in sql/aggregates.sql does the same dashboard
-- job with GROUP BY, and every member can explain it.
--
-- Run once against the Supabase SQL editor, then sql/aggregates.sql for the view.
--
-- Vocabulary is enforced with CHECK constraints rather than Postgres enums: same protection
-- against a synonym creeping in, but a value can be added in one ALTER during a 22-day build
-- instead of an enum migration dance.

-- ---------------------------------------------------------------------------
-- sites — the fixed site list. Eight to ten, defined up front, so the density
-- ranking has stable groups to aggregate over.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sites (
    site        text PRIMARY KEY,
    region      text,
    created_at  timestamptz NOT NULL DEFAULT now()
);


-- ---------------------------------------------------------------------------
-- reports — one row per report, synthetic or OSHA.
-- OSHA rows carry no site taxonomy, which is why site/activity/shift are
-- nullable and why every aggregate filters them out.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    report_id      text PRIMARY KEY,
    report_text    text NOT NULL,
    source         text NOT NULL CHECK (source IN ('synthetic', 'osha')),
    site           text REFERENCES sites (site),
    activity       text,
    shift          text CHECK (shift IN ('day', 'night')),
    report_date    date NOT NULL,
    is_contractor  boolean,
    created_at     timestamptz NOT NULL DEFAULT now(),

    -- A synthetic report must be groupable or it is invisible to the dashboard —
    -- the most likely silent failure in the whole project (master plan §6).
    CONSTRAINT synthetic_rows_carry_site_taxonomy CHECK (
        source <> 'synthetic'
        OR (site IS NOT NULL AND activity IS NOT NULL AND shift IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS reports_site_idx        ON reports (site);
CREATE INDEX IF NOT EXISTS reports_activity_idx    ON reports (activity);
CREATE INDEX IF NOT EXISTS reports_report_date_idx ON reports (report_date);
CREATE INDEX IF NOT EXISTS reports_source_idx      ON reports (source);


-- ---------------------------------------------------------------------------
-- predictions — APPEND-ONLY. Never UPDATE a row here; write a new one.
-- Re-running the classifier keeps the old judgement, so "every judgement is
-- logged and reviewable" is a property of the schema, not a promise.
-- Aggregates read the latest row per report for the current model_version.
--
-- recommended_check is deliberately NOT stored: it is a static lookup keyed on
-- lsr_rule (api/recommendations.py), so persisting it would let a stale copy
-- drift from the checklist we actually ship.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                 bigserial PRIMARY KEY,
    report_id          text NOT NULL REFERENCES reports (report_id) ON DELETE CASCADE,

    hazard_assessment  text NOT NULL CHECK (hazard_assessment IN ('yes', 'no', 'insufficient_information')),
    lsr_rule           text NOT NULL CHECK (lsr_rule IN (
                           'energy_isolation', 'hot_work', 'confined_space', 'line_of_fire',
                           'work_at_height', 'lifting', 'driving', 'permit_to_work', 'none')),
    control_status     text CHECK (control_status IN ('absent', 'failed', 'present', 'unclear')),
    severity           smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
    is_sif_precursor   boolean NOT NULL,
    confidence         real NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    flagged_phrases    jsonb NOT NULL DEFAULT '[]'::jsonb,
    reasoning          text NOT NULL,

    model_version      text NOT NULL,
    prompt_version     text,
    is_fallback        boolean NOT NULL DEFAULT false,
    created_at         timestamptz NOT NULL DEFAULT now(),

    -- Rubric v2.1 §2: there is no control to assess for a hazard we could not name.
    CONSTRAINT control_status_only_when_hazard_yes CHECK (
        hazard_assessment = 'yes' OR control_status IS NULL
    ),
    -- Rubric v2.1 §6, enforced so a prompt change cannot quietly redefine the label.
    CONSTRAINT precursor_requires_all_three_gates CHECK (
        is_sif_precursor = (
            hazard_assessment = 'yes'
            AND control_status IN ('absent', 'failed')
            AND severity >= 4
        )
    )
);

-- The aggregation's latest-per-report pick reads exactly this order.
CREATE INDEX IF NOT EXISTS predictions_latest_idx
    ON predictions (report_id, created_at DESC);
CREATE INDEX IF NOT EXISTS predictions_model_version_idx
    ON predictions (model_version);


-- ---------------------------------------------------------------------------
-- report_status_events — APPEND-ONLY, like predictions. One row per triage
-- decision a human makes: dispatched to a crew, archived as reviewed, or moved
-- back to active. The current status is the newest row, not a mutable column.
--
-- Append-only matters more here than anywhere else in the schema. The whole
-- claim of this system is that it never closes a report - it reorders a reading
-- queue and a person decides. "Who archived this, when, and why" is the first
-- question asked when something later goes wrong, and a status column that is
-- overwritten in place cannot answer it. This can.
--
-- `actor` is free text rather than a foreign key: there is no user table in a
-- prototype, and recording "sanket" is worth more than recording nothing while
-- waiting for auth. It is not an identity claim and must not be presented as one.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_status_events (
    id          bigserial PRIMARY KEY,
    report_id   text NOT NULL REFERENCES reports (report_id) ON DELETE CASCADE,
    status      text NOT NULL CHECK (status IN ('active', 'dispatched', 'archived')),
    note        text,
    actor       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS report_status_events_latest_idx
    ON report_status_events (report_id, created_at DESC);


-- One row per report: its current triage status. A report nobody has touched has
-- no row here at all, and reads default it to 'active' - absence of a decision is
-- not a decision, and writing 180 'active' rows up front would say otherwise.
CREATE OR REPLACE VIEW latest_report_status AS
SELECT DISTINCT ON (report_id)
       report_id,
       status,
       note,
       actor,
       created_at AS status_changed_at
FROM report_status_events
ORDER BY report_id, created_at DESC;


-- ---------------------------------------------------------------------------
-- gold_labels — human labels. Two independent annotators plus a tiebreak row.
-- gate_split records WHICH gate the annotators disagreed on, which is the whole
-- diagnostic when agreement lands under 70%: it tells us which gate to revise
-- rather than rewriting the rubric wholesale.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold_labels (
    id                 bigserial PRIMARY KEY,
    report_id          text NOT NULL REFERENCES reports (report_id) ON DELETE CASCADE,
    annotator          text NOT NULL,
    is_tiebreak        boolean NOT NULL DEFAULT false,

    hazard_assessment  text NOT NULL CHECK (hazard_assessment IN ('yes', 'no', 'insufficient_information')),
    lsr_rule           text NOT NULL CHECK (lsr_rule IN (
                           'energy_isolation', 'hot_work', 'confined_space', 'line_of_fire',
                           'work_at_height', 'lifting', 'driving', 'permit_to_work', 'none')),
    control_status     text CHECK (control_status IN ('absent', 'failed', 'present', 'unclear')),
    severity           smallint NOT NULL CHECK (severity BETWEEN 1 AND 5),
    is_sif_precursor   boolean NOT NULL,

    notes              text,
    gate_split         smallint CHECK (gate_split IN (1, 2, 3)),
    rubric_version     text NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),

    -- One label per annotator per report. A re-label under a new rubric_version
    -- replaces the row, so the version recorded is always the one that applied.
    CONSTRAINT one_label_per_annotator_per_report UNIQUE (report_id, annotator),
    CONSTRAINT control_status_only_when_hazard_yes CHECK (
        hazard_assessment = 'yes' OR control_status IS NULL
    ),
    CONSTRAINT gate_split_only_on_tiebreak CHECK (
        is_tiebreak OR gate_split IS NULL
    )
);

CREATE INDEX IF NOT EXISTS gold_labels_report_idx ON gold_labels (report_id);


-- ---------------------------------------------------------------------------
-- Row Level Security.
-- The frontend never talks to Supabase directly — it goes through FastAPI, which
-- holds the service key. So RLS is ON with no policies: the service role bypasses
-- it, and an anon key leaked from the browser bundle reads nothing.
-- ---------------------------------------------------------------------------
ALTER TABLE sites       ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports     ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gold_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_status_events ENABLE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------------
-- The ten fixed sites. Distribution across them is deliberately uneven so the
-- rate ranking has a clean winner (master plan §6).
-- ---------------------------------------------------------------------------
INSERT INTO sites (site, region) VALUES
    ('Rig 4',             'Upper Assam'),
    ('Rig 7',             'Upper Assam'),
    ('Duliajan Field',    'Upper Assam'),
    ('Moran Gas Plant',   'Upper Assam'),
    ('Kumchai Drilling',  'Arunachal'),
    ('Jorhat Workover',   'Upper Assam'),
    ('Pipeline Sector 3', 'Upper Assam'),
    ('Baghjan Wellpad',   'Upper Assam'),
    ('Naharkatiya Depot', 'Upper Assam'),
    ('Makum Terminal',    'Upper Assam')
ON CONFLICT (site) DO NOTHING;
