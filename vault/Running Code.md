# ▶️ Running code in your notes

Every code block in the vault has a **Run** button (Execute Code plugin). The output appears right under the block.

> [!important] The Run button only appears in **Reading view**
> Press **⌘E** to switch: edit your code in the normal (editing) view, press **⌘E**, click **Run**, then press **⌘E** again to keep editing.

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
