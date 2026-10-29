"""Run the exact peer-reviewed Environment21 case with immutable asset handles."""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, subprocess
from ctypes import wintypes
R=Path(__file__).resolve().parent
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,indent=2),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--peer-receipt',type=Path,required=True);a=ap.parse_args()
    peer=load(a.peer_receipt)
    assert str(peer.get('verdict','')).lower().startswith('pass')
    assert peer['manifest_sha256']==sha(R/'MANIFEST.json')
    for p,h in load(R/'MANIFEST.json').items(): assert sha(Path(p))==h,p
    stage=load(R/'STAGING.json')
    assert not (R/'GAME_RUN_STARTED.json').exists()
    assert shutil_disk_free(R)>=stage['storage']['required_free_at_launch_bytes']
    pre=subprocess.run(['pwsh','-NoProfile','-File',str(R/'Preflight.ps1')],capture_output=True,text=True)
    (R/'preflight.console.log').write_text(pre.stdout+pre.stderr,encoding='utf-8');assert pre.returncode==0
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    k.CreateFileW.restype=wintypes.HANDLE;k.CloseHandle.argtypes=[wintypes.HANDLE]
    handles=[]
    try:
        for name in load(R/'ASSETS.json')['roster']:
            h=k.CreateFileW(str(Path(stage['cwd'])/name),0x80000000,1,None,3,0x80,None)
            if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            handles.append(h)
        save(R/'GAME_RUN_STARTED.json',{'slot':62180,'peer_receipt':str(a.peer_receipt),'peer_sha256':sha(a.peer_receipt),'asset_handles_read_only':len(handles)})
        invoke=R/'Invoke.ps1'
        command=" & '"+str(R/'runtime_harness/tools/tests/run_case.ps1')+"' -Case '"+str(R/'Case.ps1')+"' -RunDir '"+stage['active_run_dir']+"' -RunsRoot '"+str(R/'runs')+"' -Slot 62180 -GameDir '"+stage['exe_dir']+"' -WorkingDirectory '"+stage['cwd']+"' -LockTimeoutSec 1 -Label 'Environment24 cohort unfinished3 controls; private source32; stationary PNR;13frame cap640x360;64MiB log; RootV8 normal41 guard and V5 concurrency'"
        invoke.write_text("\n".join(["$ErrorActionPreference='Stop'","$env:BPH_KEEP_SLOT_EXE='1'","try {",command," $code=$LASTEXITCODE","} finally { Remove-Item Env:\\BPH_KEEP_SLOT_EXE -ErrorAction SilentlyContinue }","exit $code",""]),encoding='utf-8')
        env=dict(os.environ)
        env['PSModulePath']=';'.join([str(Path(os.environ['USERPROFILE'])/'Documents/PowerShell/Modules'),str(Path(os.environ['ProgramFiles'])/'PowerShell/Modules'),str(Path(os.environ['ProgramFiles'])/'PowerShell/7/Modules')])
        with (R/'RUN.console.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File',str(invoke)],stdout=log,stderr=subprocess.STDOUT,env=env)
        post={p:{'sha256':sha(Path(p)),'unchanged':sha(Path(p))==v['sha256']} for p,v in load(R/'NORMAL_BEFORE.json').items()}
        save(R/'NORMAL_POSTCHECK.json',{'all_unchanged':all(v['unchanged'] for v in post.values()),'files':post})
        save(R/'RUN_EXIT.json',{'exit_code':result.returncode,'asset_handles_held':len(handles),'profile_restored':sha(Path(stage['profile']))==stage['profile_seed_sha256']})
        return result.returncode
    finally:
        for h in handles:k.CloseHandle(h)
def shutil_disk_free(path):
    import shutil
    return shutil.disk_usage(path).free
if __name__=='__main__':raise SystemExit(main())
