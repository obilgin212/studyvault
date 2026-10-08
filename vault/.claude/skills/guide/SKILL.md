---
name: guide
description: Guided mode, the faster way through an assignment. {{NAME}} chooses which parts to be walked through; no diagnostic quiz and no check questions unless they ask. Short refreshers plus step-by-step scaffolds where {{NAME}} does each step, then a one-line "why". Also **Q&A mode**: {{NAME}} asks the questions and gets direct, grounded answers that each move the assignment forward. Use for "/guide <assignment>", "let me just ask questions", "Q&A mode", "I ask, you answer", "guided mode", "fast mode", "just walk me through it", "no quizzes", "help me get through this quickly", "guide me through #3 and #7", or when the class's Class Profile has help_mode: guided or help_mode: qa.
---

# /guide: guided mode ({{NAME}} makes the call)

{{NAME}} decided this assignment doesn't need the full probe → plan → teach loop. **Respect that decision.** Don't argue for quizzes and don't sneak them in. Move fast, but keep teaching: every part {{NAME}} picks still ends with {{NAME}} understanding *why*, in one line.

## 0. Load (quietly)
- Find the assignment like `/homework` step 0: `tools/sync/todo.py list` → its note → **📎 Materials** (fetch Drive files with `tools/sync/fetch.py`; saved web pages; textbook pages via `tools/pdf.py`). Also read the class's **`Class Profile.md`** (AI rules, how the class works) and `Learning Profile.md`.
- **Session note:** create `Courses/<course>/Sessions/YYYY-MM-DD <assignment> guided.md` (title + a link to the assignment note; in Q&A mode use the Q&A note below instead), tell {{NAME}} its name, and append each part's refresher, scaffold steps (with his answers) and why-line as you go.
- Read **every page** of each attachment first (`tools/pdf.py info`, then `tools/pdf.py text <pdf>` with no page numbers). Then write out the assignment's parts in full, with how many pages it has (CLAUDE.md principle 5: show them, don't send {{NAME}} to look), numbered, each with a 3–6 word tag for the skill it needs, e.g. `#3 · stratified vs cluster sample`.

## 1. One question: which parts?
Use **AskUserQuestion** once (multiSelect). Group the parts by skill so it fits in 4 options. **One option is always "❓ Q&A: I ask, you answer"** (→ §2b), so at most 2 skill groups plus "All of it": e.g. "Sampling methods (#1, #3, #4)", "Bias types (#7, #10)", "All of it", "❓ Q&A". {{NAME}} can type specifics in "Other" ("#23 and #37", "only the hard ones", "none, just check my answers at the end"). Don't ask anything else up front.

## 2. For each part {{NAME}} picked: refresher → scaffold → why
1. **Refresher (2–4 lines max):** the rule or idea, shown from the class's own source (notes PDF, textbook passage, or the teacher's wording). Include one tiny example only if it really helps.
2. **Scaffold:** break the problem into its steps and **let {{NAME}} do each step**: "What's the population here?" → "Which method puts *every* subgroup in the sample?" → … Give the next step only after {{NAME}} answers or says "next". If {{NAME}} is wrong: one short question about their reasoning, then the fix. Keep it moving (no lecture).
2b. **Metaphor (1 line, expected):** add one line with a general, everyday comparison, per `.claude/skills/teach/metaphors.md` (check its examples first; many concepts already have one). Never from his personal projects. Leave it out only if nothing simple fits.
3. **Why (1 line):** the takeaway in plain words ("Stratified = sample *within* every group; cluster = pick *whole* groups").
4. Mark the part done in the assignment note's checklist (`- [x] #3`).
Parts {{NAME}} didn't pick: skip them. If {{NAME}} wants, check their answers at the end (point at the first wrong step, no rewritten answers).

## 2b. Q&A mode: {{NAME}} asks, the tutor answers
{{NAME}} drives with their own questions. **No scaffold sequence, no check questions.** Each answer has to be *productive*: it answers what {{NAME}} asked **and** leaves them closer to finishing the assignment.

**Start:** create `Courses/<course>/Sessions/YYYY-MM-DD <assignment> Q&A.md` (title, a link to the assignment note, and the parts list in short form) and tell {{NAME}} its name. Then say you're ready in one line. Don't pre-teach.

