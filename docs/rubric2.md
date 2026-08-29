SIF Precursor Classification Rubric

Project: SIF Precursor Detection — SIH 2026
Version: 1.0
Status: Draft for team approval
Owner: M1 — Lead
Purpose: Human annotation and ML classifier evaluation

---

1. Purpose

This rubric defines how workplace safety reports are classified for Serious Injury or Fatality (SIF) precursor potential.

The goal is to ensure that:

- human annotators apply the same decision criteria;
- the ML classifier follows the same logic;
- classifications are reproducible and auditable;
- model predictions can be evaluated against human-labelled data.

Each report receives:

1. a high-energy hazard assessment;
2. a direct-control status;
3. an applicable IOGP Life-Saving Rule;
4. a severity score from 1–5;
5. a final SIF precursor decision;
6. a confidence score and supporting evidence.

---

2. Classification Output

The classification schema contains the following fields:

Field| Allowed values
"hazard_assessment"| "yes", "no", "insufficient_information"
"lsr_rule"| One of the 8 project LSRs or "none"
"control_status"| "absent", "failed", "present", "unclear", or omitted when not applicable
"severity"| Integer from 1 to 5
"is_sif_precursor"| "true" or "false"
"confidence"| Number from 0 to 1
"flagged_phrases"| List of phrases from the report supporting the decision
"reasoning"| Explanation of the classification

---

3. Core SIF Precursor Definition

A report is a SIF precursor when it describes a credible situation involving:

1. a sufficiently high-energy hazard;
2. inadequate control of that hazard; and
3. a credible possibility of serious injury or fatality.

The classification should focus on the actual conditions described in the report, not on assumptions about what might exist at the workplace.

A report should be marked "is_sif_precursor = true" only when the evidence supports a credible SIF pathway.

---

4. Hazard Assessment

4.1 Question

«Is a sufficiently high-energy hazard present in the reported situation?»

The annotator must determine whether the report describes an energy source capable of causing serious injury or fatality.

"YES"

Use "yes" when:

- a qualifying high-energy hazard is clearly present;
- the hazard magnitude meets the applicable project criterion; and
- the worker is exposed to, or credibly within the potential path of, that energy.

Examples include:

- working at a significant height;
- exposure to energized electrical systems;
- exposure to pressurized equipment;
- moving machinery capable of crushing or amputation;
- suspended loads;
- vehicle/mobile-equipment interaction;
- fire or explosion hazards.

"NO"

Use "no" when:

- no qualifying high-energy hazard is present;
- the described energy is clearly below the applicable project criterion; or
- the situation cannot realistically produce serious harm through a high-energy mechanism.

Examples:

- minor housekeeping issue;
- ordinary ergonomic discomfort;
- low-risk administrative issue;
- superficial hazard with no credible high-energy exposure.

"INSUFFICIENT_INFORMATION"

Use "insufficient_information" when:

- a potentially high-energy hazard is mentioned but its magnitude is unknown;
- the report does not provide enough information to determine whether the applicable threshold is met;
- the energy source or exposure is ambiguous.

Do not guess missing information.

---

5. High-Energy Hazard Categories

The project recognizes the following energy sources:

1. Fall from height
2. Electrical energy
3. Pressure
4. Mechanical energy
5. Thermal energy
6. Chemical energy
7. Fire/explosion
8. Vehicle/mobile-equipment energy
9. Lifting/suspended-load energy

The applicable project thresholds must be used consistently by all annotators.

Known project examples include:

Energy source| Threshold/example
Fall| Greater than 1.2 m
Electrical| Greater than 50 V
Pressure| Greater than 7 bar
Mechanical| Use approved project criterion
Thermal| Use approved project criterion
Chemical| Use approved project criterion
Fire/explosion| Use approved project criterion
Vehicle/mobile equipment| Use approved project criterion
Lifting/suspended load| Use approved project criterion

Where an exact threshold has not been formally defined, annotators must not invent one.

---

6. Control Status

6.1 Question

