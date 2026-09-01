# """
# classifier_llm.py

# The real classifier. One structured Groq API call per report, prompted with
# rubric v2.1's three gates, returning the exact schema shape `classifier.py`
# expects (see schemas.py: ClassificationResult).

# This module does NOT touch classifier.py's cache/timeout/fallback logic -
# it only implements the `Classifier` protocol (a callable with a `.version`
# attribute) and gets wired in from main.py via:

#     from . import classifier_llm
#     classifier.register_primary(classifier_llm.classify)

# Needs GROQ_API_KEY set in the environment (same key already used by
# generate_synthetic_reports_free.py).
# """

# import os
# import json
# import re
# from groq import Groq

# MODEL_NAME = "openai/gpt-oss-20b"  # same free-tier model already in use elsewhere

# client = Groq()  # reads GROQ_API_KEY from environment

# # ---------------------------------------------------------------------------
# # Rubric v2.1, condensed into a system prompt. This is not the full document -
# # it's the operative gates and the decision table, which is what the model
# # actually needs to apply consistently. Full text lives in docs/rubric.md.
# # ---------------------------------------------------------------------------

# SYSTEM_PROMPT = """You are a safety analyst applying a strict three-gate rubric to classify \
# industrial safety incident reports for SIF (Serious Injury or Fatality) precursor detection. \
# Apply the gates in this exact order and be consistent - do not soften or round in favor of a \
# more dramatic answer.

# GATE 1 - HAZARD (hazard_assessment)
# Is a high-energy hazard present, in one of these eight IOGP Life-Saving Rule categories?
# - energy_isolation: work on equipment that should have been isolated/proven dead (electrical, \
# pressure, stored mechanical/hydraulic energy, live process fluid)
# - work_at_height: a person, tool, or material able to fall far enough to kill or maim
# - lifting: cranes, hoists, rigging, slings, forklifts, suspended/swinging loads
# - line_of_fire: a person in the path of something moving, energised, or pressurised
# - confined_space: entry into a tank, vessel, pit, or space with restricted egress or hazardous atmosphere
# - hot_work: welding, cutting, grinding, or an ignition source near flammables
# - driving: operating a vehicle on site or public road
# - permit_to_work: work requiring authorisation that was not raised, valid, or followed (fallback \
# category only - use when no other category fits better)

# If several apply, use this precedence: confined_space > work_at_height > energy_isolation > \
# line_of_fire > lifting > driving > hot_work > permit_to_work.

# Chemical hazards (no dedicated category): if released from a system that should have been \
# isolated/drained first, use energy_isolation. If released and a person was in its path with no \
# isolation failure described, use line_of_fire. A missing PPE item alone, with no system release, \
# is NOT a hazard on its own - hazard_assessment is "no".

# Answer "no" when the report describes only same-level slips/trips, manual handling strain, hand \
# tools, minor sharps, heat stress, or housekeeping - these are not what this system detects.

# Answer "insufficient_information" when the text genuinely does not let you name a hazard category \
# at all (e.g. "Employee was injured. Hospitalized." with no further detail). This is NOT the same \
# as "no" - it means a human needs to read this report, not that it's safe.

# If hazard_assessment is "no" or "insufficient_information": set lsr_rule to "none", set \
# control_status to null, still score severity (see Gate 3), and is_sif_precursor is false.

# GATE 2 - CONTROL (control_status) - only assessed if Gate 1 is "yes"
# Was there a control targeting the Gate 1 hazard, and was it doing its job at that moment?
# A direct control targets the specific hazard, works even if a person makes a mistake, and was \
# verifiably in place. Training, signage, PPE that can't stop the hazard's energy, procedures on \
# paper, and "being careful" are NOT direct controls.
# - "present": a rated, targeted control was in place and the narrative explicitly says it held. \
#   Do not infer this - the text must say so.
# - "absent": no control existed, or one existed but was not used/was removed/bypassed/disabled.
# - "failed": a control was in place and did not hold (broke, gave way, was defeated by the event).
# - "unclear": a hazard is clearly present but the narrative doesn't say what the control was doing. \
#   Do NOT assume "the person got hurt so the control must have failed" - that is an unsupported \
#   inference. Silence about controls is "unclear", never "absent".
# If control_status is "present": is_sif_precursor is false regardless of severity.

