---
name: past-tests
description: Learn how a teacher writes tests from {{NAME}}'s past tests, quizzes and practice tests, then make practice match the real thing. Ingest an assessment (PDF, photos, Classroom practice test), tag every question (skill, format, problem type, the teacher's "moves"), build the class's Test Profile, forecast the next test, generate mock tests with the same structure and moves, and debrief after the real test so forecasts improve. Updates the Learner Model, Hard Problem bank and skill tree. Use for "/past-tests", "here's my old test", "upload my practice test", "learn from my quiz", "what will the next test look like", "make me a mock test", "practice like the real test".
---

# /past-tests: learn the teacher's tests → practice that matches them

Arguments: `<mode> <course> [file / test name]`. Modes: `add` (default when a file or photo comes in) · `scan` · `profile` · `forecast` · `mock` · `debrief`.

**The goal:** {{NAME}}'s practice should look like what he'll see on the test: same structure, same kind of hard, the teacher's habits, so nothing on the real test is the first time he's seen that kind of problem. **Every assessment added makes it more accurate.** Data lives in `Courses/<course>/Tests/` (`tests.json`, one note per assessment, `Test Profile.md`, forecasts, mocks); the math is in `tools/testprofile.py` (run with `~/miniconda3/envs/study/bin/python`).

Rules: past tests are {{NAME}}'s own returned work or material the teacher posted; keep them in the vault, never share them. Mock tests use **new** problems in the teacher's style, never copies of assigned or upcoming test questions. Verify every answer key before grading with it (solve it yourself, check numerically in Python, or use the `verifier` agent).

## Read first
`Courses/<course>/Class Profile.md` (test format, calculator rules, retakes), `Course Map.md` (what the next test covers), `Learner Model.md`, `_skilltree.yaml` (skill ids for tagging), `Hard Problems.md` if it exists, and `Tests/Test Profile.md` if it exists.

