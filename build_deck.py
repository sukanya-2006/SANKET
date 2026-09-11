"""
build_deck.py

Build the SIH 2026 idea-submission deck.

    python build_deck.py    ->  docs/SANKET-SIH2026-Idea-Submission.pptx

WHAT THIS IS

The team's own six-slide structure, kept as-is, with three things added:

  - real tables where a list was doing a table's job (tech stack, challenges,
    evaluation), so a judge can scan rather than read
  - the tech stack spelled out by layer, with what each piece is actually for
  - the evaluation numbers replaced with the ones that survive questioning

ON THAT LAST POINT

The previous version of slide 6 carried "Synthetic LLM F1 0.719", "OSHA F1 0.286" and a
footnote that 5 of 114 predictions used the fallback. Those were measured under a prompt that
contained a held-out report and disclosed the set's own base rate, so every LLM figure from
that run is withdrawn. The footnote had a separate cause - the cache was storing baseline
answers under the primary's key.

What replaces them is what can be defended: a cross-validated baseline F1, the independent
human agreement ceiling with its sample size, and an explicit line saying the LLM number is
being re-measured. Slide 3 also said SQLite; the data lives in Supabase PostgreSQL and SQLite
is only the on-instance cache.

Every number is a named constant traceable to the script that produced it. Change the
constant, rebuild, and every slide moves together.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --- numbers, each traceable to the script that produced it ---------------
CEILING_PCT = "97%"       # score_recheck.py - 37 of 38 agreed
CEILING_KAPPA = "0.947"   # score_recheck.py
CEILING_N = 38
BASELINE_F1 = "0.754"     # eval/run_eval.py --no-llm, 5-fold CV
BASELINE_SD = "± 0.077"
BASELINE_N = 114
SYNTHETIC_N = 150
OSHA_N = 30
OSHA_F1 = "0.118"         # score_stored_predictions.py
GOLD_N = 173
OPEN_TIEBREAKS = 7        # data/labeling_disagreements.csv

LIVE_APP = "https://sanket-frontend.onrender.com"

LOGO = "docs/assets/sih-2026-logo.png"

BLUE = RGBColor(0x00, 0x70, 0xC0)
NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLACK = RGBColor(0x00, 0x00, 0x00)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)
GREEN = RGBColor(0x1E, 0x7A, 0x5E)
PURPLE = RGBColor(0x5B, 0x4E, 0xA8)
AMBER = RGBColor(0x9C, 0x64, 0x0C)
RED = RGBColor(0xB4, 0x3A, 0x2E)
PILL = RGBColor(0x7B, 0x5E, 0xA7)
CARD = RGBColor(0xF2, 0xF6, 0xFA)
BAND = RGBColor(0xE8, 0xF1, 0xF8)
LINE = RGBColor(0xC9, 0xD8, 0xE6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = 13.333, 7.5
SERIF = "Times New Roman"
SANS = "Arial"
FOOT = 7.08


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def tbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return tf


def para(tf, text, size=15, bold=False, color=INK, after=7, first=False,
         align=PP_ALIGN.LEFT, font=SANS):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.alignment = align
    p.space_after = Pt(after)
    for r in p.runs:
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = font
    return p


def rect(slide, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE):
    sh = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    sh.shadow.inherit = False
    return sh


def table(slide, x, y, w, col_widths, rows, header_fill=NAVY, size=12.5, row_h=0.34):
    """A real PowerPoint table. Used where a list was doing a table's job."""
    n_rows, n_cols = len(rows), len(rows[0])
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y),
                                   Inches(w), Inches(row_h * n_rows))
    tbl = shape.table
    tbl.first_row = True
    tbl.horz_banding = True

    for c, cw in enumerate(col_widths):
        tbl.columns[c].width = Inches(cw)

    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.1)
            cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_fill if r == 0 else (
                WHITE if r % 2 else CARD)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = val
            p.space_after = Pt(0)
            for run in p.runs:
                run.font.size = Pt(size if r else size)
                run.font.bold = (r == 0)
                run.font.color.rgb = WHITE if r == 0 else INK
                run.font.name = SANS
    return tbl


