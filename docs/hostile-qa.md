# Hostile Q&A — question bank and model answers

**Owner:** Member 1. **Everyone reads this.** The random-person drill means any member may be
asked any question, so "that's not my section" is not an available answer.

Three judges, in character:

- **Judge A — ML professor.** Evaluation design, leakage, synthetic-data circularity, why not
  fine-tune, what F1 hides, prompt overfitting, whether the ceiling logic is sound.
- **Judge B — OIL/HSE engineer, twenty years in the field.** Whether the categories match
  reality, whether the plausible-variation test is how professionals actually think, contractor
  reporting culture, under-reporting, what happens to a worker whose report gets ranked low.
- **Judge C — deployment and product.** Why not ChatGPT, why not a field in the existing HSSE
  platform, cost at scale, who maintains the prompt, what breaks in year two.

**Rules for every answer.** Placeholders stay placeholders until the eval runs. Never say "black
box", "our accuracy is X", "100% accurate", "AI-powered" as a description, or that we prevent
fatalities. Four sentences is the ceiling — a long answer reads as a nervous one.

**The three-why chain.** Every answer below survives one "why". Before the presentation, take each
one and ask "why" three times. Where you run out of road, that is what to study — not the answer,
the reasoning underneath it.

---

## The hardest five — memorise these

### "Who decided what counts as serious?"

> We did, and we wrote it down before we labelled anything. The three-gate structure comes from
> the literature the problem statement itself cites — DEKRA, the EEI precursor model — and the
> eight hazard categories are IOGP Report 459. The severity scale and the threshold for "serious"
> are our own calibration, and our rubric says so explicitly rather than dressing them up as
> sourced. We also had it reviewed by an EHS professional outside the team before we used it.

**Do not say:** "it's industry standard" (it is partly ours) · "the model decides" (it does not) ·
anything that implies the thresholds came from a paper.

### "You wrote the reports and graded yourself."

> Partly true, and it is why we did three things. The person who wrote the rubric and the person
> who generated the reports had no contact until both finished. Two of us then labelled all 180
> independently and reported our disagreement rate, so you can see the ceiling rather than trust
> us. And a sixth of the set is real OSHA narratives nobody on this team wrote.

**Do not say:** "the data is realistic" · anything defensive. Concede the premise first — it is a
fair hit, and conceding it is what makes the rest credible.

### "What happens when your model is wrong and someone dies?"

> The system never closes a report — it reorders the reading queue, so a report we rank low is
> still read, just later. That is why we tuned for recall over precision: missing a precursor
> costs a life, a false alarm costs twenty minutes. Every judgement is logged with the gate it
> used and the phrases it flagged, so a wrong call is auditable rather than invisible. It is a
> triage aid for a safety officer, not a replacement for one.

**Do not say:** "that won't happen" · "the human is responsible" (true but cold) · any number
about how often it is wrong that you do not have.

### "Why can't ChatGPT already do this?"

> It can classify one report — we use a language model for exactly that. The product is what
> surrounds it: a fixed schema so a thousand reports are comparable, a ranked aggregation by site
> and barrier, and a measured agreement number so you know what the labels are worth. Ask
> ChatGPT the same report twice and you get two different shapes, which you cannot aggregate.

**Do not say:** "ours is better" · "we use a special prompt" · anything that suggests we built a
model. We did not.

### "Show me a case your system gets wrong."

> *(Have it open. Show it before they ask, in the demo.)* This one — a supervisor stopped the job
> before anyone was exposed, and the system read that as a barrier that held. It is a hole in our
> rubric rather than a model failure: our own red-team found the same conflict in two of fifteen
> adversarial cases. The fix is a clarifying rule about human intervention, which is written and
> waiting on the agreement check.

**Do not say:** "I can't think of one" — that is the worst possible answer, and it invites them to
find one for you.

---

## Judge A — ML professor

**"Why F1 and not accuracy?"**
> At roughly 22% positives, answering "no" to everything scores 78%. Accuracy would make a useless
> model look good. We report F1 and PR-AUC, and PR-AUC is why the classifier has to emit a real
> confidence float rather than a verdict.

**"Your test data is synthetic. Isn't that circular?"**
> For the synthetic split, yes — it measures the model against our own writing, which is why we
> do not stop there. The 30 OSHA reports are real text nobody on the team produced, and we report
> that separately as a generalisation check. We never merge the two into one number, because that
> would hide exactly this problem.

**"Why not test the baseline on OSHA too?"**
> The baseline is trained on synthetic reports, so testing it on OSHA measures domain transfer
> rather than model quality — an unfair fight it loses for the wrong reason. We would be
> manufacturing a bigger gap than we earned. So the OSHA table is LLM-only, and we say why.

