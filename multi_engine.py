# coding: utf-8
"""ZORRO MULTI-REPAIR, verified closed-loop experiment.

ONLY a pinned historical educational GitHub repo with secure counterparts.
Uses AST-scoped patch extraction, negative controls, actual activate/reject/
rollback, 45 sealed independent probes across SQLi/XSS/IDOR.
No generic code execution, remote network operations or production changes.
"""
from __future__ import annotations
import argparse,ast,datetime,difflib,hashlib,json,pathlib,re,shutil,subprocess,sys,uuid

HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE/"baseline"
VENV=pathlib.Path(sys.executable)
HOLDOUT=HERE/"holdout_multi.py"
PUBLIC=HERE/"public_regressions.py"
RUNS=HERE/"runs"
HEAD="c7a274622b17ef47a7a43ffcbd4591171085ddbe"
BASE_SHA="061ea786bce4d259de91817002c3b2a9645106d0062ed13bdf8c3bdd0c07d5da"
HOLD_SHA="6c70d103878893a714ae70422208976f72e98d54f2859365d84593f5b77c0be2"
PUBLIC_SHA="632b9cb16b761d4e35870fbd0f9eeb20544e9a51d796e4a333a3aefce44adf80"
TASKS={
 "SQLi":{"vuln":"vulnerable_products","secure":"secure_products",
         "uri":"/vulnerable/products","secure_uri":"/secure/products",
         "public_tag":"sqli","obsolete":"test_vulnerable_search_allows_sql_injection"},
 "XSS":{"vuln":"vulnerable_xss","secure":"secure_xss",
        "uri":"/vulnerable/xss","secure_uri":"/secure/xss",
        "public_tag":"xss","obsolete":"test_vulnerable_xss_reflects_unescaped_html"},
 "IDOR":{"vuln":"vulnerable_account","secure":"secure_account",
         "uri":"/vulnerable/account/<int:account_id>","secure_uri":"/secure/account/<int:account_id>",
         "public_tag":"idor","obsolete":"test_vulnerable_account_allows_other_users_record"},
}
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args):
 return subprocess.run(["git","-C",str(BASE),*args],capture_output=True,text=True,check=True,timeout=30).stdout.strip()
def verify_inputs():
 if git("rev-parse","HEAD")!=HEAD or git("status","--porcelain"):
  raise RuntimeError("Original GitHub repository not clean or changed")
 checks=((BASE/"app/routes.py",BASE_SHA),(HOLDOUT,HOLD_SHA),
        (PUBLIC,PUBLIC_SHA))
 for f,h in checks:
  if not f.is_file() or sha(f)!=h:raise RuntimeError("Immutable source changed: "+str(f))
 if not VENV.is_file():raise RuntimeError("Pinned virtual environment missing")
def copy(src,dest):
 src=pathlib.Path(src).resolve()
 dest=pathlib.Path(dest).resolve()
 if dest.exists() or not dest.is_relative_to(HERE.resolve()):
  raise RuntimeError("Refusing unsafe destination "+str(dest))
 shutil.copytree(src,dest,ignore=shutil.ignore_patterns(
     ".git","__pycache__","*.pyc",".pytest_cache","web_security_lab.db",
     "web_security_lab.db-journal","web_security_lab.db-shm","web_security_lab.db-wal"))
def inventory(folder):
 out={}
 for f in pathlib.Path(folder).rglob("*"):
  if f.is_symlink():raise RuntimeError("Symlink not permitted in experiment")
  if not f.is_file():continue
  rel=f.relative_to(folder).as_posix()
  if rel.endswith("web_security_lab.db") or "__pycache__" in rel or rel.startswith("."):
   continue
  out[rel]=sha(f)
 return out
def src_function(lines,name):
 tree=ast.parse("".join(lines))
 matches=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name]
 if len(matches)!=1:raise RuntimeError("Expected exactly one function "+name)
 n=matches[0]; start=min([n.lineno]+[d.lineno for d in n.decorator_list])-1
 return start,n.end_lineno,"".join(lines[start:n.end_lineno])
