# Quiz rules (shared by /teach, /homework, /exam-prep, /review, and /guide when {{NAME}} asks for checks)

A graded question exists to **measure** what {{NAME}} knows. If he can answer it without knowing the content, by spotting the longest option, the bolded one, the one with a reason attached, or "it's always A", the measurement is junk and the plan built on it is wrong.

## Building a multiple-choice question (AskUserQuestion)
1. **Write the correct claim first**, as one plain statement.
2. **Mutate it into 2 distractors** using *real* misconceptions for this topic (from the verifier's scoping pass, the Learner Model, the book's warnings): flip a sign, drop a condition, swap cause and effect, use the related-but-wrong formula, mix up two look-alike terms (speed/velocity, stratified/cluster, `:`/`++`). Each distractor should be something a student who's *almost* there would pick.
3. **Same skeleton, same length.** All options share grammar and structure and are within a few words of each other's length. If the right one is longer or more careful-sounding, rewrite the others to match.
4. **No justification inside the options.** Options state answers only. "Negative, because friction opposes motion" next to bare "Positive" gives it away. Reasons go in the question stem (if they're the point) or in the feedback.
5. **No formatting tells:** no bold/italics/emoji on one option, no "(Recommended)" ever, no description text on just one option (give every option a description or none; on graded questions, prefer none).
6. **Vary where the correct answer sits.** Never always first. Before each call, pick the correct option's position at random-ish across 1–3 and make sure it isn't the same across a whole round.
7. **"I don't know" is always the last option.** It's a real answer: it means *not learned yet*, which is different from a misconception. Never treat it as wrong-with-a-guess, and never nudge {{NAME}} away from it. (So: at most 3 real options + "I don't know"; {{NAME}} can still dictate reasoning through "Other".)
8. **The cold test:** before sending, ask yourself "could someone who never took this class get it from the wording alone?" If yes, regenerate.
9. **Never the assigned problems themselves.** Use parallel items.
10. Math in the question text: plain Unicode (`f′(x) = 3x²`, `∫₀¹`, `ΔK`), since the question box doesn't render LaTeX. Code: short, inline in the question.

## After every answer: instant feedback, before anything else
For each question in the round, one compact line block:
- **✓ Correct** or **✗ Not quite** (or **· I don't know**, neutral)
- **Answer:** the correct option, stated in full
- **Why:** one or two lines on why it's right, and **if he picked a distractor, the specific misconception that option encodes** ("that's the 'friction always does zero work' idea…")

Then continue (next question, teach, or ask for his reasoning). If an answer came through "Other" with reasoning, respond to the reasoning itself: it's the richest signal.

## Reading the results
- **One miss isn't a cue to teach.** It's a data point. Characterize *which* misconception (from the distractor he picked or his reasoning), then follow up with one more targeted item if it's ambiguous.
- **"I don't know"** → mark the strand *unlearned* (⬜/🟥), not misconceived.
- **All correct** → the questions were too easy for him; next round jumps sharply harder (see the probe's bracketing in `teach/SKILL.md`), don't creep up one notch.
- Log each question, his answer and the verdict in the session note: `> [!question]` with the options, then his answer and your ✓/✗ feedback.
