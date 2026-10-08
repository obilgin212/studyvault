---
name: homework
description: Assignment-driven learning. {{NAME}} gives an assignment (web link, textbook reference like "Ch3 Rv1 p.150 1-45 odd", a photo of a worksheet, a PDF, or pasted text). Figure out what skills it needs, run a quick quiz to find the gaps, teach just up to what's needed to do and understand the assignment, then support {{NAME}} while they do it (hints and checks, not answers). Use for "/homework", "here's my homework/assignment/worksheet/reading guide", "help me with this problem set", or any shared image of assigned problems.
---

# /homework: assignment → gap quiz → teach to the gap → {{NAME}} does it

The goal is that {{NAME}} **can do the assignment themselves and understands it**, with as little time wasted as possible. Only teach what the assignment needs and {{NAME}} doesn't already have. **Never hand over final answers to assigned problems.** Teach on *parallel* problems (same skill, different numbers or functions), then give hints and check {{NAME}}'s work.

**Haskell / AP CS:** read `Courses/<the Haskell class>/Teaching Haskell.md` (template: kit `templates/Teaching Haskell.md`) first and follow it (sources, code style in notes, homework rules).

**Session note:** once the assignment is identified, create `Courses/<course>/Sessions/YYYY-MM-DD <assignment> help.md` (title + a link to the assignment note), tell {{NAME}} its name, and append the session to it as you go (lesson steps, questions and answers, feedback, figures) so the chat and the note mirror each other. The assignment note keeps the problem list, skills map and checklist.

## Mode: full or guided, and {{NAME}} decides
Default is the full flow below (gap quiz → teach to the gap → support). **Use guided mode instead (`.claude/skills/guide/SKILL.md`)** when {{NAME}} asks for it ("guided mode", "fast", "no quizzes", "just walk me through #3 and #7") or the class's `Class Profile.md` has `help_mode: guided`. **Q&A mode** (guide §2b) when {{NAME}} says "let me just ask questions" / "Q&A" or the profile has `help_mode: qa`. Don't push back on {{NAME}}'s choice. {{NAME}} can switch mid-assignment ("go deep" / "back to fast").

## 0. {{NAME}} names an assignment or class material ("help me with A14", "the SAT prep", "my Ch 6 guided notes")
Guided notes, labs, practice tests and other *materials* aren't on the To-Do list: search the class's `Class Materials.md` for them (by name, chapter number or topic), fetch the attachment with `tools/sync/fetch.py`, and read the class's `Syllabus & Schedule.md` for context (unit, pacing, what the teacher expects).

It's probably already in the vault with its materials. Find it first:
1. `~/miniconda3/envs/study/bin/python tools/sync/todo.py list` (open work: title, course, due), then open its note: `Courses/<course>/Assignments/…` or `Courses/Other/<class>/Assignments/…` (the To-Do item links to it). If more than one matches, ask in one line which one. If "my homework" is vague, take the soonest-due open item in that course.
2. Read the note's **📎 Materials** section. For every PDF: `tools/pdf.py info` first, then read **all** pages (`tools/pdf.py text <pdf>` with no page numbers) and render any page with images (see CLAUDE.md: never stop at page 1). It has the teacher's instructions and every attachment:
   - 🌐 **web pages** are already saved locally (`_sources/web/…`): read that copy.
   - 📄 **Google Drive files:** download them now, since {{NAME}} asking for help with this assignment is the request: `cd tools/sync && ~/miniconda3/envs/study/bin/python fetch.py "<url>" "<vault>/Courses/<course>/_sources/handouts"`. Say in one line which file you're fetching. Then read it (render PDF pages that contain math or figures), and update the note's line to link the local file.
   - **Textbook pages mentioned:** render them with `tools/pdf.py`. If the textbook isn't in the vault, say so and offer `/add-course`.
   - 📝 **Google Forms** are for {{NAME}} to fill in. Help with the content; don't submit anything.
