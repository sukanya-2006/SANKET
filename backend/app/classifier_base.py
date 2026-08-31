"""
classifier_base.py

The baseline classifier - what answers when the primary (Groq) classifier
fails, times out, or returns something the schema rejects twice. Per the
tech stack doc, this is deliberately simple: TF-IDF + Logistic Regression,
predicting is_sif_precursor directly, with explainability via top-weighted
words rather than SHAP.

IMPORTANT - this only predicts is_sif_precursor with real ML. The other
schema fields (lsr_rule, control_status, severity) are filled with coarse,
honest heuristics below - the baseline was never meant to match the LLM's
depth on those fields, only to give a reasonable, fast, always-available
fallback answer. This is intentional, not a shortcut - see the tech stack
doc's framing of the baseline-vs-LLM gap as the strongest differentiator
in the eval section.

Needs backend/app/baseline_model.joblib to exist - run train_baseline.py
first (from the project root, after gold_labels.csv exists). Until that
model file exists, importing this module raises a clear error rather than
silently falling back to something untrained - see classifier.py's own
fallback-to-stub behaviour for what happens if THIS classifier also fails
to load.
"""

import json
import os

import joblib

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "baseline_model.joblib")
_TOP_WORDS_PATH = os.path.join(os.path.dirname(__file__), "baseline_top_words.json")

if not os.path.exists(_MODEL_PATH):
    raise FileNotFoundError(
        f"{_MODEL_PATH} not found. Train the baseline first: "
        "run `python train_baseline.py` from the project root once "
        "data/gold_labels.csv exists (after M1/M3 finish labeling)."
    )

_pipeline = joblib.load(_MODEL_PATH)

_top_words = {"top_positive": [], "top_negative": []}
if os.path.exists(_TOP_WORDS_PATH):
    with open(_TOP_WORDS_PATH, "r", encoding="utf-8") as f:
        _top_words = json.load(f)

_TOP_POSITIVE_WORDS = {item["word"] for item in _top_words.get("top_positive", [])}

# Very coarse keyword -> LSR rule mapping, used only when the binary model
# says "precursor" and we need SOME rule to display - this is a heuristic
# fallback, not a trained classifier. The LLM classifier does this properly;
# this only needs to be good enough for a degraded-mode answer.
_LSR_KEYWORDS = {
    "confined_space": ["confined space", "tank", "vessel", "hatch", "pit", "vent"],
    "work_at_height": ["height", "scaffold", "fall", "ladder", "harness", "guardrail"],
    "energy_isolation": ["isolat", "lockout", "lock-out", "lock out", "energiz", "de-energiz"],
    "line_of_fire": ["line of fire", "struck by", "swung", "path of"],
    "lifting": ["crane", "hoist", "rigging", "sling", "forklift", "load"],
    "hot_work": ["weld", "cutting", "grinding", "ignition", "flame", "hot work"],
    "driving": ["vehicle", "truck", "driving", "drove", "collision"],
}


def _guess_lsr_rule(text: str) -> str:
    lowered = text.lower()
    for rule, keywords in _LSR_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return rule
    return "none"


def classify(report_text: str) -> dict:
    """Implements the Classifier protocol from classifier.py.

    Returns a dict matching ClassificationResult's fields. Only
    is_sif_precursor and confidence come from real model output - the rest
    are honest, coarse heuristics appropriate for a degraded-mode fallback,
    not a second opinion meant to rival the primary classifier.
    """
    proba = _pipeline.predict_proba([report_text])[0]
    is_precursor = bool(proba[1] >= 0.5)
    confidence = float(proba[1] if is_precursor else proba[0])

    lowered = report_text.lower()
    matched_words = [w for w in _TOP_POSITIVE_WORDS if w in lowered]

    lsr_rule = _guess_lsr_rule(report_text) if is_precursor else "none"

    return {
        "hazard_assessment": "yes" if is_precursor else "no",
        "lsr_rule": lsr_rule,
        # The baseline has no real signal on control status - "unclear" is
        # the honest answer, not a guess dressed up as one.
        "control_status": "unclear" if is_precursor else None,
        # Coarse: precursor predictions default to severity 4 (the minimum
        # that satisfies is_sif_precursor under the rubric's own decision
        # table), non-precursors to 2. This is a placeholder scale, not a
        # real severity judgement - the LLM classifier is what actually
        # reasons about severity.
        "severity": 4 if is_precursor else 2,
        "is_sif_precursor": is_precursor,
        "confidence": round(confidence, 4),
        "flagged_phrases": matched_words[:5],
        "reasoning": (
            f"Baseline keyword model (TF-IDF + logistic regression): "
            f"{'flagged' if is_precursor else 'did not flag'} this report as a "
            f"SIF precursor (confidence {confidence:.2f}). This is a fast, "
            f"degraded-mode fallback - it does not reason about control status "
            f"or plausible-variation severity the way the primary classifier does."
        ),
    }


# Required by the Classifier protocol in classifier.py
classify.version = "baseline-tfidf-logreg-v1"