**"Why not fine-tune?"**
> 180 labelled examples would overfit almost immediately. At this scale prompting wins, and it
> also keeps the reasoning inspectable — a fine-tuned model would give us a label with no per-gate
> justification to audit.

**"How do you know you haven't overfit the prompt to your dev split?"**
> We tuned on about 30 reports and opened the held-out set exactly once, at the end. That is a
> discipline, not a guarantee — if you want the stronger version, the OSHA number is the honest
> check, because we never tuned against it at all.

**"What does your ceiling argument actually claim?"**
> Two people applying the same written rubric agreed `[AGREEMENT]` percent of the time. Anything
> above that is not measurable with our labels, so a system claiming 95% would be claiming to be
> more consistent than the ground truth it was scored against. We quote our own ceiling because a
> number above it should make you suspicious.

**"Kappa versus raw agreement?"**
> Kappa subtracts the agreement you would get from chance alone. At a 22% positive rate two people
> guessing randomly still agree often, so raw agreement flatters us and kappa does not.

**"What does F1 hide?"**
> Which errors we make. F1 treats a missed precursor and a false alarm as equally bad, and for us
> they are not — that is why we also state the recall-over-precision choice explicitly, and why we
> report severity MAE separately so you can see whether we are wrong about *how* dangerous.

**"What is your schema-failure rate?"**
> `[SCHEMA_FAIL]` — it is measured, not estimated. Pydantic validates every model response; on
> failure we retry once and then fall back to the baseline, and the counter is exposed on the API.
> Hallucination becomes a logged number rather than an open risk.

**"Your severity scale is ordinal. Why MAE?"**
> Because being wrong by one level and wrong by three levels are different mistakes, and a
> classification metric would treat them identically. MAE against the adjudicated human severity
> is the simplest honest answer.

**"Is TF-IDF a real baseline or a strawman?"**
> Real — it is built and scored first, before the LLM exists, with its own train/test split. It is
> also genuinely competitive on the obvious cases, which is the point: the gap shows up exactly on
> the reports where reading matters.

---

## Judge B — OIL/HSE engineer

**"Do your eight categories match what we actually see?"**
> They are the IOGP Life-Saving Rules, so they are your categories rather than ours. We use eight
> of the nine — we dropped Bypassing Safety Controls because barrier defeat is what our second
> gate already measures, and carrying it in both places would double-count it. If your site uses a
> different taxonomy, that mapping is a config change, not a rebuild.

**"Is the plausible-variation test how professionals actually think?"**
> It is our attempt at how you already think when you say "that could have been a lot worse". If
> it does not match, that is the most useful thing you could tell us today — the rubric is a
> document we revise, and the whole system is downstream of it.

**"Contractor crews under-report. Doesn't that break your ranking?"**
> Yes, and it is the sharpest limitation we have. Ranking by rate rather than raw count stops a
> site being punished for reporting honestly, but nothing protects us from a site that reports
> nothing at all. A site with a suspiciously low report count is a finding for a human, and we
> would not claim otherwise.

**"What happens to the worker whose report gets ranked low?"**
> It still gets read — we reorder the queue, we never close or discard anything. That was a
> deliberate design constraint, because a system that silently drops reports would teach people to
> stop writing them.

**"Would HSE trust a student system?"**
> Not on our say-so, and it should not. What it can check is the reasoning: every judgement names
> the gate, the rule, the barrier status and the exact phrases it keyed on, so a safety officer can
> disagree in ten seconds. Trust comes from a month of it agreeing with your own reading, not from
> our pitch.

**"Near-miss reports are written badly. Half are one line."**
> Agreed, and the system has a third answer for that: `insufficient_information`, which routes to
> a human rather than guessing. We deliberately did not let it infer a barrier status from silence
> — if the report does not say, we say we do not know.

**"You are using US injury data for an Indian operation."**
> The OSHA set is a check that the classifier handles real writing nobody on our team produced —
> nothing more. We do not claim it represents Indian operations, and the site-level dashboard runs
> on synthetic data only because OSHA records carry no site taxonomy.

**"Your reports mention Rig 4 and Duliajan. Is that real Oil India data?"**
> No, and we want to be clear about it before you ask. Our data is synthetic plus public OSHA. We
> named sites plausibly so the dashboard demonstrates something recognisable; no operational data
> was used and none was available to us.

**"What about reports in Assamese or Hindi?"**
> Handled in the classification prompt directly — we have code-mixed Hindi and Hinglish reports in
> the set to prove it. There is no separate translation pipeline, which means nothing is lost in a
> translation step before the judgement.

**"A precursor is not the same as an incident. Are you inflating numbers?"**
> The opposite — we are counting something that currently is not counted at all. We never present
> a precursor count as an incident count, and the dashboard labels it as SIF-potential rather than
> as harm.

