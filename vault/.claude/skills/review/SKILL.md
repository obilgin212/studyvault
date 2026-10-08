---
name: review
description: Short spaced-review session across all courses (or one), driven by the Learner Models. Picks shaky and stale concepts and quizzes them with rebuild prompts and mixed questions. Use for "/review", "quick review", "what should I study today".
---

# /review: 10–15 minute mixed review

1. Read every `Courses/*/Learner Model.md` (or just the named course) and each Course Map's Upcoming table.
2. Pick 5–8 concepts. Where `Courses/<course>/Tests/stats.json` exists, skills that show up often on that teacher's tests (and were missed there) move up the priority list. Include concepts whose note says **"guided … (fast mode, not checked)"**: those were done in guided mode with no check, so give each one quick check (a single question, not a lesson) and set 🟩 if {{NAME}} gets it right. **Always include one problem from a 🔴/🟠 archetype in `Courses/<course>/Hard Problems.md`** (full-length, unscaffolded, finished to the final answer; a cold correct solve turns it 🟢). Priority: 🟥/🟨 concepts for a test in the next 7 days → 🟥 → 🟨 not seen in 3+ days → 🟩 not seen in 14+ days (to keep them fresh).
3. Create `Courses/<course>/Sessions/YYYY-MM-DD Review.md` (mixed courses: `Reviews/YYYY-MM-DD Review.md`) and log the session there as you go (questions, answers, feedback). Interleave courses and question types: AskUserQuestion multiple choice built by `.claude/skills/teach/quizzes.md` (✓/✗ + answer + why after each), "rebuild X from scratch, talking it through", and a short problem. "I don't know" → mark it unlearned, no penalty for honesty.
4. When {{NAME}} misses one: ask for their reasoning, fix the misconception, and set the concept to 🟥 or 🟨.
5. Update each Learner Model (levels, last seen), then say in one line what to study next.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").
