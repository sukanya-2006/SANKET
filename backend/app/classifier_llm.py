"""
classifier_llm.py

The real classifier. One structured Groq API call per report, prompted with
rubric v2.2's three gates, returning the exact schema shape `classifier.py`
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
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"  # same free-tier model already in use elsewhere

# Built on first use, not at import. Constructing this at import time meant a missing
# GROQ_API_KEY took down the entire API — no /health, no /reports, no dashboard — which is
# the opposite of the degraded mode this classifier is supposed to sit behind.
_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq()  # reads GROQ_API_KEY from environment
    return _client

# ---------------------------------------------------------------------------
# Rubric v2.2, condensed into a system prompt. This is not the full document -
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
- line_of_fire also includes caught-in, caught-between, pinch-point, crush, kickback,
  and unguarded-moving-part events when a person's body is exposed to the movement
  or release of mechanical energy. Examples include hands caught in rollers/chucks,
  machinery pinch points, moving machine parts, and material kicked back toward a worker.
- confined_space: entry into a tank, vessel, pit, or space with restricted egress or hazardous atmosphere
- hot_work: welding, cutting, grinding, or an ignition source near flammables
- driving: operating a vehicle on site or public road
- When a vehicle itself is moving and strikes, pins, or runs over a person, classify
  the primary hazard as driving. When the hazard is a load being lifted, suspended,
  swung, or dropped by equipment, classify it as lifting. When the primary exposure
  is a moving object or machine part striking/catching a person, classify it as
  line_of_fire.
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
dramatic thing you can imagine. This is a genuine discriminating judgement, not a reflex - a
Gate-1-yes report does NOT automatically land at 4 or 5.

Score each report on its own facts, and do NOT calibrate to how often you expect severe reports
to occur. You have no reliable information about the base rate of the set you are reading, and
guessing at it makes you wrong on the report in front of you. If the realistic worst-case outcome
genuinely involves permanent disability or death, score 4 or 5 even if that means many reports in
a row land there. Never lower a score to keep a distribution looking plausible.

(Our own labelled set runs at roughly 59% precursors, because every synthetic report was
generated centred on a hazard category. An earlier version of this prompt asserted "roughly one
in five", which is the rate in a realistic report stream but not in this data - and the model was
penalised for obeying it. See docs/eval-diagnosis.md.)

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
(b) THE ONE-CHANGE RULE. You may change EXACTLY ONE thing: the timing by a few seconds, OR the
    position by a metre, OR remove one last-second catch or rescue. Not two. Not a chain. If you
    catch yourself thinking "and then, if he had also...", you have made a second change - go
    back and score the version with one. Two human annotators diverged by three and four points
    on 76 of 180 reports precisely because one of them chained changes and the other did not.

THE BANDS. Judge by the observable outcome, not by how serious the situation sounds. These are
the same words the human annotators are applying, and you are scored against their labels.

1 = first aid from a site kit, nothing more. The hazard has no realistic path to worse
    (same-level slip, minor sharps, a control that meaningfully reduced exposure).
2 = seen by a doctor, back at work the same or next shift. Stitches, sprain, minor burn. A
    hazard existed but the person's exposure to its failure mode was marginal or brief.
3 = off work for a while, THEN BACK TO THE SAME JOB. Fracture, deep laceration needing surgery,
    concussion. Full recovery expected, no permanent restriction. This is a common, legitimate
    landing point - do not treat 3 as a rare exception.
4 = THE PERSON CANNOT RETURN TO THE SAME JOB. Amputation, loss of an eye, spinal cord injury,
    burn needing grafts, permanent restriction. Not "was badly hurt" - permanently unable.
5 = someone dies, and you can name the mechanism in one sentence after ONE change.
IMPORTANT SEVERITY CALIBRATION - read this as a correction to a WORDING trap, not a push toward
high scores:
Do not downgrade severity just because the report uses a mild-sounding WORD like "hospitalized"
when the underlying MECHANISM you'd get after ONE change is genuinely fatal or permanently
disabling. The word "hospitalized" alone tells you nothing - a hospitalization for observation
after a two-foot fall is a 2, and a hospitalization after a vehicle pinning is very possibly a 5.
Read the mechanism, not the adjective.

Use severity 4 when the described mechanism could realistically cause permanent loss of function,
amputation, major disabling injury, or inability to return to the same job after ONE change.
Use severity 5 when ONE realistic change could result in death.

For vehicle strikes, crushing/pinning, severe falls, major machinery entrapment, falling heavy
objects, electrical contact, or serious head/neck injuries, explicitly apply the ONE-CHANGE RULE
rather than anchoring on the reported outcome's wording alone - but the ONE-CHANGE RULE cuts both
ways. Most reports in these categories still describe a mechanism where the realistic worst case,
after exactly one change, is a fracture or laceration with full recovery (severity 3), not death.
Only move to 4 or 5 when the one-change mechanism itself - not the category name - actually
reaches "permanently unable to do the job" or "named cause of death."

THE 3/4 BOUNDARY IS THE ONE THAT DECIDES THE LABEL, and it is a single question:
    "Would this person be permanently unable to do the same job again?"
    Yes -> 4 or 5.   No -> 3 or below.
If you are genuinely torn between 3 and 4, answer 3 and say why in `reasoning`.

An actual fatality, amputation, or ICU admission in the report scores 4 or 5 by definition. But a
mild actual outcome does NOT automatically mean high severity either, and neither does a hazard
merely being present near a person who was never really exposed to its failure mode - both
directions of error matter equally here.

A third worked example, because "hospitalized" is exactly the word that misleads: a worker is
struck by a swinging pipe wrench that slips off a fitting, is hospitalized overnight for a scalp
laceration and observation, and is discharged the next day with no lasting deficit. One change
(the wrench striking a few centimetres differently) does not plausibly turn this into a fatality
or a permanent disability - it stays a laceration needing stitches. Score this 3, not 5, even
though the actual report says "hospitalized."

Before you finalize a 4 or 5, re-read your own `reasoning` and check it names a specific
realistic mechanism of death or permanent disability after exactly one change - not just the
hazard category. If it doesn't, the score is too high; lower it.

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
    response = None
    last_exc = None

    for attempt in range(3):
        try:
            response = _get_client().chat.completions.create(
                model=MODEL_NAME,
                max_tokens=500,
                temperature=0.1,
                reasoning_effort="low",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this safety report:\n\n{report_text}"},
                ],
            )
            break

        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()

            is_retryable = (
                "429" in err_str
                or "rate_limit" in err_str
                or "connection" in err_str
                or "socket" in err_str
                or "unreachable" in err_str
            )

            if is_retryable and attempt < 2:
                import time
                time.sleep(3.0 * (attempt + 1))
                continue

            raise

    if response is None:
        raise RuntimeError(
            f"Groq call failed after all retries: {last_exc}"
        ) from last_exc
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
    # decision table (v2.2 §6) - never trust the model's boolean directly. The model
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
# The version string ends up in predictions.model_version and scopes every dashboard
# aggregate, so it must change whenever the prompt does - otherwise old and new judgements
# are averaged together silently.
# Bumped from g3fix4 to g3fix5: the g3fix2/g3fix3/g3fix4 "IMPORTANT SEVERITY CALIBRATION"
# block was written to stop the model from being misled by mild-sounding WORDING like
# "hospitalized" when the underlying mechanism was actually severe. That fix was correct
# on its own, but 0cdd7e8 separately removed the base-rate anchor that had been the only
# thing pulling the distribution back down for reports outside the enriched synthetic gold
# set. With both changes in place and nothing to counterbalance the calibration block on
# real (non-enriched) worker-submitted text, the model was left with a one-directional
# nudge toward 4/5 and started landing on severity 5 for most live reports regardless of
# their actual content - see the investigation notes in docs/severity-5-bug-investigation.md.
# g3fix5 reframes the calibration block as a correction to *wording*, not a push toward
# high scores, and adds a third worked example plus a self-check specifically for the
# "hospitalized" trap that most triggered the bias.
classify.version = "groq-openai/gpt-oss-20b-rubric-v2.2-g3fix5"