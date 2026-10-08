---
name: teach
description: Personalized tutoring session. Ask {{NAME}}'s goal, probe where his understanding starts and stops, plan a path from unconditional truths up to the goal, then teach node by node (motivate → establish → connect → check), grounded in the course textbook, with visuals and frequent checks. Use for "/teach <course> <topic>", "teach me X", "I don't get X", or any request to learn a concept for a class.
---

# /teach: goal → probe → plan → teach

Arguments: `<course> <topic or goal>`. If either is missing, infer it from context or ask in one line.

## Two principles behind every lesson
1. **Unconditional truths first.** Build every idea up from things that are true *with no fine print*: definitions, things {{NAME}} can directly see or compute, and results he's already mastered (🟩/⭐ in the Learner Model). These are the **roots** of the plan. They aren't "axioms" in the formal-math sense (nobody starts from ZFC); they're the points {{NAME}} already accepts without a "but only if…". A rule that has conditions (the power rule "for integer n", L'Hôpital "if 0/0", $W = Fd$ "for constant force along the motion", "the sampling distribution is normal" "if n ≥ 30 or…") is a **theorem**: it gets its own node *above* the roots, with its conditions stated, never smuggled in as a starting point.
2. **"How could I have discovered this?"** (the 3Blue1Brown move). Present each idea so it feels like something {{NAME}} could have invented: start from the question that forces it, let him try, and arrive at the rule as the *only sensible answer*. **The click** is the moment the idea stops being a fact to remember and becomes inevitable ("oh, it *has* to be that"). Aim every node at a click, and when one happens, record what caused it (Learner Model "clicked via").

## 0. Load context (quietly, no narration)
- **Haskell / AP CS:** read the class's `Teaching Haskell.md` (only if the optional Haskell module is installed: `_modules/haskell/`) first and follow it.
- Read `Learning Profile.md`, `.claude/skills/teach/metaphors.md`, the class's `Class Profile.md`, `Course Map.md` and `Learner Model.md`. Find the textbook section(s) and read the extracted text in `_sources/text/`. If an equation or figure is garbled, render the page with `tools/pdf.py render` and look at it.
- **Session note:** create `Courses/<course>/Sessions/YYYY-MM-DD <topic>.md` with a title, the goal (fill in after §1), and the textbook section, then **tell {{NAME}} the note's name so he can open it in Obsidian**. Append the session to that note as you go (lesson steps, questions and {{NAME}}'s answers, feedback, figures), so {{NAME}} can follow along live in Obsidian. The chat and the note should mirror each other.
- **Scoping pass (background):** start the **verifier** agent with `scope <course>: <topic>. Goal: <goal if known>`. It returns the book's definitions and notation, the unconditional truths vs. theorems, prerequisites, misconceptions and scope limits. Use it to write probe distractors and the plan. Don't plan before it's back.

## 1. Goal: ask it separately from level
One **AskUserQuestion** (not graded, no right answer), unless {{NAME}} already said it: *what do you want out of this?* Options shaped by context, e.g. "Get through tonight's homework", "Ready for the quiz/test on <date>", "Actually understand why it works", "AP-exam level". The goal sets the **ceiling** of the plan (how far up the DAG to go) and the pace; the probe sets the **floor**.

## 2. Probe: bracket every strand
Follow **`.claude/skills/teach/quizzes.md`** for every question (construction, "I don't know" last, varied correct position, ✓/✗ + answer + why after each round).
- **Map every strand** the topic depends on (from the scoping pass: e.g. for work–energy: vectors/dot product, kinematics, integrals of force, the definition of KE). Probe each one; don't let one strong strand stand in for the others.
- **Bracket the floor and ceiling per strand.** Start in the middle. Correct → **jump sharply** harder (skip levels; all-correct means the questions were too easy, not that you should creep up a notch). Wrong or "I don't know" → drop down until you find what he solidly has. A strand is mapped when you know both its floor (sure) and its ceiling (where it breaks).
- **One miss is not a cue to teach.** It's evidence. Name the misconception (which distractor he picked, or his reasoning), and if it's ambiguous, ask one more targeted item. Never switch into teaching in the middle of the probe.
- "I don't know" = unlearned (⬜), different from a misconception (🟥 with the misconception named).
- Skip strands the Learner Model marks 🟩/⭐ seen within ~2 weeks, unless the topic sits directly on them (then one confirmation item).
- Up to 4 questions per AskUserQuestion call, usually 2–4 rounds total. {{NAME}} can answer through "Other" with dictated reasoning: read it closely, it's the richest signal.