# GATE 3 - SEVERITY (severity, 1-5) - always score this, for every report
# CRITICAL: score the PLAUSIBLE WORST-CASE variation, never the actual reported outcome. Ask
# explicitly: "if the timing shifted by a few seconds, the position by a metre, or a last-second
# catch/rescue had NOT happened, what is the REALISTIC outcome THEN?" - realistic, not the most
# dramatic thing you can imagine. This is a genuine discriminating judgement, not a reflex - most
# Gate-1-yes reports should NOT automatically land at 4 or 5. Base rate check: across a large set
# of real safety reports where a hazard was present, only roughly one in five plausibly escalates
# to a life-altering or fatal outcome. If you find yourself scoring 4 or 5 for most reports you
# read, you are almost certainly over-scoring - stop and re-examine what specifically makes THIS
# scenario's worst case severe, rather than defaulting to "height/energy/confined space = severe."

# Concretely ask two things before assigning 4 or 5:
# (a) Was the person's body actually in a position where the failure mode could reach them? A
#     hazard existing nearby is not the same as the person being exposed to its consequences.
# (b) Is the escalation path SHORT and DIRECT - one plausible step from where the report ends to
#     death/permanent injury - not a chain of several unlikely things all going wrong at once?

# 1 = first aid at most, and the hazard has no realistic path to worse (same-level slip, minor
#     sharps, a control that meaningfully reduced exposure even if not perfectly "present")
# 2 = medical treatment, no lost time, genuinely low worst-case potential - e.g. a hazard existed
#     but the person's actual exposure to its failure mode was marginal or brief
# 3 = lost-time injury, AND the plausible worst-case is a serious-but-recoverable injury (broken
#     bone, deep laceration) - not death or permanent disability. This is a common, legitimate
#     landing point - do not treat 3 as a rare exception.
# 4 = life-altering plausible outcome (amputation, major burn, blindness, serious head/spinal
#     injury, permanent impairment) - reserve this for scenarios where the escalation from what
#     happened to this outcome is direct and short, not several steps removed
# 5 = fatality is a plausible, direct outcome of the counterfactual variation

# An actual fatality, amputation, or ICU admission in the report scores 4 or 5 by definition. But a
# mild actual outcome does NOT automatically mean high severity either, and neither does a hazard
# merely being present near a person who was never really exposed to its failure mode - both
# directions of error matter equally here.

# DECISION
# is_sif_precursor is true ONLY when: hazard_assessment is "yes" AND control_status is "absent" or \
# "failed" AND severity is 4 or 5. Every other combination is false - including "unclear" and \
# "insufficient_information" cases, which are not confirmed precursors but still need human review \
# (that's what severity + these flags are for, not the boolean).

# OUTPUT FORMAT
# Respond with ONLY a single JSON object, no markdown fences, no commentary, matching exactly:
# {
#   "hazard_assessment": "yes" | "no" | "insufficient_information",
#   "lsr_rule": "energy_isolation" | "hot_work" | "confined_space" | "line_of_fire" | \
# "work_at_height" | "lifting" | "driving" | "permit_to_work" | "none",
#   "control_status": "absent" | "failed" | "present" | "unclear" | null,
#   "severity": <integer 1-5>,
#   "is_sif_precursor": true | false,
#   "confidence": <float 0.0-1.0, your confidence in this classification>,
#   "flagged_phrases": [<short exact phrases from the report text that drove your decision>],
#   "reasoning": "<one or two sentences explaining the gates and the decision>"
# }"""


# def _extract_json(raw_text: str) -> dict:
#     """Strip markdown fences if the model added them despite instructions, then parse."""
#     text = raw_text.strip()
#     # Handle ```json ... ``` or ``` ... ``` wrapping
#     fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
#     if fence_match:
#         text = fence_match.group(1)
#     return json.loads(text)


# def classify(report_text: str) -> dict:
#     """Implements the Classifier protocol from classifier.py.

