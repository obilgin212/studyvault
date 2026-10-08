# Code exercises in notes (shared by /teach, /homework, /exam-prep, /check)

> Haskell: the class's `Teaching Haskell.md` (only if the optional Haskell module is installed: `_modules/haskell/`) sets *how* to teach it. This file covers the block mechanics.

{{NAME}} runs code **inside Obsidian** with the Execute Code plugin (a Run button under each block, output inline). **The Run button only appears in Reading view** (⌘E toggles editing ↔ reading). Remind {{NAME}} the first time in a session. The plugin is configured to use `tools/runhs` → `tools/hsnote.py` (Haskell: **the note is one ghci session**) and `tools/runpy` (the `study` conda env + the `check` module). `Running Code.md` at the vault root is the reference example.

## Use code whenever running it would teach something
- **AP CS (Haskell):** every new idea gets a playground block, and every skill gets an exercise with tests.
- **Calc / Physics (Python):** numerical checks of derivations (NDER vs the rule you derived; simulate drag by small time steps vs the v(t) you derived), plots of f vs f′, and parameter exploration. The code *confirms* the math; it doesn't replace the derivation.
- **Rebuild from understanding** (from the Learning Profile): "write `sdq` without looking", "re-implement `zip` with pattern matching" are exercises with tests.

## Haskell: write it like Python; the note is one session (read top to bottom)
{{NAME}} doesn't want `ghci>` prompts or `main`. Just write code: `tools/hsnote.py` classifies each top-level item. **Definitions** (`f x = …`, guards, signatures, `data`/`import`, `xs = …`) are loaded for every block below. **Everything else is an expression** whose value is shown (several get a `▸` label). `:t`/`:i`/`:k` lines work, a later definition of a name replaces earlier ones, `:l file.hs` loads a file, and blocks above that don't compile are skipped with a ⚠️. Never write `ghci>` in notes you create.

**🧪 Playground:** some definitions, then a few expressions exploring them, in the same block or the next.

**✏️ Exercise + 🔒 Tests:** the exercise block comes first, and the tests block **below** it is a bare `runTests [...]` expression (`Check` gets imported automatically when `runTests` appears):

````markdown
```haskell
-- ✏️ Your code: replace `undefined`, then Run this block (it should say ✓ Loaded)
<name> :: <type signature: give it, so errors are readable>
<name> = undefined
```

```haskell
-- 🔒 Tests: Run this block to check your code above (don't edit)
runTests [ test "<expr as text>" (<expr>) <expected>
         , test ... ]
```
````

## Python: blocks run independently
Top-level fenced blocks only (the plugin can't see blocks inside callouts). The tests block goes **before** the exercise block, with a label that's unique within the note: `python {label: 'tests-<name>'}` containing `from check import test` then `test("label", lambda: f(x), expected, tol=1e-6)`, and the exercise block is `python {import: 'tests-<name>'}` with a `def f(...): ...` stub. The tests run *after* the exercise code finishes (atexit). Playground blocks can `plt.show()`, and the plot embeds inline.

## Rules
- **Haskell:** code blocks must be top-level (not inside callouts). Don't put the assigned homework functions in a note that also defines parallel practice versions with the same name, because later definitions shadow earlier ones.
- 3–5 visible tests: the typical case, then the edge cases the lesson is about (empty list, one element, a corner/discontinuity). Keep the **nastier edge cases hidden** for `check`.
- Test labels show the expression (`"firstOr 42 []"`), so a failure reads like a question.
- For assigned homework, exercises are **parallel problems**, never the assigned function itself. {{NAME}} writes the real homework in their own file.
- After {{NAME}} runs it: 🎉 → ask "explain why it works" (and give the hidden tests via `check`). ❌/💥 → ask for their reasoning first (Learning Profile), then point at the *first* failing line of output.

## Running it yourself
```bash
~/miniconda3/envs/study/bin/python tools/notecode.py list "<note>"
~/miniconda3/envs/study/bin/python tools/notecode.py run "<note>" <index|label> [--tests hidden.hs]
```
`run` builds exactly what the plugin builds (Haskell: via `tools/hsnote.py`, all Haskell blocks above; Python: label/import). Hidden tests with `--tests FILE`: for **Haskell**, FILE holds a `runTests [...]` expression appended to the given block (run them against the ✏️ exercise block's index); for **Python**, FILE is a tests block (`from check import test` …). Write FILE to the scratchpad, never the vault.
