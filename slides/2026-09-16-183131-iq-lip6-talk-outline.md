# Pathfinder: IQ lab, LIP6 talk outline

Status: a working outline, not a finished presentation. It records the intended
content slide by slide, and several preparation notes below are still open: the
repricing figures on slide 8, the exact corpus dimensions on slides 9 and 10,
and the Q3P3 outcome, which may change before the talk is given.

Audience: quantum researchers, including users of AI agents.

Format: 11 slides, approximately 15 minutes, followed by 5 minutes of questions.

Narrative: a seminar question, its systematic generation and investigation, the pilot's results, then economics and scale-up.

Presentation rule: whenever a slide mentions a specific Q or P paper, show its two-line
plain-language summary beside the label. Repeat the summary when the paper reappears;
do not rely on the audience remembering an index. The paper cards below are on-screen
content, not speaker-only notes. Apply the same rule to examples added during slide production
and to the backup slides.

## 1. A question from the audience... Time: 1 minute.

### On screen

> "You use an external judge to rank the agents' contributions. Could you ask the agents themselves?"
> "Wouldn't they misreport?"
> "There is a mechanism-design paper about that..."

### Graphic

A fictional seminar scene, with P6 on the speaker's screen and Q4 appearing beside the audience's question. Clearly label this an imagined exchange.

### Paper cards

**P6: an outside judge for a team of AI agents**

> A team of AI agents works together, but it is hard to tell which agents contribute most.
> An outside AI judge compares what they see to estimate their contributions and guide training.

**Q4: incentives to report what you know**

> Agents have private information, but may benefit from misleading others about it.
> The paper designs rewards that, under its assumptions, make truthful reporting worthwhile.

### Spoken point

This is familiar: someone recognises that another paper might change the question, supply a method, or expose an assumption. Pathfinder tries to systematise both finding that question and investigating it.

## 2. What if we asked across an entire collection?

Time: 1 minute.

### On screen

> 10 papers on mechanism design x 10 papers on agent cooperation
>
> 100 possible encounters
>
> 14 investigated pairs -> 5 internally accepted manuscripts

### Graphic

The existing 10x10 heatmap, with a simple legend: colour represents scan score, outlines mark investigated pairs, stars mark accepted manuscripts. Highlight Q4P6.

Heatmap source: `notes/figures/2026-09-14-campaign-heatmap.tex`.

### Paper cards beside the highlighted Q4P6 cell

**Q4: incentives to report what you know**

> Agents have private information, but may benefit from misleading others about it.
> The paper designs rewards that, under its assumptions, make truthful reporting worthwhile.

**P6: an outside judge for a team of AI agents**

> A team of AI agents works together, but it is hard to tell which agents contribute most.
> An outside AI judge compares what they see to estimate their contributions and guide training.

### Spoken point

These are proposed connections, not similarity scores. The scanner asks what could actually be investigated and what might be learned.

Small qualification: "Acceptance is internal to the protocol, not external scientific validation."

## 3. Scan. Research. Edit.

Time: 1 minute.

### On screen

> **Scan:** propose and prioritise questions.
>
> **Research:** investigate them, challenge them, establish what survives.
>
> **Edit:** make the outcome assessable by a human expert.

### Graphic

A broad workflow diagram, with a branching edit phase:

- A successful research outcome can enter manuscript preparation and review.
- Any terminal research outcome can produce a readable account.

### Spoken point

The output is not necessarily a positive paper. A precise obstruction, an abandoned conjecture, or an explanation of missing evidence can also be useful.

## 4. The research question is allowed to change

Time: 1 minute 15 seconds.

### On screen

> Researcher agents share a ledger.
>
> They consolidate their findings.
>
> A separate verifier challenges the result.

### Graphic

The simplified research state diagram. Make the paths visually distinct:

- Return to research when more investigation is needed.
- Return to the note when the exposition or argument needs repair.
- Stop with a draft or a paused outcome.

Keep the paused terminal states stacked above the successful draft state. No transition tuples, counter notation, or formal guard table.

### Spoken point

The seed is a starting hypothesis, not a claim the researchers must defend. Budgets bound the loops.

## 5. Q4P6: when can we dispense with the judge?

Time: 2 minutes.

### Paper cards

**Q4: incentives to report what you know**

