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


## NEW: Repair V2 verified against original QuixBugs defects (2026-10-22)

The original demo and the first mutation prototype above are preserved for reproducibility.
**V2 is a separate experimental engine** with bounded AST-guided repair templates:
positional-argument swaps, numeric cursor shifts, collection-variable substitutions,
numeric-return invariants, and boolean/arithmetic/comparison-operator changes.
These are generic syntactic transformations. It is still not an LLM, production
autonomous code agent, or a substitute for a human engineer.

### Meaningful external benchmark

QuixBugs is a real published research benchmark: https://github.com/jkoppel/QuixBugs
We pin source commit \`4257f44b0ff1181dedaedee6a447e133219fcebf\` and use
**the original flawed files in \`python_programs/\`**. We did not create or
inject any errors into these six benchmark samples. Public regression and
separate holdout tests are maintained in \`benchmark_specs/\`. Only public
regression tests are used while selecting a patch. After repair, we also compare
the resulting function's AST with the benchmark's supplied correct reference
implementation from \`correct_python_programs/\`. No reference source is used
to generate candidate fixes.

| Original defect | Result | Independent holdout | Exact semantic AST match with reference |
| --- | --- | --- | --- |
| \`gcd\`: swapped recursion arguments | **PASS** | 9 passed | Yes |
| \`bucketsort\`: wrong enumerated collection | **PASS** | 5 passed | Yes |
| \`is_valid_parenthesization\`: missing final invariant | **PASS** | 8 passed | Yes |
| \`find_in_sorted\`: cursor fails to advance | **PASS** | 7 passed | Yes |
| \`powerset\`: missing subsets | **NO FIX FOUND** | not evaluated | No |
| \`reverse_linked_list\`: missing pointer update | **NO FIX FOUND** | not evaluated | No |

**4/6 genuine, pre-existing benchmark defects repaired** in the predeclared
six-case experiment; **4/4 repairs match upstream's reference functions** at
the AST level. Original source files stayed untouched. These six cases were
*selected deliberately to evaluate the supported classes of transformations
and include negative controls*. They are NOT a random or representative sample
of QuixBugs or real software, so 4/6 must not be described as a generalized
66.7% success rate.

### Reproduce it without an API key

Python 3.10+, Git and \`pytest==9.1.1\` are required.

\`\`\`bash
python -m pip install pytest==9.1.1
python experimental/run_quixbugs.py --out benchmark-results/run1 --require-successes 4 --max-candidates 80
\`\`\`

The harness clones the original benchmark at its pinned revision, uses
\`repair_v2.py\` on six isolated project copies, then writes:
\`BENCHMARK_AUDIT.json\`, per-case \`FINAL_AUDIT.json\`, working code copies,
and \`VERIFIED_REPAIR.patch\` for only accepted patches.
The GitHub Actions workflow \`quixbugs-original-defects.yml\` independently
reruns these checks on an ephemeral GitHub runner and publishes JSON audit
artifacts. Existing work remains in its own folder; no original files are
silently overwritten.

### Requirements for using V2 on another project

\`\`\`bash
python experimental/repair_v2.py --project /path/to/trusted-project --target module.py --out /tmp/zorro-trial
\`\`\`

The project must have \`tests/\` and \`holdout/\` with meaningful pytest tests.
Use it **only on trusted local projects** and review its diffs. The runner
executes project code and offers *no malicious-code sandbox*. It cannot safely
test arbitrary downloaded repositories on your personal laptop.
A passing test suite is evidence, not a proof of secure production behavior.
