#!/usr/bin/env python3
"""ZORRO OPEN REPAIR POC: bounded, test-driven one-token Python repairs.
Works on a user-supplied local Python project, not on the pinned ZORRO lab.
NOTICE: pytest executes project code; use only on trusted disposable projects.
"""
from __future__ import annotations
import argparse
import ast
import difflib
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import tokenize

FLIPS = {
    ">": ("<", ">=", "<="),
    "<": (">", "<=", ">="),
    ">=": ("<=", ">", "<"),
    "<=": (">=", "<", ">"),
    "==": ("!=",),
    "!=": ("==",),
    "+": ("-", "*"),
    "-": ("+",),
    "*": ("+",),
    "and": ("or",),
    "or": ("and",),
    "True": ("False",),
    "False": ("True",),
}
SKIP = shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "runs")
def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def test(work: pathlib.Path, subfolder: str) -> dict:
    start = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "--tb=no",
             "--disable-warnings", "-p", "no:cacheprovider", subfolder],
            cwd=work, env=env, text=True, capture_output=True, timeout=35)
        out = proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired:
        return {"valid": False, "exit": "TIMEOUT", "passed": 0, "failed": 9999,
                "tail": "pytest exceeded 35 seconds"}
    # Match summary counts but reject collection errors.
    summary = out.strip().splitlines()[-1] if out.strip() else "(no output)"
    p = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    errors = re.search(r"(\d+) errors?", summary)
    passed = int(p.group(1)) if p else 0
    failed = int(f.group(1)) if f else 0
    valid = proc.returncode in (0, 1) and passed + failed > 0 and not errors
    if proc.returncode == 1 and failed == 0:
        valid = False
    return {"valid": bool(valid), "exit": proc.returncode,
            "passed": passed, "failed": failed, "summary": summary,
            "seconds": round(time.monotonic()-start, 3), "tail": out[-1200:]}