«What is the status of the direct control intended to prevent exposure to the identified hazard?»

A direct control is a control specifically intended to prevent or stop exposure to the relevant hazardous energy.

Examples:

- machine guard;
- interlock;
- verified energy isolation;
- physical barrier;
- exclusion zone;
- fall-protection system;
- engineered shutdown;
- effective containment.

---

6.2 "ABSENT"

Use "absent" when the required direct control is not present.

Examples:

- required guard is missing;
- fall-protection system is not provided;
- required isolation has not been established;
- exclusion barrier is missing.

---

6.3 "FAILED"

Use "failed" when the direct control exists but does not function effectively.

Examples:

- guard is installed but broken;
- interlock does not work;
- isolation mechanism failed;
- barrier is present but cannot prevent exposure.

Use "failed" rather than "absent" when the control exists but is ineffective.

---

6.4 "PRESENT"

Use "present" when the relevant direct control is clearly present and functioning effectively.

The evidence should indicate that the control is capable of preventing the relevant exposure.

A generic statement such as "workers were trained" does not establish that a direct control was present.

---

6.5 "UNCLEAR"

Use "unclear" when the report does not provide enough information to determine whether the relevant direct control was present or effective.

Do not assume that a control existed simply because normal procedures would require it.

For this project:

«Absence of evidence of a required direct control is treated as evidence of absence unless the report explicitly establishes that the control was present and effective.»

---

7. Controls That Do Not Automatically Count as Direct Controls

The following do not independently satisfy the direct-control requirement:

- training;
- worker awareness;
- toolbox talks;
- general safety procedures;
- safety policies;
- verbal instructions;
- supervision;
- PPE alone;
- permits alone.

These may provide useful context but should not automatically result in "control_status = present".

The control must specifically address the hazardous energy involved.

---

8. Bypassed Controls

A bypassed, defeated, disabled, removed, or intentionally circumvented direct control should generally be treated as an ineffective control.

Therefore:

control_status = failed

when a required direct control exists but has been deliberately bypassed or defeated.

Examples:

- safety interlock bypassed;
- machine guard deliberately removed;
- alarm disabled;
- isolation defeated;
- safety device circumvented.

The associated LSR field should not use a separate "Bypassing Safety Controls" value because the project treats bypassing as part of the control assessment.

---

9. Life-Saving Rule (LSR)

Each report should be assigned one project LSR where applicable.

The project uses the following eight Life-Saving Rules:

Enum value| Meaning
"energy_isolation"| Work involving hazardous energy requiring isolation
"hot_work"| Hot work involving ignition or high-temperature sources
"confined_space"| Entry/work in confined spaces
"line_of_fire"| Exposure to moving objects, stored energy, or hazardous trajectories
"work_at_height"| Work where a fall from height is possible
"lifting"| Mechanical lifting or suspended loads
"driving"| Driving or vehicle/mobile-equipment activities
"permit_to_work"| Work requiring formal authorization/permit controls
"none"| No applicable project LSR

---

10. LSR Selection Rules

Select the LSR that most directly represents the hazardous activity described.

If multiple LSRs appear applicable, choose the one most directly connected to the SIF pathway.

LSR classification is descriptive and does not by itself determine whether a report is a SIF precursor.

For example:

hazard_assessment = yes
control_status = present
lsr_rule = work_at_height
is_sif_precursor = false

A report can therefore involve an LSR activity without being a SIF precursor.

---

11. "NONE" for LSR

Use:

lsr_rule = none

when:

- none of the eight project LSRs applies;
- the described situation does not correspond to an LSR activity; or
- there is insufficient evidence to identify a relevant LSR.

Do not force an LSR assignment simply because the report describes a safety issue.

---

12. Severity Score

Every report receives a severity score from 1 to 5.

The severity score represents the credible consequence severity of the reported situation, rather than the likelihood of the event occurring.

