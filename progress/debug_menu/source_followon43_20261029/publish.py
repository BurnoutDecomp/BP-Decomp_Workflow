exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
import datetime
SRC=json.loads((R/'SOURCE_COMMITS.json').read_text());C=json.loads((R/'COMPOSITION.json').read_text());CR=json.loads((R/'COMPILE_RECEIPT.json').read_text());assert CR['verdict']=='PASS_COMPILE_ONLY' and CR['source_tree']==SRC['source_tree']==C['source_tree'];SOURCE=SRC['source43'];REF='refs/heads/codex/source-followon-20261029'
def run(repo,*args,input=None,env=None,check=True):
 p=subprocess.run(['git','-C',str(repo),*args],input=input,env=env,capture_output=True)
 if check and p.returncode:raise RuntimeError(str(args)+'\n'+p.stderr.decode(errors='replace'))
 return p
def remote(repo,ref):return run(repo,'ls-remote','--heads','origin',ref).stdout.decode().split()
for repo in [B,W]:
 assert not remote(repo,REF),'new private branch already exists remotely'
 assert run(repo,'show-ref','--verify','--quiet',REF,check=False).returncode==1,'new private branch already exists locally'
assert remote(B,'refs/heads/dev')[0]==BASE,'delivered source41 canonical dev changed'
WB=remote(W,'refs/heads/main')[0];run(W,'fetch','--no-tags','origin',WB)
dirty=[B/'src/GameSource/Graphics/BrnRendererModule.cpp',B/'src/GameSource/World/BrnWorldModule.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.cpp',B/'src/GameSource/World/BrnWorldModuleIO_DispatchInputBuffer.h',W/'progress/status.json'];before={str(p):sha(p.read_bytes()) for p in dirty}
checks=json.loads(run(W,'show',WB+':progress/debug_menu/source_batch_20261028/CHECKPOINTS.json').stdout);assert len(checks['incremental_reviewed_source_passes'])==41
for row in SRC['records']:
 checks['incremental_reviewed_source_passes'].append({**row,'packet_id':'scoring_payload_ordered_distance' if row['packet_id']=='scoring' else 'cpu_perfmon_graph_math_finite_witness','source_files':[{'path':f['path'],'pre_git_blob_oid':f['pre_blob'],'post_git_blob_oid':f['post_blob'],'post_raw_sha256':f['post_sha256']} for f in row['files']],'review_verdict':'pass_source_review','native_game_launched':False,'affected_sites':[],'validation':'Independent source/negative/post control review and eight fresh full owning-TU pre/post compiles against delivered41; no shared-source fallback','review_scope':'Full signed64 stunt payload and ordered NaN distance rejection only; no gameplay/network native credit.' if row['packet_id']=='scoring' else 'Original graph floating-point operation ordering and finite extracted-body witness only; no native rendering/site credit.'})
checks.update(status='private43 reviewed CPU and scoring source checkpoint; build/native pending',workflow_branch='codex/source-followon-20261029',workflow_base=WB,b5_source_branch='codex/source-followon-20261029',b5_source_head=SOURCE,b5_base=BASE)
save('CHECKPOINTS43.json',checks)
receipt={'schema':1,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'private_branch':'codex/source-followon-20261029','source41':BASE,'workflow_parent':WB,'source43':SOURCE,'source_tree':SRC['source_tree'],'source_delta_paths':C['source_diff_paths'],'checkpoint_records':43,'review_report_sha256':sha(review.read_bytes()),'owning_TU_pre_post_compiles':8,'warnings':0,'unique_observed_headers':846,'source32_to41_observed_header_drift':[],'source_snapshot_headers':2620,'site_credit':0,'native_credit':0,'normal_written':False,'public_refs_mutated':False,'shared_dirty_hashes_before':before,'previous_completed_source_next_branch':'retired, not recreated','private_Replay':'untouched and unmerged','Environment':'excluded pending independent review','CI_guard':'separate six-path revision under Root review; this private checkpoint does not apply or publish the guard'}
save('PUBLICATION_RECEIPT.json',receipt)
we=dict(os.environ,GIT_INDEX_FILE=str(R/'workflow.index'));run(W,'read-tree',WB,env=we)
payloads={'progress/debug_menu/source_batch_20261028/CHECKPOINTS.json':(R/'CHECKPOINTS43.json').read_bytes()};meta='progress/debug_menu/source_followon43_20261029/'
names=['COMPOSITION.json','INPUT_INTEGRITY.json','COMPILE_RECEIPT.json','OBSERVED_DEPENDENCIES.json','DEPENDENCY_DRIFT.json','SOURCE_COMMITS.json','PUBLICATION_RECEIPT.json','prepare.py','verify_compile.py','commit_source.py','publish.py','SOURCE_DIFF.patch','scoring.patch','cpu.patch','compile.cmd']
names += [p.name for p in R.glob('pre_*.log')]+[p.name for p in R.glob('post_*.log')]+[p.name for p in R.glob('pre_*.rsp')]+[p.name for p in R.glob('post_*.rsp')]+[p.name for p in R.glob('pre_*.exit')]+[p.name for p in R.glob('post_*.exit')]
transport=[]
for n in names:
 raw=(R/n).read_bytes();data=raw.replace(b'\r\n',b'\n') if n.endswith(('.cmd','.bat')) else raw;payloads[meta+n]=data
 if raw!=data:transport.append({'path':meta+n,'physical_run_sha256':sha(raw),'Git_index_LF_sha256':sha(data),'policy':'Existing *.cmd text eol=crlf checks out the original CRLF commands; no false dirty raw CRLF index blob'})