## `add`: learn from one assessment
1. **Get the file.** Photos/PDFs {{NAME}} drops in or into `Inbox/` (convert HEIC like `/homework` does). A Classroom practice test or review packet: find it in `Class Materials.md` and fetch it with `tools/sync/fetch.py <url> Courses/<course>/_sources/tests` ({{NAME}} asking for this counts as approval). Keep originals in `Courses/<course>/_sources/tests/`. **Read every page** (`tools/pdf.py info`, then `text` with no page range; render every page that has math, figures or handwriting and look at it).
2. **Transcribe** every question into `Courses/<course>/Tests/<id>.md` (`<id>` = `YYYY-MM-DD <short name>`, e.g. `2026-10-08 Ch4 Test`): number, points, format, calculator yes/no, the full question (LaTeX), and **{{NAME}}'s result** read from the grading marks (✓/✗/partial, points lost, the teacher's comments). If the page shows no grading, ask {{NAME}} in one line which ones he missed or found hard (that's the most valuable signal); never guess a result.
3. **Tag every question** (in a table in the note, and in the record):
   - `skills`: node ids from `_skilltree.yaml` (add missing nodes to the spec first, in the right branch with `needs`).
   - `format` mc / frq / short / proof / other; `parts` (number of dependent parts); `difficulty` 1–3 (3 = harder than the book's typical exercise for that section).
   - `archetype`: a short id for the chapter-specific problem type (e.g. `inverse-slope-solve-for-b`), with a one-line label and a **`transfer`** sentence: what this type becomes in another chapter.
   - `twists`: the teacher's moves, from the shared list in `tools/testprofile.py` (`no-scaffold`, `solve-hidden-step`, `multi-rep`, `reverse`, `prior-chapter`, `messy-algebra`, `justify`, `trap-distractor`, `no-calc-numbers`, `combined-skills`, `conceptual`, `unit-context`, `long-multi-part`). Add a new twist id to that list only if nothing fits, with a one-line description.
   - `source`: where it came from if recognizable (search the textbook: `tools/pdf.py search`), e.g. `§4.3 #28 (unscaffolded)` or `AP 2019 FRQ 5`. A teacher who pulls from the book's review exercises is a pattern worth knowing.
4. **Save:** write the record JSON (format in `tools/testprofile.py`'s docstring; include `"archetypes": {id: {"label", "transfer"}}` for new ones) to the scratchpad, then `testprofile.py add "<course>" <file>`. It validates the tags (fix anything it rejects), stores the assessment and rebuilds `Tests/Test Profile.md` + `Tests/stats.json`. Use `kind` honestly: `test`, `quiz`, `practice` (a teacher-made or book practice test), `homework`. **Never add tutor-made mocks** (they would teach the system its own style instead of the teacher's).
5. **Feed the rest of the system:**
   - **Learner Model:** a real-test result is the strongest evidence there is. A miss → that skill at most 🟨 with the misconception named ("Ch4 Test #3: used $f'(a)$"); a clean solve of a difficulty-3 question → evidence toward 🟩.
   - **Hard Problems.md:** every missed or difficulty-3 question becomes or reinforces an archetype (🔴 if missed), with verified practice per `/exam-prep` step 0.
   - **Skill tree:** `tools/skilltree.py "<course>"` (cards now show "🎯 on tests N×", the header lists test priorities).
   - Add qualitative patterns the numbers can't show (wording habits, how partial credit is given, what the teacher said about the test) under **Tutor's notes** at the bottom of `Test Profile.md`.
6. Tell {{NAME}} in 3–5 lines what this assessment taught: the strongest new pattern, what cost points, how confident the profile now is, and what to do with it ("next mock will include 2 `solve-hidden-step` problems").

## `scan`: find more material
Search `Class Materials.md` (and `Syllabus & Schedule.md`) for practice tests, review packets, old quizzes, "test review", answer keys. List what exists per chapter with links; fetch and `add` the ones {{NAME}} picks (kind `practice`, or `quiz`/`test` if they're real past assessments). Ask {{NAME}} whether he has older tests on paper (photos are fine). **More assessments = a sharper profile.**

## `profile`: what the teacher does
Show the top of `Tests/Test Profile.md` in chat: structure, where the points go, the 3 most common moves, the problem types that cost {{NAME}} points, and the confidence level. If confidence is low, say so and suggest `scan`.

## `forecast`: the next test
For the next assessment (Course Map Upcoming / Class Profile `next_assessment`):
1. **Structure:** the profile's typical one for that kind (test vs quiz), adjusted for anything the teacher announced.
2. **Coverage:** the sections on the test (Course Map) → skill-tree nodes, weighted like the profile's unit weights (emphasis the teacher gave in class or the syllabus counts too).
3. **Predicted problems:** apply each common **move** to the **new chapter's** skills, using each archetype's `transfer` sentence: e.g. the teacher always removes the scaffold (`no-scaffold`) → predict the new chapter's hardest book exercise asked without its helper parts; `prior-chapter` → predict which earlier skill gets pulled in (from the skill tree's `needs`). Rank by likelihood × {{NAME}}'s weakness (Learner Model, skill tree priorities).
4. Write `Tests/Forecast <test>.md`: structure, coverage table, 6–10 predicted problem types each with *why predicted* (which pattern, how many past assessments support it) and {{NAME}}'s readiness (🟥/🟨/🟩), plus confidence. Log it: a JSON `{"for": "<future test id>", "twists": [...], "skills": [...], "structure": {"questions": N, ...}}` → `testprofile.py forecast "<course>" <file>`.

## `mock`: practice that looks like the test
Build `Tests/Mock <test> v<N>.md` from the forecast (make one first if none exists):
- **Same shape:** same number of questions, the same format mix, points, time limit and calculator split as the profile; the same share of difficulty-3 questions (never easier than the real thing: `/exam-prep` step 0's bar).
- **Same moves:** every common move appears at least once; each Hard Problems 🔴/🟠 archetype in coverage appears unscaffolded; distractors built the way this teacher builds them (`trap-distractor` habits from past MC).
- **New problems** in the teacher's style (from the book's unassigned/review exercises with scaffolds removed, or written fresh), each with a **verified** key collapsed under it (`> [!check]-`).
- Timed: post the whole mock at once; {{NAME}} works on paper and sends photos or dictates answers, and says "done" (record start/finish times from the messages). Grade like the teacher grades (points per part, justification wording if `justify` is a habit), show exactly where points went, then **update the Learner Model, Hard Problems.md and the skill tree** from the results (mocks don't go into `tests.json`). Offer a v2 aimed at what he missed.

## `debrief`: after the real test
1. `add` the real test as soon as it's back (or from {{NAME}}'s memory of the questions right after, marked `"result": "unknown"` until graded; update later).
2. `testprofile.py score "<course>" "<test id>"` compares it with the logged forecast (which moves and skills were predicted vs. real). Tell {{NAME}} plainly what the forecast got right and wrong, and record why under Tutor's notes ("missed: teacher added a related-rates question from the next chapter's first section"). This is how the forecasts get better.
3. Same as `/exam-prep` §5: which questions were hard → Hard Problems.md.

## Studying with it
- `/exam-prep` reads `Tests/Test Profile.md` and the latest forecast: its diagnostic covers the forecast's coverage, and its timed set is a mock (same shape and moves).
- `/review` weights picks by `Tests/stats.json`: skills that show up often on this teacher's tests and aren't solid come first.
- The skill tree header's **🎯 Test priorities** is the short list to study.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs`, `ref` and `find`, then run it again. Tell {{NAME}} in one line what changed on his tree.