def chrome(slide, title, n, serif=True):
    """Template furniture: team oval, centred title, logo, blue footer band."""
    o = rect(slide, 0.3, 0.2, 1.42, 0.66, fill=WHITE, line=PILL, shape=MSO_SHAPE.OVAL)
    tf = o.text_frame
    tf.word_wrap = True
    para(tf, "Signal-0", size=12.5, color=BLACK, first=True, after=0,
         align=PP_ALIGN.CENTER)

    size = 31 if len(title) <= 34 else 25
    tf = tbox(slide, 1.95, 0.14, 9.0, 0.82, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, title, size=size, bold=True, color=BLACK, first=True, after=0,
         align=PP_ALIGN.CENTER, font=SERIF if serif else SANS)

    if os.path.exists(LOGO):
        slide.shapes.add_picture(LOGO, Inches(11.15), Inches(0.16), height=Inches(0.8))

    rect(slide, 0, FOOT, W, H - FOOT, fill=BLUE)
    tf = tbox(slide, 0, FOOT + 0.07, W, 0.28)
    para(tf, "@SIH Idea submission- Template", size=10.5, color=WHITE, first=True,
         after=0, align=PP_ALIGN.CENTER)
    tf = tbox(slide, W - 1.05, FOOT + 0.07, 0.65, 0.28)
    para(tf, str(n), size=10.5, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.RIGHT)


def panel(slide, x, y, w, h, title, col):
    """A titled colour-headed panel, matching the team's slide-3 treatment."""
    rect(slide, x, y, w, h, fill=CARD, line=LINE)
    rect(slide, x, y, w, 0.52, fill=col)
    tf = tbox(slide, x, y + 0.11, w, 0.34)
    para(tf, title, size=16, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.CENTER)


