"""
build_deck.py

Build the SIH 2026 idea-submission deck.

    python build_deck.py    ->  docs/SANKET-SIH2026-Idea-Submission.pptx

STICKING TO THE TEMPLATE

Instruction 5 says to use the provided template "without changing the idea details pointers".
So every prescribed heading is kept word for word and answered underneath:

    Slide 2  IDEA TITLE                Proposed Solution (Describe your Idea/Solution/Prototype)
                                       - Detailed explanation of the proposed solution
                                       - How it addresses the problem
                                       - Innovation and uniqueness of the solution
    Slide 3  TECHNICAL APPROACH        - Technologies to be used
                                       - Methodology and process for implementation
    Slide 4  FEASIBILITY AND VIABILITY - Analysis of the feasibility of the idea
                                       - Potential challenges and risks
                                       - Strategies for overcoming these challenges
    Slide 5  IMPACT AND BENEFITS       - Potential impact on the target audience
                                       - Benefits of the solution
    Slide 6  RESEARCH AND REFERENCES   - Details / Links of the reference and research work

Instruction 2 says avoid paragraphs, so answers are short points and one flow chart.
Instruction 3 says keep it easy to understand, so the language is plain and the numbers are
few - only the ones a judge would ask for, each with its sample size.

The furniture matches the blank template: white ground, black centred sans title, the team
oval top-left, the SIH logo top-right, and the blue footer band reading
"@SIH Idea submission- Template" with the slide number. The blue is RGB(0,112,192), sampled
from the template PDF; the logo is the real asset extracted from it.

WHY A SCRIPT

Every number is a named constant traceable to the script that produced it. This deck has
carried a wrong figure three times, each time because a number was retyped into a slide by
hand and then drifted from the repo. Change the constant, rebuild, and every slide moves.
"""

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --- the only numbers that reach a slide ----------------------------------
CEILING_PCT = "97%"       # score_recheck.py - 37 of 38 agreed
CEILING_KAPPA = "0.947"   # score_recheck.py
CEILING_N = 38
BASELINE_F1 = "0.75"      # eval/run_eval.py --no-llm, 5-fold CV, n=114
SYNTHETIC_N = 150
OSHA_N = 30

LIVE_APP = "https://sanket-frontend.onrender.com"
LIVE_API = "https://sanket-backend-put3.onrender.com"

LOGO = "docs/assets/sih-2026-logo.png"

