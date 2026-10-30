"""Run only the peer-reviewed private startup baseline; never install normal payloads."""
import argparse,ctypes,datetime,hashlib,json,os,subprocess
from ctypes import wintypes
from pathlib import Path
N=Path(__file__).resolve().parent;R=N.parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')
def normal_check(stage,label):
 rows=load(N/'NORMAL_PROTECTION.before.json');observations=[];bad=[]
 for p,row in rows.items():
  h=sha(p);mutable=Path(p).name in ['BrnGame.log','BrnGame.emergency.log']
  observations.append({'path':p,'sha256':h,'bytes':Path(p).stat().st_size,'frozen_sha256':row['sha256'],'mutable_log':mutable,'changed':h!=row['sha256']})
  if h!=row['sha256'] and not mutable:bad.append(p)
 save(R/('NORMAL_'+label+'.json'),{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'observations':observations,'nonlog_drift':bad,'normal_writes':False,'log_writer_attribution':'none; V8 observational snapshots only'})
 assert not bad,('Protected normal non-log drift',bad)
 return observations
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--peer-receipt',required=True,type=Path);ap.add_argument('--peer-sha',required=True);a=ap.parse_args()
 assert sha(a.peer_receipt)==a.peer_sha and str(load(a.peer_receipt)['verdict']).lower().startswith('pass')
 assert load(a.peer_receipt)['manifest_sha256']==sha(N/'PREFLIGHT_MANIFEST.json')
 stage=load(N/'STAGING.json');manifest=load(N/'PREFLIGHT_MANIFEST.json')
 for p,h in manifest.items():assert sha(p)==h,p
 assert stage['slot']==62173 and not stage['normal_deployment'] and not stage['skip_intro']
 assert not Path(stage['active_run_dir']).exists(),'Fresh one-shot run directory required'
 assert not (Path(stage['exe_dir'])/'BrnGame.log').exists(),'Fresh private log required'
 for name,h in stage['launch_files'].items():assert sha(Path(stage['exe_dir'])/name)==h,name
 for p,h in {**stage['runtime_overlay_files'],**stage['runtime_shared_readonly_dependencies']}.items():assert sha(p)==h,p
 assert sha(Path(stage['exe_dir'])/'config.ini')==stage['config_sha256']
 assert sha(Path(stage['profile']))==stage['profile_seed_sha256']
 normal_check(stage,'BEFORE')
 with (R/'GAME_RUN_STARTED.json').open('x') as f:json.dump({'peer_receipt':str(a.peer_receipt),'peer_sha256':a.peer_sha,'slot':62173,'source':stage['source'],'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},f)
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];kernel.CreateFileW.restype=wintypes.HANDLE;kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 assets=load(N/'DATA_SNAPSHOT.json');handles=[]
 try:
  for name in assets['roster']:
   h=kernel.CreateFileW(str(Path(stage['cwd'])/name),0x80000000,1,None,3,0x80,None)
   if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
   handles.append(h)
  save(R/'ASSET_GUARD.json',{'held':len(handles),'access':'GENERIC_READ','share':'FILE_SHARE_READ only; write/delete opens denied'})
  script=N/'Invoke.ps1';command=" & '"+str(N/'runtime_harness/tools/tests/run_case.ps1')+"' -Case '"+str(N/'Case.ps1')+"' -RunDir '"+stage['active_run_dir']+"' -RunsRoot '"+str(R/'runs')+"' -Slot 62173 -GameDir '"+stage['exe_dir']+"' -WorkingDirectory '"+stage['cwd']+"' -LockTimeoutSec 1 -Label 'Private source22e6735 startup baseline; unbypassed EA/Criterion to ordinary title/profile/world/driving; 450s total120s video phase; ten frames; no forced Replay states; normal Source41 protected'"
  script.write_text("\n".join(["$ErrorActionPreference='Stop'","$env:BPH_KEEP_SLOT_EXE='1'","try {",command," $code=$LASTEXITCODE","} finally { Remove-Item Env:\\BPH_KEEP_SLOT_EXE -ErrorAction SilentlyContinue }","exit $code",""]))
  env=dict(os.environ);env['TEMP']=env['TMP']=str(R/'tmp');env['PSModulePath']=';'.join([str(Path(os.environ['USERPROFILE'])/'Documents/PowerShell/Modules'),str(Path(os.environ['ProgramFiles'])/'PowerShell/Modules'),str(Path(os.environ['ProgramFiles'])/'PowerShell/7/Modules')])
  with (R/'RUN.console.log').open('w',encoding='utf-8') as log:p=subprocess.run(['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],stdout=log,stderr=subprocess.STDOUT,env=env)
  save(R/'RUN_EXIT.json',{'exit_code':p.returncode,'asset_handles_held':len(handles)})
  normal_check(stage,'AFTER')
  for name,h in stage['launch_files'].items():assert sha(Path(stage['exe_dir'])/name)==h,name
  if Path(stage['profile']).exists():assert sha(Path(stage['profile']))==stage['profile_seed_sha256']
  return p.returncode
 finally:
  for h in handles:kernel.CloseHandle(h)
if __name__=='__main__':raise SystemExit(main())
