"""
build_deck.py

Build the SIH 2026 idea-submission deck, in the official SIH template, with the numbers that
are actually true.

    python build_deck.py        ->  docs/SANKET-SIH2026-Idea-Submission.pptx

TEMPLATE FIDELITY

Matches the supplied SIH2026-IDEA-Presentation-Format: white ground, centred bold serif title,
the team pill top-left, the official SIH 2026 logo top-right, and the blue footer band reading
"@SIH Idea submission- Template" with the slide number on the right. The footer blue is
RGB(0,112,192), sampled from the template PDF rather than guessed, and the logo is the real
asset lifted out of it - not a redraw.

WHY A SCRIPT AND NOT A HAND-EDITED FILE

Every figure lives in a named constant below, each traceable to the script that produced it.
This deck has carried a wrong number three times - a withdrawn agreement ceiling, a withdrawn
LLM F1, and a rubric attribution for work that never happened - and each time the figure had
been retyped into a slide by hand and then quietly diverged from the repo. Regenerating means
the deck cannot drift again: change the constant, rebuild, and every slide moves together.

WHAT IT DELIBERATELY DOES NOT CLAIM

No LLM F1 - every one we have measured came from a prompt containing a held-out report, so
they are all withdrawn until the re-classification finishes. No accuracy figure. No compliance
or certification claim. And no "Oil India system" framing: this is a prototype built for their
problem statement, which is a different sentence and the only one that is true.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --- every number that reaches a slide, and the script that produced it ----
CEILING_PCT = "97.4%"           # score_recheck.py
CEILING_KAPPA = "0.947"         # score_recheck.py
CEILING_N = 38                  # 40 sampled, 2 excluded as incomplete
BASELINE_F1 = "0.754 ± 0.077"   # eval/run_eval.py --no-llm, 5-fold CV
BASELINE_PRAUC = "0.847"
BASELINE_N = 114
OSHA_F1 = "0.118"               # score_stored_predictions.py
OSHA_N = 30
SYNTHETIC_N = 150
GOLD_N = 173
PRECURSOR_RATE = "58.7%"        # 84/143 in the gold set
REPORTS_PER_DAY = "63"          # 200,000 tokens/day / ~3,150 per report

LOGO = "docs/assets/sih-2026-logo.png"

# --- template palette, sampled from the supplied PDF -----------------------
FOOTER_BLUE = RGBColor(0x00, 0x70, 0xC0)
TITLE_INK = RGBColor(0x1F, 0x38, 0x64)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x59, 0x59, 0x59)
ACCENT = RGBColor(0x00, 0x70, 0xC0)
FLAG = RGBColor(0xB4, 0x3A, 0x2E)
GREEN = RGBColor(0x1E, 0x7A, 0x5E)
PILL = RGBColor(0x7B, 0x5E, 0xA7)
CARD = RGBColor(0xF4, 0xF7, 0xFA)
LINE = RGBColor(0xD5, 0xDF, 0xE8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = 13.333, 7.5
SERIF = "Times New Roman"
SANS = "Calibri"


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def tbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return tf


def para(tf, text, size=15, bold=False, color=INK, after=6, first=False,
         align=PP_ALIGN.LEFT, font=SANS, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.alignment = align
    p.space_after = Pt(after)
    for r in p.runs:
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
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


def chrome(slide, title, n, team_pill=True):
    """The SIH template furniture: pill, centred serif title, logo, footer band."""
    if team_pill:
        p = rect(slide, 0.28, 0.22, 1.5, 0.62, fill=WHITE, line=PILL,
                 shape=MSO_SHAPE.OVAL)
        tf = p.text_frame
        tf.word_wrap = True
        para(tf, "Signal-0", size=13, color=INK, first=True, after=0,
             align=PP_ALIGN.CENTER, font=SANS)

    tf = tbox(slide, 1.95, 0.2, 9.0, 0.95, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, title.upper(), size=33, bold=True, color=TITLE_INK, first=True,
         after=0, align=PP_ALIGN.CENTER, font=SERIF)

    if os.path.exists(LOGO):
        slide.shapes.add_picture(LOGO, Inches(11.05), Inches(0.18), height=Inches(0.92))

    rect(slide, 0, H - 0.42, W, 0.42, fill=FOOTER_BLUE)
    tf = tbox(slide, 0, H - 0.36, W, 0.3)
    para(tf, "@SIH Idea submission- Template", size=11, color=WHITE, first=True,
         after=0, align=PP_ALIGN.CENTER, font=SANS)
    tf = tbox(slide, W - 1.1, H - 0.36, 0.7, 0.3)
    para(tf, str(n), size=11, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.RIGHT, font=SANS)


def card(slide, x, y, w, h, title, accent=ACCENT):
    rect(slide, x, y, w, h, fill=CARD, line=LINE)
    rect(slide, x, y, w, 0.045, fill=accent)
    tf = tbox(slide, x + 0.3, y + 0.24, w - 0.6, 0.35)
    para(tf, title.upper(), size=12, bold=True, color=accent, first=True, after=0)


def bullets(slide, x, y, w, items, size=14, gap=9, lead="•  "):
    tf = tbox(slide, x, y, w, 0.4)
    for i, it in enumerate(items):
        para(tf, lead + it, size=size, after=gap, first=(i == 0))
    return tf


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ======================= 1. TITLE PAGE ================================
    s = blank(prs)
    tf = tbox(s, 0.8, 0.35, 9.6, 1.4)
    para(tf, "SMART INDIA HACKATHON 2026", size=36, bold=True, color=TITLE_INK,
         first=True, after=2, align=PP_ALIGN.CENTER, font=SERIF)
    para(tf, "TITLE PAGE", size=30, bold=True, color=TITLE_INK, after=0,
         align=PP_ALIGN.CENTER, font=SERIF)
    if os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, Inches(10.5), Inches(0.3), height=Inches(1.15))

    tf = tbox(s, 0.85, 2.15, 8.6, 4.4)
    para(tf, "Problem Statement ID –  SIH26165", size=16, bold=True, first=True, after=12)
    para(tf, "Problem Statement Title –  AI/NLP Engine to Detect Serious Injury & "
             "Fatality (SIF) Precursors in OIL's Unsafe-Act/Unsafe-Condition and "
             "Near-Miss Reports", size=16, bold=True, after=12)
    para(tf, "Theme –  Smart Automation", size=16, bold=True, after=12)
    para(tf, "PS Category –  Software", size=16, bold=True, after=12)
    para(tf, "Team ID –  ____", size=16, bold=True, after=12)
    para(tf, "Team Name –  Signal-0", size=16, bold=True, after=0)

    rect(s, 9.7, 2.15, 3.1, 1.75, fill=CARD, line=LINE)
    rect(s, 9.7, 2.15, 3.1, 0.05, fill=FOOTER_BLUE)
    tf = tbox(s, 9.95, 2.5, 2.6, 1.2)
    para(tf, "SANKET", size=30, bold=True, color=TITLE_INK, first=True, after=3,
         align=PP_ALIGN.CENTER, font=SERIF)
    para(tf, "SIF Precursor Detection", size=11.5, color=MUTED, after=0,
         align=PP_ALIGN.CENTER)

    # The lower half of the SIH title page is empty by default. One line on what the
    # thing actually does earns that space better than whitespace does.
    rect(s, 0.85, 5.42, 11.95, 1.22, fill=FOOTER_BLUE)
    tf = tbox(s, 1.25, 5.64, 11.15, 0.85)
    para(tf, "Reads a free-text safety report and answers one question: could this have "
             "killed someone?", size=18, bold=True, color=WHITE, first=True, after=6,
         align=PP_ALIGN.CENTER)
    para(tf, "Three gates  ·  hazard, control status, plausible severity  ·  tagged to the "
             "IOGP Life-Saving Rules",
         size=13, color=RGBColor(0xCF, 0xE4, 0xF5), after=0, align=PP_ALIGN.CENTER)

    # ======================= 2. SANKET ====================================
    s = blank(prs)
    chrome(s, "SANKET — From Incident Narratives to Early Safety Warnings", 2)

    tf = tbox(s, 0.55, 1.32, 12.2, 0.5)
    para(tf, "SANKET analyzes safety and near-miss reports using AI to detect potential "
             "Serious Injury & Fatality (SIF) precursors.",
         size=16, bold=True, color=TITLE_INK, first=True, after=0)

    card(s, 0.55, 1.98, 5.95, 2.5, "Identifies")
    bullets(s, 0.88, 2.52, 5.35, [
        "Hazard & Life-Saving Rule",
        "Control status",
        "Severity (1–5)",
        "SIF Precursor: Yes / No",
        "Evidence & reasoning",
    ], gap=10)

    card(s, 6.83, 1.98, 5.95, 2.5, "Innovation")
    bullets(s, 7.16, 2.52, 5.35, [
        "LLM + ML hybrid approach",
        "Explainable risk assessment",
        "One-Change severity rule",
        "Prioritized safety-review queue",
    ], gap=10)

    rect(s, 0.55, 4.72, 12.23, 2.05, fill=WHITE, line=LINE)
    tf = tbox(s, 0.88, 4.94, 11.6, 0.35)
    para(tf, "THE DECISION, MADE VISIBLE", size=12, bold=True, color=ACCENT,
         first=True, after=0)
    for i, (g, q, a) in enumerate([
            ("GATE 1", "Hazard present?", "yes / no / insufficient"),
            ("GATE 2", "Was a control doing its job?", "absent / failed / present / unclear"),
            ("GATE 3", "Plausible worst case?", "severity 1–5")]):
        x = 0.88 + i * 3.95
        rect(s, x, 5.42, 3.55, 1.12, fill=CARD, line=LINE)
        tf = tbox(s, x + 0.24, 5.6, 3.1, 0.85)
        para(tf, g, size=10, bold=True, color=ACCENT, first=True, after=3)
        para(tf, q, size=13, bold=True, after=3)
        para(tf, a, size=10, color=MUTED, after=0)
        if i < 2:
            at = tbox(s, x + 3.58, 5.82, 0.34, 0.35)
            para(at, "→", size=17, bold=True, color=ACCENT, first=True, after=0,
                 align=PP_ALIGN.CENTER)

    # ======================= 3. TECHNICAL APPROACH ========================
    s = blank(prs)
    chrome(s, "Technical Approach", 3)

    card(s, 0.55, 1.42, 3.75, 3.55, "Tech")
    bullets(s, 0.88, 1.98, 3.2, ["React", "FastAPI · Python", "Groq · GPT-OSS-20B",
                                 "TF-IDF + Logistic Regression", "Supabase (Postgres)"],
            gap=12)
    tf = tbox(s, 0.88, 4.42, 3.2, 0.45)
    para(tf, "SQLite is the on-instance classification cache only.",
         size=9.5, color=MUTED, first=True, after=0, italic=True)

    card(s, 4.62, 1.42, 4.05, 3.55, "Flow")
    for i, st in enumerate(["Report", "AI / NLP", "Hazard", "Life-Saving Rule",
                            "Control status", "Severity", "SIF Decision", "Risk Priority"]):
        col = ACCENT if i in (0, 7) else INK
        tf = tbox(s, 4.98, 1.98 + i * 0.365, 3.4, 0.3)
        para(tf, "%d.  %s" % (i + 1, st), size=13, bold=(i in (0, 7)), color=col,
             first=True, after=0)

    card(s, 8.99, 1.42, 3.79, 3.55, "SIF Rule", accent=FLAG)
    tf = tbox(s, 9.32, 2.02, 3.2, 1.3)
    para(tf, "Hazard = YES", size=15, bold=True, first=True, after=7)
    para(tf, "+   Control = Absent / Failed", size=15, bold=True, after=7)
    para(tf, "+   Severity ≥ 4", size=15, bold=True, after=0)
    rect(s, 9.32, 3.5, 3.15, 0.48, fill=FLAG)
    tf = tbox(s, 9.32, 3.6, 3.15, 0.33)
    para(tf, "→   SIF PRECURSOR", size=14, bold=True, color=WHITE, first=True,
         after=0, align=PP_ALIGN.CENTER)
    tf = tbox(s, 9.32, 4.16, 3.15, 0.7)
    para(tf, "Computed from the gates, never typed. A database CHECK constraint enforces "
             "it, so no model can emit a contradicting row.",
         size=9.5, color=MUTED, first=True, after=0)

    rect(s, 0.55, 5.24, 12.23, 1.42, fill=CARD, line=LINE)
    tf = tbox(s, 0.9, 5.46, 11.55, 1.0)
    para(tf, "DESIGNED TO DEGRADE, NOT TO FAIL", size=11, bold=True, color=ACCENT,
         first=True, after=6)
    para(tf, "Every call runs under a hard deadline. A rate-limited request retries inside "
             "that deadline, then a locally trained TF-IDF model answers instead — and the "
             "response says so. The API reports which classifier actually served it, so a "
             "degraded answer is visible rather than silent.", size=12.5, after=0)

    # ======================= 4. FEASIBILITY ===============================
    s = blank(prs)
    chrome(s, "Feasibility and Viability", 4)

    card(s, 0.55, 1.42, 5.95, 3.2, "Feasible because")
    bullets(s, 0.88, 1.98, 5.35, [
        "Uses existing incident reports",
        "No specialized hardware",
        "API-based & scalable",
        "LLM + local fallback",
        "Human-in-the-loop",
    ], gap=11)

    card(s, 6.83, 1.42, 5.95, 3.2, "Challenges → Solutions")
    bullets(s, 7.16, 1.98, 5.35, [
        "Unstructured text → LLM analysis",
        "Ambiguous controls → 4-state classification",
        "API failure → retry inside a deadline, then fallback",
        "Domain variation → tested on %d real OSHA narratives (F1 %s)"
        % (OSHA_N, OSHA_F1),
    ], gap=11)

    rect(s, 0.55, 4.88, 12.23, 1.78, fill=RGBColor(0xFD, 0xF3, 0xF1),
         line=RGBColor(0xE8, 0xC9, 0xC3))
    tf = tbox(s, 0.9, 5.1, 11.55, 1.4)
    para(tf, "THE CONSTRAINT WE ACTUALLY HIT", size=11, bold=True, color=FLAG,
         first=True, after=6)
    para(tf, "Not compute — tokens. The free tier caps us near %s reports a day, so a full "
             "re-classification takes days, not minutes. Everything downstream is built "
             "around that: the classifier is resumable, refuses to store a fallback answer "
             "as though it were real, and the dashboard keeps reporting on the last model "
             "version that covers the corpus instead of going blank mid-migration."
             % REPORTS_PER_DAY, size=12.5, after=0)

    # ======================= 5. IMPACT ====================================
    s = blank(prs)
    chrome(s, "Impact and Benefits", 5)

    card(s, 0.55, 1.42, 5.95, 3.0, "Potential impact")
    bullets(s, 0.88, 1.98, 5.35, [
        "Early detection of SIF precursors in OIL safety reports",
        "Prioritized review of high-risk incidents",
        "Ranks sites by precursor RATE, not count — so a site is not "
        "punished for reporting diligently",
    ], gap=12)

    card(s, 6.83, 1.42, 5.95, 3.0, "Benefits")
    tf = tbox(s, 7.16, 1.98, 5.35, 2.3)
    for i, (k, v) in enumerate([
            ("Safety", "proactive intervention before serious incidents"),
            ("Operational", "removes the manual first-pass screen"),
            ("Economic", "prevents costly injuries, incidents and downtime"),
            ("Scalable", "ten reports or ten thousand, same pipeline")]):
        para(tf, "•  %s: %s" % (k, v), size=14, after=12, first=(i == 0))

    rect(s, 0.55, 4.68, 12.23, 0.9, fill=FOOTER_BLUE)
    tf = tbox(s, 0.55, 4.88, 12.23, 0.5)
    para(tf, "Safety Reports  →  SIF Precursors  →  Risk Prioritization  →  "
             "Early Action  →  Safer Operations",
         size=16, bold=True, color=WHITE, first=True, after=0, align=PP_ALIGN.CENTER)

    tf = tbox(s, 0.55, 5.84, 12.23, 0.6)
    para(tf, "It never closes a report. It reorders the queue a human already reads, and "
             "puts the ones with fatal potential at the top.",
         size=13, color=MUTED, first=True, after=0, align=PP_ALIGN.CENTER, italic=True)

    # ======================= 6. RESEARCH & REFERENCES =====================
    s = blank(prs)
    chrome(s, "Research and References", 6)

    tf = tbox(s, 0.55, 1.35, 12.23, 0.85)
    para(tf, "Research:", size=13, bold=True, color=ACCENT, first=True, after=3)
    para(tf, "IOGP Life-Saving Rules  ·  DEKRA SIF Framework  ·  EEI SIF Model",
         size=14, after=9)
    para(tf, "Data:", size=13, bold=True, color=ACCENT, after=3)
    para(tf, "%d synthetic reports  +  %d real OSHA severe-injury narratives  ·  "
             "%d gold labels" % (SYNTHETIC_N, OSHA_N, GOLD_N), size=14, after=0)

    tf = tbox(s, 0.55, 2.92, 12.23, 0.35)
    para(tf, "PROTOTYPE EVALUATION", size=13, bold=True, color=ACCENT, first=True, after=0)

    for i, (col, label, big, unit, sub) in enumerate([
            (GREEN, "HUMAN CEILING", CEILING_KAPPA, "Cohen's kappa",
             "%s agreement · two annotators, independently · n=%d" % (CEILING_PCT, CEILING_N)),
            (ACCENT, "TF-IDF BASELINE", BASELINE_F1.split()[0], "F1  " + BASELINE_F1.split(maxsplit=1)[1],
             "5-fold cross-validated · PR-AUC %s · n=%d" % (BASELINE_PRAUC, BASELINE_N)),
            (MUTED, "OSHA GENERALISATION", OSHA_F1, "F1",
             "real narratives nobody on the team wrote · n=%d, too small to conclude from" % OSHA_N)]):
        x = 0.55 + i * 4.12
        rect(s, x, 3.34, 3.9, 1.66, fill=WHITE, line=LINE)
        rect(s, x, 3.34, 3.9, 0.05, fill=col)
        tf = tbox(s, x + 0.28, 3.54, 3.35, 0.28)
        para(tf, label, size=9.5, bold=True, color=col, first=True, after=0)
        tf = tbox(s, x + 0.28, 3.84, 3.35, 0.52)
        para(tf, big, size=29, bold=True, color=INK, first=True, after=0)
        tf = tbox(s, x + 1.62, 4.0, 2.0, 0.3)
        para(tf, unit, size=10.5, color=MUTED, first=True, after=0)
        tf = tbox(s, x + 0.28, 4.44, 3.35, 0.5)
        para(tf, sub, size=9, color=MUTED, first=True, after=0)

    rect(s, 0.55, 5.16, 12.23, 0.62, fill=RGBColor(0xFD, 0xF3, 0xF1),
         line=RGBColor(0xE8, 0xC9, 0xC3))
    tf = tbox(s, 0.9, 5.3, 11.6, 0.4)
    para(tf, "LLM figure withdrawn, deliberately — we found a held-out report inside our "
             "own prompt and pulled the number rather than ship it. Re-measurement in "
             "progress.", size=11.5, bold=True, color=FLAG, first=True, after=0)

    tf = tbox(s, 0.55, 5.94, 12.23, 0.9)
    para(tf, "STATED UP FRONT, BECAUSE A JUDGE WILL FIND THEM", size=9.5, bold=True,
         color=MUTED, first=True, after=4)
    para(tf, "Our precursor rate is %s, not the 20–25%% the problem statement cites — our "
             "generator centred every synthetic report on a hazard. The ceiling is a "
             "%d-report re-label, so we quote the subset. We report no accuracy figure, and "
             "never a baseline scored on its own training data."
             % (PRECURSOR_RATE, CEILING_N), size=10, color=MUTED, after=6)
    para(tf, "GitHub:  SANKET — AI-powered SIF precursor detection", size=11, bold=True,
         after=0)

    out = "docs/SANKET-SIH2026-Idea-Submission.pptx"
    prs.save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    build()
