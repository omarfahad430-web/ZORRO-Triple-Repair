# ZORRO Open Repair — experimental test-driven fixer

> **Prototype, not a general autonomous coding agent.** This component is separate from the original `multi_engine.py` teaching demo. It can try a small set of single-token Python operator substitutions in an existing local project, then use automated tests to accept or reject them.

## Quick start

Prerequisites: Python 3.10+ and pytest 9.x. Run only on **trusted, disposable** projects whose tests you are willing to execute. A virtual environment is **not** a security sandbox.

```bash
python -m pip install pytest==9.1.1
python experimental/open_repair.py \
  --project experimental/fixtures/cart_rules \
  --target cart_rules.py \
  --out trial-output/cart \
  --max-rounds 5
```

On Windows PowerShell, use the same command on one line instead of the backslashes.

Outputs live outside the input project: a complete `FINAL_AUDIT.json`, an isolated `working_copy/`, and `VERIFIED_REPAIR.patch` **only on verified success**. The original input project is preserved. Never reuse an existing output directory.

## What it does

1. Run existing `tests/` in a working copy and record failing assertions.
2. Generate deterministic candidates for selected operators (comparisons, arithmetic and booleans) in the specified Python file; no language model or external API is used.
3. Test one candidate at a time, restore the working copy after each trial and keep only an improvement that does not reduce passing tests.
4. Once all public regression tests pass, run separate `holdout/` tests that were not used to select candidate changes.
5. Record the full outcome, counts, changes and hashes.

The holdout tests are **separate**, not secret. Passing a finite test set is not a formal correctness or security guarantee. Source code, dependencies, and test assertions should be reviewed before real use.

## Reproducible fixtures

| Fixture | Before | After | Extra holdout | Outcome |
| --- | --- | --- | --- | --- |
| `fixtures/cart_rules` (three deliberately seeded bugs) | 6 failed, 6 passed | 12 passed | 18 passed | PASS |
| `fixtures/negative_control` (complex string normalization) | 1 failed, 1 passed | no repair | not run | NO_FIX_FOUND |

In a separate local test on 2026-10-22, a deliberately injected `==` versus `!=` regression in a copy of the real `benhodgson/baluhn` open-source module (commit `cf910c680cdaea97f3af40376e5f08c9211327a6`) was repaired. Six public tests and twelve separate holdout tests passed. This was a **seeded regression**, not a discovered production defect. The upstream repository was not modified.

## Limits and safety

- Supports only selected **single-token** operator changes. It cannot reliably fix arbitrary code or multi-line algorithms.
- Needs pre-existing, meaningful pytest suites in `tests/` and `holdout/`. Weak tests produce weak evidence.
- **Executes Python test code.** Do not run untrusted repositories. It has no isolation against malicious tests, local file modifications or network access. If you must assess unknown code, use a properly isolated environment outside this tool.
- Does **not** perform security certification, broad vulnerability scanning, or autonomous repository repair.
- A repair can overfit its tests. Always review the patch and validate it in a separate environment.
- Uses existing project files for local analysis. No remote model or AI API calls.

## CI

`.github/workflows/experimental-open-repair.yml` verifies the positive fixture, independent holdout, source immutability and a negative-control failure. It doesn't claim to validate arbitrary real-world projects.

The original `run_demo.py` and `multi_engine.py` are unchanged by this experimental addition.