**Sort each question first:**
| {{NAME}} asks… | Answer with |
|---|---|
| a **concept** ("what's a confounding variable?", "how is an experiment different?") | the answer, directly |
| the **answer to an assigned part** ("what's #3?", "is it observational?") | the concept that decides it + a parallel example + a nudge question. **Not** the final answer |
| "**is this right?**" / pastes their answer | check mine: ✅, or point at the first wrong idea and ask about it |
| "**how do I start #5?**" | just the setup: the first step or a list of what a full answer must contain (e.g. "control · randomize · replicate · what you measure"), no content filled in |

**Shape of a productive answer (≤ ~8 lines):**
1. **Direct answer first** (1–3 lines). No warm-up.
2. **From the class's source:** transcribe the definition or rule and cite it (`[Bock Ch12 p.317]`, the teacher's notes PDF). Never "see p.317".
3. **A tiny example on *different* data** than the worksheet (the textbook's own example is ideal), so it transfers without being copyable.
4. **➡️ For your assignment:** name the part(s) this unlocks (`#3, #6c`) and give **one nudge**: a question about *their* problem that starts the next step ("In the SAT study, who decided which students took the class?"). The nudge is the productive part. It's not a quiz, and {{NAME}} can ignore it.

**Log** each exchange in the Q&A note: `> [!question] <{{NAME}}'s question>`, then the answer. When {{NAME}} says he wrote a part, tick it in the assignment note's checklist. Keep a running list "Concepts asked" at the bottom of the Q&A note.
**Mixing modes:** "guide me through #5" switches that part to the §2 scaffold. "back to Q&A" returns.

## 3. Controls {{NAME}} can use any time
| {{NAME}} says | Do |
|---|---|
| "skip" / "I got it" | Move to the next part. Mark it `skipped` (not checked) |
| "more" / "slower" | Expand the refresher, add a worked *similar* example, smaller steps |
| "just the setup" | Give only the first step or formula setup, then stop |
| "check mine" | {{NAME}} gives their answer: confirm or point at the first wrong step |
| "quiz me" / "check me on this" | 1–3 questions built by `.claude/skills/teach/quizzes.md`, ✓/✗ + answer + why after each; only when he asks |
| "go deep" | Switch to `/teach`-style for this concept (probe + checks) |
| "back to fast" | Return to guided mode |
| "Q&A" / "let me ask" | Switch to Q&A mode (§2b) |
| "guide me through #N" | Scaffold that part (§2), then back to the previous mode |

## 4. Rules that don't change in guided mode
- **{{NAME}} still produces the answers.** Scaffolds ask {{NAME}} to do each step. Never write out a full final answer {{NAME}} could copy. Graded work stays {{NAME}}'s.
- **Strict classes** (`ai_policy: STRICT` in the Class Profile, currently Physics and Lit): refreshers, questions and scaffolds only; nothing that reads like submittable text.
- Spoken or dictated answers are fine. Read for meaning.

## 5. Close (30 seconds, no quiz)
- Learner Model: for each guided skill (and each concept from the Q&A note's "Concepts asked", with the note `asked in Q&A YYYY-MM-DD`), set **🟨 developing** with note `guided YYYY-MM-DD (fast mode, not checked)`. Never 🟩 from guided mode alone. Skipped parts: no change. This is what lets `/review` bring those skills back later as quick spaced checks, which is the trade-off for skipping quizzes now.
- If the whole assignment is done: `tools/sync/todo.py done "<title words>"`.
- One line to {{NAME}}: what was covered, and which skills `/review` will revisit.

## Default mode per class
If {{NAME}} says "always use guided mode for <class>", set `help_mode: guided` in that class's `Class Profile.md` frontmatter ("always Q&A for <class>" → `help_mode: qa`; remove it to go back). `/homework` checks it.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").

## If a download fails
`fetch.py` exit code 3 = the school sign-in expired (about every 2 weeks): ask {{NAME}} to run `~/miniconda3/envs/study/bin/python tools/sync/login.py` (sign in, check Classroom **and** Google Docs load, close the window), then retry the same command. Any other failure: say what it printed, and ask for a screenshot or paste only if the file really can't be exported.