Score| Meaning
1 — Negligible| No credible injury or only trivial consequence
2 — Minor| Minor injury possible; unlikely to result in serious harm
3 — Moderate| Significant injury possible, but SIF-level consequence is not the most credible outcome
4 — Severe| Serious/life-altering injury is realistically possible
5 — Catastrophic| Fatality or extremely severe/life-altering injury is realistically possible

Severity 1

Examples:

- minor housekeeping issue;
- negligible physical hazard;
- no credible injury pathway.

Severity 2

Examples:

- minor injury could reasonably occur;
- low-energy exposure;
- small cuts, bruises, or similar consequences.

Severity 3

Examples:

- significant injury is plausible;
- injury may require medical treatment;
- situation has meaningful harm potential but does not establish a clear SIF pathway.

Severity 4

Examples:

- permanent disability;
- major traumatic injury;
- amputation;
- serious hospitalization;
- credible life-altering injury.

Severity 5

Examples:

- credible fatality;
- catastrophic injury;
- extremely high-energy exposure where a fatal outcome is realistically possible.

Important: Severity is a consequence scale, not a probability score.

A high severity score does not automatically make a report a SIF precursor.

---

13. SIF Precursor Decision

The final field:

is_sif_precursor

is a Boolean decision.

"true"

Use "true" when all of the following are satisfied:

1. "hazard_assessment = yes";
2. the direct control is absent, failed, or otherwise ineffective;
3. the consequence is plausibly severe enough to cause life-altering injury or fatality;
4. the SIF pathway is supported by the report evidence.

Typical combination:

hazard_assessment = yes
control_status = absent
severity = 4 or 5
is_sif_precursor = true

or:

hazard_assessment = yes
control_status = failed
severity = 4 or 5
is_sif_precursor = true

---

"false"

Use "false" when:

- no qualifying high-energy hazard exists;
- the direct control is clearly present and effective;
- the potential consequence is not SIF-level;
- or the report does not establish a credible SIF pathway.

Examples:

hazard_assessment = no
control_status = null
severity = 2
is_sif_precursor = false

or:

hazard_assessment = yes
control_status = present
severity = 5
is_sif_precursor = false

The second example is important: high energy + high severity potential does not automatically mean SIF precursor when the direct control is demonstrably effective.

---

14. Insufficient Information and Final Classification

The schema uses a Boolean "is_sif_precursor", so uncertainty must be handled carefully.

If the evidence is genuinely insufficient to establish a SIF precursor, the annotator should not automatically label it "true".

Use:

hazard_assessment = insufficient_information

or:

control_status = unclear

where appropriate, and set:

is_sif_precursor = false

unless the available evidence independently establishes a credible SIF precursor.

The "reasoning" field must explain the uncertainty.

---

15. Evidence: Flagged Phrases

"flagged_phrases" must contain short excerpts from the original report that support the classification.

Good examples:

[
  "working 3 metres above ground",
  "guard had been removed",
  "machine was still energized"
]

Poor examples:

[
  "dangerous",
  "SIF",
  "unsafe"
]

Flagged phrases should identify actual evidence, not the annotator's conclusion.

Where possible, include evidence for:

- the hazardous energy;
- the control failure/absence;
- the potential serious consequence.

---

16. Reasoning

The "reasoning" field should briefly explain how the evidence led to the classification.

A good reasoning statement should answer:

1. What hazard is present?
2. What is the control status?
3. What consequence is credible?
4. Why is the final SIF decision true or false?

Good example

«"The worker was exposed to an energized electrical system above the project threshold. The required isolation was not established, leaving the direct control absent. Contact with the energized equipment could plausibly result in fatal electrocution, so the report is classified as a SIF precursor."»

Poor example

«"This is very dangerous and should be fixed."»

Reasoning must be evidence-based and should not introduce facts that are not contained in the report.

---

17. Confidence

"confidence" is a value from:

0.0 to 1.0

It represents the classifier/annotator's confidence in the final classification.

Interpretation:

Confidence| Interpretation
0.90–1.00| Very strong evidence
0.75–0.89| Strong evidence
0.50–0.74| Moderate evidence
0.00–0.49| Weak/uncertain evidence

Confidence must not be confused with severity.

