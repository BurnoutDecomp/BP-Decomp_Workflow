exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
import datetime
C=json.loads((R/'COMPOSITION.json').read_text());assert json.loads((R/'COMPILE_RECEIPT.json').read_text())['source_tree']==C['source_tree'];assert json.loads((R/'PRIOR38_COMPILE_REUSE.json').read_text())['prior_all1278_dependency_hashes_still_match']
REF='refs/heads/codex/source-next-20261029'
def run(repo,*a,env=None,input=None):
 p=subprocess.run(['git','-C',str(repo),*a],env=env,input=input,capture_output=True)
 if p.returncode:raise RuntimeError(str(a)+'\n'+p.stderr.decode(errors='replace'))
 return p.stdout+p.stderr if a and a[0]=='push' else p.stdout
def remote(repo,ref):return run(repo,'ls-remote','--heads','origin',ref).decode().split()[0]
for repo,expected in [(B,BASE),(W,WB)]:assert run(repo,'rev-parse',REF).decode().strip()==remote(repo,REF)==expected
public_before={'b5_dev':remote(B,'refs/heads/dev'),'workflow_main':remote(W,'refs/heads/main')}
dirty=[B/'src/GameSource/Graphics/BrnRendererModule.cpp',B/'src/GameSource/World/BrnWorldModule.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.h',W/'progress/status.json'];before={str(p):sha(p.read_bytes()) for p in dirty}
env=dict(os.environ,GIT_INDEX_FILE=str(R/'source-publish.index'));run(B,'read-tree',BASE,env=env);parent=BASE;commits=[]
for row in C['records']:
 for f in row['files']:
  assert run(B,'rev-parse',':'+f['path'],env=env).decode().strip()==f['pre_blob']
  run(B,'update-index','--cacheinfo','100644,'+f['post_blob']+','+f['path'],env=env)
 tree=run(B,'write-tree',env=env).decode().strip()
 title='Restore original reverse exhaust voice update guards' if row['packet_id']=='sound31_40' else 'Route normal cameras through the active testbed state'
 body='Use the dynamic mixer helper independently of the separate car submix and retain pointer-guarded reverse voice setters plus unconditional wrapper update.' if row['packet_id']=='sound31_40' else 'Test the embedded state GENERIC_UPDATE value through IsActive in both camera readers, and remove the phantom duplicate selector member.'
 msg=(title+'\n\n'+body+'\n\nFresh independent source review and owning-TU compiles pass. Source/control evidence only; no native audio or camera playback claim.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n').encode();commit=run(B,'commit-tree',tree,'-p',parent,input=msg).decode().strip()
 assert b'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>' in run(B,'show','-s','--format=%B',commit)
 row.update(source_commit=commit,source_parent=parent,source_tree=tree);commits.append({'packet_id':row['packet_id'],'commit':commit,'parent':parent,'tree':tree});parent=commit
source=parent;assert tree==C['source_tree'];run(B,'-c','core.whitespace=cr-at-eol','diff','--check',BASE,source)
save('SOURCE_COMMITS.json',{'base':BASE,'source_commit':source,'source_tree':tree,'commits':commits})
checks=json.loads(run(W,'show',WB+':progress/debug_menu/source_batch_20261028/CHECKPOINTS.json'));assert len(checks['incremental_reviewed_source_passes'])==38
limits={'sound31_40':'Exact DualGinsuExhaustEffect ProcessUpdate revision03 only. Separate dynamic-mixer and reverse-voice predicates; no audible/PCM/native or complete effect chain claim. Earlier revision01/02 FAIL records remain unchanged.','arb_testbed':'Exact IsActive GENERIC_UPDATE predicate, two camera readers and removal of the phantom selector only. Author has no SEAL; pinned integrity files and fresh combined independent report bind this revision. No native camera/ICE/assets/pixels claim.'}
for row in C['records']:
 checks['incremental_reviewed_source_passes'].append({**row,'packet_id':'sound_debug_controls_31_40_revision03' if row['packet_id']=='sound31_40' else 'arb_state_testbed_normal_camera','source_files':[{'path':f['path'],'pre_git_blob_oid':f['pre_blob'],'post_git_blob_oid':f['post_blob'],'post_raw_sha256':f['post_sha256']} for f in row['files']],'review_verdict':'pass_source_review','review_scope':limits[row['packet_id']],'fresh_integration_pre_post_owning_TU_compiles':6,'native_game_launched':False,'affected_sites':[]})
