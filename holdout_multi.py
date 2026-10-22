# coding: utf-8
"""SEALED independent acceptance oracle for three deliberately insecure
GitHub educational endpoints. This script is outside all agent worktrees.

Uses only in-process Flask test_client against synthetic data. No network.
"""
from __future__ import annotations
import datetime,json,pathlib,subprocess,os,sys
from markupsafe import escape
if len(sys.argv)!=2:raise SystemExit("Usage: holdout_multi.py <absolute-project-dir>")
root=pathlib.Path(sys.argv[1]).resolve()
if not root.is_dir() or not (root/"app/routes.py").is_file():
 raise SystemExit("Source unavailable")
os.chdir(root)
sys.path.insert(0,str(root))
from app import create_app
app=create_app({"TESTING":True})
case=[]
def check(vuln,name,ok,detail):
 case.append({"class":vuln,"name":name,"passed":bool(ok),"detail":detail})
def call(path,query=None):
 return app.test_client().get(path,query_string=query or {})
regular={"laptops":["Security Laptop","Packet Analysis Laptop"],
         "networking":["Network Adapter"],"security":["USB Security Key"]}
for category,expected in regular.items():
 r=call("/vulnerable/products",{"category":category})
 for match in expected:
  check("SQLi",f"normal_{category}_{match}",r.status_code==200 and match.encode() in r.data,
        {"http":r.status_code,"found":match.encode() in r.data})
payloads=[
 "' OR '1'='1",
 "' OR 1=1 --",
 "laptops' OR 'a'='a",
 "security' OR 2=2 --",
 "anything' OR 'x'='x",
 "' OR 'b'='b",
 "' OR 1=1 /*",
 "nomatch-token-2026",
]
for i,payload in enumerate(payloads):
 try:
  r=call("/vulnerable/products",{"category":payload})
  leaked=any(x in r.data for x in [b"Security Laptop",b"Network Adapter",b"USB Security Key"])
  check("SQLi",f"bad_filter_{i}",r.status_code==200 and not leaked and
        b"No products found." in r.data,
        {"http":r.status_code,"unexpected_products":leaked})
 except Exception as e:
  check("SQLi",f"bad_filter_{i}",False,{"exception":type(e).__name__})
empty=call("/vulnerable/products",{"category":""})
check("SQLi","no_filter_keeps_all",empty.status_code==200 and
      b"Security Laptop" in empty.data and b"Network Adapter" in empty.data,
      {"http":empty.status_code})

xss_examples=[
 "<script>demo</script>",
 "<svg onload=prompt(1)>",
 "<img src=x onerror=alert(1)>",
 "<b>bold</b>",
 "<iframe src=x></iframe>",
 "<details open>example</details>",
 "<div>sample</div>",
 "<a href='#'>link</a>",
 "<marquee>moving</marquee>",
 "<h1>Header</h1>",
 "<p>paragraph</p>",
 "safe plain text",
]
for i,msg in enumerate(xss_examples):
 response=call("/vulnerable/xss",{"message":msg})
 safe=str(escape(msg)).encode("utf-8")
 ok=response.status_code==200 and safe in response.data
 if "<" in msg:ok=ok and msg.encode() not in response.data
 check("XSS",f"escape_{i}",ok,
       {"http":response.status_code,"raw_reflected":("<" in msg and msg.encode() in response.data),
        "escaped_present":safe in response.data})

for who,own,other,owned_marker,foreign_marker in [
 ("alice",1,2,b"Alice private account information",b"Bob private account information"),
 ("bob",2,1,b"Bob private account information",b"Alice private account information")]:
 client=app.test_client()
 login=client.get("/login/"+who)
 check("IDOR",who+"_login",login.status_code==302,{"http":login.status_code})
 owned=client.get(f"/vulnerable/account/{own}")
 check("IDOR",who+"_own_http",owned.status_code==200,{"http":owned.status_code})
 check("IDOR",who+"_own_visible",owned_marker in owned.data,{"shown":owned_marker in owned.data})
 foreign=client.get(f"/vulnerable/account/{other}")
 check("IDOR",who+"_foreign_http",foreign.status_code==403,{"http":foreign.status_code})
 check("IDOR",who+"_foreign_hidden",foreign_marker not in foreign.data,
       {"shown":foreign_marker in foreign.data})
 safe=client.get(f"/secure/account/{other}")
 check("IDOR",who+"_safe_reference",safe.status_code==403,{"http":safe.status_code})
 nonexistent=client.get("/vulnerable/account/9999")
 check("IDOR",who+"_nonexistent",nonexistent.status_code in (403,404),{"http":nonexistent.status_code})
anon=app.test_client()
for n in (1,2):
 res=anon.get(f"/vulnerable/account/{n}")
 check("IDOR",f"anonymous_{n}_http",res.status_code!=200,{"http":res.status_code})
 check("IDOR",f"anonymous_{n}_data",b"private account information" not in res.data,
       {"shown":b"private account information" in res.data})
known=app.test_client().get("/secure/products",query_string={"category":"laptops"})
check("IDOR","unrelated_secure_reference",known.status_code==200 and
      b"Security Laptop" in known.data,{"http":known.status_code})
check("IDOR","home_still_works",anon.get("/").status_code==200,{"homepage_http":anon.get("/").status_code})
groups={}
for category in ("SQLi","XSS","IDOR"):
 subset=[x for x in case if x["class"]==category]
 groups[category]={"total":len(subset),"passed":sum(x["passed"] for x in subset),
                   "failed":sum(not x["passed"] for x in subset),
                   "failure_names":[x["name"] for x in subset if not x["passed"]]}
summary={"schema":1,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "only_local_synthetic_flask_calls":True,"target_source":str(root),
 "classes":groups,"total":len(case),
 "passed":sum(x["passed"] for x in case),"failed":sum(not x["passed"] for x in case),
 "cases":case}
print("ZORRO_SEALED_HOLDOUT="+json.dumps(summary,ensure_ascii=True),flush=True)
raise SystemExit(0 if summary["failed"]==0 else 2)

