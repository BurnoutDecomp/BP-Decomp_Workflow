import os, subprocess, json, hashlib, re, difflib
from pathlib import Path

W=Path('D:/Reverse/BP-Decomp_Workflow'); B=W/'b5-decomp'; R=Path(__file__).resolve().parent; S=W/'scratch/DEBUG_MENU_1011'
BASE='abbc9047d850a4665d959993012261c55205e5e5'; WB='36863b946cd721b93b38ea81e2b9ec06e01bbbde'
E=dict(os.environ,GIT_INDEX_FILE=str(R/'source.index'))
def g(*a,env=E,input=None):
 p=subprocess.run(['git','-C',str(B),*a],env=env,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: raise RuntimeError(str(a)+'\n'+p.stderr.decode(errors='replace'))
 return p.stdout
def sha(b): return hashlib.sha256(b).hexdigest()
def lf(b): return b.replace(b'\r\n',b'\n')
def save(n,d): (R/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')

g('read-tree',BASE)
spec=[
 ('traffic21','review_traffic_chunk21_reinsert_caller_sol_20261029/reviewed-integration.patch','review_traffic_chunk21_reinsert_caller_sol_20261029/INTEGRATION_SUPPLEMENT.md'),
 ('traffic22','review_traffic_chunk22_policy_sol_cc2b2c953e/reviewed-changes.patch','review_traffic_chunk22_policy_sol_cc2b2c953e/REVIEW.md'),
 ('traffic23','swarm_traffic_source_backlog_20261028/chunk23_pressure_split_occupancy/changes.patch','chunk23_review_2fe37081d92a4d2e9382a689e831519b/REVIEW.md'),
 ('traffic24','swarm_traffic_source_backlog_20261028/chunk24_crashed_articulated_pairing/changes.patch','swarm_traffic_source_backlog_20261028/review_chunk24_independent_426e00ca061d4212af82aef28df54832/REVIEW.md'),
 ('effects32','review_effects_arbitrator_bound32_20261029_73e60d3f/strict-bound32.patch','review_effects_arbitrator_bound32_20261029_73e60d3f/REVIEW.md'),
 ('camera','review_camera_x360_compressed_picture_20261029_independent/independently_derived.patch','review_camera_x360_compressed_picture_20261029_independent/REVIEW.md')]
rows=[]
for name,patch,review in spec:
 raw=(S/patch).read_bytes(); b=lf(raw)
 if name=='effects32': b=b.replace(b'a/b5-decomp/',b'a/').replace(b'b/b5-decomp/',b'b/')
 if name=='camera':
  camera=[];out=[]
  pins=json.loads((S/'swarm_camera_x360_compressed_picture_recovery_20261029/PINS.json').read_text())['files']
  for row in json.loads((S/'review_camera_x360_compressed_picture_20261029_independent/derived_pre_post_bindings.json').read_text())['files']:
   x=row['path']; before=g('show',':'+x);physical=(B/x).read_bytes();after=(S/'swarm_camera_x360_compressed_picture_recovery_20261029/overlay'/x).read_bytes()
   assert sha(physical)==row['preimage_sha256'] and sha(after)==row['postimage_sha256'],x
   assert lf(before)==lf(physical),x
   if before==lf(before):after=lf(after)
   out.append(''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile='a/'+x,tofile='b/'+x)).encode())
   camera.append({'path':x,'source32_pre_sha256':sha(before),'reviewed_physical_pre_sha256':row['preimage_sha256'],'reviewed_overlay_post_sha256':row['postimage_sha256'],'integration_post_sha256':sha(after),'only_existing_Git_line_endings_preserved':True})
  b=b''.join(out);save('CAMERA_DELIVERY_BINDINGS.json',camera)
 p=R/(name+'.patch'); p.write_bytes(b)
 assert 'VERDICT: pass' in (S/review).read_text(),review
 paths=re.findall(r'^\+\+\+ b/(.+)$',b.decode(),re.M)
 pre={x:g('show',':'+x) for x in paths}
 g('-c','core.autocrlf=false','apply','--cached','--check',str(p)); g('-c','core.autocrlf=false','apply','--cached',str(p))
 bindings=[]
 for x in paths:
  post=g('show',':'+x); bindings.append({'path':x,'pre_sha256':sha(pre[x]),'post_sha256':sha(post),'pre_blob':g('hash-object','--stdin',input=pre[x]).decode().strip(),'post_blob':g('hash-object','--stdin',input=post).decode().strip()})
 transport='Reviewer LF patch unchanged' if name in ('traffic21','traffic22') else 'LF transport normalization only'
 if name=='effects32':transport='LF transport normalization and removal of b5-decomp path prefix only'
 if name=='camera':transport='Derived from sealed exact pre/post source; preserve each Git preimage CRLF/LF convention'
 rows.append({'packet_id':name,'review_path':review,'review_sha256':sha((S/review).read_bytes()),'reviewed_patch_path':patch,'reviewed_patch_sha256':sha(raw),'integration_patch':p.name,'integration_patch_sha256':sha(b),'transport':transport,'files':bindings,'raw_cached_apply_check':0,'raw_cached_apply':0,'site_credit':0,'native_credit':0})
tree=g('write-tree').decode().strip(); save('COMPOSITION.json',{'source_base':BASE,'workflow_base':WB,'source_tree':tree,'records':rows,'source_diff_paths':g('diff','--cached','--name-only',BASE).decode().splitlines(),'normal_written':False,'public_refs_changed':False,'native_game_launched':False})
(R/'SOURCE_DIFF.patch').write_bytes(g('diff','--cached',BASE))
print(json.dumps({'tree':tree,'paths':len(g('diff','--cached','--name-only',BASE).decode().splitlines()),'records':len(rows)}))