payloads[meta+'COMMAND_EOL.json']=(json.dumps(transport,indent=2)+'\n').encode();payloads[meta+'REVIEW_REPORT.md']=review.read_bytes()
for root in ['scoring_resume_20261029','scoring_resume_20261029_exact_eol','cpu_perfmon_graph_math_witness_20261029']:
 for n in ['SEAL.json','MANIFEST.json','MANIFEST.sha256','DELIVERY.json']:
  p=S/root/n
  if p.exists():payloads[meta+'author/'+root+'/'+n]=p.read_bytes()
payloads[meta+'README.md']=b'Private43 contains the independently approved scoring payload/ordered-distance repair and CPU PerfMon graph-math finite witness after delivered41. Five exact source paths, all reviewed32 preimages still identical in delivered41. Eight full actual pre/post TU compiles pass with zero warnings/errors;846 observed compiler headers match pinned Git blobs and no observed source header drifts32-to41. Original preimage failures and author/reviewer seals remain explicit. Scoring mixed-EOL caller bytes are preserved exactly.\n\nSource evidence only. No full shipping link, native game/network/rendering proof, site credit or normal refresh. Environment awaits independent review; private Replay is untouched. The completed source-next branch stays retired; this is the new source-followon branch. CI publication protection is a separate reviewed workflow fix and is not bundled here.\n'
files=[]
for i,(path,data) in enumerate(payloads.items()):
 p=R/'objects'/str(i);p.parent.mkdir(exist_ok=True);p.write_bytes(data);files.append((path,p))
objects=run(W,'hash-object','-w','--no-filters','--stdin-paths',input=('\n'.join(str(p) for _,p in files)+'\n').encode()).stdout.decode().splitlines();assert len(objects)==len(files)
entries='160000 '+SOURCE+'\tb5-decomp\n'+''.join('100644 '+obj+'\t'+path+'\n' for (path,_),obj in zip(files,objects));run(W,'update-index','--index-info',input=entries.encode(),env=we);tree=run(W,'write-tree',env=we).stdout.decode().strip()
msg=b'Checkpoint reviewed scoring and CPU graph-math follow-ons privately\n\nKeep delivered41 as the source parent and preserve exact reviewed mixed-EOL source bytes. Retain the combined independent report, author seals, negative/post witnesses and eight clean full-TU integration compiles. No build/native/site or normal-installation claim.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n';workflow=run(W,'commit-tree',tree,'-p',WB,input=msg).stdout.decode().strip();run(W,'-c','core.whitespace=cr-at-eol','diff','--check',WB,workflow,'--','*.json','*.py','*.md')
for repo,new in [(B,SOURCE),(W,workflow)]:run(repo,'update-ref','--create-reflog',REF,new,'0'*40)
out={'private_branch':'codex/source-followon-20261029','source43':SOURCE,'workflow43':workflow,'source_tree':SRC['source_tree'],'workflow_tree':tree,'source41':BASE,'workflow_parent':WB,'checkpoint_records':43,'source_paths':C['source_diff_paths'],'compile_count':8,'warnings':0,'normal_or_public_modified':False,'metadata_root':meta};save('LOCAL_PINS.json',out)
print('LOCAL_PINS '+json.dumps(out),flush=True)
for repo,new,n in [(B,SOURCE,'source.push.log'),(W,workflow,'workflow.push.log')]:
 p=run(repo,'push','origin',new+':'+REF);(R/n).write_bytes(p.stdout+p.stderr);assert remote(repo,REF)[0]==new
assert all(sha(Path(p).read_bytes())==h for p,h in before.items());save('REMOTE_PINS.json',out);print('REMOTE_PINS '+json.dumps(out),flush=True)