> Agents have private information, but may benefit from misleading others about it.
> The paper designs rewards that, under its assumptions, make truthful reporting worthwhile.

**P6: an outside judge for a team of AI agents**

> A team of AI agents works together, but it is hard to tell which agents contribute most.
> An outside AI judge compares what they see to estimate their contributions and guide training.

### On screen

> **Seed:** use Q4's reporting incentives in a no-judge variation of P6.
>
> **Obstacle:** truthful reports can still be insufficient for ranking.
>
> **Conclusion:** under explicit observation and overlap conditions, peer reports identify the comparison model's ranking without an external judge.

### Graphic

A three-panel progression: **external judge -> agents reporting their observations -> calibrated comparison network**.

Use a small triangle of overlapping observers to illustrate calibration, then a connected network to illustrate propagation.

### Spoken point

Reports must be informative, their errors suitably structured, and observations sufficiently overlapping. This is a conditional application combining established ingredients, not a general solution to measuring contribution.

The boundary should remain visible: **recovering a model-defined ranking is not automatically measuring causal contribution.**

## 6. Q7P1: a tale of two runs

Time: 2 minutes.

### Paper cards

**Q7: sharing resources among self-interested participants**

> Participants compete for limited resources and care about their own benefits.
> The paper proposes messages and payments intended to lead them to an efficient allocation.

**P1: learning while paying attention to bad outcomes**

> An agent learns which actions to take while limiting losses in the worst fraction of cases.
> The paper estimates this risk from noisy samples and uses those estimates to guide learning.

### On screen

> **Seed:** adapt Q7's resource-sharing mechanism to participants who care about bad outcomes,
> using P1's approach to learning about risk.
>
> **First run:** useful bounds on the error from approximating risk,
> but the mechanism application assumes that a suitable mechanism exists.
>
> **Rerun:** Q7's printed rules do not provide the guarantees that application needs.
> Its payment rule can leave a participant worse off: a benefit of 9.5, but a payment of 10.5.
>
> **Follow-up:** corrected payments and stronger assumptions recover conditional guarantees.
> The first run's approximation bound survives; its intended application needed repair.

### Graphic

Start from a shared seed, then show separate investigation lanes:

- **First run:** risk approximation -> error bounds -> mechanism premise left unresolved.
- **Rerun:** audit the mechanism -> expose faulty guarantees -> follow-up develops a conditional repair.

Place the 9.5 benefit / 10.5 payment counterexample beside the second lane.
Connect the surviving approximation result to the repaired application with an arrow labelled
"error control remains useful". Do not suggest that the rerun simply continued the first run's reasoning.

### Spoken point

The first run was not worthless, and the later run did not merely produce another equally satisfactory answer.
The approximation result is independent of the defective payment rule, so it survives.
But the first run did not establish the mechanism needed for its intended application.

The separate rerun exposed that gap. Its subsequent paper follow-up repaired the payments under stronger assumptions,
with guarantees for a fixed approximation to risk and error bounds for the difference from true risk.
This is a conditional repair, not a general validation of Q7 or a demonstration of efficient learning in practice.

The lesson is that internal acceptance is not a scientific certificate:
revisiting a connection can preserve a useful result while overturning confidence in its intended application.

## 7. Q3P3: does the critic help, or just the extra review?

Time: 1 minute 30 seconds.

### Paper cards

**Q3: AI agents trading in a market**

> AI agents act as buyers and sellers, placing offers and making trades.
> The paper compares their market performance with a human benchmark.

**P3: a critic for the code reviewer**

> A reviewer checks an AI agent's code, and a critic challenges the review before the code is revised.
> The paper tests whether this back-and-forth produces better programs than other review methods.

### On screen

> **Seed:** Q3's market experiments motivate a question about P3's review protocol:
> does performance come from the agents' information, or from the rules of interaction?
>
> **Finding:** P3's reported comparisons do not isolate the critic's contribution
> from repeated review, stopping rules, and additional computation.
>
> **Missing experiment:** compare adversarial review with an iterating single reviewer
> on the same tasks, with equal computational budgets.
>
> **Outcome:** the researchers proposed the control, but lacked the materials needed
> to reproduce and extend P3's experiments. The cross-paper claim remains untested.

### Graphic

Side-by-side review loops, both leading to the same task evaluation:

- **Single reviewer:** review -> revise -> review again.
- **Adversarial review:** reviewer + critic -> revise -> review again.

