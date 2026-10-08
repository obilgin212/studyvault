# Optional module: Racket

**Not installed by default.** Install it only when the student takes a class that uses Racket / DrRacket (e.g. *How to Design Programs*, *Picturing Programs*), and **ask first**.

1. Install Racket from https://racket-lang.org (the student runs the installer). Note the folder, e.g. `/Applications/Racket v8.x`.
2. macOS: `cp _modules/racket/tools/runrkt tools/ && chmod +x tools/runrkt`, then edit `tools/runrkt` so its path matches the installed Racket version. Windows: copy `_modules/racket/tools/runrkt.cmd` to `tools\` and fix its path (usually `C:\Program Files\Racket\racket.exe`).
3. Obsidian Execute Code settings (quit Obsidian first): `racketPath` = `<HOME>/StudyVault/tools/runrkt`, `racketInject` = `#lang racket` plus a newline plus `(require test-engine/racket-tests)`.
4. Test: a ```` ```racket ```` block with `(+ 1 2)` in a note, Reading view, **Run**.
