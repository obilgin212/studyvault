# StudyVault setup: instructions for Claude Code

You are setting up **StudyVault** (a personal AI tutor + Google Classroom tracker that lives in an Obsidian vault) on this student's Mac. You are running in the kit folder. Work through the phases in order. **Ask the student** wherever a step says so (use AskUserQuestion for choices, plain questions for free text); otherwise act. After each phase, say in one line what's done.

**Nothing is assumed about this student.** Their classes, teachers, textbooks, AI policies, units and dates come from **their own Google Classroom** (`collect.py --list-classes`, `classindex.py`) and their documents; their preferences (learning style, metaphors, modes, college plans) come from **their answers**. The skills and tools mention example classes (AP Calc, Haskell…) only as illustrations. Never copy those into this student's setup unless they actually take that class.

Rules for the whole setup:
- This is the student's own computer and accounts. Never type passwords or sign in for them: every sign-in is done by the student in a window you open.
- Ask before installing anything system-wide (Miniconda, GHC, Racket, Homebrew packages).
- The vault goes to `~/StudyVault` (the tools assume that path). If `~/StudyVault` already exists, stop and ask.
- Personalize carefully: every `{{PLACEHOLDER}}` must be gone at the end (`grep -rn "{{" ~/StudyVault --include=*.md --include=*.json --include=*.py` must print nothing except code that legitimately contains `{{`, e.g. Python format strings in tools/).

---

