---
name: exam-prep
description: Test preparation. Diagnose weak spots across an exam's topics, drill them with AP-style and textbook-grounded practice (rebuild-from-memory, FRQ, timed sets), and produce a cheat-sheet summary. Use for "/exam-prep", "I have a test on X", "help me study for my quiz/test/exam".
---

# /exam-prep: diagnose → drill → timed set → summary

Arguments: `<course> <exam>` (e.g. `AP Calc BC ch3`). Read `Learning Profile.md`, the Course Map (exam date and coverage), and the Learner Model. Work out how much time is left. **If the test is tomorrow, keep it tight:** diagnose fast, drill the weakest two or three areas, do one timed set, and write the summary. Don't try to cover everything evenly.

Create `Courses/<course>/Sessions/YYYY-MM-DD Exam prep <exam>.md` and tell {{NAME}} its name. Log everything there as you go. Every multiple-choice question follows `.claude/skills/teach/quizzes.md` (✓/✗ + answer + why after each). Verify every answer key you write (solve it yourself or use the `verifier`) before grading with it.

## 1. Rapid diagnostic (about 10 min)
- 2–3 AskUserQuestion rounds (up to 4 questions each) covering **every section on the exam**, in the style of the textbook's exercises and the AP exam. Include an "I don't know" option.
- Base questions on the textbook's own exercises and "Quick Quiz for AP Preparation" pages (search with `tools/pdf.py search`). Write each question out in full in the chat and note (render the page region with `--clip` if it has a graph or table), and tag where it came from (e.g. `[Ch3 Review #41, p.151]`). Never make {{NAME}} open the book to see a question or its answer.
- Bracket like the /teach probe: all-correct on a section → jump to its hardest item type; a miss → name the misconception before calling it weak.
- Update the Learner Model right away. Show a small table (topic → 🟥/🟨/🟩) and the drill order, weakest first.

## 2. Targeted drill (per weak area)
Loop (a one-line everyday metaphor in the reminder when it really fits, per `.claude/skills/teach/metaphors.md`): a short focused reminder (one step, a visual if it helps) → a **rebuild** prompt ("without looking, write the quotient rule and explain why the minus sign is where it is") → 2–3 practice problems, harder each time.
- {{NAME}} talks through their work out loud (dictation). **When they miss one, ask them to explain their reasoning** before you correct anything, then name the precise misconception.
- Include classic trap problems: continuous but not differentiable, speed vs velocity, sign of $v\cdot a$ for speeding up, $\frac{d}{dx}\sec x$ vs $\tan x$, quotient-rule order.
- Move on once {{NAME}} gets two in a row right.

## 3. Timed set
- A mixed set in AP format, e.g. **6 multiple choice + 1 multi-part FRQ**, with a time limit (about 2 min per MC and 10 min per FRQ). Post the whole set in the note at once. {{NAME}} answers in chat (dictated is fine) and says "done". Record their start and finish times from the messages.
- Grade with an AP-style rubric (points per part), show where points were lost, and follow up on any new weak spot.

## 4. Summary sheet
Write `Courses/<course>/<exam> Summary.md`: every rule and definition on the test, each with a one-line "why" (so it can be rebuilt, not just memorized), the traps {{NAME}} actually fell into, and 2–3 sketches or visuals of the key graph relationships. Update the Learner Model and flashcards.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").