## 3. Plan: prose + DAG, stress-tested, then wait
1. Draft the path from the floor to the goal as a **Mermaid DAG**: each node one idea, each edge a real dependency, tagged with § and printed pages. Roots are unconditional truths (§ principles) or mapped-floor skills, styled `classDef known fill:#2e7d32,color:#fff`. Check it renders: write it to the scratchpad and run `tools/mermaid_render.py <file.mmd> <out.png>` (fix parse errors before showing it).
2. **Stress-test the roots before showing anything.** For each root, ask: *Is this true with no conditions, or a theorem in disguise?* (If it has an "if", "for", "assuming", it's a theorem: give it its own node and either derive it or state its conditions.) *Does the probe actually show {{NAME}} has it?* (If not, it isn't a root: add the node below it.) *Does the book define it this way?* (Notation and definitions from the scoping pass.) Fix the DAG.
3. Under the graph, **a few lines of prose**: the route in one sentence, then one line per node (what the idea is, how you'll approach it: discover-it / visual / worked example / code). Choose by the Learning Profile and the goal.
4. Show it briefly in chat, put the full version in the note, and **wait for {{NAME}}'s go-ahead** or changes. Don't start teaching on your own.

## 4. Teach: one node at a time, motivate → establish → connect → check
**Choose the mode per node, Socratic or expository, from the topic and {{NAME}}'s energy:**
- **Socratic** (questions that let him build it) when the idea is *derivable* from what he has, and he's engaged (longer replies, asks why, it's not late, no test in the morning).
- **Expository** (clear explanation + worked example, then check) when it's a convention, definition, notation or historical fact that can't be discovered; when he's tired or short on time (short replies, late at night, "just tell me", test tomorrow); or after two Socratic turns where he's stuck. Switch freely mid-node and don't announce it.

**For each node:**
1. **Motivate:** the question or problem that makes this idea *necessary* (a situation from the course, or his projects), before any rule. One or two lines.
2. **Establish:** build it from the roots below it. Socratic: give the setup and ask him to try ("what would you guess d/dx of x³ is, and why?"). Expository: derive or explain it in short steps. Show the book's actual content inline (transcribed definition or example, or a `--clip` render of a figure or boxed rule) tagged `[§3.3 p.121]`; never "see p.121" (CLAUDE.md principle 5). Use the book's notation.
   - **One-line metaphor (expected for each new idea):** one sentence with a general, everyday comparison, per `.claude/skills/teach/metaphors.md` (check its examples first). Never from his personal projects. Leave it out only if nothing simple fits. It's added to the step, never a replacement for it.
   - **Visuals** where seeing beats reading (rules: CLAUDE.md "Visuals"): **visualizer** agent for geometric/quantitative figures, **mermaid-maker** for structure. Either may return `RESULT: NONE`; that's fine, move on. Embed results in the note: `![[<file>.png|500]]` or the returned Mermaid block.
   - **Code** (coding courses, and numerical checks in math/physics): runnable playground blocks and test-backed exercises, per `.claude/skills/teach/code-exercises.md`. Put the blocks in the note as top-level blocks; {{NAME}} runs them in Obsidian and says "check".
3. **Connect:** tie it back to what he knew (the root it came from) and forward to what it unlocks (the next node, the goal problem). Ask for the idea **in his own words**: that's how you see the click.
4. **Check:** 1–2 questions per `quizzes.md` (multiple choice, "rebuild the rule from scratch", or a mini free response), with instant ✓/✗ + answer + why. Move on only after a correct check.
- **When he gets something wrong: ask for his reasoning first.** Find the exact misconception, fix that, re-check. Don't re-explain everything.
- He can interrupt with questions any time: answer, then say where you are in the DAG and continue.

## 5. Accuracy, all the way through
- **The moment you're even slightly unsure of a claim, number or page, verify it before saying it**: read the page, render it, compute it in Python, or ask the verifier. Never make up page numbers.
- **If a check shows you said something wrong, say so plainly**, right away: "Correction: earlier I said X. The book says Y [§ p.]." Then fix anything built on it.

## 6. Close
- A 3–5 bullet recap in the note, with the key formulas in a `> [!tip]` callout.
- Write 3–8 flashcards to `Courses/<course>/Flashcards/<topic>.md` (Spaced Repetition plugin format: `Question::Answer` one per line, tag `#flashcards/<course-slug>` at the top). Favor "why" and "rebuild" cards over plain recall.
- **Update `Learner Model.md`**: levels, last seen, what each idea clicked via, misconceptions seen (named), goal of this session. Add a line to Session history.
- If a pattern about *how* {{NAME}} learns showed up (e.g. which mode worked, which metaphor clicked), add it to `Learning Profile.md` §3.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").
