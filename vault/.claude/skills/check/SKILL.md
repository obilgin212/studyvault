---
name: check
description: Check {{NAME}}'s code exercise(s) in the current lesson or assignment note. Runs their code against the visible tests plus hidden edge-case tests, then reviews it like a tutor (reasoning first, no answers). Use when {{NAME}} says "check", "check my code", "did I get it", "run my code", or pastes/points at a code block.
---

# check: run + hidden tests + review

Read `.claude/skills/teach/code-exercises.md` first (the block format and the tools). For Haskell, also read `Courses/<the Haskell class>/Teaching Haskell.md` (template: kit `templates/Teaching Haskell.md`).

1. **Find the note:** the note this session is logging to. Otherwise, the most recently modified `.md` under `Courses/*/Sessions` or `Courses/*/Assignments` (`ls -t`). Say which note and exercise you're checking in one line.
2. **Find the exercise:** `tools/notecode.py list "<note>"`. Exercise blocks: Haskell ones start with `-- ✏️` (their tests are the `runTests [...]` block below); Python ones have `import: 'tests-…'`. If {{NAME}} named one, use that; otherwise use the most recently edited one, i.e. the one no longer containing `undefined` / `...`.
3. **Run the visible tests:** Haskell: run the 🔒 tests block's index. Python: run the exercise block's index.
4. **Run hidden tests:** write 3–6 extra tests to the scratchpad. Haskell: one `runTests [ test "…" (…) … ]` expression, run with `--tests FILE` against the ✏️ exercise block's index. Python: a tests block (`from check import test` …), run with `--tests FILE` against the exercise block. Cover edge cases the visible tests skip: empty or singleton input, negatives and zero, large values, the corner the lesson was about, a type or laziness trap. Run with `--tests <file>`. Never put hidden tests in the vault or show their expected values before {{NAME}} has reasoned about the failure.
5. **Review, as a tutor:**
   - All pass → say so, then ask {{NAME}} to **explain why it works** (one or two sentences), and give one "what would happen if…" follow-up.
   - Something fails → show the failing *input* only (e.g. "`firstOr 0 []` crashes"), and **ask {{NAME}} to predict what their code does on it and why**. Only after they answer, give a hint using the hint ladder: which idea applies → the first step → a parallel example. Never paste the corrected code.
   - Compile errors → translate GHC's message into plain words, point at the line in *their* block, and ask what they think the type mismatch means.
   - Also comment on style that matters for learning (e.g. using `head` instead of pattern matching when the lesson is pattern matching), briefly.
6. **Log it:** append the result to the note under the exercise (`> [!check]` callout: pass/fail counts, what was tricky). Update `Learner Model.md` (skill level, misconception) and add to `Learning Profile.md` §3 if a pattern shows up.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").