3. If the Materials section is missing or older than a day, refresh it first: `cd tools/sync && ~/miniconda3/envs/study/bin/python materials.py --only "<title words>"`.
4. Then continue at step 2 below (skills map). The assignment is already captured, so skip step 1.

## 1. Capture the assignment (whatever form it comes in)

Work out the course from the content, or ask in one line. Save the assignment as `Courses/<course>/Assignments/YYYY-MM-DD <short name>.md` with the source at the top, the **full problem list written out** (LaTeX for math, fenced code for code), and a status checklist `- [ ] 1.` per problem. Tell {{NAME}} the note's name so they can open it in Obsidian.

| Input | How to capture it |
|---|---|
| **Web link** (e.g. a class website reading guide) | WebFetch the page, asking for *every question verbatim, including code*. Also fetch the reading it points to (e.g. the Learn You a Haskell chapter) and save it to `_sources/` with its URL. That becomes the ground truth to teach from. |
| **Textbook reference** (e.g. "Ch3 Rv1 (p.150): 1-45 odd") | Parse the section, page and problem list ("odd" means every odd number in the range). Find the pages in `Course Map.md` and `tools/pdf.py search`. **Render the pages** (`tools/pdf.py render`, `--zoom 1.5`) and read them as images, because the extracted text garbles math. Copy the exact problems and their instructions (e.g. "In Exercises 1–30, find the derivative"). Problems can continue onto the next page. |
| **Photo** (Physics worksheet, handouts) | {{NAME}} either drags the image into the chat or drops it in `Inbox/` (AirDrop and iCloud land in `~/Downloads`, so check the newest images there too). Convert HEIC first: `sips -s format jpeg in.HEIC --out Inbox/name.jpg`. Read the image and transcribe every problem, including given values, units and diagrams (describe them in words). **Show {{NAME}} the transcription and ask them to confirm anything blurry or ambiguous** before going further. Move the image into `Courses/<course>/Assignments/img/`. |
| **PDF / pasted text** | Read it directly (render PDF pages that contain math or figures). |

If the course folder doesn't exist yet, create a minimal one first: `Course Map.md` (sources + Upcoming table), an empty `Learner Model.md` table and `Sessions/`, modeled on `_examples/AP Calc BC/`. Run the full `/add-course` later.

## 2. Map problems → skills (think before quizzing)

In the assignment note, add a **skills map**: a table of `skill | problems that need it | Learner Model level`, plus a small Mermaid graph of the prerequisites. Group big sets: 23 derivative problems might need only ~6 distinct skills (power rule with negative/fractional exponents, product, quotient, trig derivatives, the second derivative, tangent/normal lines). Include **hidden prerequisites** too (algebra simplification, trig identities, unit conversions, Haskell syntax like parentheses in patterns). Look up each skill in `Learner Model.md`. Add any skills it doesn't have yet as ⬜ rows.

Sort the skills:
- 🟩/⭐ seen recently → **skip** (maybe one confirmation question if the assignment really depends on it)
- ⬜ unknown → **probe**
- 🟥/🟨 → **probe briefly, probably teach**

## 3. Quick gap quiz (one round, maybe two)

- **AskUserQuestion**, up to 4 questions per call, **one question per skill that needs probing**, hardest-skill-first so a correct answer can clear the easier ones below it. Build every question by **`.claude/skills/teach/quizzes.md`** (distractors from real misconceptions, same length, no reasons in options, no "(Recommended)", correct position varied, "I don't know" last, ✓/✗ + answer + why right after). Use parallel items, **never the assigned problems themselves**.
- One miss isn't automatically 📘: name the misconception first (quizzes.md "Reading the results").
- Code courses: ask things like "what does this expression evaluate to?", "which definition compiles?", "what's wrong with this pattern?" with short code in the question. Physics: concept checks (free-body setup, sign conventions, which equation applies) as well as one quantitative item.
- {{NAME}} can answer through "Other" with dictated reasoning. Read that reasoning for misconceptions.
- Stop as soon as every skill on the map has a verdict. The quiz should take about **3–5 minutes**. This is not a full probe like `/teach`.
- Update the skills map with the results: `✅ ready` / `📘 teach` for each skill.