def generate(source_file,cls,kind):
 t=TASKS[cls]
 original=pathlib.Path(source_file).read_text(encoding="utf-8")
 lines=original.splitlines(keepends=True)
 beg,end,old=src_function(lines,t["vuln"])
 _,_,secure=src_function(lines,t["secure"])
 if t["uri"] not in old or t["secure_uri"] not in secure:
  raise RuntimeError("Route source does not match pinned source")
 if kind=="deny_everyone":
  args="(account_id: int)" if cls=="IDOR" else "()"
  patch=f'@main.route("{t["uri"]}")\ndef {t["vuln"]}{args}:\n    abort(403)\n'
 elif kind=="secure_reference_transfer":
  patch=secure.replace(t["secure_uri"],t["uri"],1)
  patch=patch.replace("def "+t["secure"]+"(","def "+t["vuln"]+"(",1)
  patch=patch.replace('mode="Secure"','mode="Vulnerable"',1)
  if cls=="IDOR" and "AND users.username = ?" not in patch:
   raise RuntimeError("No guarded owner comparison")
  if cls=="SQLi" and "WHERE category = ?" not in patch:
   raise RuntimeError("SQL is not parameterized")
  if cls=="XSS" and "unsafe=False" not in patch:
   raise RuntimeError("Templating is not HTML-escaped")
 else:raise ValueError("Unrecognized strategy")
 if not patch.endswith("\n"):patch+="\n"
 updated="".join(lines[:beg])+patch+"".join(lines[end:])
 ast.parse(updated)
 # Auditable: only the target AST function may change. Existing safe reference
 # and unrelated endpoints must remain exact.
 other=dict((n.name,ast.dump(n,include_attributes=False)) for n in
            ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name!=t["vuln"])
 changed=dict((n.name,ast.dump(n,include_attributes=False)) for n in
            ast.parse(updated).body if isinstance(n,ast.FunctionDef) and n.name!=t["vuln"])
 if other!=changed:raise RuntimeError("Patch changed unrelated Python function")
 pathlib.Path(source_file).write_text(updated,encoding="utf-8")
 return {"class":cls,"kind":kind,"sha256":sha(source_file)}
def run_cmd(label,repo,args):
 temp=repo.parent/("tmp_"+label+"_"+uuid.uuid4().hex[:6])
 cp=subprocess.run([str(VENV),"-B","-m","pytest","-q","-p","no:cacheprovider",
                    "--basetemp",str(temp),*args],
                   cwd=repo,capture_output=True,text=True,timeout=90)
 return {"exit":cp.returncode,"summary":cp.stdout.splitlines()[-1] if cp.stdout else "",
         "stdout_tail":cp.stdout[-2500:],"stderr_tail":cp.stderr[-420:],
         "args":args}
def sealed(repo):
 if sha(HOLDOUT)!=HOLD_SHA:raise RuntimeError("Holdout mutated")
 cp=subprocess.run([str(VENV),"-B",str(HOLDOUT),str(repo)],
                   cwd=repo,capture_output=True,text=True,timeout=50)
 rows=[json.loads(line.split("ZORRO_SEALED_HOLDOUT=",1)[1])
       for line in cp.stdout.splitlines() if line.startswith("ZORRO_SEALED_HOLDOUT=")]
 if len(rows)!=1:raise RuntimeError("Failed to parse sealed holdout: "+cp.stderr[-200:])
 doc=rows[0]
 return {"pass":doc["passed"],"fail":doc["failed"],"total":doc["total"],
         "classes":doc["classes"],"seal_intact":sha(HOLDOUT)==HOLD_SHA}
