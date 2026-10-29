exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
import datetime
WBASE32=WB;WB='33df46f7db47d95db5db3c2003890c9e971234e1'
assert not subprocess.check_output(['git','-C',str(W),'diff','--name-only',WBASE32,WB,'--','b5-decomp','tools','progress/debug_menu/source_batch_20261028/CHECKPOINTS.json']).strip(),'non-metadata workflow drift'
C=json.loads((R/'COMPOSITION.json').read_text());CR=json.loads((R/'COMPILE_RECEIPT.json').read_text());assert CR['verdict']=='PASS_COMPILE_ONLY' and CR['source_tree']==C['source_tree']
assert json.loads((R/'INPUT_INTEGRITY.json').read_text())['status']=='PASS'
REF='refs/heads/codex/source-next-20261029';zero='0'*40
def run(repo,*args,input=None,env=None,check=True):
 p=subprocess.run(['git','-C',str(repo),*args],input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if check and p.returncode:raise RuntimeError(str(args)+'\n'+p.stderr.decode(errors='replace'))
 return p
def remote(repo,ref):return run(repo,'ls-remote','--heads','origin',ref).stdout.decode().split()
for repo,public_ref,expected in [(B,'refs/heads/dev',BASE),(W,'refs/heads/main',WB)]:
 assert remote(repo,public_ref)[0]==expected,'public ref drift'
 assert not remote(repo,REF),'private remote ref already exists'
 assert run(repo,'show-ref','--verify','--quiet',REF,check=False).returncode==1,'private local ref already exists'
shared_paths=[B/'src/GameSource/Graphics/BrnRendererModule.cpp',B/'src/GameSource/World/BrnWorldModule.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.h',W/'progress/status.json']
shared={str(p):sha(p.read_bytes()) for p in shared_paths}
statuses={str(repo):run(repo,'status','--porcelain=v1','--untracked-files=normal').stdout.decode() for repo in [W,B]}
env=dict(os.environ,GIT_INDEX_FILE=str(R/'source-publish.index'));parent=BASE;commits=[]
run(B,'read-tree',BASE,env=env)
descriptions={'traffic21':('Restore bounded Traffic lane reinsertion caller','Restore the two-attempt per-frame query, lane repair, sampled transform and physical-time reset from the independently reviewed exact method delta.'),'traffic22':('Restore Traffic streamer allow-failure policy','Pass the original final true constructor policy through the existing typed request path; preserve the reviewed source comments.'),'traffic23':('Restore Traffic split occupancy pressure','Use the real destination span count and reciprocal with scalar fused multiply-add, retaining guard and strict-minimum behavior.'),'traffic24':('Restore articulated Traffic emergency crash pairing','Retain role-specific reciprocal-link assertions and enqueue the counterpart in the existing emergency crash array; only the reviewed first-loop hunk changes.'),'effects32':('Restore original Effects callback formatting bounds','Pass literal32 to the two selected-name SPrintf calls while retaining33-byte event storage and all other callback behavior.'),'camera':('Restore compressed local Camera texture submission','Recover the reviewed four-argument void method and declaration, with prepared-texture queue metadata and the exact reviewed fixture-friend declarations.')}
for row in C['records']:
 for f in row['files']:
  actual=run(B,'rev-parse',':'+f['path'],env=env).stdout.decode().strip();assert actual==f['pre_blob'],f['path']
  run(B,'update-index','--cacheinfo','100644,'+f['post_blob']+','+f['path'],env=env)
 tree=run(B,'write-tree',env=env).stdout.decode().strip();title,body=descriptions[row['packet_id']]
 msg=(title+'\n\n'+body+'\n\nSource review and compile evidence only; no native or site credit.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n').encode()
 commit=run(B,'commit-tree',tree,'-p',parent,input=msg).stdout.decode().strip()
 assert run(B,'show','-s','--format=%B',commit).stdout.endswith(b'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n\n')
 row['source_commit']=commit;row['source_parent']=parent;row['source_tree']=tree;commits.append({'packet_id':row['packet_id'],'commit':commit,'parent':parent,'tree':tree});parent=commit
source=parent;assert commits[-1]['tree']==C['source_tree']
run(B,'-c','core.whitespace=cr-at-eol','diff','--check',BASE,source)
save('SOURCE_COMMITS.json',{'base':BASE,'source_commit':source,'source_tree':C['source_tree'],'commits':commits})
checks=json.loads(run(W,'show',WB+':progress/debug_menu/source_batch_20261028/CHECKPOINTS.json').stdout);assert len(checks['incremental_reviewed_source_passes'])==32
ids={'traffic21':'traffic_chunk21_reinsert_caller','traffic22':'traffic_chunk22_car_streamer_policy','traffic23':'traffic_chunk23_pressure_split_occupancy','traffic24':'traffic_chunk24_crashed_articulated_pairing','effects32':'effects_arbitrator_bound32','camera':'camera_x360_compressed_picture'}
limits={'traffic21':'Exact bounded caller and reset/setter only; missing positive request-list producer and complete module/query/runtime behavior remain unverified.','traffic22':'Constructor and request transport only; loader failure interpretation and full streaming completion are outside scope.','traffic23':'Prepared-runtime span occupancy only; console floating-point hardware and unprepared-runtime parity remain unverified.','traffic24':'Articulated first-loop emergency enqueue only; full owner scheduling and emergency drain/runtime remain unverified.','effects32':'Two SPrintf literal32 bounds only; event storage remains33 and source callback fixtures are not whole-engine/native proof.','camera':'Prepared-source method and existing host queue path only. Prepare, Update and GetLocalCameraPicture remain placeholders. Bridge event72 forwards GUI569 to PhotoBooth and its cached copy; queue timing and borrowed output-ring lifetime remain unverified.'}
for row in C['records']:
 record={**row,'packet_id':ids[row['packet_id']],'source_files':[{'path':f['path'],'pre_git_blob_oid':f['pre_blob'],'post_git_blob_oid':f['post_blob'],'post_raw_sha256':f['post_sha256']} for f in row['files']],'review_verdict':'pass_source_review','review_scope':limits[row['packet_id']],'validation':'Independent packet controls plus fresh source32-pre/final-candidate-post owning-TU and Camera caller compiles; zero warnings/errors.','native_game_launched':False,'affected_sites':[]}
 checks['incremental_reviewed_source_passes'].append(record)
checks.update(status='private38 source checkpoint; independent narrow source reviews and integration compiles pass; full build/native pending',workflow_branch='codex/source-next-20261029',workflow_base=WB,b5_source_branch='codex/source-next-20261029',b5_source_head=source,b5_base=BASE,review_policy='Each receipt retains its own limits; no site/native credit or public integration follows from this checkpoint')
assert len(checks['incremental_reviewed_source_passes'])==38
save('CHECKPOINTS38.json',checks)
meta='progress/debug_menu/source_next_20261029/'
receipt={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'private_ref':REF,'source_base':BASE,'workflow_base':WB,'source_commit':source,'source_tree':C['source_tree'],'source_commits':commits,'reviewed_record_count_before':32,'reviewed_record_count_after':38,'source_diff_paths':C['source_diff_paths'],'whole_game_build_or_link':False,'native_game_launched':False,'normal_written':False,'public_refs_changed':False,'site_credit':0,'native_credit':0,'shared_dirty_path_hashes_before':shared,'shared_status_before':statuses,'camera_delivery_note':'Derived actual patch from exact reviewed pre/post; existing Git CRLF/LF convention preserved per file. CAMERA_DELIVERY_BINDINGS and actual cached application/postimages seal delivery.','sound31_40':'Excluded pending fresh revision03 independent review','replay_private_branch':'Preserved untouched and unmerged','preparation_failures':'Response-file comment parser and missing sibling header initial failures retained; final12 compiles pass'}
save('PUBLICATION_RECEIPT.json',receipt)
wen=dict(os.environ,GIT_INDEX_FILE=str(R/'workflow-publish.index'));run(W,'read-tree',WB,env=wen);run(W,'update-index','--cacheinfo','160000,'+source+',b5-decomp',env=wen)
def add(path,data):
 oid=run(W,'hash-object','-w','--stdin',input=data).stdout.decode().strip();run(W,'update-index','--add','--cacheinfo','100644,'+oid+','+path,env=wen)
add('progress/debug_menu/source_batch_20261028/CHECKPOINTS.json',(R/'CHECKPOINTS38.json').read_bytes())
members=['COMPOSITION.json','CAMERA_DELIVERY_BINDINGS.json','DEPENDENCY_DRIFT.json','INPUT_INTEGRITY.json','COMPILE_RECEIPT.json','OBSERVED_DEPENDENCIES.json','SOURCE_COMMITS.json','PUBLICATION_RECEIPT.json','SOURCE_DIFF.patch','prepare.py','compile_prepare.py','verify_compile.py','verify_inputs.py','publish.py','compile.cmd','response_preparation_failure.log','missing_sibling_header_failure.log']+[x.name for x in R.glob('*.patch') if x.name!='SOURCE_DIFF.patch']+[x.name for x in R.glob('pre_*.log')]+[x.name for x in R.glob('post_*.log')]+[x.name for x in R.glob('pre_*.rsp')]+[x.name for x in R.glob('post_*.rsp')]+[x.name for x in R.glob('pre_*.exit')]+[x.name for x in R.glob('post_*.exit')]
for n in sorted(set(members)):add(meta+n,(R/n).read_bytes())
for row in C['records']:
 add(meta+'reviews/'+row['packet_id']+'.md',(S/row['review_path']).read_bytes())
 if row['packet_id']=='traffic21':add(meta+'reviews/traffic21_original_delivery_failure.md',(S/'review_traffic_chunk21_reinsert_caller_sol_20261029/REVIEW.md').read_bytes())
readme='Private38-record source checkpoint based on public source32. Adds Traffic21-24, two Effects SPrintf bounds and the Camera prepared-texture submission method. Eight source paths; six narrow source reviews and12 fresh integration compiles pass with zero warnings/errors. Camera delivery binds exact reviewed pre/post bytes while preserving existing Git line endings. Actual compiler-read headers match pinned source32/candidate Git blobs; source fallback into the shared tree is absent.\n\nSource evidence only. Full shipping build/link, native gameplay, camera capture/event timing and menu/site credit remain pending. Sound31-40 and the private Replay branch are excluded. Normal/public refs, shared Renderer/World/status WIP and ledger counts are unchanged. Earlier failed patch/preparation attempts remain explicit.\n'
add(meta+'README.md',readme.encode());wt=run(W,'write-tree',env=wen).stdout.decode().strip()
msg=b'Checkpoint reviewed Traffic, Effects and Camera source follow-ons\n\nBind six exact source deltas and independent review limits after public source32. Retain actual pre/post compile receipts, observed dependencies, valid patch transports and source32-to38 receipt lineage. Full build and native validation remain pending.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n'
workflow=run(W,'commit-tree',wt,'-p',WB,input=msg).stdout.decode().strip()
run(W,'-c','core.whitespace=cr-at-eol','diff','--check',WB,workflow,'--','*.json','*.md','*.py')
for repo,new in [(B,source),(W,workflow)]:run(repo,'update-ref','--create-reflog',REF,new,zero)
for repo,new,n in [(B,source,'source.push.log'),(W,workflow,'workflow.push.log')]:
 p=run(repo,'push','origin',new+':'+REF);(R/n).write_bytes(p.stdout+p.stderr);assert remote(repo,REF)[0]==new
assert all(sha(Path(p).read_bytes())==h for p,h in shared.items())
for repo,public_ref,expected in [(B,'refs/heads/dev',BASE),(W,'refs/heads/main',WB)]:assert remote(repo,public_ref)[0]==expected
out={'private_branch':'codex/source-next-20261029','source_remote_head':source,'workflow_remote_head':workflow,'source_tree':C['source_tree'],'workflow_tree':wt,'source_commits':commits,'source_diff_paths':C['source_diff_paths'],'shared_dirty_paths_preserved':True,'normal_written':False,'public_refs_unchanged':True,'metadata_root':meta,'reviewed_checkpoint_records':38,'compile_count':12,'compile_warnings':0,'source32_base':BASE,'workflow32_base':WBASE32,'workflow_metadata_base':WB}
save('REMOTE_HEADS.json',out);print(json.dumps(out,indent=2))