For example:

severity = 5
confidence = 0.55

means the potential consequence is catastrophic, but the evidence supporting the classification is uncertain.

---

18. Decision Examples

Example 1 — SIF Precursor

Report:

«"Worker was repairing a machine while the electrical supply remained energized. The isolation procedure had not been completed."»

Assessment:

hazard_assessment = yes
control_status = absent
lsr_rule = energy_isolation
severity = 5
is_sif_precursor = true

Reason:

The report establishes high-energy electrical exposure and absence of the direct isolation control. Fatal injury is credible.

---

Example 2 — High Energy but Controlled

Report:

«"Technician worked near energized equipment. The circuit was isolated, locked out and verified de-energized before work began."»

Assessment:

hazard_assessment = yes
control_status = present
lsr_rule = energy_isolation
severity = 5
is_sif_precursor = false

Reason:

High-energy electrical equipment exists, but the relevant direct control is verified as effective.

---

Example 3 — Fall Hazard

Report:

«"Worker was performing maintenance approximately 3 metres above ground without fall protection."»

Assessment:

hazard_assessment = yes
control_status = absent
lsr_rule = work_at_height
severity = 5
is_sif_precursor = true

Reason:

The height exceeds the project threshold, fall protection is absent, and a fatal or life-altering fall is credible.

---

Example 4 — Control Present

Report:

«"Worker performed maintenance from an elevated platform. Guardrails were installed and inspected before work."»

Assessment:

hazard_assessment = yes
control_status = present
lsr_rule = work_at_height
severity = 4
is_sif_precursor = false

Reason:

Although elevated work presents potentially severe consequences, the direct fall-prevention control is reported as present and effective.

---

Example 5 — Insufficient Information

Report:

«"Worker was exposed to a pressure-related hazard during maintenance."»

Assessment:

hazard_assessment = insufficient_information
control_status = unclear
lsr_rule = energy_isolation
severity = 3
is_sif_precursor = false

Reason:

The report does not provide enough information about pressure magnitude or the status of the relevant control to establish a SIF pathway.

---

Example 6 — Minor Hazard

Report:

«"Several small pieces of packaging were found on the floor near the workstation."»

Assessment:

hazard_assessment = no
control_status = null
lsr_rule = none
severity = 1
is_sif_precursor = false

---

19. Annotation Rules

Annotators must:

- use only information contained in the report;
- apply the same thresholds and definitions to every report;
- avoid guessing missing facts;
- distinguish hazard presence from control effectiveness;
- distinguish severity from likelihood;
- provide evidence through "flagged_phrases";
- explain non-obvious decisions in "reasoning".

Annotators must not:

- classify something as SIF solely because it sounds dangerous;
- classify something as SIF solely because an LSR was violated;
- treat PPE or training alone as an effective direct control;
- invent energy magnitudes;
- infer controls that are not supported by the report;
- change labels to improve agreement with another annotator.

---

20. Human Double-Annotation Protocol

All reports in the annotation dataset must be independently labelled by two annotators.

Current annotation ownership:

- M3 — First annotator
- M1 — Second annotator

The annotators must work independently.

During independent annotation, annotators must not:

- discuss individual reports;
- reveal their labels;
- compare decisions;
- modify decisions based on the other annotator.

This ensures that inter-annotator agreement measures actual consistency.

---

21. Cohen's Kappa

Agreement is evaluated using Cohen's kappa on the primary SIF classification:

is_sif_precursor = true
is_sif_precursor = false

Target:

κ >= 0.70

If:

κ >= 0.70

the rubric is considered to have acceptable inter-annotator agreement for the current annotation round.

If:

κ < 0.70

the team must:

1. identify the main sources of disagreement;
2. revise the rubric;
3. increment the rubric version;
4. document the changes;
5. re-label all reports independently from scratch;
6. recalculate Cohen's kappa.

Annotators must not simply edit old labels to artificially increase agreement.

---

22. Rubric Versioning

Every annotation and model prediction must record the rubric version used.

Example:

