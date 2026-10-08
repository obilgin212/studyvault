# Optional module: Haskell

**Not installed by default.** Install it only when the student takes a class that uses Haskell, e.g. their Classroom or syllabus mentions Haskell, *Learn You a Haskell*, `ghci`, or `.hs` files. The tutor can do this any time: the student says "set up Haskell", or the tutor notices a Haskell class during setup or `/add-course` and **asks first**.

What it adds: Haskell code blocks that run inside Obsidian notes, written like Python (no `ghci>`, no `main`; each note is one session), test-backed exercises checked by `check`, and a "how to teach me Haskell" note for the class.

## Steps (Claude Code, from `~/StudyVault`)
1. **Install GHC** (ask the student first; it downloads ~1 GB):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | BOOTSTRAP_HASKELL_NONINTERACTIVE=1 sh
   ~/.ghcup/bin/ghc --version
   ```
2. **Copy the runner into the vault:**
   ```bash
   cp _modules/haskell/tools/hsnote.py _modules/haskell/tools/runhs tools/ && mkdir -p tools/hs && cp _modules/haskell/tools/hs/Check.hs tools/hs/ && chmod +x tools/runhs
   ```
3. **Obsidian Execute Code settings** (quit Obsidian first): set `runghcPath` = `<HOME>/StudyVault/tools/runhs` (Windows: `tools\runhs.cmd`), `ghcPath`/`ghciPath` = ghcup's `ghc`/`ghci` (macOS `~/.ghcup/bin/`, Windows `C:\ghcup\bin\ghc.exe` / `ghci.exe`), `haskellInject` = `-- HSNOTE @vault_path @note_path`, `haskellInteractive` = false in `.obsidian/plugins/execute-code/data.json`. (Re-running the kit's `setup/fill_obsidian_settings.py` does this automatically once `tools/hsnote.py` exists.)

**Windows:** step 1 is instead (PowerShell, not as admin): `Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; & ([ScriptBlock]::Create((Invoke-WebRequest https://www.haskell.org/ghcup/sh/bootstrap-haskell.ps1 -UseBasicParsing))) -Interactive:$false` (installs to `C:\ghcup`); in step 2 also copy `_modules/haskell/tools/runhs.cmd` to `tools/`.
4. **Teaching note:** copy `_modules/haskell/Teaching Haskell.md` into the Haskell class's folder (`Courses/<class>/`), and fill `{{CLASS_SITE}}` (the class website, or delete that line) and `{{HASKELL_HOMEWORK_FOLDER}}` (where the student keeps their `.hs` homework). Optionally save *Learn You a Haskell* chapters into that class's `_sources/lyah/` (one Markdown file per chapter).
5. **Tell the tutor:** add the section in `_modules/haskell/CLAUDE-section.md` to `CLAUDE.md` (before "## Two ways through an assignment"), with `<class>` replaced by the folder name.
6. **Demo note:** copy `_modules/haskell/Running Haskell.md` to the vault root.
7. **Test:** `~/miniconda3/envs/study/bin/python tools/notecode.py list "Running Haskell.md"`, then run its first Haskell block (`notecode.py run "Running Haskell.md" 0`). In Obsidian, open the note in Reading view (⌘E) and press **Run**.
