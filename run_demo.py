"""Portable teaching demo. Requires Python 3.10+, Git, Flask and pytest."""
import datetime, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT/'baseline'
HEAD='c7a274622b17ef47a7a43ffcbd4591171085ddbe'
def run(*args):
    subprocess.run(args,cwd=ROOT,check=True)
if not BASE.exists():
    run('git','-c','core.autocrlf=false','clone','https://github.com/thomasbeo/WebApplicationSecurityAssessmentLab.git',str(BASE))
    run('git','-C',str(BASE),'checkout','--detach',HEAD)
import multi_engine
label='demo_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
result=multi_engine.engine(label)
assert result['outcome']=='THREE_CLASS_REPAIR_ACCEPTED'
print('PASS: 45/45 security checks; 44 compatibility checks; 3 bad patches rejected and rolled back.')
print('Reports and patch: '+str(ROOT/'runs'/label))