#     Returns a plain dict matching ClassificationResult's fields - classifier.py's
#     _coerce() validates it against the Pydantic schema, so a malformed field here
#     triggers the retry-then-baseline-fallback path automatically. This function
#     should raise on any hard failure (network error, bad JSON) rather than try
#     to patch things up - that's what the fallback pipeline is for.
#     """
#     response = client.chat.completions.create(
#         model=MODEL_NAME,
#         max_tokens=3000,  # generous headroom - gpt-oss-20b spends tokens on internal
#                           # reasoning before the visible answer; too low silently
#                           # truncates to an empty response (finish_reason="length")
#         temperature=0.1,  # low temperature - this is a classification task, not creative writing
#         reasoning_effort="low",  # rubric gives explicit rules; deep reasoning isn't
#                                   # needed and just burns the token budget
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": f"Classify this safety report:\n\n{report_text}"},
#         ],
#     )

#     raw_content = response.choices[0].message.content

#     if not raw_content or not raw_content.strip():
#         raise ValueError(
#             f"Groq returned an empty response (finish_reason="
#             f"{response.choices[0].finish_reason!r}). Likely truncated by max_tokens."
#         )

#     result = _extract_json(raw_content)

#     # control_status should be null when hazard_assessment isn't "yes" - guard against
#     # the model returning an empty string instead of proper JSON null.
#     if result.get("control_status") in ("", "null", "None"):
#         result["control_status"] = None

#     # Recompute is_sif_precursor ourselves from the three gates, per the rubric's own
#     # decision table (v2.1 §6) - never trust the model's boolean directly. The model
#     # can be internally inconsistent (e.g. returning severity=3 AND
#     # is_sif_precursor=true in the same response, which the rubric says is invalid).
#     # A database check constraint caught exactly this once; deriving the boolean
#     # deterministically here means it can never happen again, for any report.
#     result["is_sif_precursor"] = (
#         result.get("hazard_assessment") == "yes"
#         and result.get("control_status") in ("absent", "failed")
#         and isinstance(result.get("severity"), (int, float))
#         and result["severity"] >= 4
#     )

#     return result


# # Required by the Classifier protocol in classifier.py
# # Bumped to distinguish predictions made under the corrected Gate 3 prompt
# # (less over-flagging) from earlier ones under the same base model version -
# # this lets a resumable reclassify script tell old and new answers apart.
# classify.version = "groq-openai/gpt-oss-20b-rubric-v2.1-g3fix2"






"""
classifier_llm.py

The real classifier. One structured Groq API call per report, prompted with
rubric v2.1's three gates, returning the exact schema shape `classifier.py`
expects (see schemas.py: ClassificationResult).

This module does NOT touch classifier.py's cache/timeout/fallback logic -
it only implements the `Classifier` protocol (a callable with a `.version`
attribute) and gets wired in from main.py via:

    from . import classifier_llm
    classifier.register_primary(classifier_llm.classify)

Needs GROQ_API_KEY set in the environment (same key already used by
generate_synthetic_reports_free.py).
"""

import os
import json
import re
from groq import Groq

MODEL_NAME = "openai/gpt-oss-20b"  # same free-tier model already in use elsewhere

client = Groq()  # reads GROQ_API_KEY from environment

# ---------------------------------------------------------------------------
# Rubric v2.1, condensed into a system prompt. This is not the full document -
# it's the operative gates and the decision table, which is what the model
# actually needs to apply consistently. Full text lives in docs/rubric.md.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a safety analyst applying a strict three-gate rubric to classify \
industrial safety incident reports for SIF (Serious Injury or Fatality) precursor detection. \
Apply the gates in this exact order and be consistent - do not soften or round in favor of a \
more dramatic answer.

GATE 1 - HAZARD (hazard_assessment)
Is a high-energy hazard present, in one of these eight IOGP Life-Saving Rule categories?
- energy_isolation: work on equipment that should have been isolated/proven dead (electrical, \
pressure, stored mechanical/hydraulic energy, live process fluid)
- work_at_height: a person, tool, or material able to fall far enough to kill or maim
- lifting: cranes, hoists, rigging, slings, forklifts, suspended/swinging loads
- line_of_fire: a person in the path of something moving, energised, or pressurised
- confined_space: entry into a tank, vessel, pit, or space with restricted egress or hazardous atmosphere
- hot_work: welding, cutting, grinding, or an ignition source near flammables
- driving: operating a vehicle on site or public road
- permit_to_work: work requiring authorisation that was not raised, valid, or followed (fallback \
category only - use when no other category fits better)