BLUE = RGBColor(0x00, 0x70, 0xC0)
NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLACK = RGBColor(0x00, 0x00, 0x00)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)
GREEN = RGBColor(0x1E, 0x7A, 0x5E)
AMBER = RGBColor(0x9C, 0x64, 0x0C)
RED = RGBColor(0xB4, 0x3A, 0x2E)
PILL = RGBColor(0x7B, 0x5E, 0xA7)
CARD = RGBColor(0xF2, 0xF6, 0xFA)
LINE = RGBColor(0xC9, 0xD8, 0xE6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = 13.333, 7.5
FONT = "Arial"
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


def para(tf, text, size=16, bold=False, color=INK, after=8, first=False,
         align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.alignment = align
    p.space_after = Pt(after)
    for r in p.runs:
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = FONT
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


def chrome(slide, title, n):
    """Template furniture: team oval, black centred title, logo, blue footer band."""
    o = rect(slide, 0.3, 0.18, 1.35, 0.72, fill=WHITE, line=PILL, shape=MSO_SHAPE.OVAL)
    tf = o.text_frame
    tf.word_wrap = True
    para(tf, "Signal-0", size=13, color=BLACK, first=True, after=0, align=PP_ALIGN.CENTER)

    tf = tbox(slide, 1.9, 0.16, 9.0, 0.78, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, title, size=32, bold=True, color=BLACK, first=True, after=0,
         align=PP_ALIGN.CENTER)

    if os.path.exists(LOGO):
        slide.shapes.add_picture(LOGO, Inches(11.15), Inches(0.14), height=Inches(0.82))

    rect(slide, 0, FOOT, W, H - FOOT, fill=BLUE)
    tf = tbox(slide, 0, FOOT + 0.07, W, 0.28)
    para(tf, "@SIH Idea submission- Template", size=10.5, color=WHITE, first=True,
         after=0, align=PP_ALIGN.CENTER)
    tf = tbox(slide, W - 1.05, FOOT + 0.07, 0.65, 0.28)
    para(tf, str(n), size=10.5, bold=True, color=WHITE, first=True, after=0,
         align=PP_ALIGN.RIGHT)


def heading(slide, x, y, w, text, color=NAVY, size=17):
    """One of the template's prescribed pointers. Kept word for word."""
    tf = tbox(slide, x, y, w, 0.34)
    para(tf, text, size=size, bold=True, color=color, first=True, after=0)


def points(slide, x, y, w, items, size=15, gap=9):
    tf = tbox(slide, x, y, w, 0.4)
    for i, it in enumerate(items):
        para(tf, "•  " + it, size=size, after=gap, first=(i == 0))
    return tf


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ==================== 1. TITLE PAGE ==================================
    s = blank(prs)
    tf = tbox(s, 0.7, 0.32, 9.8, 0.72)
    para(tf, "SMART INDIA HACKATHON 2026", size=38, bold=True, color=NAVY,
         first=True, after=0, align=PP_ALIGN.CENTER)
    tf = tbox(s, 0.7, 1.24, 9.8, 0.6)
    para(tf, "TITLE PAGE", size=30, color=BLACK, first=True, after=0,
         align=PP_ALIGN.CENTER)
    if os.path.exists(LOGO):
        s.shapes.add_picture(LOGO, Inches(10.6), Inches(0.3), height=Inches(1.1))

    tf = tbox(s, 0.9, 2.35, 11.5, 3.9)
    for i, (k, v) in enumerate([
            ("Problem Statement ID", "SIH26165"),
            ("Problem Statement Title", "AI/NLP Engine to Detect Serious Injury & Fatality "
                                        "(SIF) Precursors in OIL's Unsafe-Act / "
                                        "Unsafe-Condition and Near-Miss Reports"),
            ("Theme", "Smart Automation"),
            ("PS Category", "Software"),
            ("Team ID", "____"),
            ("Team Name (Registered on portal)", "Signal-0")]):
        para(tf, "•  %s -  %s" % (k, v), size=18, after=17, first=(i == 0))

    # Working prototype link. Judges can open it while the slide is still up.
    rect(s, 0.9, 6.15, 11.53, 0.62, fill=CARD, line=LINE)
    tf = tbox(s, 1.15, 6.3, 11.0, 0.34)
    para(tf, "Working prototype:   %s" % LIVE_APP, size=15, bold=True, color=NAVY,
         first=True, after=0)

    # ==================== 2. IDEA TITLE ==================================
    s = blank(prs)
    chrome(s, "IDEA TITLE", 2)

    tf = tbox(s, 0.6, 1.02, 12.1, 0.45)
    para(tf, "SANKET  —  finding the reports that could have killed someone",
         size=21, bold=True, color=NAVY, first=True, after=0)

    heading(s, 0.6, 1.62, 12.1, "Proposed Solution (Describe your Idea/Solution/Prototype)")

    heading(s, 0.6, 2.12, 12.1, "Detailed explanation of the proposed solution",
            color=BLACK, size=15)
    points(s, 0.95, 2.5, 11.5, [
        "A worker types or speaks a safety report. The AI reads it and asks three questions.",
        "Is there a serious hazard?   Was a safety control missing or broken?   "
        "How bad could it have been?",
        "If all three point the wrong way, the report is flagged and moves to the top of "
        "the queue."], size=15, gap=7)

    heading(s, 0.6, 4.0, 12.1, "How it addresses the problem", color=BLACK, size=15)
    points(s, 0.95, 4.38, 11.5, [
        "OIL gets more reports than anyone can read carefully, so the dangerous ones get "
        "lost in the pile.",
        "SANKET reads every one and reorders the pile. It never closes a report — a person "
        "still decides."], size=15, gap=7)

    heading(s, 0.6, 5.5, 12.1, "Innovation and uniqueness of the solution",
            color=BLACK, size=15)
    points(s, 0.95, 5.88, 11.5, [
        "Three separate checks instead of one risk score, so you can see which one drove "
        "the answer.",
        "If the AI is unreachable a small local model answers, and the screen says which "
        "one answered."], size=15, gap=7)

    # ==================== 3. TECHNICAL APPROACH ==========================
    s = blank(prs)
    chrome(s, "TECHNICAL APPROACH", 3)

    heading(s, 0.6, 1.0, 12.1,
            "Technologies to be used (e.g. programming languages, frameworks, hardware)")
    points(s, 0.95, 1.4, 11.9, [
        "Frontend: React      Backend: FastAPI (Python)      Database: Supabase (PostgreSQL)",
        "AI model: Groq GPT-OSS-20B      Backup model: TF-IDF + Logistic Regression, "
        "runs locally"], size=15, gap=7)

    heading(s, 0.6, 2.42, 12.1,
            "Methodology and process for implementation (Flow Chart)")

    def node(x, y, w, h, title, sub, col=NAVY):
        rect(s, x, y, w, h, fill=WHITE, line=LINE)
        t = tbox(s, x + 0.1, y, w - 0.2, h, anchor=MSO_ANCHOR.MIDDLE)
        para(t, title, size=13, bold=True, color=col, first=True, after=2,
             align=PP_ALIGN.CENTER)
        if sub:
            para(t, sub, size=10.5, color=MUTED, after=0, align=PP_ALIGN.CENTER)

    def link(x, y, ch="→"):
        t = tbox(s, x, y, 0.42, 0.3)
        para(t, ch, size=18, bold=True, color=BLUE, first=True, after=0,
             align=PP_ALIGN.CENTER)

    node(0.9, 2.88, 2.4, 0.84, "Worker reports", "typed or voice")
    link(3.38, 3.15)
    node(3.88, 2.88, 2.4, 0.84, "FastAPI", "receives it")
    link(6.36, 3.15)
    node(6.86, 2.88, 2.75, 0.84, "AI reads it", "Groq GPT-OSS-20B", col=GREEN)
    link(9.69, 3.15)
    node(10.19, 2.88, 2.24, 0.84, "Three checks", "hazard · control · severity")

    # The flow wraps at the RIGHT edge, so the down arrow belongs under the last box of
    # row one - not in the middle, where it reads as an unrelated branch.
    link(11.1, 3.82, "↓")

    node(0.9, 4.3, 2.4, 0.84, "HSE officer acts", "dispatch or archive")
    link(3.38, 4.57, "←")
    node(3.88, 4.3, 2.4, 0.84, "Ranked queue", "worst first")
    link(6.36, 4.57, "←")
    node(6.86, 4.3, 2.75, 0.84, "Flagged or not", "with its reasoning", col=RED)
    link(9.69, 4.57, "←")
    node(10.19, 4.3, 2.24, 0.84, "Saved", "PostgreSQL")

    rect(s, 0.9, 5.42, 6.0, 1.3, fill=CARD, line=LINE)
    tf = tbox(s, 1.15, 5.6, 5.5, 0.95)
    para(tf, "WHEN IS IT FLAGGED?", size=11, bold=True, color=RED, first=True, after=6)
    para(tf, "Hazard yes  +  control missing or broken  +  could have been severe",
         size=13, bold=True, after=4)
    para(tf, "All three, or it is not flagged.", size=12, color=MUTED, after=0)

    rect(s, 7.2, 5.42, 5.23, 1.3, fill=CARD, line=LINE)
    tf = tbox(s, 7.45, 5.6, 4.75, 0.95)
    para(tf, "IF THE AI IS DOWN", size=11, bold=True, color=AMBER, first=True, after=6)
    para(tf, "The local backup model answers", size=13, bold=True, after=4)
    para(tf, "and the screen names which model did.", size=12, color=MUTED, after=0)

    # ==================== 4. FEASIBILITY =================================
    s = blank(prs)
    chrome(s, "FEASIBILITY AND VIABILITY", 4)

    heading(s, 0.6, 1.1, 12.1, "Analysis of the feasibility of the idea")
    points(s, 0.95, 1.52, 11.8, [
        "Uses the safety reports OIL already writes — no new data collection needed.",
        "No special hardware. Runs on an ordinary web server.",
        "A working prototype is already built and live."], size=15.5, gap=9)

    heading(s, 0.6, 3.12, 12.1, "Potential challenges and risks")
    points(s, 0.95, 3.54, 11.8, [
        "Every person writes a report differently.",
        "Many reports never say whether a safety control was in place.",
        "The AI service can be slow, busy or unavailable.",
        "An AI answer nobody can check is not worth trusting."], size=15.5, gap=9)

    heading(s, 0.6, 5.44, 12.1, "Strategies for overcoming these challenges")
    points(s, 0.95, 5.86, 11.8, [
        "A written rulebook that both the AI and our human reviewers follow.",
        "\"Not stated\" is a valid answer for the control question — we never guess.",
        "A local backup model, and every answer records which model produced it."],
        size=15.5, gap=9)

    # ==================== 5. IMPACT ======================================
    s = blank(prs)
    chrome(s, "IMPACT AND BENEFITS", 5)

    heading(s, 0.6, 1.15, 12.1, "Potential impact on the target audience")
    points(s, 0.95, 1.6, 11.8, [
        "HSE officers read the dangerous reports first, not in the order they arrived.",
        "Managers see which sites and shifts keep producing near-misses.",
        "Workers get an answer in seconds, so reporting feels worth doing."],
        size=16, gap=14)

    heading(s, 0.6, 3.5, 12.1,
            "Benefits of the solution (social, economic, environmental, etc.)")
    points(s, 0.95, 3.95, 11.8, [
        "Social — a warning acted on before someone is hurt or killed.",
        "Economic — less time screening reports by hand, fewer incidents, less downtime.",
        "Environmental — the same failures that injure people also cause spills and leaks.",
        "Organisational — every judgement is recorded, so audits are straightforward."],
        size=16, gap=14)

    rect(s, 0.9, 6.08, 11.53, 0.76, fill=BLUE)
    tf = tbox(s, 0.9, 6.28, 11.53, 0.4)
    para(tf, "Safety Reports  →  Precursors Found  →  Priority  →  Early Action  →  "
             "Safer Operations",
         size=16, bold=True, color=WHITE, first=True, after=0, align=PP_ALIGN.CENTER)

    # ==================== 6. RESEARCH AND REFERENCES =====================
    s = blank(prs)
    chrome(s, "RESEARCH  AND REFERENCES", 6)

    heading(s, 0.6, 1.12, 12.1, "Details / Links of the reference and research work")
    points(s, 0.95, 1.56, 11.8, [
        "IOGP Life-Saving Rules — the hazard categories we tag against",
        "DEKRA SIF Framework — serious injuries have identifiable precursors",
        "EEI SIF Model — a precursor is a hazard with a missing or failed control",
        "OSHA Severe Injury Reports — %d real published narratives, used to test the system "
        "on writing nobody on our team wrote" % OSHA_N], size=15.5, gap=11)

    heading(s, 0.6, 3.85, 12.1, "How we tested it")
    points(s, 0.95, 4.29, 11.8, [
        "%d safety reports written for this prototype, each reviewed by two people using "
        "the same rulebook." % SYNTHETIC_N,
        "On a %d-report sample the two reviewers worked separately and agreed %s of the "
        "time (Cohen's kappa %s)." % (CEILING_N, CEILING_PCT, CEILING_KAPPA),
        "No system should claim to be more consistent than the people who made its labels.",
        "Our simple backup model scores F1 %s. The AI model is being re-measured after we "
        "found and fixed a flaw in our own test setup." % BASELINE_F1], size=15, gap=10)

    rect(s, 0.9, 6.12, 11.53, 0.72, fill=CARD, line=LINE)
    tf = tbox(s, 1.15, 6.24, 11.0, 0.5)
    para(tf, "Live prototype:  %s" % LIVE_APP, size=14, bold=True, color=NAVY,
         first=True, after=3)
    para(tf, "GitHub:  SANKET — AI-powered SIF precursor detection", size=14, bold=True,
         color=NAVY, after=0)

    out = "docs/SANKET-SIH2026-Idea-Submission.pptx"
    prs.save(out)
    print("wrote %s" % out)


if __name__ == "__main__":
    build()
