# Demo script — 5 minutes, word for word

**Owner:** Member 1. Structure is locked; do not reorder.

**Placeholders are placeholders.** `[AGREEMENT]`, `[KAPPA]`, `[F1_BASE]`, `[F1_LLM]`,
`[F1_OSHA]`, `[SEVERITY_MAE]` do not exist until the evaluation runs. If you find yourself about
to say a specific number before day 13, stop — it is invented.

**Never say:** "it's a black box" · "our accuracy is X%" · "it's 100% accurate" · "AI-powered" as
a substitute for saying what it does · anything claiming we *prevent* fatalities. We surface
warnings. Humans act.

Timings assume 140 words per minute plus pauses for the live section.

| Section | Window | Words | Spoken |
|---|---|---|---|
| Problem | 0:00–0:30 | 76 | 33s |
| Why reading fails | 0:30–1:00 | 66 | 28s |
| What we built | 1:00–1:30 | 74 | 32s |
| **Live demo** | 1:30–3:30 | 185 | 79s + 40s interaction |
| Numbers + the miss | 3:30–4:15 | 101 | 43s |
| Deployment framing | 4:15–4:45 | 68 | 29s |
| Close | 4:45–5:00 | 23 | 10s |
| | | **593** | **≈ 4:54** |

Six seconds of slack. That is intentional — you will lose more than that to the judge typing.

---

## 0:00–0:30 · The problem

> Over fifteen years, non-fatal accidents in the US fell fifty-one percent. Fatalities fell
> twenty-five and a half.
>
> Those two lines should move together. They don't — because the things that cause a sprained
> wrist are not the things that kill people.
>
> Roughly one report in four already describes a situation that could have killed someone. It is
> sitting in the pile, unread, next to four hundred reports about a wet floor.

*Both figures are from the problem statement itself. If challenged, say so.*

---

## 0:30–1:00 · Why triage-by-reading fails

> Oil India collects these through their HSSE platform — unsafe acts, unsafe conditions, near
> misses. A safety officer reads them. Monthly. Sometimes quarterly.
>
> Not because anyone is lazy. Because there are thousands, they are free text, and the dangerous
> ones do not look dangerous.
>
> "Cover removed to check a fault" is six words. It is also somebody standing in front of a live
> circuit.

---

## 1:00–1:30 · What we built

> So we built a reader.
>
> Every report goes through three gates. One — is there a high-energy hazard, from the eight IOGP
> Life-Saving Rules. Two — was the barrier there, and was it doing its job. Three — if one small
> thing had gone differently, would somebody be dead.
>
> All three yes, and it is a precursor. And it tells you which gate decided and which words made
> it decide, so you can disagree with it.

---

## 1:30–3:30 · Live

### Beat 1 — the judge types (≈ 40s)

> Type a report. Anything you would actually see on a site.

*Hand over the keyboard. Do not narrate while they type. When the result lands:*

> Hazard: energy isolation. Barrier: absent. Severity four. Precursor.
>
> And these are the words it keyed on — "not isolated", "no lockout". That is not a summary. Those
> are the phrases you would have looked for yourself.

### Beat 2 — the ambiguous case (≈ 40s)

*Paste the prepared barrier-held report. This is the most important thirty seconds of the pitch.*

> Now watch this one. Worker fell four metres. Harness clipped to a rated anchor, the fall arrest
> worked, he walked away.
>
> Hazard: yes. Barrier: present. **Not** a precursor.
>
> That is the one that matters. A keyword system sees "fell four metres" and flags it. This read
> that the barrier held, and said no. That is the difference between counting words and reading.

### Beat 3 — the dashboard (≈ 40s)

*Switch to screen 3. Do not let this get cut for time — it is the actual product.*

> And this is what a safety manager opens on Monday.
>
> Rig 4: eleven energy-isolation precursors this quarter. Nine of them on night shift.
>
> That is not a chart. That is a decision — somebody goes and looks at night-shift isolation
> practice at Rig 4.
>
> Ranked by rate, not raw count. A site that reports honestly should not come out looking worse
> than a site that reports nothing.

---

## 3:30–4:15 · Numbers, and one we get wrong

