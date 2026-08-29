"""Static verification checklists keyed to `lsr_rule`.

THIS IS A LOOKUP TABLE, NOT MODEL OUTPUT. The text below is fixed at authoring time and is
never generated, rewritten, or ranked by the LLM. Nothing in this module calls a model.

Rationale (backend patch v1.1, Amendment B): the system surfaces reports for human attention;
it does not author safety advice. Each entry is a conservative verification prompt that
restates the control the rule already requires, so a reviewer is reminded what to check —
not told what to conclude.

If asked on stage: "Recommendations are static, regulator-aligned checklists keyed to the
rule — the model never generates safety advice."
"""

from ..schemas import LSRRule

RECOMMENDED_CHECKS: dict[LSRRule, str] = {
    LSRRule.ENERGY_ISOLATION: (
        "Verify energy isolation: sources identified, isolated, locked, tagged, and zero-energy "
        "state proven at the point of work before the guard or cover comes off."
    ),
    LSRRule.HOT_WORK: (
        "Verify hot-work controls: valid permit, gas test current, flammables removed or covered, "
        "fire watch posted, and the area re-checked after work stops."
    ),
    LSRRule.CONFINED_SPACE: (
        "Verify confined-space entry: authorised permit, atmospheric test before and during entry, "
        "ventilation running, attendant posted, and a rescue plan that does not rely on the attendant "
        "entering."
    ),
    LSRRule.LINE_OF_FIRE: (
        "Verify line-of-fire position: exclusion zone set and enforced, no one under a suspended load "
        "or in the path of moving, energised, or pressurised equipment, and stored energy released."
    ),
    LSRRule.WORK_AT_HEIGHT: (
        "Verify fall protection: rated anchor identified, harness inspected and actually clipped, "
        "edge protection or guardrail in place, and dropped-object controls for tools and materials."
    ),
    LSRRule.LIFTING: (
        "Verify the lift: current lift plan, rigging inspected and within rated capacity, load path "
        "clear of people, taglines in use, and the crane inside its load chart."
    ),
    LSRRule.DRIVING: (
        "Verify journey controls: driver authorised and fit, seatbelts worn, speed appropriate to the "
        "road, vehicle inspection current, and no in-vehicle phone use."
    ),
    LSRRule.PERMIT_TO_WORK: (
        "Verify work authorisation: permit valid for this scope and time window, hazards and controls "
        "understood by everyone on the job, and the permit closed out when conditions change."
    ),
    LSRRule.NONE: (
        "No Life-Saving Rule was tagged. Confirm the hazard category with the reporting supervisor "
        "before triage."
    ),
}


def recommended_check_for(lsr_rule: LSRRule, is_sif_precursor: bool) -> str | None:
    """Return the fixed check for a rule, or None when the report is not a precursor.

    Populated only for precursors: a non-precursor report gets no prompt, so reviewers are not
    trained to ignore the field.
    """
    if not is_sif_precursor:
        return None
    return RECOMMENDED_CHECKS.get(LSRRule(lsr_rule))
