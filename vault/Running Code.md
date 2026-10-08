# ▶️ Running code in your notes

Every code block in the vault has a **Run** button (Execute Code plugin). The output appears right under the block.

> [!important] The Run button only appears in **Reading view**
> Press **⌘E** to switch: edit your code in the normal (editing) view, press **⌘E**, click **Run**, then press **⌘E** again to keep editing.

---

## Haskell: write it like Python, and every block is live

Just write code. No `main`, no prompts:
- **Definitions** (`doubleMe x = x + x`, type signatures, `data`, `import`, `nums = [1,2,3]`) are remembered for every block *below*.
- **Anything else is an expression**, and its value is shown under the block. Several expressions each get a `▸` label.
- `:t`, `:i`, `:k` work on their own line.
- **Redefine** a name further down and the new version wins from there on.
- **`:l path/to/file.hs`** pulls in a file's definitions (path relative to the note, or the vault).
- A block with only definitions shows `✓ Loaded: …`. If a block *above* doesn't compile, it's skipped with a ⚠️, and you still get your result.
- Learn You a Haskell's `ghci> …` examples still work if you paste them in as they are.

### 🧪 Try it
```haskell
doubleMe x = x + x
doubleUs x y = doubleMe x + doubleMe y

doubleMe 9
doubleUs 28 88 + doubleMe 123
:t doubleUs
```

```haskell
nums = [1, 2, 3]
map doubleMe nums
[ x * 10 | x <- nums, odd x ]
let y = 5 in y * y
```

```haskell
-- a later definition replaces the earlier one
doubleMe x = x * 2
doubleMe 9
```

### ✏️ Exercise: `firstOr`
Write `firstOr d xs`: return the first element of `xs`, or the default `d` if the list is empty. Use **pattern matching**, not `if`/`head`. *(Learn You a Haskell, "Syntax in Functions" → pattern matching.)*

```haskell
-- ✏️ Your code: replace `undefined`, then Run this block (it should say ✓ Loaded)
firstOr :: Int -> [Int] -> Int
firstOr = undefined
```

```haskell
-- 🔒 Tests: Run this block to check your code above (don't edit)
runTests [ test "firstOr 0 [5,6,7]" (firstOr 0 [5,6,7]) 5
         , test "firstOr 0 [9]"     (firstOr 0 [9])     9
         , test "firstOr 42 []"     (firstOr 42 [])     42 ]
```

> [!tip]- Stuck? (hint 1)
> You need one equation per *shape* of list: the empty list `[]`, and a list with a first element `(x:_)`.

When all the tests pass, type **`check`** to the tutor. It runs extra hidden edge cases, and if one fails, it asks you to explain your reasoning.

---

## Python (calc and physics)

Each Python block runs on its own. Exercises use a 🔒 tests block **above** your ✏️ code, linked by a label.

### ✏️ Exercise: symmetric difference quotient *(Calc §3.2, p.113)*
Write `sdq(f, a, h)`, the calculator's NDER: $\dfrac{f(a+h)-f(a-h)}{2h}$.

```python {label: 'tests-sdq'}
# 🔒 Tests (don't edit, don't run this block by itself)
from check import test
import math
test("sdq(x², 3)",        lambda: sdq(lambda x: x**2, 3, 1e-3), 6, tol=1e-6)
test("sdq(sin, 0)",       lambda: sdq(math.sin, 0, 1e-3), 1, tol=1e-6)
test("sdq(|x|, 0) ≠ f'(0)", lambda: sdq(abs, 0, 1e-3), 0)   # NDER is fooled at a corner!
```

```python {import: 'tests-sdq'}
# ✏️ Your code: then Run this block
def sdq(f, a, h):
    ...
```

### 🧪 Graphs show up inline
```python
import numpy as np, matplotlib.pyplot as plt
x = np.linspace(-2, 2, 200)
plt.plot(x, x**3, label="f(x) = x³")
plt.plot(x, 3*x**2, label="f'(x) = 3x²")
plt.axhline(0, color="gray", lw=0.5); plt.legend(); plt.show()
```
