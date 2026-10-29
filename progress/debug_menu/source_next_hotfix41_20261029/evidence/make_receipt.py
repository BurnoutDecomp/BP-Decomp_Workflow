from pathlib import Path
import subprocess,json,hashlib,difflib
root=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
base='abbc9047d850a4665d959993012261c55205e5e5'
path='src/GameSource/Gui/BrnGuiVideoEvents.h'
pre=subprocess.check_output(['git','-C',str(root/'b5-decomp'),'show',base+':'+path])
(out/'pre/GameSource/Gui/BrnGuiVideoEvents.h').write_bytes(pre)
post=(out/'post/GameSource/Gui/BrnGuiVideoEvents.h').read_bytes()
patch=''.join(difflib.unified_diff(pre.decode().splitlines(True),post.decode().splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(out/'intro-video-events.patch').write_text(patch,encoding='utf-8',newline='')
receipt={'base_b5':base,'path':path,'pre_sha256':hashlib.sha256(pre).hexdigest(),'post_sha256':hashlib.sha256(post).hexdigest(),
 'pre_git_blob':subprocess.check_output(['git','-C',str(root/'b5-decomp'),'rev-parse',base+':'+path],text=True).strip(),
 'patch_sha256':hashlib.sha256((out/'intro-video-events.patch').read_bytes()).hexdigest(),
 'regression':json.loads((out/'regression_results.json').read_text()),
 'consumer_gates':json.loads((out/'consumer-gates/results.json').read_text()),
 'original_evidence':['.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82476C68.json','.ida-exports/BURNOUT_X360_ARTIST.XEX/0x82476CF8.json','.ida-exports/BURNOUT_X360_ARTIST.XEX/0x824F17C0.json',
 'references/DecFIGS/dwarfdump/GameSource/Gui/BrnGuiEventTypeDefs.h:8444-8464'],
 'game_launched':False,'normal_logs_config_modified':False,'shared_source_modified':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