checks.update(status='private40 source checkpoint; narrow independent source reviews and integration compiles pass; full build/native pending',workflow_base=WB,b5_source_head=source,b5_base=BASE)
save('CHECKPOINTS40.json',checks)
receipt={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'private_ref':REF,'source38':BASE,'workflow38':WB,'source_commit':source,'source_tree':tree,'source_commits':commits,'checkpoint_records':40,'added_source_paths':C['source_diff_paths'],'complete_source32_delta_paths':run(B,'diff','--name-only',PUBLIC,source).decode().splitlines(),'source_review_report_sha256':sha(report.read_bytes()),'new_owning_TU_compiles':6,'prior_owning_caller_compiles':12,'prior_compiles_reused_only_after_header_intersection_and_all1278_hash_reverification':True,'warnings':0,'shared_dirty_hashes_before':before,'public_heads_before':public_before,'public_refs_mutated_by_this_task':False,'normal_written':False,'native_game':False,'whole_game_build_or_link':False,'site_credit':0,'native_credit':0,'source38_receipts_retained':True,'replay_private_branch':'untouched and unmerged','excluded_pending_independent_review':['Scoring exact-EOL four-path patch','CPU PerfMon finite-witness packet']}
save('PUBLICATION_RECEIPT.json',receipt)
we=dict(os.environ,GIT_INDEX_FILE=str(R/'workflow-publish.index'));run(W,'read-tree',WB,env=we);run(W,'update-index','--cacheinfo','160000,'+source+',b5-decomp',env=we)
def add(path,data):
 obj=run(W,'hash-object','-w','--stdin',input=data).decode().strip();run(W,'update-index','--add','--cacheinfo','100644,'+obj+','+path,env=we)
meta='progress/debug_menu/source_next_followon40_20261029/'
add('progress/debug_menu/source_batch_20261028/CHECKPOINTS.json',(R/'CHECKPOINTS40.json').read_bytes())
for p in R.iterdir():
 if p.is_file() and (p.suffix in ('.py','.json','.patch','.rsp','.log','.exit','.cmd')) and p.name!='CHECKPOINTS40.json':add(meta+p.name,p.read_bytes())
add(meta+'REVIEW_REPORT.md',report.read_bytes());add(meta+'RETIRED_REFS.json',(P/'RETIRED_REFS.json').read_bytes())
for n in pins:add(meta+'arb_author/'+n,(arb/n).read_bytes())
for n in ['SEAL.json','MANIFEST.sha256']:add(meta+'sound_author/'+n,(sound/n).read_bytes())
readme='Private40-record checkpoint adds the independently approved Sound31-40 revision03 and ArbStateTestbed normal-camera source fix after private38. Four new source paths, all exact source32/source38 preimages; valid LF patches and six fresh actual pre/post owning-TU compiles pass with zero warnings/errors.737 observed headers are bound to source38/candidate Git blobs. None of the newly changed headers occurs in the prior six postcompile dependency sets, and all1,278 prior input hashes still match, so the prior12 compile receipts remain applicable.\n\nNo whole-game build/link, native audio/camera/ICE, normal refresh, public integration, ledger/site or original-no-op credit. Source38 and rejected earlier Sound revisions remain distinct. Private Replay stays unmerged. Scoring and CPU PerfMon remain excluded pending independent review.\n';add(meta+'README.md',readme.encode())
wt=run(W,'write-tree',env=we).decode().strip();msg=b'Checkpoint reviewed Sound and testbed camera source follow-ons\n\nAdvance private38 to40 with exact source pins, the fresh independent report, valid patch transports and six clean integration compiles. Reverify prior source38 dependency hashes and preserve all evidence limits.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n';workflow=run(W,'commit-tree',wt,'-p',WB,input=msg).decode().strip();run(W,'-c','core.whitespace=cr-at-eol','diff','--check',WB,workflow,'--','*.json','*.md','*.py')
for repo,new,old in [(B,source,BASE),(W,workflow,WB)]:run(repo,'update-ref',REF,new,old)
for repo,new,n in [(B,source,'source.push.log'),(W,workflow,'workflow.push.log')]:
 (R/n).write_bytes(run(repo,'push','origin',new+':'+REF));assert remote(repo,REF)==new
assert all(sha(Path(p).read_bytes())==h for p,h in before.items())
out={'private_branch':'codex/source-next-20261029','source_remote_head':source,'workflow_remote_head':workflow,'source_tree':tree,'workflow_tree':wt,'source38':BASE,'workflow38':WB,'source_commits':commits,'new_paths':C['source_diff_paths'],'complete_source32_delta_paths':receipt['complete_source32_delta_paths'],'checkpoint_records':40,'new_compile_count':6,'earlier_compile_count':12,'warnings':0,'normal_written':False,'public_refs_mutated_by_this_task':False,'public_heads_after':{'b5_dev':remote(B,'refs/heads/dev'),'workflow_main':remote(W,'refs/heads/main')},'shared_dirty_hashes_preserved':True,'metadata_root':meta};save('REMOTE_HEADS.json',out);print(json.dumps(out,indent=2))