def stage_judge(repo,completed,cls):
 public=run_cmd(cls.lower()+"_public",repo,
   ["tests/test_zorro_multi.py","-k",TASKS[cls]["public_tag"]])
 hold=sealed(repo)
 required=[*completed,cls]
 correct=all(hold["classes"][x]["failed"]==0 for x in required)
 normal=public["exit"]==0
 # Confirm previous issues have not regressed in the public tests.
 previous={}
 for earlier in completed:
  p=run_cmd("prior_"+earlier.lower(),repo,
    ["tests/test_zorro_multi.py","-k",TASKS[earlier]["public_tag"]])
  previous[earlier]=p
  if p["exit"]!=0:correct=False
 return {"accepted":bool(correct and normal),"public":public,
  "previous_public":previous,"sealed":hold,
  "checked_classes":required}
def engine(run_id,negative_only=False):
 if not re.fullmatch(r"[a-zA-Z0-9_]{3,30}",run_id):
  raise ValueError("Invalid run ID")
 verify_inputs()
 run=RUNS/run_id
 if run.exists():raise RuntimeError("No overwriting prior runs")
 RUNS.mkdir(exist_ok=True)
 run.mkdir()
 stage=run/"active"
 copy(BASE,stage)
 # This public test file is not allowed to be edited by candidate strategies.
 shutil.copy2(PUBLIC,stage/"tests/test_zorro_multi.py")
 start_original=inventory(stage)
 original_hash=sha(stage/"app/routes.py")
 if original_hash!=BASE_SHA:raise RuntimeError("Baseline drift")
 old_suite=run_cmd("baseline",stage,["tests","--ignore=tests/test_zorro_multi.py"])
 if old_suite["exit"]!=0 or "31 passed" not in old_suite["summary"]:
  raise RuntimeError("Original GitHub tests not green")
 before=sealed(stage)
 if (before["total"],before["pass"],before["fail"])!=(45,23,22):
  raise RuntimeError("Real 45-case baseline changed: "+repr(before))
 task_data={"schema":1,"started_at":stamp(),"run":run_id,
  "scope":"pinned teaching GitHub CWE-639, SQLi and reflected XSS",
  "source_commit":HEAD,"source_sha256":BASE_SHA,
  "sealed_oracle_sha256":HOLD_SHA,"public_tests_sha256":PUBLIC_SHA,
  "baseline_holdout":before,"baseline_original_31":old_suite,
  "tested_candidates":[],"accepted_classes":[],"rollback_count":0,
  "candidate_strategy":"deterministic AST reference transplant, not general LLM patch generation",
  "external_targets":0,"baseline_unmodified":True}
 completed=[]
 for cls in TASKS:
  strategies=["deny_everyone"] if negative_only else ["deny_everyone","secure_reference_transfer"]
  accepted=False
  for attempt,kind in enumerate(strategies,1):
   pending=run/(cls.lower()+"_"+kind)
   copy(stage,pending)
   edited=generate(pending/"app/routes.py",cls,kind)
   expected=inventory(stage)
   changed=inventory(pending)
   modified=sorted(k for k in set(expected)|set(changed) if expected.get(k)!=changed.get(k))
   if modified!=["app/routes.py"] or sha(pending/"tests/test_zorro_multi.py")!=PUBLIC_SHA:
    raise RuntimeError("Modification escaped AST allowlist")
   previous=run/(cls.lower()+"_preapply_"+str(attempt))
   stage.rename(previous)
   pending.rename(stage)
   verdict=stage_judge(stage,completed,cls)
   trial={"class":cls,"attempt":attempt,"strategy":kind,
          "applied":True,"edit":edited,"judge":verdict,
          "candidate_sha256":sha(stage/"app/routes.py")}
   if verdict["accepted"]:
    previous.rename(run/(cls.lower()+"_rollback_checkpoint"))
    completed.append(cls)
    trial["decision"]="ACCEPTED"
    accepted=True
    task_data["accepted_classes"].append(cls)
    task_data["tested_candidates"].append(trial)
    break
   quarantine=run/(cls.lower()+"_rejected_"+str(attempt))
   stage.rename(quarantine)
   previous.rename(stage)
   if inventory(stage)!=expected:
    raise RuntimeError("Automatic rollback failed integrity comparison")
   trial["decision"]="REJECTED_AND_ROLLED_BACK"
   trial["restored_sha256"]=sha(stage/"app/routes.py")
   task_data["rollback_count"]+=1
   task_data["tested_candidates"].append(trial)
  if not accepted:
   if negative_only:break
   raise RuntimeError("No accepted fix for "+cls)
 if negative_only:
  if inventory(stage)!=start_original:
   raise RuntimeError("Rejected run changed baseline")
  task_data["outcome"]="ALL_REJECTED_SAFE_ORIGINAL"
 else:
  if completed!=list(TASKS):
   raise RuntimeError("Incomplete three-class repair")
  final=sealed(stage)
  if (final["pass"],final["fail"],final["total"])!=(45,0,45):
   raise RuntimeError("Final independent holdout not fully green")
  compatible=run_cmd("compatible",stage,["tests","-k",
    "not test_vulnerable_search_allows_sql_injection and not test_vulnerable_xss_reflects_unescaped_html and not test_vulnerable_account_allows_other_users_record"])
  full=run_cmd("full_original",stage,["tests","--tb=line"])
  task_data["accepted_full_holdout"]=final
  task_data["compatible_tests"]=compatible
  task_data["complete_tests"]=full
  if compatible["exit"]!=0 or "44 passed, 3 deselected" not in compatible["summary"]:
   raise RuntimeError("Multi repair functional regression suite failed")
  if full["exit"]!=1 or "3 failed, 44 passed" not in full["summary"]:
   raise RuntimeError("Historical vulnerability tests not transparently failed")
  patched=(stage/"app/routes.py").read_text(encoding="utf-8").splitlines(keepends=True)
  orig=(BASE/"app/routes.py").read_text(encoding="utf-8").splitlines(keepends=True)
  diff="".join(difflib.unified_diff(orig,patched,
    fromfile="a/app/routes.py",tofile="b/app/routes.py"))
  if not all(x in diff for x in ["AND users.username = ?","WHERE category = ?","unsafe=False"]):
   raise RuntimeError("Patch lacks 3 security checks")
  (run/"THREE_CLASS_VERIFIED.patch").write_text(diff,encoding="utf-8")
  task_data["patch_sha256"]=sha(run/"THREE_CLASS_VERIFIED.patch")
  task_data["outcome"]="THREE_CLASS_REPAIR_ACCEPTED"
  task_data["accepted_source_sha256"]=sha(stage/"app/routes.py")
 if sha(BASE/"app/routes.py")!=BASE_SHA:
  raise RuntimeError("Baseline source mutated")
 task_data["finished_at"]=stamp()
 with (run/"FINAL_AUDIT.json").open("x",encoding="utf-8") as fh:
  json.dump(task_data,fh,ensure_ascii=False,indent=2)
 print(json.dumps({"result":task_data["outcome"],"run":run_id,
  "classes":task_data["accepted_classes"],"attempts":len(task_data["tested_candidates"]),
  "auto_rollbacks":task_data["rollback_count"],
  "sealed_after":task_data.get("accepted_full_holdout",{}).get("pass"),
  "compatible":task_data.get("compatible_tests",{}).get("summary"),
  "known_obsolete":task_data.get("complete_tests",{}).get("summary"),
  "audit":str(run/"FINAL_AUDIT.json")},ensure_ascii=True,indent=2),flush=True)
 return task_data
if __name__=="__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--run",required=True)
 parser.add_argument("--negative-only",action="store_true")
 args=parser.parse_args()
 report=engine(args.run,args.negative_only)
 raise SystemExit(0 if ((report["outcome"]=="ALL_REJECTED_SAFE_ORIGINAL")==args.negative_only) else 2)