## Phase 1: prerequisites (check, then install what's missing)
1. macOS. Claude Code is installed (you're running in it) and logged in with a Claude subscription (Pro or Max). Background jobs use `claude -p --model haiku`, which counts toward the plan's usage.
2. **Google Chrome** in `/Applications` (the Classroom sync drives the real Chrome with its own separate profile).
3. **Obsidian** (https://obsidian.md). If missing, ask the student to install it.
4. **Miniconda** at `~/miniconda3` (ask first; installer from https://docs.conda.io/en/latest/miniconda.html, macOS, matching `uname -m`). Then create the env:
   ```bash
   ~/miniconda3/bin/conda create -y -n study python=3.12
   ~/miniconda3/envs/study/bin/pip install pymupdf matplotlib numpy playwright pyyaml openpyxl
   ```
   (Playwright uses the installed Chrome via `channel="chrome"`, so no `playwright install` is needed.)
5. Diagram renderer library (MIT-licensed mermaid.js, used to check diagrams before showing them):
   ```bash
   mkdir -p vault/tools/vendor && curl -fL -o vault/tools/vendor/mermaid-11.min.js https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js
   ```
   (Any 11.x works; the renderer uses the file named `mermaid-*.min.js` in `tools/vendor`.)
6. **Don't install Haskell or Racket here.** They're optional modules (`vault/_modules/`), set up only if a class needs them (Phase 6).

## Phase 2: get to know the student (ask)
Ask, then keep the answers for Phase 4:
- First name, pronouns, grade (e.g. junior/senior).
- How they learn best (they can answer briefly now and run `/profile` later for the full quiz).
- **Metaphor style** (AskUserQuestion): "general, everyday comparisons (money, sports, driving)" or "comparisons from my own life and projects" or "no metaphors".
- Hobbies / projects / sports / languages (for `About Me.md`; optional).
- Do they **dictate** (voice typing)? (keeps the "Voice" section in CLAUDE.md or removes it)
- Applying to college **this cycle**? If yes: their school's college platform (Naviance / the school's college platform / Scoir / other), their early deadlines, the name of the senior-class Google Classroom (if there is one).

## Phase 3: copy the vault
```bash
cp -R vault ~/StudyVault
mkdir -p ~/StudyVault/{Courses,Inbox/sync}
```
Copy the templates: `templates/CLAUDE.md`, `templates/Learning Profile.md`, `templates/About Me.md`, `templates/Dashboard.md` into `~/StudyVault/`. If college = yes: `mkdir ~/StudyVault/College && cp templates/college/* ~/StudyVault/College/` (also keep `.claude/skills/college`); if no: delete `~/StudyVault/.claude/skills/college` and `~/StudyVault/tools/college`.

## Phase 4: personalize
1. Replace `{{NAME}}` with the student's first name in every file under `~/StudyVault` (`.md`, `.py`, `.json`). The skills and agents describe the student with he/him/his. **If the student's pronouns are different, edit those words** in `~/StudyVault/.claude/**/*.md` and `CLAUDE.md` so they read naturally (don't do a blind find-and-replace: "his" can mean other things).
2. Fill `CLAUDE.md`'s placeholders: `{{PRONOUNS}}`, `{{GRADE}}`, `{{CORE_CLASSES}}` (after Phase 6), `{{ONE_LINE_ABOUT}}` (one sentence from About Me, or delete), `{{METAPHOR_STYLE}}`:
   - everyday → "Keep them **general and everyday** (money, sports, driving, cooking…), never from {{NAME}}'s personal projects."
   - own life → "Build them from {{NAME}}'s real life in `About Me.md`: specific, accurate, one line." and rewrite `.claude/skills/teach/metaphors.md` rule 3 and the opening paragraph to match.
   - none → "Don't use metaphors." and delete the metaphor lines from teach/guide/homework skills.
   `{{STRICT_CLASSES_SENTENCE}}` comes from the class profiles (Phase 6): e.g. "History and English are strict: explain and question only, never produce submittable work", or "no class has a strict AI policy yet". Remove the optional Haskell / College blocks if they don't apply (and their `<!-- OPTIONAL -->` comments). Remove the "Voice" section if they don't dictate.
3. Write `Learning Profile.md` §1 from their answer (in their words) and `About Me.md`.

## Phase 5: Google Classroom sign-in + class list
1. Tell the student: "A separate Chrome window will open. Sign in with your **school** Google account only, check that Classroom AND Google Docs load, then quit that window with ⌘Q." Then run:
   ```bash
   cd ~/StudyVault/tools/sync && ~/miniconda3/envs/study/bin/python login.py
   ```
2. Detect the school's sign-in page (an expired session, about every 2 weeks, lands there; that's how the tools notice it):
   ```bash
   ~/miniconda3/envs/study/bin/python detect_sso.py
   ```
   It lists the non-Google sites the sign-in window visited, most likely first. If the top one is clearly a sign-in/identity portal, run it again with `--write` to save it to `config.json → signin_markers`. If it prints that only Google was visited, leave `signin_markers` empty.
3. List their classes:
   ```bash
   ~/miniconda3/envs/study/bin/python collect.py --list-classes
   ```
   (The first letter of each name may appear twice: Classroom's avatar letter. Matching ignores that.)
4. Ask which are **core classes** (the ones to track and tutor; clubs/homeroom are ignored). For each, pick a short folder name (e.g. "AP Bio", "Spanish 3"). Fill `tools/sync/config.json → classes` with `{"match": "<a distinctive part of the Classroom name>", "course": "<folder name>"}`. If a class has a public course website, add it to `public_sites` (see the example entry). College = yes and there's a senior-class classroom → `college_classes: [{"match": "<part of its name>", "course": "College"}]` and fill `college` (platform, not_platform or "", early_deadline). Otherwise set `college_classes: []`.

## Phase 6: build each class
For each core class:
1. `mkdir -p "~/StudyVault/Courses/<folder>/"{_sources/text,Sessions,Visuals,Flashcards,Assignments}` and copy `templates/Class Profile.md` there (replace `{{COURSE}}`).
2. Pull its Classroom data: `cd ~/StudyVault/tools/sync && ~/miniconda3/envs/study/bin/python classindex.py --course "<folder>"` → writes `Class Materials.md` and `Syllabus & Schedule.md`.
3. Read those and fill the Class Profile frontmatter (teacher, grading, late work, retakes, **ai_policy**, current unit, next assessment). Only facts from the class's own documents; leave a field empty rather than guess.
4. Ask whether they have the **textbook as a PDF** for that class. If yes, run `/add-course` logic: copy it to `_sources/textbook.pdf`, build `Course Map.md`, an empty `Learner Model.md` and `_skilltree.yaml` (see `.claude/skills/add-course/SKILL.md`). If not, create a minimal `Course Map.md` (units from the syllabus), an empty `Learner Model.md`, and a small `_skilltree.yaml` from the syllabus units.
5. **Programming classes:** if a class's Classroom posts or syllabus show it uses **Haskell** (Haskell, *Learn You a Haskell*, `ghci`, `.hs` files) or **Racket** (DrRacket, *How to Design Programs*), tell the student and ask whether to set it up now; if yes, follow `~/StudyVault/_modules/haskell/INSTALL.md` or `_modules/racket/INSTALL.md`. If no class uses them, do nothing: the modules stay in `_modules/` (uninstalled) so the tutor can add them later if the student starts such a class.
`_examples/AP Calc BC/` is a finished example (Course Map, Learner Model format, skill-tree spec): model new classes on it, then you may delete it.
Then: `~/miniconda3/envs/study/bin/python ~/StudyVault/tools/classes_table.py` (writes `Classes.md`) and `~/miniconda3/envs/study/bin/python ~/StudyVault/tools/skilltree.py --all`.

## Phase 7: Obsidian
1. Ask the student to open `~/StudyVault` as a vault in Obsidian ("Open folder as vault"), turn on community plugins, and install **Execute Code** (Settings → Community plugins → Browse → "Execute Code" → Install → Enable). Optional: **Spaced Repetition** (for the flashcards).
2. After they say it's installed: quit Obsidian, then write the plugin settings (from the kit folder):
   ```bash
   ~/miniconda3/envs/study/bin/python setup/fill_obsidian_settings.py
   ```
   and reopen Obsidian. Code blocks get a **Run** button in Reading view (⌘E). `Running Code.md` is the demo note: have them press Run on its first Python block.

## Phase 8: first sync + daily schedule
```bash
cd ~/StudyVault/tools/sync && ~/miniconda3/envs/study/bin/python collect.py      # first run = baseline (3–7 min)
~/miniconda3/envs/study/bin/python todo.py render
zsh schedule.sh install        # runs at login + hourly; the real sync happens once a day
```
Check `~/StudyVault/To-Do.md` lists their open Classroom work. If a test date or assignment looks wrong, say so; don't hide it.

## Phase 9: hand-off
Verify: no `{{` placeholders left in `.md` files; `tools/skilltree.py --all` runs; `todo.py list` works. Then tell the student, briefly:
- Start the tutor: `cd ~/StudyVault && claude`. Try `/sync`, then `/homework <an assignment name>` or `/teach <class> <topic>`, and `/profile` for the learning-style quiz.
- Every ~2 weeks the school sign-in expires: they get a Mac notification; run `~/miniconda3/envs/study/bin/python ~/StudyVault/tools/sync/login.py`.
- Integrity: the tutor teaches on parallel problems and never hands over answers to assigned work; classes with strict AI policies get explanations and questions only; college essays are always their own words.