If several apply, use this precedence: confined_space > work_at_height > energy_isolation > \
line_of_fire > lifting > driving > hot_work > permit_to_work.

Chemical hazards (no dedicated category): if released from a system that should have been \
isolated/drained first, use energy_isolation. If released and a person was in its path with no \
isolation failure described, use line_of_fire. A missing PPE item alone, with no system release, \
is NOT a hazard on its own - hazard_assessment is "no".

Answer "no" when the report describes only same-level slips/trips, manual handling strain, hand \
tools, minor sharps, heat stress, or housekeeping - these are not what this system detects.

Answer "insufficient_information" when the text genuinely does not let you name a hazard category \
at all (e.g. "Employee was injured. Hospitalized." with no further detail). This is NOT the same \
as "no" - it means a human needs to read this report, not that it's safe.

If hazard_assessment is "no" or "insufficient_information": set lsr_rule to "none", set \
control_status to null, still score severity (see Gate 3), and is_sif_precursor is false.

GATE 2 - CONTROL (control_status) - only assessed if Gate 1 is "yes"
Was there a control targeting the Gate 1 hazard, and was it doing its job at that moment?
A direct control targets the specific hazard, works even if a person makes a mistake, and was \
verifiably in place. Training, signage, PPE that can't stop the hazard's energy, procedures on \
paper, and "being careful" are NOT direct controls.
- "present": a rated, targeted control was in place and the narrative explicitly says it held. \
  Do not infer this - the text must say so.
- "absent": no control existed, or one existed but was not used/was removed/bypassed/disabled.
- "failed": a control was in place and did not hold (broke, gave way, was defeated by the event).
- "unclear": a hazard is clearly present but the narrative doesn't say what the control was doing. \
  Do NOT assume "the person got hurt so the control must have failed" - that is an unsupported \
  inference. Silence about controls is "unclear", never "absent".
If control_status is "present": is_sif_precursor is false regardless of severity.

GATE 3 - SEVERITY (severity, 1-5) - always score this, for every report
CRITICAL: score the PLAUSIBLE WORST-CASE variation, never the actual reported outcome. Ask
explicitly: "if the timing shifted by a few seconds, the position by a metre, or a last-second
catch/rescue had NOT happened, what is the REALISTIC outcome THEN?" - realistic, not the most
dramatic thing you can imagine. This is a genuine discriminating judgement, not a reflex - most
Gate-1-yes reports should NOT automatically land at 4 or 5. Base rate check: across a large set
of real safety reports where a hazard was present, only roughly one in five plausibly escalates
to a life-altering or fatal outcome. If you find yourself scoring 4 or 5 for most reports you
read, you are almost certainly over-scoring - stop and re-examine what specifically makes THIS
scenario's worst case severe, rather than defaulting to "height/energy/confined space = severe."

Two worked examples to calibrate against:
- A contractor on a ladder loses footing and falls six inches onto a padded floor, spraining a
  wrist. Even though a required guard rail was missing, the fall distance is trivial - the
  realistic worst case is still a sprain or minor fracture, not a life-altering injury. Score
  this 2, not 4.
- A worker slips off a hatch and drops two feet onto a steel floor, recovering immediately with
  no injury. A missing latch is a real control gap, but a two-foot drop with an immediate,
  uninjured recovery has no direct path to death - the worst case here is a bruise or minor
  sprain. Score this 2, not 5.
Do not let "a control was missing" by itself pull severity upward - severity is about the
physical consequence of the realistic counterfactual, not about how serious the control gap
sounds on its own.

Concretely ask two things before assigning 4 or 5:
(a) Was the person's body actually in a position where the failure mode could reach them? A
    hazard existing nearby is not the same as the person being exposed to its consequences.
(b) Is the escalation path SHORT and DIRECT - one plausible step from where the report ends to
    death/permanent injury - not a chain of several unlikely things all going wrong at once?

1 = first aid at most, and the hazard has no realistic path to worse (same-level slip, minor
    sharps, a control that meaningfully reduced exposure even if not perfectly "present")
2 = medical treatment, no lost time, genuinely low worst-case potential - e.g. a hazard existed
    but the person's actual exposure to its failure mode was marginal or brief
3 = lost-time injury, AND the plausible worst-case is a serious-but-recoverable injury (broken
    bone, deep laceration) - not death or permanent disability. This is a common, legitimate
    landing point - do not treat 3 as a rare exception.
