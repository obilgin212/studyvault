"""Tiny test helper for Python exercise blocks in Obsidian (Execute Code plugin).

Tests block:   from check import test
               test("f(2)", lambda: f(2), 4)          # exact
               test("v(1.0)", lambda: v(1.0), 9.8, tol=1e-3)   # numeric, relative tolerance
Tests run automatically after your code finishes, so the tests block can be imported *before* your code.
"""
import atexit
import math

_tests = []


def test(label, thunk, expected, tol=None):
    _tests.append((label, thunk, expected, tol))


def _close(a, b, tol):
    try:
        if tol is not None:
            if isinstance(a, (list, tuple)):
                return len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
            return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
        return a == b
    except TypeError:
        return False


@atexit.register
def _run():
    if not _tests:
        return
    passed = 0
    for label, thunk, expected, tol in _tests:
        try:
            got = thunk()
        except Exception as e:  # show the crash, keep going
            print(f"💥 {label}\n     crashed:  {type(e).__name__}: {e}")
            continue
        if _close(got, expected, tol):
            passed += 1
            print(f"✅ {label} = {expected!r}")
        else:
            print(f"❌ {label}\n     expected: {expected!r}\n     got:      {got!r}")
    n = len(_tests)
    print()
    print(f"🎉 All {n} tests passed. Now explain *why* it works." if passed == n
          else f"{passed}/{n} passed. Read the first ❌/💥 and reason about it before changing code.")