def bullets(slide, x, y, w, items, size=14.5, gap=9, lead="●  "):
    tf = tbox(slide, x, y, w, 0.4)
    for i, it in enumerate(items):
        para(tf, lead + it, size=size, after=gap, first=(i == 0))
    return tf


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ==================== 1. TITLE PAGE ==================================
    s = blank(prs)
    tf = tbox(s, 0.6, 0.3, 9.9, 0.75)
    para(tf, "SMART INDIA HACKATHON 2026", size=37, bold=True, color=NAVY,
         first=True, after=0, align=PP_ALIGN.CENTER, font=SERIF)
    tf = tbox(s, 0.6, 1.12, 9.9, 0.6)
    para(tf, "TITLE PAGE", size=30, bold=True, color=BLACK, first=True, after=0,
         align=PP_ALIGN.CENTER, font=SERIF)
    if os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, Inches(10.55), Inches(0.28), height=Inches(1.08))

    tf = tbox(s, 0.85, 2.15, 11.6, 3.9)
    for i, (k, v) in enumerate([
            ("Problem Statement ID", "SIH26165"),
            ("Problem Statement Title", "AI/NLP Engine to Detect Serious Injury & Fatality "
                                        "(SIF) Precursors in OIL's "
                                        "Unsafe-Act/Unsafe-Condition and Near-Miss Reports"),
            ("Theme", "Smart Automation"),
            ("PS Category", "Software"),
            ("Team ID", "____"),
            ("Team Name", "Signal-0")]):
        para(tf, "•  %s -  %s" % (k, v), size=17.5, bold=True, after=16, first=(i == 0))

    rect(s, 0.85, 6.2, 11.6, 0.6, fill=BAND, line=LINE)
    tf = tbox(s, 1.1, 6.34, 11.1, 0.34)
    para(tf, "Working prototype:   %s" % LIVE_APP, size=14.5, bold=True, color=NAVY,
         first=True, after=0)

    # ==================== 2. SANKET ======================================
    s = blank(prs)
    chrome(s, "SANKET — From Incident Narratives to Early Safety Warnings", 2)

    rect(s, 0.6, 1.15, 12.13, 0.72, fill=BAND, line=LINE)
    tf = tbox(s, 0.95, 1.33, 11.5, 0.4)
    para(tf, "SANKET analyzes safety / near-miss reports using AI to detect potential "
             "Serious Injury & Fatality (SIF) precursors.",
         size=16, bold=True, color=NAVY, first=True, after=0)

    panel(s, 0.6, 2.08, 6.0, 2.5, "Identifies", NAVY)
    bullets(s, 0.95, 2.78, 5.4, ["Hazard & Life-Saving Rule", "Control status",
                                 "Severity (1–5)", "SIF Precursor: Yes / No",
                                 "Evidence & reasoning"], size=14.5, gap=8)

    panel(s, 6.73, 2.08, 6.0, 2.5, "Innovation", GREEN)
    bullets(s, 7.08, 2.78, 5.4, ["LLM + ML hybrid approach", "Explainable risk assessment",
                                 "One-Change severity rule",
                                 "Prioritized safety-review queue"], size=14.5, gap=8)

    tf = tbox(s, 0.6, 4.78, 12.13, 0.3)
    para(tf, "HOW A REPORT IS JUDGED", size=12, bold=True, color=NAVY, first=True, after=0)
    table(s, 0.6, 5.14, 12.13, [2.0, 4.6, 5.53], [
        ["Gate", "Question", "Possible answers"],
        ["1  Hazard", "Is a high-energy hazard present?",
         "yes  ·  no  ·  insufficient information"],
        ["2  Control", "Was a safety barrier doing its job?",
         "absent  ·  failed  ·  present  ·  unclear"],
        ["3  Severity", "How bad could it realistically have been?",
         "1  to  5"],
    ], size=13, row_h=0.42)

    # ==================== 3. TECHNICAL APPROACH ==========================
    s = blank(prs)
    chrome(s, "TECHNICAL APPROACH", 3)

    panel(s, 0.5, 1.12, 6.35, 4.15, "Tech Stack", NAVY)
    table(s, 0.72, 1.82, 5.9, [1.5, 2.4, 2.0], [
        ["Layer", "Technology", "Purpose"],
        ["Frontend", "React", "worker + admin screens"],
        ["Backend", "FastAPI (Python)", "REST API, validation"],
        ["AI model", "Groq GPT-OSS-20B", "reads the report"],
        ["Fallback", "TF-IDF + LogReg", "answers if AI is down"],
        ["Database", "Supabase (PostgreSQL)", "reports + predictions"],
        ["Cache", "SQLite", "on-instance, repeat calls"],
    ], size=11, row_h=0.44)

    panel(s, 7.0, 1.12, 2.85, 4.15, "Flow", GREEN)
    # Boxes first, arrows second - drawing an arrow before the box below it puts the box
    # on top and the arrow disappears.
    steps = ["Report", "AI / NLP", "Hazard", "LSR", "Control",
             "Severity", "SIF Decision", "Risk Priority"]
    box_h, pitch = 0.3, 0.42
    for i, step in enumerate(steps):
        y = 1.82 + i * pitch
        rect(s, 7.22, y, 2.4, box_h, fill=WHITE, line=LINE)
        tf = tbox(s, 7.22, y, 2.4, box_h, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, step, size=11.5, bold=True, color=NAVY, first=True, after=0,
             align=PP_ALIGN.CENTER)
    for i in range(len(steps) - 1):
        y = 1.82 + i * pitch + box_h
        tf = tbox(s, 7.22, y - 0.02, 2.4, pitch - box_h + 0.04,
                  anchor=MSO_ANCHOR.MIDDLE)
        para(tf, "↓", size=11, bold=True, color=GREEN, first=True, after=0,
             align=PP_ALIGN.CENTER)

    panel(s, 10.0, 1.12, 2.83, 4.15, "SIF Rule", PURPLE)
    rect(s, 10.22, 1.9, 2.39, 1.5, fill=WHITE, line=LINE)
    tf = tbox(s, 10.32, 2.05, 2.19, 1.25)
    para(tf, "Hazard = YES", size=13, bold=True, color=NAVY, first=True, after=7,
         align=PP_ALIGN.CENTER)
    para(tf, "+  Control =\nAbsent / Failed", size=13, bold=True, color=NAVY, after=7,
         align=PP_ALIGN.CENTER)
    para(tf, "+  Severity ≥ 4", size=13, bold=True, color=NAVY, after=0,
         align=PP_ALIGN.CENTER)
    rect(s, 10.22, 3.52, 2.39, 0.42, fill=PURPLE)
    tf = tbox(s, 10.22, 3.62, 2.39, 0.28)
    para(tf, "→   SIF", size=13.5, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.CENTER)
    tf = tbox(s, 10.22, 4.08, 2.39, 1.0)
    para(tf, "All three, or it is not flagged. The flag is computed from the gates, "
             "never typed.", size=10, color=MUTED, first=True, after=0,
         align=PP_ALIGN.CENTER)

    # System architecture, as four deployed tiers. The band underneath used to carry three
    # lines of deployment prose; the same space says more as a diagram, and "where does the
    # LLM sit / what happens when it fails" is the pair of questions judges actually ask.
    rect(s, 0.5, 5.42, 12.33, 1.42, fill=BAND, line=LINE)
    tf = tbox(s, 0.78, 5.56, 11.8, 0.28)
    para(tf, "SYSTEM ARCHITECTURE", size=11.5, bold=True, color=NAVY, first=True, after=0)

    tiers = [
        ("CLIENT", "React SPA", "worker screen  ·  admin triage", BLUE),
        ("API", "FastAPI on Render", "REST  ·  Pydantic validation  ·  CORS", NAVY),
        ("MODELS", "Groq GPT-OSS-20B", "with local TF-IDF fallback", GREEN),
        ("DATA", "Supabase PostgreSQL", "reports · predictions · labels", PURPLE),
    ]
    for i, (tier, name, sub, col) in enumerate(tiers):
        x = 0.78 + i * 3.02
        rect(s, x, 5.9, 2.72, 0.78, fill=WHITE, line=LINE)
        rect(s, x, 5.9, 2.72, 0.05, fill=col)
        t = tbox(s, x + 0.12, 5.96, 2.48, 0.68)
        para(t, tier, size=9, bold=True, color=col, first=True, after=2,
             align=PP_ALIGN.CENTER)
        para(t, name, size=12, bold=True, color=INK, after=2, align=PP_ALIGN.CENTER)
        para(t, sub, size=8.5, color=MUTED, after=0, align=PP_ALIGN.CENTER)
        if i < 3:
            t = tbox(s, x + 2.74, 6.14, 0.26, 0.3)
            para(t, "→", size=14, bold=True, color=BLUE, first=True, after=0,
                 align=PP_ALIGN.CENTER)

    # ==================== 4. FEASIBILITY =================================
    s = blank(prs)
    chrome(s, "FEASIBILITY AND VIABILITY", 4)

    panel(s, 0.5, 1.15, 5.3, 2.78, "Feasible because", GREEN)
    bullets(s, 0.82, 1.9, 4.7, ["Uses existing incident reports",
                                "No specialized hardware",
                                "API-based & scalable",
                                "LLM + local fallback",
                                "Human-in-the-loop"], size=14, gap=11)

    tf = tbox(s, 6.05, 1.2, 6.8, 0.3)
    para(tf, "CHALLENGES  →  SOLUTIONS", size=12, bold=True, color=NAVY, first=True,
         after=0)
    table(s, 6.05, 1.56, 6.78, [2.9, 3.88], [
        ["Challenge", "Solution"],
        ["Unstructured text", "LLM reads it against a written rubric"],
        ["Ambiguous controls", "4-state classification, silence ≠ absent"],
        ["API failure or rate limit", "Retry inside a deadline, then local model"],
        ["Domain variation", "Tested on %d real OSHA reports - F1 %s, an honest gap" % (OSHA_N, OSHA_F1)],
        ["Model version changes", "Dashboard scopes to one version at a time"],
    ], size=11.5, row_h=0.45)

    rect(s, 0.5, 4.55, 12.33, 2.27, fill=BAND, line=LINE)
    tf = tbox(s, 0.85, 4.74, 11.7, 0.3)
    para(tf, "HUMAN-IN-THE-LOOP — the system ranks, a person decides", size=12.5,
         bold=True, color=NAVY, first=True, after=0)
    for i, (step, sub) in enumerate([
            ("Report arrives", "worker types or speaks it"),
            ("AI classifies", "three gates + reasoning"),
            ("Queue reorders", "highest risk first"),
            ("Officer reviews", "reads the reasoning"),
            ("Officer decides", "dispatch or archive")]):
        x = 0.85 + i * 2.38
        rect(s, x, 5.18, 2.12, 0.88, fill=WHITE, line=LINE)
        tf = tbox(s, x + 0.1, 5.18, 1.92, 0.88, anchor=MSO_ANCHOR.MIDDLE)
        para(tf, step, size=12, bold=True, color=NAVY, first=True, after=2,
             align=PP_ALIGN.CENTER)
        para(tf, sub, size=9.5, color=MUTED, after=0, align=PP_ALIGN.CENTER)
        if i < 4:
            tf = tbox(s, x + 2.14, 5.5, 0.24, 0.3)
            para(tf, "→", size=15, bold=True, color=BLUE, first=True, after=0,
                 align=PP_ALIGN.CENTER)
    tf = tbox(s, 0.85, 6.25, 11.7, 0.34)
    para(tf, "SANKET never closes a report. It only changes the order they are read in.",
         size=13, bold=True, color=RED, first=True, after=0)

    # ==================== 5. IMPACT ======================================
    s = blank(prs)
    chrome(s, "IMPACT AND BENEFITS", 5)

    panel(s, 0.5, 1.12, 6.05, 2.52, "Potential impact on target audience", NAVY)
    bullets(s, 0.85, 1.88, 5.4, ["Early detection of SIF precursors in OIL safety reports",
                                 "Prioritized review of high-risk incidents",
                                 "Faster identification of recurring hazards across "
                                 "sites / activities"], size=14, gap=13)

    panel(s, 6.78, 1.12, 6.05, 2.52, "Benefits", GREEN)
    bullets(s, 7.13, 1.88, 5.4, ["Safety: proactive intervention before serious incidents",
                                 "Operational: reduces manual screening effort",
                                 "Economic: prevents costly injuries and downtime",
                                 "Scalable: handles large volumes of reports"],
            size=14, gap=13)

    tf = tbox(s, 0.5, 3.82, 12.33, 0.3)
    para(tf, "MEASURED ON OUR PROTOTYPE DATA", size=12, bold=True, color=NAVY,
         first=True, after=0)
    table(s, 0.5, 4.12, 12.33, [3.4, 2.6, 6.33], [
        ["What", "Value", "Meaning"],
        ["Labelled corpus", "%d reports" % (SYNTHETIC_N + OSHA_N),
         "%d written for the prototype + %d real OSHA narratives"
         % (SYNTHETIC_N, OSHA_N)],
        ["Human reviews", "%d" % (2 * (SYNTHETIC_N + OSHA_N)),
         "every report read by two people against one written rubric"],
        ["Agreed gold labels", "%d" % GOLD_N,
         "%d reports still being adjudicated" % OPEN_TIEBREAKS],
        ["Reviewer agreement", "%s  (kappa %s)" % (CEILING_PCT, CEILING_KAPPA),
         "on a %d-report sample reviewed independently" % CEILING_N],
    ], size=11.5, row_h=0.4)

    rect(s, 0.5, 6.12, 12.33, 0.72, fill=BLUE)
    tf = tbox(s, 0.5, 6.32, 12.33, 0.36)
    para(tf, "Safety Reports  →  SIF Precursors  →  Risk Prioritization  →  "
             "Early Action  →  Safer Operations",
         size=15.5, bold=True, color=WHITE, first=True, after=0, align=PP_ALIGN.CENTER)

    # ==================== 6. RESEARCH AND REFERENCES =====================
    s = blank(prs)
    chrome(s, "RESEARCH  AND REFERENCES", 6)

    tf = tbox(s, 0.5, 1.1, 12.33, 0.3)
    para(tf, "Research:", size=14, bold=True, color=NAVY, first=True, after=4)
    para(tf, "IOGP Life-Saving Rules  •  DEKRA SIF Framework  •  EEI SIF Model",
         size=14, after=0)

    tf = tbox(s, 0.5, 1.78, 12.33, 0.3)
    para(tf, "Data:", size=14, bold=True, color=NAVY, first=True, after=4)
    para(tf, "%d synthetic safety reports  +  %d OSHA severe-injury reports  ·  "
             "%d human labels" % (SYNTHETIC_N, OSHA_N, GOLD_N), size=14, after=0)

    tf = tbox(s, 0.5, 2.5, 12.33, 0.3)
    para(tf, "Prototype Evaluation:", size=14, bold=True, color=NAVY, first=True, after=0)
    table(s, 0.5, 2.88, 12.33, [3.9, 2.9, 5.53], [
        ["Measure", "Result", "How it was measured"],
        ["Human agreement ceiling", "%s  ·  kappa %s" % (CEILING_PCT, CEILING_KAPPA),
         "two reviewers, working separately, n=%d" % CEILING_N],
        ["TF-IDF baseline (F1)", "%s  %s" % (BASELINE_F1, BASELINE_SD),
         "5-fold cross-validation, n=%d" % BASELINE_N],
        ["LLM classifier (F1)", "being re-measured",
         "previous figure withdrawn — see note below"],
    ], size=12, row_h=0.46)

    rect(s, 0.5, 4.78, 12.33, 0.72, fill=RGBColor(0xFD, 0xF2, 0xEF),
         line=RGBColor(0xE5, 0xC3, 0xBC))
    tf = tbox(s, 0.85, 4.9, 11.7, 0.52)
    para(tf, "Why the LLM figure is withdrawn", size=11.5, bold=True, color=RED,
         first=True, after=3)
    para(tf, "We found one of our held-out test reports written into the AI prompt, so the "
             "old score was not a fair test. We pulled the number rather than ship it.",
         size=12, color=INK, after=0)

    tf = tbox(s, 0.5, 5.72, 12.33, 0.3)
    para(tf, "What the ceiling means", size=14, bold=True, color=NAVY, first=True, after=5)
    para(tf, "Two people applying the same rubric to the same reports agreed %s of the "
             "time. No classifier scored against those labels can honestly claim to be "
             "more consistent than the people who made them." % CEILING_PCT,
         size=13, after=0)

    rect(s, 0.5, 6.5, 12.33, 0.42, fill=BAND, line=LINE)
    tf = tbox(s, 0.8, 6.58, 11.8, 0.28)
    para(tf, "Live prototype:  %s        GitHub:  SANKET — AI-powered SIF precursor "
             "detection" % LIVE_APP, size=12.5, bold=True, color=NAVY, first=True, after=0)

    out = "docs/SANKET-SIH2026-Idea-Submission.pptx"
    prs.save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    build()