4 = life-altering plausible outcome (amputation, major burn, blindness, serious head/spinal
    injury, permanent impairment) - reserve this for scenarios where the escalation from what
    happened to this outcome is direct and short, not several steps removed
5 = fatality is a plausible, direct outcome of the counterfactual variation

An actual fatality, amputation, or ICU admission in the report scores 4 or 5 by definition. But a
mild actual outcome does NOT automatically mean high severity either, and neither does a hazard
merely being present near a person who was never really exposed to its failure mode - both
directions of error matter equally here.

DECISION
is_sif_precursor is true ONLY when: hazard_assessment is "yes" AND control_status is "absent" or \
"failed" AND severity is 4 or 5. Every other combination is false - including "unclear" and \
"insufficient_information" cases, which are not confirmed precursors but still need human review \
(that's what severity + these flags are for, not the boolean).

OUTPUT FORMAT
Respond with ONLY a single JSON object, no markdown fences, no commentary, matching exactly:
{
  "hazard_assessment": "yes" | "no" | "insufficient_information",
  "lsr_rule": "energy_isolation" | "hot_work" | "confined_space" | "line_of_fire" | \
"work_at_height" | "lifting" | "driving" | "permit_to_work" | "none",
  "control_status": "absent" | "failed" | "present" | "unclear" | null,
  "severity": <integer 1-5>,
  "is_sif_precursor": true | false,
  "confidence": <float 0.0-1.0, your confidence in this classification>,
  "flagged_phrases": [<short exact phrases from the report text that drove your decision>],
  "reasoning": "<one or two sentences explaining the gates and the decision>"
}"""


def _extract_json(raw_text: str) -> dict:
    """Strip markdown fences if the model added them despite instructions, then parse."""
    text = raw_text.strip()
    # Handle ```json ... ``` or ``` ... ``` wrapping
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    return json.loads(text)


def classify(report_text: str) -> dict:
    """Implements the Classifier protocol from classifier.py.

    Returns a plain dict matching ClassificationResult's fields - classifier.py's
    _coerce() validates it against the Pydantic schema, so a malformed field here
    triggers the retry-then-baseline-fallback path automatically. This function
    should raise on any hard failure (network error, bad JSON) rather than try
    to patch things up - that's what the fallback pipeline is for.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=3000,  # generous headroom - gpt-oss-20b spends tokens on internal
                          # reasoning before the visible answer; too low silently
                          # truncates to an empty response (finish_reason="length")
        temperature=0.1,  # low temperature - this is a classification task, not creative writing
        reasoning_effort="low",  # rubric gives explicit rules; deep reasoning isn't
                                  # needed and just burns the token budget
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this safety report:\n\n{report_text}"},
        ],
    )

    raw_content = response.choices[0].message.content

    if not raw_content or not raw_content.strip():
        raise ValueError(
            f"Groq returned an empty response (finish_reason="
            f"{response.choices[0].finish_reason!r}). Likely truncated by max_tokens."
        )

    result = _extract_json(raw_content)

    # control_status should be null when hazard_assessment isn't "yes" - guard against
    # the model returning an empty string instead of proper JSON null.
    if result.get("control_status") in ("", "null", "None"):
        result["control_status"] = None

    # Recompute is_sif_precursor ourselves from the three gates, per the rubric's own
    # decision table (v2.1 §6) - never trust the model's boolean directly. The model
    # can be internally inconsistent (e.g. returning severity=3 AND
    # is_sif_precursor=true in the same response, which the rubric says is invalid).
    # A database check constraint caught exactly this once; deriving the boolean
    # deterministically here means it can never happen again, for any report.
    result["is_sif_precursor"] = (
        result.get("hazard_assessment") == "yes"
        and result.get("control_status") in ("absent", "failed")
        and isinstance(result.get("severity"), (int, float))
        and result["severity"] >= 4
    )

    return result


# Required by the Classifier protocol in classifier.py
# Bumped to distinguish predictions made under the g3fix3 severity-calibration
# examples (short-fall / quick-recovery worked examples added to Gate 3) from
# earlier g3fix2 predictions - lets the resumable reclassify script tell them apart.
classify.version = "groq-openai/gpt-oss-20b-rubric-v2.1-g3fix3"