A shared bracket reads "same tasks, same computational budget".
A small third arm shows a random critic as an additional control for the value of critic information.
Mark these as proposed comparisons, not completed experiments.

### Spoken point

The question is not whether P3 reports an improvement, but what causes it.
The researchers identified a missing comparison in P3, rather than establishing that its critic is ineffective.
The supplied material lacked the task instances and execution setup needed to run that comparison.
A substitute benchmark could investigate the broader hypothesis, but would not by itself explain P3's reported results.

This is a substantive outcome of research even without a manuscript-ready cross-paper result:
a precise unresolved question and an experiment that could settle it.
The original thread ended at PAUSE-ON-ITERATE, not at a demonstrated negative result.

### Preparation note

An additional research iteration has been requested. Update the outcome if it produces new evidence before the talk.

## 8. The economics: search broadly, investigate selectively

Time: 1 minute 15 seconds.

### On screen

> Scanning buys breadth.
>
> Research consumes the main investigative effort.
>
> Expert assessment remains a separate cost.

### Graphic

Stage-by-stage bars for **scan / research / editing**, alongside separate indicators for:

- Token use and API-equivalent dollars.
- Wall-clock time.
- Human attention.

### Spoken point

Report subscription usage separately from API-equivalent cost. Apply the agreed common GPT-6 tariff to recorded tokens, without implying that rerunning everything at medium effort would consume identical tokens.

### Preparation note

The numerical dollar bars still need the repricing calculation. Avoid a headline human speedup: the campaign's elapsed span includes pauses, and the human comparison is illustrative rather than measured.

## 9. Scale-up: Julien's scientific neighbourhood

Time: 1 minute 15 seconds.

### On screen

> Approximately 80 x 80 papers
>
> Thousands of candidate connections
>
> An expert evaluates connections involving their own work

### Graphic

Julien's heatmap, with the 10x10 pilot shown as a small inset. Label both axes by their actual corpora, not only Q and P.

### Spoken point

Scale is not just about generating more candidates. Choosing an expert's own publications makes assessment more tractable: they already understand one side of the proposed connection, and useful suggestions feed directly into their research.

### Preparation note

Use the current experiment's exact dimensions on the finished slide.

## 10. Scale-up in quantum: QSL x vendor applications

Time: 1 minute 15 seconds.

### On screen

> Approximately 150 x 150 papers
>
> QSL research x vendor/application literature
>
> Where could a research result change an application, or an application expose a research problem?

### Graphic

The QSL/vendor-application heatmap, accompanied by a thumbnail and reference to the associated paper. Highlight a concrete connection only if its outcome is documented.

### Spoken point

This is the quantum-facing motivation for the audience: systematically finding possible transfers between research results and application requirements. The larger matrix expands the search space; it does not, by itself, establish higher scientific quality.

## 11. How much of creativity is connexion?

Time: 1 minute, then discussion.

### On screen

> **How much of scientific creativity is making connections?**
>
> If agents can propose connections, investigate them, and write up the results,
> what remains distinctively human: choosing questions, inventing concepts, judging significance?
>
> **How much longer before all mathematicians are agents?**
>
> **Can agents help with selecting corpora?**


### Graphic

Return to the opening seminar scene. Extend it into a network of papers and proposed connections,
with both humans and agents asking questions. Leave the last question prominent, with ample empty space.
Avoid a countdown or a forecast curve: the slide poses a question, not a predicted date.

### Spoken point

Pathfinder explores a particular form of creativity: bringing existing ideas together and working out what follows.
The pilot does not establish that all creativity reduces to this, or that agents can replace mathematicians.
Finding a connection, establishing its consequences, and deciding that those consequences matter are different achievements.

But if this part of research becomes cheap and scalable, the division of labour may change substantially.
Which activities remain scarce: generating candidates, proving claims, choosing worthwhile problems,
introducing useful concepts, or developing a shared sense of significance?

Use the final question as a deliberate provocation. "Most mathematical work is done by agents"
and "human mathematicians disappear" are different futures; the former does not imply the latter.

### Closing line

"If agents can make and investigate the connections, who decides which mathematics is worth doing?"

## Backup slides

- Full state diagrams and LTS specification.
- Precise Q4P6 assumptions.
- Detailed accounting.
- Scan-repeat variability once available.
