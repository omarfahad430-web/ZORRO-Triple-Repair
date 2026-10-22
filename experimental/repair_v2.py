#!/usr/bin/env python3
"""ZORRO Repair V2: bounded test-driven search on trusted local Python projects.

Experimental: changes ONE Python file inside a copy, tests each candidate,
checks withheld regression tests, and emits an auditable patch on success.
Never run against untrusted repositories: pytest runs executable project code.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tokenize

OPERATORS = {
    ">": ("<", ">=", "<="), "<": (">", "<=", ">="),
    ">=": ("<=", ">", "<"), "<=": (">=", "<", ">"),
    "==": ("!=",), "!=": ("==",),
    "+": ("-", "*"), "-": ("+",), "*": ("+",),
    "and": ("or",), "or": ("and",),
    "True": ("False",), "False": ("True",),
}

def hexdigest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def span(source: str, node: ast.AST) -> tuple[int, int]:
    """Convert AST UTF-8 byte columns to correct Unicode string offsets."""
    lines = source.splitlines(keepends=True)
    def offset(lineno: int, column: int) -> int:
        prefix = "".join(lines[:lineno-1])
        partial = lines[lineno-1].encode("utf-8")[:column].decode("utf-8")
        return len(prefix) + len(partial)
    return offset(node.lineno, node.col_offset), offset(node.end_lineno, node.end_col_offset)

def patch(source: str, edits: list[tuple[int, int, str]]) -> str:
    edits = sorted(edits, key=lambda x: x[0], reverse=True)
    for index, (a, b, replacement) in enumerate(edits):
        if not 0 <= a <= b <= len(source):
            raise ValueError("Invalid candidate span")
        if index and b > edits[index-1][0]:
            raise ValueError("Overlapping spans")
        source = source[:a] + replacement + source[b:]
    return source

def candidates(source: str):
    """General mutation templates, never a repository-specific reference patch."""
    seen = set()
    tree = ast.parse(source)
    def emit(kind, line, detail, modified):
        if modified == source or modified in seen:
            return None
        try:
            ast.parse(modified)
        except SyntaxError:
            return None
        seen.add(modified)
        return {"kind": kind, "line": line, "detail": detail, "code": modified}

    # Common bug: swapped positional arguments to a two-argument function.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and len(node.args) == 2 and not node.keywords:
            a, b = node.args
            left, right = span(source, a), span(source, b)
            old_a, old_b = source[left[0]:left[1]], source[right[0]:right[1]]
            if old_a == old_b:
                continue
            item = emit("swap_args", node.lineno, "swap two call arguments",
                        patch(source, [(left[0], left[1], old_b),
                                       (right[0], right[1], old_a)]))
            if item:
                yield item

    # Common bug: recursive calls fail to advance a cursor by one.
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and len(node.args) >= 1):
            for arg in node.args:
                if not isinstance(arg, ast.Name):
                    continue
                a, b = span(source, arg)
                for delta in ("+ 1", "- 1"):
                    item = emit("cursor_shift", node.lineno,
                                f"{arg.id} -> {arg.id} {delta}",
                                patch(source, [(a, b, f"{arg.id} {delta}")]))
                    if item:
                        yield item

    # Common bug: enumerate uses the wrong local collection.
    assigned = sorted({target.id for node in ast.walk(tree)
                       if isinstance(node, (ast.Assign, ast.AnnAssign))
                       for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
                       if isinstance(target, ast.Name)})
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "enumerate" and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)):
            old = node.args[0]
            a, b = span(source, old)
            for replacement in assigned:
                if replacement == old.id:
                    continue
                item = emit("collection_name", node.lineno,
                            f"enumerate({old.id}) -> enumerate({replacement})",
                            patch(source, [(a, b, replacement)]))
                if item:
                    yield item

    # Common bug: function exits True without verifying a numeric invariant.
    numeric_locals = sorted({t.id for n in ast.walk(tree)
                       if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                       and type(n.value.value) is int
                       for t in n.targets if isinstance(t, ast.Name)})
    for node in ast.walk(tree):
        if (isinstance(node, ast.Return) and isinstance(node.value, ast.Constant)
                and node.value.value is True):
            a, b = span(source, node.value)
            for var in numeric_locals:
                for op in ("==", "!="):
                    item = emit("return_invariant", node.lineno,
                                f"return {var} {op} 0",
                                patch(source, [(a, b, f"{var} {op} 0")]))
                    if item:
                        yield item

    # Common bug: a one-token arithmetic / logical / boundary condition error.
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            old = token.string
            if old not in OPERATORS or token.type not in (tokenize.OP, tokenize.NAME):
                continue
            if token.type == tokenize.NAME and old not in ("and", "or", "True", "False"):
                continue
            a, b = offsets[token.start[0]-1] + token.start[1], offsets[token.end[0]-1] + token.end[1]
            if source[a:b] != old:
                continue
            for replacement in OPERATORS[old]:
                item = emit("operator", token.start[0], f"{old} -> {replacement}",
                            patch(source, [(a, b, replacement)]))
                if item:
                    yield item
    except tokenize.TokenError:
        pass

def run_tests(folder: Path, suite: str, timeout: int) -> dict:
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    start = time.monotonic()
    try:
        cp = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "--tb=no",
             "--disable-warnings", "-p", "no:cacheprovider", suite],
            cwd=folder, env=env, capture_output=True, text=True,
            timeout=timeout)
        output = (cp.stdout + "\n" + cp.stderr).strip()
        # Parse only the last pytest summary to avoid counting traceback lines.
        summary = next((s.strip() for s in reversed(output.splitlines())
                        if re.search(r"\d+ (?:failed|passed)", s)), "(none)")
        failed_match = re.search(r"(\d+) failed\b", summary)
        passed_match = re.search(r"(\d+) passed\b", summary)
        failed = int(failed_match.group(1)) if failed_match else 0
        passed = int(passed_match.group(1)) if passed_match else 0
        valid = cp.returncode in (0, 1) and passed + failed > 0
        if cp.returncode == 0 and (failed or not passed):
            valid = False
        if cp.returncode == 1 and failed == 0:
            valid = False
        return {"valid": valid, "passed": passed, "failed": failed,
                "exit_code": cp.returncode, "summary": summary,
                "seconds": round(time.monotonic()-start, 3),
                "tail": output[-1200:]}
    except subprocess.TimeoutExpired:
        return {"valid": False, "passed": 0, "failed": 0,
                "exit_code": "TIMEOUT", "summary": f"timeout after {timeout}s"}

def safe_input(project: Path, relative_file: Path, out: Path):
    project, out = project.resolve(), out.resolve()
    if not project.is_dir() or project == out or project in out.parents or out.exists():
        raise ValueError("Invalid project/output paths. Output must be a new directory outside input.")
    if relative_file.is_absolute() or ".." in relative_file.parts or relative_file.suffix != ".py":
        raise ValueError("Target must be a relative Python source file")
    target = project / relative_file
    if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(project):
        raise ValueError("Target file is absent or unsafe")
    for folder in ("tests", "holdout"):
        if not (project/folder).is_dir():
            raise ValueError(f"Required {folder}/ directory is missing")
    # Do not silently follow symlinks pointing outside the project in a copy.
    for entry in project.rglob("*"):
        if entry.is_symlink():
            raise ValueError(f"Symlinks not allowed: {entry}")
    return project, target, out

def engine(project: Path, relative_file: Path, out: Path,
           max_rounds: int = 4, max_candidates: int = 120,
           timeout: int = 20) -> dict:
    project, target, out = safe_input(project, relative_file, out)
    if not (1 <= max_rounds <= 10 and 1 <= max_candidates <= 2000 and 1 <= timeout <= 120):
        raise ValueError("Invalid bounded resource settings")
    original_bytes = target.read_bytes()
    original = original_bytes.decode("utf-8")
    ast.parse(original)
    out.mkdir(parents=True)
    work = out/"working_copy"
    shutil.copytree(project, work, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", ".pytest_cache", "runs", "node_modules"))
    candidate_path = work/relative_file
    audit = {"schema": 2, "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "project": str(project), "target": str(relative_file),
             "strategy": "deterministic AST/text mutation, no API or LLM",
             "original_sha256": hexdigest(original_bytes),
             "max_rounds": max_rounds, "max_candidates": max_candidates,
             "mutations_tested": 0, "rollbacks_verified": 0,
             "tested": [], "accepted": []}
    initial = run_tests(work, "tests", timeout)
    audit["baseline"] = initial
    current = original
    baseline = initial
    audit["status"] = "NO_VALID_FAILING_TESTS" if not initial["valid"] or not initial["failed"] else "NO_FIX_FOUND"
    if audit["status"] == "NO_FIX_FOUND":
        for round_no in range(1, max_rounds+1):
            winners = []
            for cand in candidates(current):
                if audit["mutations_tested"] >= max_candidates:
                    audit["limit_hit"] = "max_candidates"
                    break
                try:
                    candidate_path.write_text(cand["code"], encoding="utf-8")
                    checked = run_tests(work, "tests", timeout)
                finally:
                    candidate_path.write_text(current, encoding="utf-8")
                if candidate_path.read_text("utf-8") != current:
                    raise RuntimeError("Automatic candidate rollback failed")
                audit["mutations_tested"] += 1
                audit["rollbacks_verified"] += 1
                accepted = (checked["valid"]
                            and checked["passed"] > baseline["passed"]
                            and checked["failed"] < baseline["failed"]
                            and checked["passed"]+checked["failed"] ==
                                baseline["passed"]+baseline["failed"])
                audit["tested"].append({"round": round_no,
                        "kind": cand["kind"], "line": cand["line"],
                        "detail": cand["detail"], "accepted": accepted,
                        "passed": checked["passed"], "failed": checked["failed"],
                        "test_valid": checked["valid"]})
                if accepted:
                    winners.append((cand, checked))
            if not winners:
                break
            chosen, judged = min(winners, key=lambda x: (
                x[1]["failed"], -x[1]["passed"], x[0]["line"]))
            current = chosen["code"]
            baseline = judged
            candidate_path.write_text(current, encoding="utf-8")
            audit["accepted"].append({"round": round_no, "kind": chosen["kind"],
                                      "line": chosen["line"], "detail": chosen["detail"],
                                      "public": judged["summary"]})
            if baseline["failed"] == 0:
                # The holdout is not used to select candidates; rerun public first.
                public = run_tests(work, "tests", timeout)
                holdout = run_tests(work, "holdout", timeout)
                audit["final_public"] = public
                audit["final_holdout"] = holdout
                if public["valid"] and public["failed"] == 0 and holdout["valid"] and holdout["failed"] == 0:
                    audit["status"] = "PASS_WITH_HOLDOUT"
                else:
                    audit["status"] = "HOLDOUT_REJECTED"
                break
            if audit["mutations_tested"] >= max_candidates:
                break
    # Any unsuccessful experiment restores the working copy to the same source
    # as the input, including failures after partially improved public tests.
    if audit["status"] != "PASS_WITH_HOLDOUT":
        candidate_path.write_text(original, encoding="utf-8")
    if target.read_bytes() != original_bytes:
        raise RuntimeError("Original target modified: abort")
    audit["original_preserved"] = True
    audit["working_sha256"] = hexdigest(candidate_path.read_bytes())
    if audit["status"] == "PASS_WITH_HOLDOUT":
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True), current.splitlines(keepends=True),
            fromfile=f"a/{relative_file.as_posix()}", tofile=f"b/{relative_file.as_posix()}"))
        (out/"VERIFIED_REPAIR.patch").write_text(diff, encoding="utf-8")
        audit["patch_sha256"] = hexdigest(diff.encode("utf-8"))
    (out/"FINAL_AUDIT.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "status": audit["status"],
        "baseline": initial["summary"],
        "public": audit.get("final_public", {}).get("summary"),
        "holdout": audit.get("final_holdout", {}).get("summary"),
        "accepted": audit["accepted"],
        "candidates_tested": audit["mutations_tested"],
        "rollbacks_verified": audit["rollbacks_verified"],
        "original_preserved": audit["original_preserved"],
        "audit": str(out/"FINAL_AUDIT.json")
    }, indent=2), flush=True)
    return audit

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--target", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--max-rounds", type=int, default=4)
    p.add_argument("--max-candidates", type=int, default=120)
    p.add_argument("--timeout", type=int, default=20)
    args = p.parse_args()
    report = engine(args.project, args.target, args.out,
                    args.max_rounds, args.max_candidates, args.timeout)
    sys.exit(0 if report["status"] == "PASS_WITH_HOLDOUT" else 1)
