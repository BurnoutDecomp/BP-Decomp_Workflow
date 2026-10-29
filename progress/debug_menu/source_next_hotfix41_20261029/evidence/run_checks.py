from pathlib import Path
import subprocess, json, hashlib
root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
def rows(name):
    return [x.strip() for x in (root/'tools/build'/name).read_text().splitlines() if x.strip() and not x.startswith('#')]
flags = ' '.join(rows('msvc_flags.txt'))
includes = ' '.join('/I"'+str(root/x)+'"' for x in rows('msvc_includes.txt'))
results = []
for variant in ('pre', 'post'):
    work = out/variant
    rsp = work/'regression.rsp'
    rsp.write_text(flags+' /I"'+str(work)+'" '+includes+'\n'+
        '"'+str(out/'video_event_regression.cpp')+'"\n'+
        '"'+str(root/'b5-decomp/src/GameShared/GameClasses/Gui/Model/State/CgsGuiStateInterface.cpp')+'"\n'+
        '"'+str(root/'b5-decomp/src/GameShared/GameClasses/Development/CgsStrStream.cpp')+'"\n'+
        '/Fe"'+str(work/'regression.exe')+'" /link /OPT:REF\n')
    bat = work/'regression.bat'
    bat.write_text('@echo off\ncall "'+str(root/'tools/build/msvc_env.bat')+'" >nul 2>&1\nif errorlevel 1 exit /b 200\ncl @"'+str(rsp)+'"\n')
    p = subprocess.run(['cmd','/c',str(bat)], cwd=work, text=True, capture_output=True)
    (work/'compile.log').write_text(p.stdout+p.stderr)
    print(variant, 'compile',p.returncode,flush=True)
    result={'variant':variant,'compile_exit':p.returncode}
    if p.returncode == 0:
        p=subprocess.run([str(work/'regression.exe')],cwd=work,text=True,capture_output=True)
        (work/'regression.log').write_text(p.stdout+p.stderr)
        result.update(run_exit=p.returncode,output=p.stdout+p.stderr)
        print(p.stdout+p.stderr,flush=True)
    else: print((p.stdout+p.stderr)[-5000:],flush=True)
    results.append(result)
(out/'regression_results.json').write_text(json.dumps(results,indent=2))