def mutants(source: str):
    """Yield unique single-token valid Python source changes (not known fixes)."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    seen = set()
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        old = tok.string
        if old not in FLIPS or tok.type not in (tokenize.OP, tokenize.NAME):
            continue
        if tok.type == tokenize.NAME and old not in ("and", "or", "True", "False"):
            continue
        start = offsets[tok.start[0]-1] + tok.start[1]
        end = offsets[tok.end[0]-1] + tok.end[1]
        if source[start:end] != old:
            continue
        for value in FLIPS[old]:
            changed = source[:start] + value + source[end:]
            try:
                ast.parse(changed)
            except SyntaxError:
                continue
            if changed == source or changed in seen:
                continue
            seen.add(changed)
            yield {"line": tok.start[0], "from": old, "to": value,
                   "code": changed}

def do_run(project: pathlib.Path, target: pathlib.Path, out: pathlib.Path, rounds: int):
    project, out = project.resolve(), out.resolve()
    if out == project or project in out.parents:
        raise ValueError("Output directory must be outside the source project")
    if out.exists():
        raise ValueError("Output directory already exists; refusing overwrite")
    if not project.is_dir():
        raise ValueError("Project directory does not exist")
    if target.is_absolute() or ".." in target.parts or target.suffix != ".py":
        raise ValueError("Target must be a relative .py file")
    source_path = project / target
    if source_path.is_symlink() or not source_path.resolve().is_relative_to(project):
        raise ValueError("Target must be a regular file within the source project")
    if not source_path.is_file() or not (project/"tests").is_dir() or not (project/"holdout").is_dir():
        raise ValueError("Expected source .py, tests/, and holdout/ directory")
    original_bytes = source_path.read_bytes()
    original = original_bytes.decode("utf-8")
    ast.parse(original)
    out.mkdir(parents=True)
    work = out / "working_copy"
    shutil.copytree(project, work, ignore=SKIP)
    source_file = work / target
    audit = {
        "product": "ZORRO Open Repair POC, experimental",
        "scope": "single-token mutations guided by existing pytest, NOT universal code repair",
        "input_project": str(project), "target": str(target),
        "original_sha256": digest(original_bytes), "project_original_not_edited": True,
        "rounds": [], "candidate_evaluations": 0, "rejected_candidates": 0,
        "rollback_verified_count": 0,
    }
    current = original
    baseline = test(work, "tests")
    audit["baseline"] = baseline
    if not baseline["valid"] or baseline["failed"] == 0:
        audit["outcome"] = "BASELINE_NOT_A_VALID_FAILING_SUITE"
    else:
        audit["outcome"] = "NO_FIX_FOUND"
        for step in range(1, rounds+1):
            alternatives = []
            for m in mutants(current):
                source_file.write_text(m["code"], encoding="utf-8")
                evaluation = test(work, "tests")
                source_file.write_text(current, encoding="utf-8")
                audit["candidate_evaluations"] += 1
                if source_file.read_text(encoding="utf-8") != current:
                    raise RuntimeError("Candidate rollback integrity violation")
                audit["rollback_verified_count"] += 1
                better = (evaluation["valid"] and evaluation["failed"] < baseline["failed"]
                          and evaluation["passed"] >= baseline["passed"])
                if better:
                    alternatives.append((m, evaluation))
                else:
                    audit["rejected_candidates"] += 1
            if not alternatives:
                audit["rounds"].append({"round": step, "outcome": "NO_IMPROVEMENT"})
                break
            choice, verified = min(alternatives, key=lambda z: (
                z[1]["failed"], -z[1]["passed"], z[0]["line"]))
            audit["rounds"].append({
                "round": step, "mutation": {k: v for k, v in choice.items() if k != "code"},
                "test_before": baseline["summary"], "test_after": verified["summary"]})
            current = choice["code"]
            source_file.write_text(current, encoding="utf-8")
            baseline = verified
            if baseline["failed"] == 0:
                public = test(work, "tests")
                holdout = test(work, "holdout")
                audit["final_public"] = public
                audit["independent_holdout"] = holdout
                if public["valid"] and public["failed"] == 0 and holdout["valid"] and holdout["failed"] == 0:
                    audit["outcome"] = "PASS_WITH_HOLDOUT"
                    break
                audit["outcome"] = "HOLDOUT_REJECTED"
                source_file.write_text(original, encoding="utf-8")
                break
    if source_path.read_bytes() != original_bytes:
        raise RuntimeError("ERROR: input project changed unexpectedly")
    audit["original_still_sha256"] = digest(source_path.read_bytes())
    audit["working_sha256"] = digest(source_file.read_bytes())
    if audit["outcome"] == "PASS_WITH_HOLDOUT":
        patch = "".join(difflib.unified_diff(original.splitlines(True),
                 current.splitlines(True), fromfile="a/"+str(target), tofile="b/"+str(target)))
        (out/"VERIFIED_REPAIR.patch").write_text(patch, encoding="utf-8")
        audit["patch_sha256"] = digest(patch.encode())
    audit["total_changes"] = len([r for r in audit["rounds"] if "mutation" in r])
    (out/"FINAL_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": audit["outcome"], "baseline": audit["baseline"]["summary"],
        "final_public": audit.get("final_public", {}).get("summary"),
        "final_holdout": audit.get("independent_holdout", {}).get("summary"),
        "changes": audit["total_changes"],
        "candidates_tested": audit["candidate_evaluations"],
        "rejected_candidates": audit["rejected_candidates"],
        "rollbacks_verified": audit["rollback_verified_count"],
        "original_unchanged": audit["original_sha256"] == audit["original_still_sha256"],
        "audit": str(out/"FINAL_AUDIT.json")
    }, indent=2), flush=True)
    return audit["outcome"] == "PASS_WITH_HOLDOUT"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=pathlib.Path)
    parser.add_argument("--target", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--max-rounds", type=int, default=5)
    x = parser.parse_args()
    raise SystemExit(0 if do_run(x.project, x.target, x.out, x.max_rounds) else 1)
