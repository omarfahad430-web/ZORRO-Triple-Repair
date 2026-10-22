#!/usr/bin/env python3
"""Reproduce ZORRO against ORIGINAL published QuixBugs Python defects.

No faults are seeded or patched ahead of time. Tests are written separately
and selected cases are declared up front. Never run unknown repositories
outside an isolated development environment.
"""
import argparse
import ast
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

UPSTREAM = "https://github.com/jkoppel/QuixBugs.git"
PIN = "4257f44b0ff1181dedaedee6a447e133219fcebf"
CASES = ("gcd", "bucketsort", "is_valid_parenthesization", "find_in_sorted",
         "powerset", "reverse_linked_list")
HERE = pathlib.Path(__file__).resolve().parent

def git(*argv):
    result = subprocess.run(["git", *map(str, argv)], text=True,
                            capture_output=True, check=True, timeout=60)
    return result.stdout.strip()

def execute(checkout: pathlib.Path | None, out: pathlib.Path,
            require_successes: int, max_candidates: int) -> dict:
    out = out.resolve()
    if out.exists():
        raise ValueError("Refusing to overwrite output directory")
    out.mkdir(parents=True)
    if checkout is None:
        checkout = out/"upstream_quixbugs"
        git("clone", UPSTREAM, checkout)
        git("-C", checkout, "checkout", "--detach", PIN)
    checkout = checkout.resolve()
    head = git("-C", checkout, "rev-parse", "HEAD")
    if head != PIN:
        raise ValueError(f"Expected pinned QuixBugs commit {PIN}, got {head}")
    sha = lambda data: hashlib.sha256(data).hexdigest()
    rows = []
    started = time.monotonic()
    for name in CASES:
        spec = HERE/"benchmark_specs"/name
        original = checkout/"python_programs"/f"{name}.py"
        if not original.is_file():
            raise RuntimeError(f"Original upstream source missing: {original}")
        project = out/"projects"/name
        project.mkdir(parents=True)
        shutil.copy2(original, project/f"{name}.py")
        shutil.copytree(spec/"tests", project/"tests")
        shutil.copytree(spec/"holdout", project/"holdout")
        source_bytes = original.read_bytes()
        correct = checkout/"correct_python_programs"/f"{name}.py"
        def first_function(text):
            return next((ast.dump(node, include_attributes=False)
                        for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef)), None)
        golden_ast = first_function(correct.read_text("utf-8")) if correct.is_file() else None
        cmd = [sys.executable, "-B", str(HERE/"repair_v2.py"),
               "--project", str(project), "--target", f"{name}.py",
               "--out", str(out/"results"/name),
               "--max-rounds", "3", "--max-candidates", str(max_candidates),
               "--timeout", "8"]
        t0 = time.monotonic()
        cp = subprocess.run(cmd, text=True, capture_output=True, timeout=900)
        audit_path = out/"results"/name/"FINAL_AUDIT.json"
        report = json.loads(audit_path.read_text("utf-8")) if audit_path.is_file() else {}
        patched_path = out/"results"/name/"working_copy"/f"{name}.py"
        reference_match = (
            report.get("status") == "PASS_WITH_HOLDOUT"
            and golden_ast is not None and patched_path.is_file()
            and first_function(patched_path.read_text("utf-8")) == golden_ast
        )
        row = {
            "name": name, "upstream_file": f"python_programs/{name}.py",
            "upstream_source_sha256": sha(source_bytes),
            "source_preserved": (project/f"{name}.py").read_bytes() == source_bytes,
            "reference_implementation_ast_match": reference_match,
            "exit_code": cp.returncode, "status": report.get("status", "ERROR"),
            "baseline": report.get("baseline", {}).get("summary"),
            "final_public": report.get("final_public", {}).get("summary"),
            "final_holdout": report.get("final_holdout", {}).get("summary"),
            "candidates_tested": report.get("mutations_tested", 0),
            "successful_patches": len(report.get("accepted", [])),
            "seconds": round(time.monotonic()-t0,2),
            "log_tail": (cp.stdout + cp.stderr)[-800:],
        }
        rows.append(row)
        print(f"{name}: {row['status']} from {row['baseline']} => "
              f"{row['final_public']} / holdout {row['final_holdout']} "
              f"in {row['seconds']}s", flush=True)
    passed = sum(r["status"] == "PASS_WITH_HOLDOUT" for r in rows)
    summary = {
        "schema": 1,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "upstream": UPSTREAM, "upstream_commit": PIN,
        "cases_predeclared": list(CASES), "no_seeded_bugs": True,
        "successes": passed, "attempted": len(rows),
        "golden_reference_matches": sum(r["reference_implementation_ast_match"] for r in rows),
        "failures": len(rows)-passed,
        "passed_required_threshold": passed >= require_successes,
        "all_original_sources_preserved": all(r["source_preserved"] for r in rows),
        "elapsed_s": round(time.monotonic()-started,2),
        "results": rows,
    }
    (out/"BENCHMARK_AUDIT.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"successes": passed, "attempted": len(rows),
          "minimum_required": require_successes,
          "originals_preserved": summary["all_original_sources_preserved"],
          "report": str(out/"BENCHMARK_AUDIT.json")}, indent=2), flush=True)
    return summary

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=pathlib.Path,
                   help="Existing checkout at the exact pinned QuixBugs commit")
    p.add_argument("--out", type=pathlib.Path, required=True)
    p.add_argument("--require-successes", type=int, default=0)
    p.add_argument("--max-candidates", type=int, default=120)
    x = p.parse_args()
    report = execute(x.checkout, x.out, x.require_successes, x.max_candidates)
    sys.exit(0 if report["passed_required_threshold"]
             and report["all_original_sources_preserved"] else 1)
