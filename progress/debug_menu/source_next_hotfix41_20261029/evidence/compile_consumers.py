exec((__import__('pathlib').Path(__file__).parent/'run_checks.py').read_text().split('results = []')[0])
sources = [
 'GameSource/Gui/Flow/HUD/States/BrnBootVideos.cpp',
 'GameSource/Gui/Flow/HUD/States/BrnBootLegal.cpp',
 'GameSource/Gui/Flow/HUD/States/BrnPostTitleScreenLoad.cpp',
 'GameSource/Gui/Flow/Screen/States/BrnIntro.cpp',
 'GameSource/Gui/Flow/Screen/States/BrnVideo.cpp',
 'GameSource/Gui/BrnGuiMovieManager.cpp',
 'GameSource/Gui/BrnGuiModule.cpp',
]
work=out/'consumer-gates'
work.mkdir(exist_ok=True)
rsp=work/'compile.rsp'
rsp.write_text(flags+' /c /I"'+str(out/'post')+'" '+includes+'\n'+
 '\n'.join('"'+str(root/'b5-decomp/src'/x)+'"' for x in sources)+'\n')
bat=work/'compile.bat'
bat.write_text('@echo off\ncall "'+str(root/'tools/build/msvc_env.bat')+'" >nul 2>&1\nif errorlevel 1 exit /b 200\ncl @"'+str(rsp)+'"\n')
p=subprocess.run(['cmd','/c',str(bat)],cwd=work,text=True,capture_output=True)
(work/'compile.log').write_text(p.stdout+p.stderr)
(work/'results.json').write_text(json.dumps({'exit':p.returncode,'sources':sources},indent=2))
print('consumer-gates exit',p.returncode)
print(p.stdout+p.stderr)
