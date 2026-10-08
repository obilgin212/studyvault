# StudyVault setup on Windows: instructions for Claude Code

Same system and the same phases as `setup/SETUP.md` (the macOS guide). **Read `setup/SETUP.md` too**: everything below replaces only the steps that differ on Windows; for every other step, follow SETUP.md exactly. Ask the student wherever a step says so; otherwise act. After each phase, say in one line what's done.

> **Honesty note:** StudyVault was built and tested on macOS. The Windows path uses the same tools with Windows-specific pieces (Task Scheduler, `.cmd` runners, a tray notification, Windows paths), but may hit problems a Mac never shows. When something fails, tell the student exactly what happened and fix it; don't work around it silently.

Windows facts that apply everywhere:
- Claude Code on Windows runs shell commands in **Git Bash** (from Git for Windows), so commands below are bash syntax; `~` is `C:\Users\<name>`. Use `cygpath -w <path>` when a Windows program needs a backslash path.
- Python lives at `~/miniconda3/envs/study/python.exe` (no `bin/`). Phase 1 creates a small `bin/python` shim so every command in the skills and docs (`~/miniconda3/envs/study/bin/python …`) works unchanged in Git Bash.
- Files contain emoji: Python must run in UTF-8 mode (`PYTHONUTF8=1`, set in Phase 1).
- The sync's Chrome profile lives in `%LOCALAPPDATA%\StudyVaultSync\chrome-profile` (macOS: `~/Library/Application Support/StudyVaultSync`). The tools pick the right one automatically.

---

## Phase 1: prerequisites (Windows 10 or 11)
1. Claude Code is installed and logged in with a Claude Pro/Max subscription; `git --version` works (Git for Windows).
2. **Google Chrome** installed (normally `C:\Program Files\Google\Chrome\Application\chrome.exe`).
3. **Obsidian** installed. If missing, ask the student to install it from https://obsidian.md.
4. **Miniconda** at `~/miniconda3` ("Just Me" install). Ask first, then:
   ```bash
   curl -L -o "$TEMP/miniconda.exe" https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
   cmd //c "$(cygpath -w "$TEMP/miniconda.exe") /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%USERPROFILE%\miniconda3"
   ~/miniconda3/Scripts/conda.exe create -y -n study python=3.12
   ~/miniconda3/envs/study/python.exe -m pip install pymupdf matplotlib numpy playwright pyyaml openpyxl
   ```
   (Playwright drives the installed Chrome via `channel="chrome"`: no `playwright install` needed.)
5. **UTF-8 mode + the `bin/python` shim:**
   ```bash
   setx PYTHONUTF8 1
   export PYTHONUTF8=1
   mkdir -p ~/miniconda3/envs/study/bin
   printf '#!/usr/bin/env bash\nexport PYTHONUTF8=1\nexec "$HOME/miniconda3/envs/study/python.exe" "$@"\n' > ~/miniconda3/envs/study/bin/python
   chmod +x ~/miniconda3/envs/study/bin/python
   ~/miniconda3/envs/study/bin/python -c "import fitz, playwright, yaml; print('python ok')"
   ```
6. Diagram library: same `curl` command as SETUP.md phase 1 step 5.
7. Don't install Haskell or Racket here (optional modules, Phase 6 of SETUP.md).

## Phase 2: interview
Same as SETUP.md. For dictation, Windows has **voice typing: Win+H** in any text box.

## Phase 3: copy the vault
Same as SETUP.md (`cp -R vault ~/StudyVault`, then the templates).

## Phase 4: personalize
Same as SETUP.md, plus these Windows edits in `~/StudyVault`:
- In every `.md` file (vault root, `.claude/`, `_modules/`): **⌘E → Ctrl+E**, **⌘Q** (quit Chrome) → "close the window", and in `CLAUDE.md`'s Voice section "macOS Dictation" → "Windows voice typing (Win+H)".
- `.claude/skills/homework/SKILL.md`, the photo row: replace the `sips -s format jpeg in.HEIC --out …` conversion with Python: `~/miniconda3/envs/study/bin/python -m pip install pillow pillow-heif` once, then `python -c "from pillow_heif import register_heif_opener; register_heif_opener(); from PIL import Image; Image.open('in.HEIC').save('Inbox/name.jpg')"`. Also "AirDrop and iCloud land in ~/Downloads" → "phone photos usually land in ~/Downloads or ~/Pictures".
- The Python runner for Obsidian is `tools/runpy.cmd` (already in the vault; the zsh `runpy` is for macOS).

## Phase 5: Classroom sign-in
Same commands as SETUP.md (`login.py`, `detect_sso.py`, `collect.py --list-classes`), run from `~/StudyVault/tools/sync` with `~/miniconda3/envs/study/bin/python`. Tell the student to **close** the sign-in Chrome window when Classroom and Google Docs both load (no ⌘Q on Windows). If `login.py` can't find Chrome, check `C:\Program Files\Google\Chrome\Application\chrome.exe` exists.

## Phase 6: build each class
Same as SETUP.md. Optional modules on Windows: each `INSTALL.md` has a **Windows** line (ghcup installs to `C:\ghcup`; copy the `.cmd` runners).

## Phase 7: Obsidian
Same as SETUP.md: the student installs the **Execute Code** community plugin, quits Obsidian, then from the kit folder:
```bash
~/miniconda3/envs/study/bin/python setup/fill_obsidian_settings.py
```
(It writes Windows paths, pointing Python at `tools\runpy.cmd`.) Reopen Obsidian; in `Running Code.md` press **Ctrl+E** for Reading view and **Run** the first Python block.

## Phase 8: first sync + daily schedule (Task Scheduler)
```bash
cd ~/StudyVault/tools/sync && ~/miniconda3/envs/study/bin/python collect.py
~/miniconda3/envs/study/bin/python todo.py render
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w ~/StudyVault/tools/sync/schedule_windows.ps1)" install
powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w ~/StudyVault/tools/sync/schedule_windows.ps1)" status
```
The task runs at logon and hourly with `pythonw.exe` (no window); the real sync happens once a day. Notifications (sign-in expired, new work) appear as Windows tray balloons.

## Phase 9: hand-off
Same as SETUP.md, with Windows wording: start the tutor with `cd ~/StudyVault && claude` (in Git Bash or PowerShell); when the school sign-in expires (~2 weeks) run `~/miniconda3/envs/study/bin/python ~/StudyVault/tools/sync/login.py` (Git Bash) or `%USERPROFILE%\miniconda3\envs\study\python.exe %USERPROFILE%\StudyVault\tools\sync\login.py` (Command Prompt).