## 4. Teach to the gap (only 📘 skills, in prerequisite order)

Use the `/teach` node loop (read `.claude/skills/teach/SKILL.md` §4: motivate → establish → connect → check, Socratic or expository by topic and {{NAME}}'s energy, its one-line everyday metaphors (`.claude/skills/teach/metaphors.md`), and its two principles: unconditional truths first, "how could I have discovered this?"): one reasoning step at a time, grounded in the course source, with the source's content **shown inline** and tagged (`[§3.3 p.122]`, `[LYAH ch4 "Guards, guards!"]`), never "go look it up" (CLAUDE.md principle 5), and **visuals where they help** ({{NAME}} asked for more graphs: `visualizer` agent for math and physics figures, `mermaid-maker` for structure, code: evaluation traces; one idea per figure, embed `![[<name>.png|500]]`, `RESULT: NONE` is fine; CLAUDE.md "Visuals"). Then:
- A **worked parallel example** → {{NAME}} does a **parallel problem out loud** → rebuild the rule from understanding.
- **Code:** give the parallel problem as a **test-backed exercise block** in the note (format: `.claude/skills/teach/code-exercises.md`). {{NAME}} writes it and hits Run in Obsidian, then says "check" for hidden edge-case tests (`check` skill). Getting a real compiler error and working out why teaches more than anything else. For the assigned problems themselves, {{NAME}} can ask you to run their homework file against tests you write, but those tests only report pass/fail on inputs and never show the solution.
- A skill is ready when {{NAME}} gets one parallel problem right *and can explain why*. Tie each skill back to its problems: "this is what you need for #11, #13, #23."

## 5. {{NAME}} does the assignment (tutor steps back)

Give them the **problem → skill → where it was taught** table, then switch to support mode:
- **Stuck?** Give graded hints: (1) which skill or idea applies → (2) the first step → (3) a parallel worked step. Never the final answer. When {{NAME}} is wrong, **ask them to explain their reasoning first**.
- **Check work** when they share it (typed, dictated, or a photo of handwritten work): find the first wrong line, not just "wrong".
  - Calc odd problems: compare with the back-of-book answers (`_sources/answers-index.md`, then render the page) **only after {{NAME}} has an answer**.
  - Code: run it against test cases.
  - Physics: check units, and sanity-check with limiting cases.
- Tick problems off in the assignment note as they're done.
- If a new gap shows up while working, do a mini-teach (step 4) on it, then go back to the assignment.

## 6. Close

If the assignment is finished, tick it off: `~/miniconda3/envs/study/bin/python tools/sync/todo.py done "<title words>"`. If it isn't, and {{NAME}} names a plan ("rest tonight"), add that with `todo.py add`.


Update `Learner Model.md` (the skills practiced, their levels, misconceptions, "clicked via"), add 3–6 flashcards for the skills that were taught, log the session in the Learner Model's Session history, and add any new learning pattern to `Learning Profile.md` §3. If a test is coming up in the Course Map, say in one line how this assignment's gaps affect studying for it.

## Skill tree (every time the Learner Model changes)
Right after updating `Learner Model.md`, rebuild the class's map: `~/miniconda3/envs/study/bin/python tools/skilltree.py "<course>"`. If it prints **🆕 added from the Learner Model**, open `Courses/<course>/_skilltree.yaml`, move each new node from branch `new` to the right unit, set its `needs` (prerequisite ids), `ref` and a few lowercase `find` words, then run it again. Tell {{NAME}} in one line what changed on his tree ("✨ Implicit differentiation is now 🟩 on your Calc tree").

## If a download fails
`fetch.py` exit code 3 = the school sign-in expired (about every 2 weeks): ask {{NAME}} to run `~/miniconda3/envs/study/bin/python tools/sync/login.py` (sign in, check Classroom **and** Google Docs load, close the window), then retry the same command. Any other failure: say what it printed, and ask for a screenshot or paste only if the file really can't be exported.