rubric_version = "1.0"

If the rubric changes:

1.0 → 1.1

all newly generated labels must use the new version.

A change to classification logic, thresholds, severity definitions, or control definitions requires a new rubric version.

---

23. ML Classifier Requirements

The ML classifier must follow this rubric rather than creating its own definition of SIF.

The model should determine:

hazard_assessment
control_status
lsr_rule
severity
is_sif_precursor
confidence
flagged_phrases
reasoning

The LLM must not invent evidence that does not appear in the report.

If structured output fails validation, the system should retry once. If validation still fails, the report should be routed for human review or handled according to the project's fallback policy.

---

24. TF-IDF Baseline

The TF-IDF baseline is intended to provide a simple traditional NLP comparison against the LLM classifier.

The baseline should predict the same primary target:

is_sif_precursor

Training must be performed only on the designated training split.

The test/held-out data must not be used during training or TF-IDF fitting.

Because the positive SIF class is expected to be smaller than the negative class, the baseline should account for class imbalance, including through:

class_weight = "balanced"

where appropriate.

---

25. Evaluation Metrics

Accuracy should not be used as the only evaluation metric.

The evaluation should report:

- precision;
- recall;
- F1-score;
- confusion matrix;
- PR-AUC where appropriate.

The main comparison should use the same held-out reports and the same human gold labels for both:

1. TF-IDF baseline;
2. LLM classifier.

---

26. Synthetic and OSHA Evaluation Sets

The project evaluates the system using two distinct views.

Synthetic held-out set

Used for the primary comparison between:

- TF-IDF;
- LLM.

Both models are evaluated against human-labelled ground truth.

OSHA set

Used as a generalization check for the LLM classifier.

If the TF-IDF baseline was not trained/tuned for the OSHA distribution, its results must not be presented as a directly equivalent benchmark on that dataset.

---

27. Human Review

Human review should be available when:

- the classifier cannot produce valid structured output;
- evidence is insufficient;
- confidence is low;
- the classification is ambiguous;
- the system experiences an API failure;
- the offline fallback is triggered.

The classifier is a decision-support system and does not replace qualified safety professionals.

---

28. Quick Annotator Checklist

Before submitting a classification:

Hazard

- [ ] Is a high-energy hazard present?
- [ ] Does it meet the applicable project threshold?
- [ ] Is the worker actually exposed or credibly within its path?
- [ ] If information is missing, did I use "insufficient_information" rather than guess?

Control

- [ ] What direct control should prevent the exposure?
- [ ] Is it absent?
- [ ] Has it failed or been bypassed?
- [ ] Is it clearly present and effective?
- [ ] If unclear, did I use "unclear"?

LSR

- [ ] Does one of the eight project LSRs apply?
- [ ] If none applies, did I select "none"?

Severity

- [ ] Did I score consequence severity from 1–5?
- [ ] Am I evaluating consequence rather than probability?
- [ ] Does the score match the evidence?

Final decision

- [ ] Is there a credible SIF pathway?
- [ ] Is the high-energy hazard established?
- [ ] Is the direct control inadequate?
- [ ] Is a life-altering injury/fatality realistically possible?
- [ ] Is "is_sif_precursor" consistent with all of the above?

Evidence

- [ ] Did I include relevant "flagged_phrases"?
- [ ] Does "reasoning" explain the decision?
- [ ] Did I avoid adding facts that aren't in the report?

---

29. Core Decision Rule

The simplest way to remember the rubric is:

«HIGH ENERGY + INADEQUATE DIRECT CONTROL + CREDIBLE SIF CONSEQUENCE = SIF PRECURSOR»

If the high-energy hazard is absent, the direct control is effective, or the consequence is not credibly SIF-level, the report should not be classified as a SIF precursor.

When critical information is genuinely unavailable, record the appropriate uncertainty in "hazard_assessment" or "control_status" and explain it in "reasoning".

---

30. Version History

Version| Date| Change| Owner
1.0| 2026-08-29| Initial rubric aligned with classification schema| M1