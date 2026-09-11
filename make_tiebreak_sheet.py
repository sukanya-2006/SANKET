"""
make_tiebreak_sheet.py

Turn the seven open disagreements into a worksheet someone can finish in fifteen minutes.

    python make_tiebreak_sheet.py

Writes data/tiebreak_sheet.md - the report text, both annotators' answers side by side, the
gate they actually split on, and the one rubric rule that settles that gate.

WHY A SEPARATE SHEET

data/labeling_disagreements.csv has the raw columns, but adjudicating from it means holding the
rubric open in another window and working out which gate each pair differs on. Six of the seven
are the same question - is the realistic worst case a permanent injury or not - and putting
that question next to the text is most of the work.

WHAT IT DOES NOT DO

It does not suggest an answer, rank the options, or hint which annotator is right. The gate is
computed from where the two labels differ; the rubric text is quoted verbatim. Whoever fills
this in is the tiebreaker, and if this file nudged them the label would not be a human
judgement any more.
"""

import csv
import io
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DISAGREEMENTS = "data/labeling_disagreements.csv"
REPORTS = "data/synthetic/synthetic_reports_for_labeling.csv"
OUT = "data/tiebreak_sheet.md"

# Quoted verbatim from docs/rubric.md so the sheet cannot drift from the rubric.
GATE_RULES = {
    1: (
        "GATE 1 - is a high-energy hazard present, in one of the eight IOGP categories?\n"
        "> Answer `no` for same-level slips/trips, manual handling strain, hand tools, minor\n"
        "> sharps, heat stress, or housekeeping. Answer `insufficient_information` only when\n"
        "> the text does not let you name a hazard category at all - that means a human needs\n"
        "> to read it, not that it is safe."
    ),
    2: (
        "GATE 2 - was there a control targeting that hazard, and was it doing its job?\n"
        "> `absent`: no control existed, or one existed and was not used, removed, bypassed.\n"
        "> `failed`: a control was in place and did not hold.\n"
        "> `present`: a rated, targeted control held, and the text explicitly says so.\n"
        "> `unclear`: the narrative says nothing either way. Silence is `unclear`.\n"
        ">\n"
        "> A report that states a control was not done IS `absent` - that is reading, not\n"
        "> inferring. Reserve `unclear` for narratives that simply do not mention controls."
    ),
    3: (
        "GATE 3 - the 3/4 boundary, which is the one that decides the label:\n"
        ">     \"Would this person be permanently unable to do the same job again?\"\n"
        ">     Yes -> 4 or 5.   No -> 3 or below.\n"
        ">\n"
        "> THE ONE-CHANGE RULE. Change EXACTLY ONE thing: the timing by a few seconds, OR the\n"
        "> position by a metre, OR remove one last-second catch or rescue. Not two, not a\n"
        "> chain. If you catch yourself thinking \"and then, if he had also...\", go back.\n"
        ">\n"
        "> 3 = off work for a while, THEN BACK TO THE SAME JOB.\n"
        "> 4 = cannot return to the same job. Amputation, lost eye, permanent restriction.\n"
        "> 5 = someone dies, and you can name the mechanism in one sentence after ONE change.\n"
        ">\n"
        "> If you are genuinely torn between 3 and 4, answer 3 and say why."
    ),
}


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def which_gate(row):
    """The gate the two annotators actually split on, in rubric order."""
    if row["hazard_assessment_a"] != row["hazard_assessment_b"]:
        return 1
    if (row.get("control_status_a") or "") != (row.get("control_status_b") or ""):
        return 2
    if row["severity_a"] != row["severity_b"]:
        return 3
    return 0


def main():
    rows = read(DISAGREEMENTS)
    texts = {str(r["report_id"]).strip(): r["text"] for r in read(REPORTS)}

    by_gate = {}
    for r in rows:
        by_gate.setdefault(which_gate(r), []).append(r)

    out = []
    out.append("# Tiebreak sheet — %d open disagreements\n" % len(rows))
    out.append("Generated from `data/labeling_disagreements.csv`. One person decides each of "
               "these, applying the rubric. Nothing here suggests an answer.\n")
    out.append("**How to record a decision.** Write the winning value in the DECISION line, "
               "add one sentence of reasoning, then append the row to `data/gold_labels.csv` "
               "with `annotator` set to `agreed`.\n")

    counts = ", ".join("gate %d: %d" % (g, len(v)) for g, v in sorted(by_gate.items()))
    out.append("Split by gate — %s.\n" % counts)
    out.append("---\n")

    for gate in sorted(by_gate):
        group = by_gate[gate]
        out.append("## Gate %d — %d report%s\n" % (gate, len(group), "" if len(group) == 1 else "s"))
        out.append("%s\n" % GATE_RULES.get(gate, "Gate could not be determined automatically."))
        out.append("")

        for r in group:
            rid = str(r["report_id"]).strip()
            out.append("### Report %s\n" % rid)
            text = texts.get(rid) or r.get("text_a") or "(text not found)"
            out.append("> %s\n" % text.replace("\n", " ").strip())
            out.append("| | akanksha | sukanya |")
            out.append("|---|---|---|")
            out.append("| hazard | %s | %s |" % (r["hazard_assessment_a"], r["hazard_assessment_b"]))
            out.append("| rule | %s | %s |" % (r["lsr_rule_a"], r["lsr_rule_b"]))
            out.append("| control | %s | %s |" % (r.get("control_status_a") or "—",
                                                  r.get("control_status_b") or "—"))
            out.append("| severity | %s | %s |" % (r["severity_a"], r["severity_b"]))
            out.append("")
            out.append("**DECISION:** hazard `____`  rule `____`  control `____`  severity `__`")
            out.append("")
            out.append("**WHY:** ______________________________________________")
            out.append("")
            out.append("---")
            out.append("")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))

    print("Wrote %s" % OUT)
    print("  %d disagreements, %s" % (len(rows), counts))
    print("  report ids: %s" % ", ".join(sorted((str(r["report_id"]).strip() for r in rows),
                                                key=lambda x: int(x) if x.isdigit() else 0)))


if __name__ == "__main__":
    main()
