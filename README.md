# ZORRO Triple Repair — Reproducible Python Repair Research

[![QuixBugs benchmark](https://github.com/omarfahad430-web/ZORRO-Triple-Repair/actions/workflows/quixbugs-original-defects.yml/badge.svg)](https://github.com/omarfahad430-web/ZORRO-Triple-Repair/actions/workflows/quixbugs-original-defects.yml)

**New, experimental:** [ZORRO Repair V2 and full reproducible benchmark](experimental/README.md).

ZORRO now includes a bounded, test-guided Python code-repair prototype that
recovered the independently documented correct solutions to **4 out of 6
deliberately selected, original QuixBugs defects**. These were genuine existing
research benchmark errors, not errors seeded by us. All four passing patches
matched the benchmark's official reference function syntax trees, and passed
additional holdout tests. Two harder cases failed without a false success claim.

Run the exact benchmark yourself (Python 3.10+, Git, `pytest==9.1.1`):

```sh
python -m pip install pytest==9.1.1
python experimental/run_quixbugs.py --out benchmark-results/run1 --require-successes 4 --max-candidates 80
```

**Important limitations:** This is not autonomous AI, does not fix arbitrary
projects and should only execute trusted projects and tests in disposable
environments. The six samples were selected for the supported transformations;
4/6 is NOT a general success-rate estimate. See benchmark evidence and
negative controls in [the V2 documentation](experimental/README.md).

---

## Original pinned teaching demonstration

**الشيفرة متاحة للتجربة محليًا دون مفتاح API أو اشتراك مدفوع.**
يلزم Python 3.10 أو أحدث وGit. نزّل المستودع عبر **Code → Download ZIP**
وفك الضغط، ثم افتح الطرفية داخل المجلد ونفّذ أوامر نظامك أدناه.
ستُنشأ تقارير الاختبار والفرق البرمجي داخل `runs/`.

Alternatively, clone this release:
```sh
git clone https://github.com/omarfahad430-web/ZORRO-Triple-Repair.git
cd ZORRO-Triple-Repair
```

Requires Python 3.10+, Git and an internet connection for installation.
Download and extract this folder. Open a terminal in it.

Windows:
```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run_demo.py
```

macOS / Linux:
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_demo.py
```

The runner downloads the teaching repository from
https://github.com/thomasbeo/WebApplicationSecurityAssessmentLab
and checks out commit c7a274622b17ef47a7a43ffcbd4591171085ddbe.
Upstream source is not redistributed in this package.

Expected result (also reproduced on Windows before publication): baseline 23/45 security checks, repaired 45/45,
44 compatibility tests pass, 3 deliberately bad fixes rejected and rolled back.
Reports, rejected candidates, rollback checkpoints and the accepted patch are
written to a new runs/demo_* folder each time. Original baseline is preserved.
Three original educational tests intentionally expect vulnerabilities; they
fail after remediation, and are explicitly excluded from compatibility counts.

This is deterministic AST transfer from secure reference functions already
present in one pinned lab. It is not a general coding agent, independent
security certification, or a production vulnerability scanner. The published
45 checks are reviewable, not a fresh blind evaluation. No API key is needed.
Tests use Flask test_client and synthetic records; no web server is started.
Use a disposable development environment: Python tests are executable code,
and a virtual environment is not a security sandbox.

**حدود التجربة:** ينقل البرنامج إصلاحات مرجعية موجودة أصلًا في مختبر تعليمي
محدد، ويختبرها ويرفض التعديلات التي تعطل الوظائف. الاختبارات الـ45 مكتوبة
ضمن المشروع نفسه؛ ليست تدقيقًا أمنيًا مستقلًا من جهة خارجية، ولا تثبت القدرة
على إصلاح مشاريع عشوائية. ثلاثة اختبارات قديمة تتوقع وجود الثغرات تفشل بعد
الإصلاح عمدًا وتظهر في التقرير، بينما تنجح اختبارات التوافق الـ44.
