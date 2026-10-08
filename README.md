# StudyVault: a personal AI tutor that lives in Obsidian and knows your classes

A learning system built on **Claude Code** (your Claude subscription, no API keys) and an **Obsidian** vault:

- **Tutoring grounded in your own class materials:** your textbooks (with page citations, and the content shown inline instead of "see p. 121"), handouts, syllabi and your teacher's AI policy.
- **Probe → plan → teach:** it finds where your understanding starts and stops before teaching, plans a path from things you already know, then teaches one step at a time with quick checks.
- **Google Classroom sync** without any API: a headless Chrome reads Classroom (read-only) once a day. It builds a **To-Do list** from your real To-do and Missing lists, writes a note per assignment with its materials, and turns teacher announcements into tasks.
- **Two ways through homework:** full (`/homework`: gap quiz → teach to the gap → hints) or guided (`/guide`: you pick the parts, no quizzes). It never gives final answers to assigned problems.
- **Skill trees:** one Obsidian canvas per class, colored by what you actually know, updated after every session, with links to every note where you worked on each skill.
- **Runnable code in notes** (Python, Haskell notebook-style, Racket) with hidden-test checking.
- **Visuals:** diagram and figure agents that check their own output.
- **Optional college module:** deadline tracker, story bank, essay feedback with version history. It never writes a word of your essays.

## What you need
- A Mac, a Claude **Pro or Max** subscription with Claude Code, Google Chrome, Obsidian.
- A school Google account with Classroom (for the sync; the tutor works without it).

## Set it up
Clone or download this repo, then follow **[SETUP-PROMPT.md](SETUP-PROMPT.md)**: open Claude Code in this folder and paste the prompt. Claude reads [`setup/SETUP.md`](setup/SETUP.md) and installs, personalizes and configures everything with you: your classes, textbooks, learning style and metaphors. You do the sign-ins yourself.

## What's in here
| Path | What it is |
|---|---|
| `vault/.claude/skills/` | the tutor's skills: `/teach`, `/homework`, `/guide`, `/exam-prep`, `/review`, `/sync`, `/profile`, `/add-course`, `check`, `/college` |
| `vault/.claude/agents/` | `verifier` (textbook-first fact checks and topic scoping), `visualizer` (matplotlib figures), `mermaid-maker` (diagrams) |
| `vault/tools/` | PDF/textbook tools, code runners, skill trees, Classroom sync (`tools/sync/`), college tools |
| `templates/` | `CLAUDE.md` (the tutor's rules, with placeholders), Learning Profile, About Me, Dashboard, Class Profile, college notes |
| `setup/SETUP.md` | the step-by-step setup that Claude Code follows |
| `obsidian/` | settings for the Execute Code plugin (paths filled in during setup) |

## Principles it's built on
Teach at the edge of what you know. Put the effort into the material, not the logistics. Ground every claim in your own sources and verify before saying it. Quiz often, with fair questions. Bring the source to you instead of sending you to it. Your choice of mode is respected. Assigned work stays yours.

## Privacy
Everything stays on your Mac: the vault, the Chrome profile with your school sign-in (in `~/Library/Application Support/StudyVaultSync`), and the sync snapshots. Nothing in this repo contains anyone's personal data. Don't commit your own vault to a public repo.

License: MIT (see `LICENSE`).