---

## Judge C — deployment and product

**"Why can't OIL just add a checkbox to their HSSE platform?"**
> They could, and the honest answer is that a self-reported checkbox measures who is cautious, not
> what is dangerous. The judgement here is made from the narrative after the fact, consistently,
> by something applying the same rubric to report ten thousand as to report one.

**"What does this cost at scale?"**
> One model call per report. At Oil India's reporting volume that is a rounding error against a
> single lost-time incident, and the cached and baseline paths cost nothing at all. Our own build
> budget is about a thousand rupees.

**"Who maintains the prompt when you graduate?"**
> That is a real risk and we designed around it. The prompt is one file, the rubric it implements
> is a written document, and the schema is enforced by the database rather than by the prompt — so
> a maintainer changes the prompt and the constraints tell them if they broke the definition.

**"What breaks in year two?"**
> Three things: the model version moves and the outputs shift, the site taxonomy changes as
> operations change, and the rubric drifts from how the safety team actually thinks. The first is
> why every prediction row stores its model version. The other two need an annual re-labelling of
> a sample, which is a process commitment, not a code one.

**"What if the API is down during a shift?"**
> A local keyword model answers instead and the interface says "degraded mode" in those words. It
> is worse — `[F1_BASE]` against `[F1_LLM]` — and we would rather show you a worse answer honestly
> than a blank screen. We test that path; it is not a slide.

**"Where does the data live? This is safety-sensitive."**
> Report text goes to the model provider for classification, and everything else stays in the
> operator's own Postgres. For a real deployment, the questions to settle are the provider's data
> retention terms and whether narratives need de-identifying first — we would not pretend that is
> already solved.

**"Is this a product or a project?"**
> Today it is a working prototype with a measured accuracy ceiling and a stated set of
> limitations. What makes it deployable rather than a demo is that it sits downstream of the
> reporting that already exists and changes nobody's workflow — it reorders a queue.

**"Who is the user?"**
> The safety officer doing the monthly triage, and the HSE manager deciding where to send an audit
> next quarter. The first uses the queue, the second uses the density ranking, and they are the
> two screens we built first.

**"What is genuinely new here?"**
> Four things, and none of them is using a language model. The two-field auditable judgement —
> hazard and barrier status separately, so you can see which one drove the call. Evaluation
> measured against a human agreement ceiling rather than against itself. Density aggregation by
> site, activity and barrier, which is what the problem statement actually asked for. And a
> degraded mode that is tested rather than promised.

**"Your competitor VelocityEHS already ships a PSIF classifier."**
> They do, and the problem statement cites them. We are not claiming to beat a commercial product
> — we are showing that the approach is reproducible, auditable, and explainable to the people who
> have to act on it, in a build a small team can maintain.

**"How long from report submitted to report classified?"**
> Seconds rather than the monthly or quarterly cycle in the problem statement. That is the whole
> operational claim, and it is the number we would measure first in a real deployment.

---

## Ethics, security, scale

**"Could this be used to discipline workers?"**
> It could, and that would destroy it. A site that gets punished for its precursor count stops
> reporting, and then the system goes blind — which is exactly why we rank by rate rather than
> count. Any real deployment needs that written into the policy, not just the software.

**"Are you storing personal data?"**
> Narratives may contain names; nothing in our schema requires them. For deployment we would
> de-identify on ingest, and the fact that we have not needed to yet is because our data is
> synthetic.

**"What stops someone gaming it by writing vague reports?"**
> Nothing, and vague reports come back as `insufficient_information` rather than as clean
> negatives — so gaming it produces a visible pile of unreadable reports rather than a quiet pass.
> That is a management signal in itself.

**"Ten thousand reports a day?"**
> The classification is per-report and parallel, the aggregation is SQL over an indexed table, and
> the cache absorbs repeats. Nothing here needs rearchitecting for volume; the constraint is API
> cost, and it is small.

**"Why no vector database or clustering?"**
> Because the question is not "which reports are similar" — it is "which sites are dangerous". A
> GROUP BY answers that exactly, and every member of this team can read the query aloud and tell
> you what it computes. Embeddings would add a component nobody could explain under questioning.

---

## Live drill format

For the interactive version, run it like this:

1. Judge asks. **Answer out loud, timed.** Written answers do not transfer to a room.
2. Score 1–5: *5* — answers the actual question in under four sentences, concedes what should be
   conceded. *3* — correct but rambling or defensive. *1* — hedged, invented a number, or used a
   banned phrase.
3. Then **three whys** on whatever you said.
4. Anything scoring under 4 goes on the study list — the reasoning, not the wording.

Memorised answers collapse on the second why. That is the point of the drill.
