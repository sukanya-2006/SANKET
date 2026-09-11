"""
build_deck.py

Build the SIH 2026 idea-submission deck, in the official SIH template, with the numbers that
are actually true.

    python build_deck.py        ->  docs/SANKET-SIH2026-Idea-Submission.pptx

TEMPLATE FIDELITY AND THE SUBMISSION RULES

The template's own "Important Instructions" slide sets the brief, and this file follows it:
six slides including the title, no paragraphs (points, diagrams and infographics instead),
precise wording, and PDF as the upload format. The furniture matches the supplied
SIH2026-IDEA-Presentation-Format: white ground, centred bold serif title, the team pill
top-left, the official SIH 2026 logo top-right, and the blue footer band reading "@SIH Idea
submission- Template" with the slide number on the right. The footer blue is RGB(0,112,192),
sampled from the template PDF rather than guessed, and the logo is the real asset lifted out
of it.

"No paragraphs" is the rule that shapes every slide here. Anything that wanted to be prose is
either a labelled row, a chip, a small diagram, or it is cut.

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
BASELINE_F1 = "0.754"           # eval/run_eval.py --no-llm, 5-fold CV
BASELINE_SD = "± 0.077"
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
BLUE = RGBColor(0x00, 0x70, 0xC0)
TITLE_INK = RGBColor(0x1F, 0x38, 0x64)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x55, 0x5E, 0x68)
FLAG = RGBColor(0xB4, 0x3A, 0x2E)
GREEN = RGBColor(0x1E, 0x7A, 0x5E)
AMBER = RGBColor(0xA1, 0x6A, 0x0B)
PILL = RGBColor(0x7B, 0x5E, 0xA7)
CARD = RGBColor(0xF3, 0xF7, 0xFB)
TINT = RGBColor(0xE4, 0xEF, 0xF8)
LINE = RGBColor(0xC9, 0xD8, 0xE6)
WARN_BG = RGBColor(0xFD, 0xF2, 0xEF)
WARN_LN = RGBColor(0xE5, 0xC3, 0xBC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = 13.333, 7.5
SERIF = "Times New Roman"
SANS = "Calibri"
FOOT = 7.08          # top of the footer band


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def tbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return tf


def para(tf, text, size=14, bold=False, color=INK, after=6, first=False,
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


def chip(slide, x, y, w, h, text, fill, fg=WHITE, size=11.5, bold=True):
    sh = rect(slide, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    try:
        sh.adjustments[0] = 0.2
    except (IndexError, KeyError):
        pass
    tf = sh.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    para(tf, text, size=size, bold=bold, color=fg, first=True, after=0,
         align=PP_ALIGN.CENTER)
    return sh


def arrow(slide, x, y, w=0.3):
    tf = tbox(slide, x, y, w, 0.3)
    para(tf, "→", size=16, bold=True, color=BLUE, first=True, after=0,
         align=PP_ALIGN.CENTER)


def chrome(slide, title, n):
    """The SIH template furniture: pill, centred serif title, logo, footer band."""
    p = rect(slide, 0.26, 0.2, 1.42, 0.58, fill=WHITE, line=PILL, shape=MSO_SHAPE.OVAL)
    tf = p.text_frame
    tf.word_wrap = True
    para(tf, "Signal-0", size=12.5, color=INK, first=True, after=0, align=PP_ALIGN.CENTER)

    # Long titles wrap to two lines and crowd whatever sits under them, so shrink instead.
    size = 31 if len(title) <= 34 else (26 if len(title) <= 48 else 23)
    tf = tbox(slide, 1.85, 0.14, 9.1, 0.9, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, title.upper(), size=size, bold=True, color=TITLE_INK, first=True, after=0,
         align=PP_ALIGN.CENTER, font=SERIF)

    if os.path.exists(LOGO):
        slide.shapes.add_picture(LOGO, Inches(11.1), Inches(0.16), height=Inches(0.85))

    rect(slide, 0, FOOT, W, H - FOOT, fill=BLUE)
    tf = tbox(slide, 0, FOOT + 0.06, W, 0.3)
    para(tf, "@SIH Idea submission- Template", size=10.5, color=WHITE, first=True,
         after=0, align=PP_ALIGN.CENTER)
    tf = tbox(slide, W - 1.05, FOOT + 0.06, 0.65, 0.3)
    para(tf, str(n), size=10.5, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, title, accent=BLUE, fill=CARD):
    rect(slide, x, y, w, h, fill=fill, line=LINE)
    rect(slide, x, y, w, 0.042, fill=accent)
    tf = tbox(slide, x + 0.26, y + 0.19, w - 0.52, 0.3)
    para(tf, title.upper(), size=11, bold=True, color=accent, first=True, after=0)


def points(slide, x, y, w, items, size=13.5, gap=8, lead="•  "):
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
    tf = tbox(s, 0.8, 0.3, 9.5, 1.3)
    para(tf, "SMART INDIA HACKATHON 2026", size=34, bold=True, color=TITLE_INK,
         first=True, after=2, align=PP_ALIGN.CENTER, font=SERIF)
    para(tf, "TITLE PAGE", size=28, bold=True, color=TITLE_INK, after=0,
         align=PP_ALIGN.CENTER, font=SERIF)
    if os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, Inches(10.6), Inches(0.28), height=Inches(1.05))

    tf = tbox(s, 0.85, 1.95, 8.5, 3.3)
    for label, value in [
            ("Problem Statement ID", "SIH26165"),
            ("Problem Statement Title", "AI/NLP Engine to Detect Serious Injury & Fatality "
                                        "(SIF) Precursors in OIL's Unsafe-Act / "
                                        "Unsafe-Condition and Near-Miss Reports"),
            ("Theme", "Smart Automation"),
            ("PS Category", "Software"),
            ("Team ID", "____"),
            ("Team Name", "Signal-0")]:
        para(tf, "%s  –  %s" % (label, value), size=15.5, bold=True,
             first=(label == "Problem Statement ID"), after=13)

    rect(s, 9.62, 1.95, 3.18, 1.62, fill=CARD, line=LINE)
    rect(s, 9.62, 1.95, 3.18, 0.05, fill=BLUE)
    tf = tbox(s, 9.85, 2.28, 2.72, 1.1)
    para(tf, "SANKET", size=29, bold=True, color=TITLE_INK, first=True, after=2,
         align=PP_ALIGN.CENTER, font=SERIF)
    para(tf, "SIF Precursor Detection", size=11, color=MUTED, after=0,
         align=PP_ALIGN.CENTER)

    # The template leaves the lower half of the title page empty. One line on what the
    # system does, plus the three gates as chips, earns that space better than whitespace.
    rect(s, 0.85, 5.32, 11.95, 1.5, fill=BLUE)
    tf = tbox(s, 1.2, 5.52, 11.25, 0.45)
    para(tf, "Reads a free-text safety report and answers one question: "
             "could this have killed someone?",
         size=17, bold=True, color=WHITE, first=True, after=0, align=PP_ALIGN.CENTER)
    for i, t in enumerate(["HAZARD", "CONTROL STATUS", "PLAUSIBLE SEVERITY"]):
        chip(s, 2.55 + i * 3.0, 6.12, 2.6, 0.44, t, TINT, fg=TITLE_INK, size=11.5)
        if i < 2:
            tf = tbox(s, 5.2 + i * 3.0, 6.16, 0.35, 0.35)
            para(tf, "→", size=15, bold=True, color=WHITE, first=True, after=0,
                 align=PP_ALIGN.CENTER)

    # ==================== 2. SANKET ======================================
    s = blank(prs)
    chrome(s, "SANKET — Early Safety Warnings from Incident Narratives", 2)

    tf = tbox(s, 0.5, 1.2, 12.33, 0.4)
    para(tf, "Reads a safety or near-miss report and answers one question: "
             "could this have killed someone?",
         size=16, bold=True, color=TITLE_INK, first=True, after=0, align=PP_ALIGN.CENTER)

    card(s, 0.5, 1.75, 6.05, 2.3, "What it identifies")
    points(s, 0.82, 2.25, 5.5, ["Hazard + Life-Saving Rule", "Control status",
                                "Severity (1-5)", "SIF Precursor: Yes / No",
                                "Evidence & reasoning"], size=14, gap=9)

    card(s, 6.78, 1.75, 6.05, 2.3, "What makes it different", accent=GREEN)
    points(s, 7.1, 2.25, 5.5, ["Three gates, not one score",
                               "One-Change severity rule",
                               "LLM + local ML fallback",
                               "Ranks a queue - never closes a report",
                               "Every judgement logged"], size=14, gap=9)

    rect(s, 0.5, 4.22, 12.33, 2.6, fill=WHITE, line=LINE)
    tf = tbox(s, 0.85, 4.44, 11.6, 0.3)
    para(tf, "THE THREE GATES", size=11.5, bold=True, color=BLUE, first=True, after=0)

    for i, (g, q, opts, col) in enumerate([
            ("GATE 1  ·  HAZARD", "Is a high-energy hazard present?",
             "yes · no · insufficient", BLUE),
            ("GATE 2  ·  CONTROL", "Was a barrier doing its job?",
             "absent · failed · present · unclear", AMBER),
            ("GATE 3  ·  SEVERITY", "Plausible worst case?", "1 - 5", GREEN)]):
        x = 0.85 + i * 3.92
        rect(s, x, 4.84, 3.5, 1.18, fill=CARD, line=LINE)
        rect(s, x, 4.84, 3.5, 0.04, fill=col)
        tf = tbox(s, x + 0.24, 5.0, 3.05, 0.9)
        para(tf, g, size=10.5, bold=True, color=col, first=True, after=4)
        para(tf, q, size=12.5, bold=True, after=4)
        para(tf, opts, size=10, color=MUTED, after=0)
        if i < 2:
            arrow(s, x + 3.56, 5.28, 0.3)

    chip(s, 0.85, 6.22, 11.6, 0.44,
         "SIF PRECURSOR  =  Hazard YES   +   Control ABSENT / FAILED   +   Severity >= 4",
         FLAG, size=13.5)

    # ==================== 3. ARCHITECTURE ================================
    s = blank(prs)
    chrome(s, "Technical Approach", 3)

    def layer(y, h, label, col):
        """One horizontal band. Each is a single thing you can point at and explain."""
        rect(s, 0.5, y, 1.62, h, fill=col)
        t = tbox(s, 0.5, y + h / 2 - 0.16, 1.62, 0.32)
        para(t, label, size=10.5, bold=True, color=WHITE, first=True, after=0,
             align=PP_ALIGN.CENTER)
        rect(s, 2.12, y, 10.71, h, fill=CARD, line=LINE)

    def node(x, y, w, h, title, sub, col=TITLE_INK):
        # Vertically centred: these boxes differ in height across layers, and top-aligning
        # the text leaves the taller ones looking half-empty.
        rect(s, x, y, w, h, fill=WHITE, line=LINE)
        t = tbox(s, x + 0.12, y, w - 0.24, h, anchor=MSO_ANCHOR.MIDDLE)
        para(t, title, size=11.5, bold=True, color=col, first=True, after=2,
             align=PP_ALIGN.CENTER)
        if sub:
            para(t, sub, size=9, color=MUTED, after=0, align=PP_ALIGN.CENTER)

    def down(x, y):
        t = tbox(s, x, y, 0.4, 0.26)
        para(t, "↓", size=15, bold=True, color=BLUE, first=True, after=0,
             align=PP_ALIGN.CENTER)

    layer(1.12, 1.0, "CLIENT", BLUE)
    node(2.42, 1.24, 4.7, 0.76, "Field Worker  ·  React",
         "voice or typed report  →  instant classification")
    node(7.62, 1.24, 4.7, 0.76, "HSE Admin  ·  React",
         "triage queue  ·  dispatch / archive  ·  risk board")
    down(6.5, 2.16)

    layer(2.46, 1.42, "API", BLUE)
    node(2.42, 2.62, 3.05, 1.08, "FastAPI", "REST  ·  Pydantic-validated")
    node(5.72, 2.62, 3.4, 1.08, "Classifier boundary",
         "cache → primary → retry → fallback")
    node(9.37, 2.62, 2.95, 1.08, "Aggregation", "plain SQL  ·  GROUP BY")
    down(6.5, 3.94)

    layer(4.24, 1.28, "MODELS", GREEN)
    node(2.42, 4.42, 4.7, 0.94, "PRIMARY  ·  Groq gpt-oss-20b",
         "three-gate prompt  ·  JSON out  ·  hard deadline", col=GREEN)
    node(7.62, 4.42, 4.7, 0.94, "FALLBACK  ·  TF-IDF + LogReg",
         "local  ·  no network  ·  answers when the API cannot", col=AMBER)
    down(6.5, 5.58)

    layer(5.86, 1.02, "DATA", TITLE_INK)
    for i, (t, sub) in enumerate([("reports", "150 synthetic · 30 OSHA"),
                                  ("predictions", "append-only log"),
                                  ("gold_labels", "173 human labels"),
                                  ("report_status", "triage state")]):
        node(2.42 + i * 2.52, 6.0, 2.36, 0.74, t, sub)

    # ==================== 4. FEASIBILITY =================================
    s = blank(prs)
    chrome(s, "Feasibility and Viability", 4)

    card(s, 0.5, 1.15, 6.05, 2.75, "Feasible because", accent=GREEN)
    points(s, 0.82, 1.68, 5.5, ["Uses incident reports that already exist",
                                "No specialized hardware",
                                "API-based & scalable",
                                "LLM + local fallback",
                                "Human-in-the-loop"], size=14.5, gap=13)

    card(s, 6.78, 1.15, 6.05, 2.75, "Challenge  →  Solution", accent=AMBER)
    points(s, 7.1, 1.68, 5.5, ["Unstructured text  →  LLM analysis",
                               "Ambiguous controls  →  4-state classification",
                               "API failure  →  retry + local fallback",
                               "Domain variation  →  %d real OSHA reports" % OSHA_N,
                               "Model changes  →  one version per dashboard"],
           size=14.5, gap=13)

    rect(s, 0.5, 4.08, 12.33, 1.62, fill=WARN_BG, line=WARN_LN)
    tf = tbox(s, 0.85, 4.28, 11.6, 0.3)
    para(tf, "OUR REAL LIMIT IS TOKENS, NOT COMPUTE", size=11.5, bold=True, color=FLAG,
         first=True, after=0)
    for i, (big, sub) in enumerate([("200,000", "tokens / day, free tier"),
                                    ("~3,150", "tokens per report"),
                                    (REPORTS_PER_DAY, "reports / day"),
                                    ("~2.8 days", "full corpus re-run")]):
        x = 0.85 + i * 2.94
        tf = tbox(s, x, 4.68, 2.7, 0.8)
        para(tf, big, size=23, bold=True, color=FLAG, first=True, after=2)
        para(tf, sub, size=10.5, color=MUTED, after=0)

    card(s, 0.5, 5.88, 12.33, 1.0, "So the pipeline is built to survive it", accent=BLUE)
    tf = tbox(s, 0.85, 6.36, 11.6, 0.36)
    para(tf, "Resumable  ·  never stores a fallback as if it were a real answer  ·  "
             "dashboard always has data to show", size=13.5, first=True, after=0)

    # ==================== 5. IMPACT ======================================
    s = blank(prs)
    chrome(s, "Impact and Benefits", 5)

    card(s, 0.5, 1.15, 6.05, 2.75, "Potential impact")
    points(s, 0.82, 1.68, 5.5, ["Early detection of SIF precursors in OIL reports",
                                "Prioritized review of high-risk incidents",
                                "Ranks sites by precursor RATE, not count",
                                "Finds recurring hazards across sites & shifts"],
           size=14.5, gap=15)

    card(s, 6.78, 1.15, 6.05, 2.75, "Benefits", accent=GREEN)
    points(s, 7.1, 1.68, 5.5, ["Safety  —  act before the incident",
                               "Operational  —  no manual first-pass screen",
                               "Economic  —  prevents injuries and downtime",
                               "Scalable  —  ten reports or ten thousand"],
           size=14.5, gap=15)

    rect(s, 0.5, 4.08, 12.33, 0.92, fill=BLUE)
    tf = tbox(s, 0.5, 4.32, 12.33, 0.46)
    para(tf, "Safety Reports  →  SIF Precursors  →  Risk Prioritization  →  "
             "Early Action  →  Safer Operations",
         size=16, bold=True, color=WHITE, first=True, after=0, align=PP_ALIGN.CENTER)

    card(s, 0.5, 5.18, 12.33, 1.7, "Why we rank by rate, not by count", accent=AMBER)
    tf = tbox(s, 0.85, 5.66, 11.6, 0.34)
    para(tf, "A site that reports honestly logs more incidents. Counting them punishes it.",
         size=13.5, bold=True, first=True, after=0)
    for i, (t, col) in enumerate([("Count  →  the busiest site always looks worst", FLAG),
                                  ("Rate  →  precursors ÷ reports, small groups held back",
                                   GREEN)]):
        x = 0.85 + i * 5.85
        rect(s, x, 6.12, 5.6, 0.5, fill=WHITE, line=LINE)
        rect(s, x, 6.12, 0.05, 0.5, fill=col)
        tf = tbox(s, x + 0.24, 6.24, 5.2, 0.3)
        para(tf, t, size=11.5, bold=True, color=col, first=True, after=0)

    # ==================== 6. RESEARCH AND REFERENCES =====================
    s = blank(prs)
    chrome(s, "Research and References", 6)

    tf = tbox(s, 0.5, 1.12, 12.33, 0.3)
    para(tf, "RESEARCH", size=10.5, bold=True, color=BLUE, first=True, after=3)
    para(tf, "IOGP Life-Saving Rules  ·  DEKRA SIF Framework  ·  EEI SIF Model",
         size=13, after=0)
    tf = tbox(s, 0.5, 1.78, 12.33, 0.3)
    para(tf, "DATA", size=10.5, bold=True, color=BLUE, first=True, after=3)
    para(tf, "%d synthetic reports  +  %d real OSHA severe-injury narratives  ·  "
             "%d gold labels  ·  2 annotators" % (SYNTHETIC_N, OSHA_N, GOLD_N),
         size=13, after=0)

    tf = tbox(s, 0.5, 2.5, 12.33, 0.3)
    para(tf, "PROTOTYPE EVALUATION", size=10.5, bold=True, color=BLUE, first=True, after=0)

    metrics = [(GREEN, "HUMAN CEILING", CEILING_KAPPA, "Cohen's kappa",
                "%s agreement  ·  independent  ·  n=%d" % (CEILING_PCT, CEILING_N)),
               (BLUE, "TF-IDF BASELINE", BASELINE_F1, "F1  " + BASELINE_SD,
                "5-fold CV  ·  PR-AUC %s  ·  n=%d" % (BASELINE_PRAUC, BASELINE_N)),
               (MUTED, "OSHA GENERALISATION", OSHA_F1, "F1",
                "real narratives  ·  n=%d, too small to conclude" % OSHA_N)]
    for i, (col, label, big, unit, sub) in enumerate(metrics):
        x = 0.5 + i * 4.16
        rect(s, x, 2.86, 3.94, 1.5, fill=WHITE, line=LINE)
        rect(s, x, 2.86, 3.94, 0.045, fill=col)
        tf = tbox(s, x + 0.26, 3.04, 3.4, 0.26)
        para(tf, label, size=9, bold=True, color=col, first=True, after=0)
        tf = tbox(s, x + 0.26, 3.3, 3.4, 0.5)
        para(tf, big, size=27, bold=True, color=INK, first=True, after=0)
        tf = tbox(s, x + 1.62, 3.46, 2.0, 0.3)
        para(tf, unit, size=10, color=MUTED, first=True, after=0)
        tf = tbox(s, x + 0.26, 3.9, 3.5, 0.4)
        para(tf, sub, size=9, color=MUTED, first=True, after=0)

    rect(s, 0.5, 4.5, 12.33, 0.56, fill=WARN_BG, line=WARN_LN)
    tf = tbox(s, 0.82, 4.66, 11.7, 0.3)
    para(tf, "LLM F1 withdrawn — we found a held-out report inside our own prompt and "
             "pulled the number rather than ship it.  Re-measurement in progress.",
         size=11.5, bold=True, color=FLAG, first=True, after=0)

    card(s, 0.5, 5.2, 12.33, 1.68, "Stated up front, because a judge will find them",
         accent=MUTED)
    caveats = [("Precursor rate %s" % PRECURSOR_RATE,
                "not the 20–25% cited — our generator centred every report on a hazard"),
               ("Ceiling is n=%d" % CEILING_N,
                "a re-label subset, so we quote the subset, never a bare kappa"),
               ("No accuracy figure",
                "and never a baseline scored on its own training data")]
    for i, (head, body) in enumerate(caveats):
        x = 0.82 + i * 3.95
        tf = tbox(s, x, 5.68, 3.7, 0.9)
        para(tf, head, size=11.5, bold=True, color=INK, first=True, after=3)
        para(tf, body, size=10, color=MUTED, after=0)

    tf = tbox(s, 0.82, 6.56, 11.7, 0.3)
    para(tf, "GitHub:  SANKET — AI-powered SIF precursor detection", size=11, bold=True,
         first=True, after=0)

    out = "docs/SANKET-SIH2026-Idea-Submission.pptx"
    prs.save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    build()