> Two of us labelled all one hundred and eighty reports independently, against a written rubric,
> without discussing a single one. We agreed `[AGREEMENT]` percent of the time. Cohen's kappa,
> `[KAPPA]`.
>
> That is our ceiling. No system here can honestly claim to beat two humans reading the same
> document.
>
> Keyword baseline, F1 `[F1_BASE]`. The language model, `[F1_LLM]`. On thirty real OSHA reports
> nobody on our team wrote, `[F1_OSHA]`.
>
> And here is one it gets wrong.

*Show the misclassification. Hand them the crack before they find it.*

> It read a supervisor stopping the job as a barrier that held. That is a hole in our rubric, not
> a model failure — and it is the first thing we would fix.

---

## 4:15–4:45 · Where it sits

> Downstream of the reporting they already have. It never closes a report. It reorders the reading
> queue.
>
> Every judgement is logged — the gate it used, the phrases it flagged, the version of the model
> that said it. A safety officer can overrule it, and you can see why it said what it said.
>
> And if our API dies mid-shift, a local model takes over and the screen says so, in those words.

---

## 4:45–5:00 · Close

> Safety programmes measure how many incidents happen.
>
> They don't measure how many could have killed someone.
>
> We built the second thing.

*Stop. Do not add anything after this line.*

---

# Contingency — when the wifi dies

**The fallback firing is part of the demo. Say it with confidence, not apology.** You rehearsed
this; they cannot tell the difference between a planned demonstration and a recovered disaster
unless you tell them.

If the API goes down mid-demo and the degraded-mode banner appears:

> — and there it is. That is the fallback. Our API just went away and the local keyword model
> picked it up, and the banner is telling you it is running in degraded mode.
>
> That is not a failure, that is the design. A safety tool that stops working when the connection
> drops is not a safety tool.
>
> What you are looking at now is the keyword baseline, which is measurably worse —
> `[F1_BASE]` against `[F1_LLM]`. And it still flagged the report.

**If the whole frontend is gone**, open the API docs page and run the same report through
`/analyze` directly:

> Same engine, no interface. Here is the raw judgement — hazard, barrier, severity, and the
> phrases it flagged.

**If everything is gone**, you have the screenshots. Say once, plainly: "We are on screenshots —
the deployment is down, not the system." Then keep the same script. Never apologise twice.

---

# 90-second version

For a corridor pitch or a hard time cut. ~205 words, 88 seconds spoken.

> Non-fatal accidents in the US fell fifty-one percent over fifteen years. Fatalities fell
> twenty-five. Those lines should move together — they don't, because what sprains a wrist is not
> what kills people. About one report in four already describes something that could have killed
> someone, buried in a pile nobody can read monthly.
>
> We read them. Three gates: is there a high-energy hazard from the eight Life-Saving Rules, was
> the barrier doing its job, and would a small realistic change have killed someone. All three
> yes, it is a precursor — and it shows you which gate decided and which words made it decide.
>
> The one that matters is the one it says no to. Worker falls four metres, harness held, walks
> away — hazard yes, barrier present, not a precursor. Keyword systems flag that. Ours reads it.
>
> Then it ranks sites by precursor rate. Rig 4, eleven energy-isolation precursors this quarter,
> nine on night shift. That is a decision, not a chart.
>
> It never closes a report. It reorders the reading queue. Safety programmes measure how many
> incidents happen — not how many could have killed someone. We built the second thing.

---

# Speaker transitions

If more than one member presents, hand over **between sections, never mid-section**. Each handover
costs about two seconds — build them into the timing.

| Section | Speaker | Handover line |
|---|---|---|
| Problem, why reading fails | M1 | "So we built a reader —" *(pass to M2)* |
| What we built | M2 | "Easier to show you." *(pass to M5, keyboard)* |
| Live demo | M5 driving, M2 narrating | "Those are the numbers behind it." *(pass to M3)* |
| Numbers + the miss | M3 | "And where it sits —" *(pass to M4)* |
| Deployment framing | M4 | *(pass back to M1 with a nod, no words)* |
| Close | M1 | — |

**Two rules.** Whoever is speaking is the only one facing the judges. And whoever owns a section
answers the questions on it — if a judge interrupts M3 during the numbers, M1 does not rescue
them. Judges notice rescue, and it reads as one person who understands and five who do not.
