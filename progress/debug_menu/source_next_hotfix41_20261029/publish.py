import subprocess,os,json,hashlib,datetime
from pathlib import Path
W=Path('D:/Reverse/BP-Decomp_Workflow');B=W/'b5-decomp';R=Path(__file__).resolve().parent;A=W/'build/intro-video-repair-20261029'
BASE='f4bc56eb6a9e720a48a852df352eef1671ad2b74';WB='ac467f9c38a16e1696061335dce9b6bd6dd897f8';REF='refs/heads/codex/source-next-20261029';P='src/GameSource/Gui/BrnGuiVideoEvents.h'
def sha(b):return hashlib.sha256(b).hexdigest()
def g(repo,*args,input=None,env=None):
 p=subprocess.run(['git','-C',str(repo),*args],input=input,env=env,capture_output=True)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stderr.decode(errors='replace'))
 return p.stdout+p.stderr if args and args[0]=='push' else p.stdout
def save(n,d):(R/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
review=(A/'ROOT_REVIEW.json').read_bytes();assert sha(review)=='fc9b98fb9c11c57dfc4e22993fe9ff706ea4ff1282193fa9de349bb9b0af32ef';rv=json.loads(review);assert rv['verdict']=='pass'
patch=(A/'intro-video-events.patch').read_bytes();assert sha(patch)==rv['patch_sha256']=='ce604f7bd9b4cfc9de2bdf13ff3ad5e92e517eb801d92ed600dd63cbde3eceaa'
pre=g(B,'show',BASE+':'+P);post=(A/'post/GameSource/Gui/BrnGuiVideoEvents.h').read_bytes();assert sha(pre)==rv['pre_sha256'] and sha(post)==rv['post_sha256'];assert b'\r' not in patch
assert sha((A/'consumer-gates/results.json').read_bytes())==rv['seven_owner_TU_compile_receipt_sha256'];assert sha((A/'consumer-gates/compile.log').read_bytes())==rv['compile_log_sha256']
assert json.loads((A/'consumer-gates/results.json').read_text())['exit']==0
for repo,old in [(B,BASE),(W,WB)]:assert g(repo,'rev-parse',REF).decode().strip()==old
se=dict(os.environ,GIT_INDEX_FILE=str(R/'source.index'));g(B,'read-tree',BASE,env=se);g(B,'-c','core.autocrlf=false','apply','--cached','--check',str(A/'intro-video-events.patch'),env=se);g(B,'-c','core.autocrlf=false','apply','--cached',str(A/'intro-video-events.patch'),env=se);assert g(B,'show',':'+P,env=se)==post
assert g(B,'diff','--cached','--name-only',BASE,env=se).decode().splitlines()==[P];tree=g(B,'write-tree',env=se).decode().strip()
msg=b'Route startup video events through the original GUI wrapper\n\nUse the recovered48-byte video definition and channel40/64-byte boxing for play and stop events. Preserve full video ID, sound, rectangle and flags through the existing queue and interpreter. The original raw508/509 observer output was rejected.\n\nRoot independent source review and actual queue negative/post controls pass; seven consumer TUs compile. Unbypassed EA/Criterion playback remains the required native gate.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n'
source=g(B,'commit-tree',tree,'-p',BASE,input=msg).decode().strip()
checks=json.loads(g(W,'show',WB+':progress/debug_menu/source_batch_20261028/CHECKPOINTS.json'));assert len(checks['incremental_reviewed_source_passes'])==40
record={'packet_id':'startup_video_gui_event_boxing_hotfix','review_verdict':'pass_source_review','root_review_sha256':sha(review),'review_scope':rv['scope'],'patch_sha256':sha(patch),'source_commit':source,'source_parent':BASE,'source_tree':tree,'source_files':[{'path':P,'pre_sha256':sha(pre),'post_raw_sha256':sha(post),'pre_git_blob_oid':g(B,'rev-parse',BASE+':'+P).decode().strip(),'post_git_blob_oid':g(B,'rev-parse',source+':'+P).decode().strip()}],'root_actual_negative_exit':17,'root_actual_post_exit':0,'consumer_TU_compile_count':7,'native_game_launched':False,'native_credit':0,'site_credit':0,'affected_sites':[],'limits':rv['limits']}
checks['incremental_reviewed_source_passes'].append(record);checks.update(status='private41 startup-video source hotfix; reviewed and consumer compiles pass; unbypassed native video/build gate pending',workflow_base=WB,b5_source_head=source,b5_base=BASE)
we=dict(os.environ,GIT_INDEX_FILE=str(R/'workflow.index'));g(W,'read-tree',WB,env=we)
meta='progress/debug_menu/source_next_hotfix41_20261029/';payloads={};normalizations=[]
for path in ['progress/debug_menu/source_next_20261029/compile.cmd','progress/debug_menu/source_next_followon40_20261029/compile.cmd']:
 raw=g(W,'show',WB+':'+path);lf=raw.replace(b'\r\n',b'\n');assert raw!=lf and b'\r' not in lf
 payloads[path]=lf;normalizations.append({'path':path,'pre_raw_sha256':sha(raw),'post_index_LF_sha256':sha(lf),'change':'CRLF to LF only in Git index; existing *.cmd text eol=crlf produces CRLF worktree bytes and a clean status','historical_raw_blob_preserved_in_parent':WB})
payloads['progress/debug_menu/source_batch_20261028/CHECKPOINTS.json']=(json.dumps(checks,indent=2)+'\n').encode()
names=['ROOT_REVIEW.json','REVIEW.md','receipt.json','regression_results.json','intro-video-events.patch','video_event_regression.cpp','run_checks.py','compile_consumers.py','make_receipt.py','consumer-gates/results.json','consumer-gates/compile.log','consumer-gates/compile.rsp','pre/compile.log','pre/regression.log','pre/regression.rsp','post/compile.log','post/regression.log','post/regression.rsp']
for n in names:payloads[meta+'evidence/'+n]=(A/n).read_bytes()
receipt={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source40':BASE,'workflow40':WB,'source41':source,'source_tree':tree,'record':record,'owned_metadata_normalization':normalizations,'source_delta_paths':[P],'build_or_native':False,'normal_written':False,'public_refs_mutated':False,'replay_branch':'untouched and unmerged','excluded':['Scoring','CPU PerfMon','Environment season candidate'],'evidence_copies':'Source evidence bytes retained exactly; portable repo-relative paths below this metadata directory; original machine command paths retained as provenance only'}
save('PUBLICATION_RECEIPT.json',receipt);save('EOL_NORMALIZATION.json',normalizations)
payloads[meta+'PUBLICATION_RECEIPT.json']=(R/'PUBLICATION_RECEIPT.json').read_bytes();payloads[meta+'EOL_NORMALIZATION.json']=(R/'EOL_NORMALIZATION.json').read_bytes();payloads[meta+'publish.py']=Path(__file__).read_bytes()
payloads[meta+'README.md']=b'Private41 fixes the original startup video queue contract: raw48-byte VideoDefinition, channel40,64-byte wrapper, event508/509. Root independent source review reran the actual StateInterface/queue negative (exit17) and patched controls (exit0); seven actual consumer TUs compiled. Full ID, sound and keep flag survive. Exact original review, patch and compile evidence are copied under evidence/ with their retained byte hashes.\n\nFull shipping build and unbypassed EA/Criterion logo playback, completion and title transition remain required before public/normal delivery. No native/site credit. Scoring/CPU/Environment remain excluded and private Replay is untouched.\n\nTwo previously committed owned compile.cmd artifacts are normalized to LF in Git. Existing *.cmd text eol=crlf still checks them out as CRLF for cmd.exe; this corrects false dirty provenance. EOL_NORMALIZATION.json retains exact predecessor hashes. The shipping checkout dirtiness was observed and reported by the builder; this successor does not silently clobber it.\n'
files=[]
for i,(path,data) in enumerate(payloads.items()):
 p=R/'objects'/str(i);p.parent.mkdir(exist_ok=True);p.write_bytes(data);files.append((path,p))
objects=g(W,'hash-object','-w','--no-filters','--stdin-paths',input=('\n'.join(str(p) for _,p in files)+'\n').encode()).decode().splitlines();assert len(objects)==len(files)
staged=('160000 '+source+'\tb5-decomp\n'+''.join('100644 '+obj+'\t'+path+'\n' for (path,_),obj in zip(files,objects))).encode();g(W,'update-index','--index-info',input=staged,env=we)
wt=g(W,'write-tree',env=we).decode().strip();msg=b'Checkpoint startup video hotfix and clean owned batch metadata\n\nAppend the root-reviewed one-header event-boxing repair as private41, retaining actual negative/post regression and seven consumer compile evidence. Normalize only the two owned compile.cmd index blobs to LF for the existing eol=crlf worktree filter. Build and unbypassed logo playback remain pending.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n';workflow=g(W,'commit-tree',wt,'-p',WB,input=msg).decode().strip()
g(B,'-c','core.whitespace=cr-at-eol','diff','--check',BASE,source);g(W,'-c','core.whitespace=cr-at-eol','diff','--check',WB,workflow,'--','*.json','*.md','*.py')
for repo,new,old in [(B,source,BASE),(W,workflow,WB)]:g(repo,'update-ref',REF,new,old)
pins={'private_branch':'codex/source-next-20261029','source41':source,'workflow41':workflow,'source_tree':tree,'workflow_tree':wt,'source40':BASE,'workflow40':WB,'root_review_sha256':sha(review),'header_post_sha256':sha(post),'checkpoint_records':41,'metadata_root':meta,'owned_cmd_index_blobs_normalized_LF':True,'public_or_normal_modified':False,'build_native_pending':True}
save('LOCAL_PINS.json',pins);print('LOCAL_PINS '+json.dumps(pins),flush=True)
for repo,new,n in [(B,source,'source.push.log'),(W,workflow,'workflow.push.log')]:
 (R/n).write_bytes(g(repo,'push','origin',new+':'+REF));assert g(repo,'ls-remote','--heads','origin',REF).decode().split()[0]==new
save('REMOTE_PINS.json',pins);print('REMOTE_PINS '+json.dumps(pins),flush=True)
