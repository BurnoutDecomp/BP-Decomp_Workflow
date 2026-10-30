"""Bind exact Texture-only data and current-save inputs; enable launch only after exact peer PASS."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess
P=Path(__file__).resolve().parent;REPO=Path('D:/Reverse/BP-Decomp_Workflow')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 data=json.dumps(v,indent=2,ensure_ascii=False)+'\n'
 if not p.exists() or p.read_text(encoding='utf-8')!=data:p.write_text(data,encoding='utf-8')
ap=argparse.ArgumentParser();ap.add_argument('--peer-review',type=Path);a=ap.parse_args()
plan=load(P/'CASE_PLAN.json');source=load(P/'CASE_SOURCE_BINDINGS.json');copy=load(P/'evidence/CURRENT_PROFILE_COPY_RECEIPT.json');identity=load(P/'pre/TEXTURE_RUN_IDENTITY.json');run=identity['run_name'];suite='resource_windows';slot=62144
assert plan['active_native_suites']==[suite] and plan['fixture']['kind']=='current_normal_profile_copy'
assert plan['fixture']['path']==copy['fixture']['path'] and plan['fixture']['sha256']==copy['fixture']['sha256']
snapshot=Path(plan['fixture']['path']);original=Path(plan['fixture']['source_normal_path']);assert sha(snapshot)==sha(original)==plan['fixture']['sha256']
assert not snapshot.samefile(original) and copy['independent_copy'] and not copy['normal_original_written']
runtime=source['runtime_harness'];runtime_root=Path(runtime['runtime_root_path'])
runtime['executed_dependency_files']={}
for rel in ['tools/tests/_checks.ps1','tools/tests/known_asserts.txt','tools/tests/frame_stats.py','tools/diagnostics/_box_lock.ps1']:
 p=runtime_root/rel;runtime['executed_dependency_files'][rel]={'sha256':sha(p),'bytes':p.stat().st_size}
source.update(candidate_source=plan['candidate_source'],candidate_source_tree=plan['candidate_source_tree'],candidate_workflow=plan['candidate_workflow_source'],candidate_workflow_tree=plan['candidate_workflow_tree'],exe_sha256=plan['shipping_build']['exe_sha256'],build_receipt_sha256=plan['shipping_build']['receipt_sha256'],build_result_sha256=plan['shipping_build']['receipt_sha256'],build_result_schema='canonical_private_native_whole_link3019')
source['input_artifacts'].pop('tools/tests/fixtures/DISCO_collect_base.sav',None)
source['input_artifacts']['private_current_normal_profile_snapshot']={'path':str(snapshot),'bytes':snapshot.stat().st_size,'sha256':sha(snapshot),'scope':'External independent per-run user-save copy; bytes never included in packet/Git'}
source['input_artifacts']['workflow/progress/debug_menu/entries.json']['scope']='Historical site identity inventory retained; not a claim of current candidate workflow contents or site credit'
write(P/'CASE_SOURCE_BINDINGS.json',source)
manifest=sha(P/'MANIFEST.json') if (P/'MANIFEST.json').exists() else 'pending_packet_seal'
review=load(a.peer_review) if a.peer_review else None
ready=bool(review and str(review.get('status',review.get('verdict',''))).lower().startswith('pass') and review.get('packet_manifest_sha256',review.get('manifest_sha256'))==manifest)
if a.peer_review:assert ready,'Peer PASS must bind the exact final packet manifest'
if ready:
 peer_relative=str(a.peer_review.resolve().relative_to(REPO.resolve())).replace('\\','/')
 assert plan['parallel_native_policy']['policy_sha256'] in a.peer_review.read_text(),'Peer report must identify exact V5 policy as well as manifest'
root=P/'suites'/suite;objects=[load(root/name) for name in ['BINDING.json','STAGING.json','ROOT_PRELAUNCH_REVIEW.json']];b,s,r=objects
stage=root/'stage'/run;run_root=Path(plan['runtime_output_root']);run_dir=run_root/run
assert not stage.exists() and not run_dir.exists(),'Use a fresh exact run identity; no overwrite'
census_text=subprocess.check_output(['powershell.exe','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter \"Name='Burnout_PC.exe'\" | Select-Object ProcessId,Name,ExecutablePath,CreationDate | ConvertTo-Json -Compress"],text=True).strip()
census=json.loads(census_text or '[]');census=[census] if isinstance(census,dict) else census
census_path=P/'pre/TEXTURE_GAME_PROCESS_CENSUS.json';write(census_path,{'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'actual read-only Win32_Process CIM query','processes':census,'informational':True})
budget=load(P/plan['readonly_physical_budget']['path']);storage=[]
for volume in ['C','D']:
 free=shutil.disk_usage(volume+':/').free;required=budget['volumes'][volume]['initial_required_bytes'];assert free>=required,(volume,free,required)
 storage.append({'volume':volume,'available_bytes':free,'required_bytes':required,'pass':True})
storage_path=P/'pre/TEXTURE_STORAGE_ACTUAL.json';write(storage_path,{'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'volumes':storage,'normal_writes':False})
normal=plan['protected_config_source'];normal_roster=load(REPO/normal['roster_path']);normal_checks=[]
for row in normal_roster['runtime_payloads']+normal_roster['profile_config_log_preserved']:
 rel=row['relative_path'];p=REPO/'build/game'/rel;h=sha(p);mutable=rel in ['BrnGame.log','BrnGame.emergency.log'];current_profile=rel.replace('\\','/')=='Memcard/Profile.sav' and h==plan['fixture']['sha256']
 assert h==row['sha256'] or mutable or current_profile,rel
 normal_checks.append({'relative_path':rel,'sha256':h,'historical_sha256':row['sha256'],'bytes':p.stat().st_size,'mutable_log':mutable,'current_profile_copy_bound':current_profile})
write(P/'pre/TEXTURE_NORMAL_CURRENT.json',{'status':'pass','rows':normal_checks,'normal_writes':False,'writer_attribution':'none'})
common={'run_name':run,'suite':suite,'slot':slot,'status':'root_reviewed_ready','executor_authority':'/root/resource_native_resume under existing Root V8 and direct source22e follow-on delegation; fresh case peer still required','prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_source':plan['candidate_source'],'candidate_source_tree':plan['candidate_source_tree'],'candidate_workflow_source':plan['candidate_workflow_source'],'candidate_workflow_tree':plan['candidate_workflow_tree'],'candidate_exe_sha256':plan['shipping_build']['exe_sha256'],'root_delegation_sha256':plan['root_execution_delegation']['sha256'],'root_parallel_delegation_sha256':plan['root_execution_delegation']['sha256'],'root_execution_delegation_sha256':plan['root_execution_delegation']['sha256'],'storage_policy_receipt_sha256':plan['root_authorized_storage_policy']['receipt_sha256'],'min_free_gib':2,'normal_install_exe_sha256':normal['normal_install_exe_sha256'],'normal_identity_roster_sha256':normal['roster_sha256'],'packet_manifest_sha256':manifest,'case_plan_sha256':sha(P/'CASE_PLAN.json'),'case_source_bindings_sha256':sha(P/'CASE_SOURCE_BINDINGS.json'),'private_stage_root':str(stage),'stage_root':str(stage),'slot_directory':str(stage/'slot'),'data_directory':str(stage/'data'),'runtime_output_root':str(run_root),'runtime_run_directory':str(run_dir),'prelaunch_census_path':str(census_path),'prelaunch_census_sha256':sha(census_path),'storage_budget_current_path':str(storage_path),'storage_budget_current_sha256':sha(storage_path),'readonly_physical_budget_sha256':plan['readonly_physical_budget']['sha256'],'readonly_source_identities_sha256':plan['readonly_source_identities']['sha256'],'profile_fixture':plan['fixture'],'current_storage_budget_pass':True,'prelaunch_game_process_count':len(census),'allowed_peer_processes':[],'max_concurrent_other_games':100,'allow_concurrent_games':True,'candidate_execution_scope_id':plan['candidate_execution_scope']['suites'][suite]['scope_id'],'case_peer_review_status':'PASS' if ready else 'pending'}
for obj in objects:
 obj.update(common)
 for key in list(obj):
  if key.startswith('normal_profile_transition_'):obj.pop(key)

s.update(created_for_this_case=False,stage_created=False,game_launched=False,shipping_receipt_sha256=plan['shipping_build']['receipt_sha256'])
s['run_policy'].update(profile_fixture_sha256=plan['fixture']['sha256'],max_frame_count=28,min_free_gib=2,max_log_mib=64,full_data_copy=False,readonly_immutable_hardlinks=True,sidecar_reserve_bytes=100663296)
b.update(slot_reserved_for_this_case=True,baseline_profile_policy='Fresh independent current-user-save C snapshot copied to only the per-run slot profile; preserve the live normal original')
r.update(status='ready' if ready else 'pending_independent_concrete_review',protocol_reviewed=ready,scripts_reviewed=ready,provenance_reviewed=ready,private_stage_reviewed=ready,launch_authorized=ready,reviewer='/root/replay_integration_review' if ready else 'pending exact named peer',reviewed_utc=review.get('created_utc',datetime.datetime.now(datetime.timezone.utc).isoformat()) if ready else datetime.datetime.now(datetime.timezone.utc).isoformat(),observations='Current-save copy and Source22e private Texture7; actual native caption/pixels gate, split C output/D stage budgets, exact scoped restoration. No native/site credit from preparation.')
for obj in objects:
 obj['v5_parallel_monitor_review_status']='PASS' if ready else 'pending'
 obj['v5_parallel_monitor_review_packet_manifest_sha256']=manifest
 obj['v5_parallel_monitor_review_policy_sha256']=plan['parallel_native_policy']['policy_sha256']
 if ready:obj.update(v5_parallel_monitor_review_path=peer_relative,v5_parallel_monitor_review_sha256=sha(a.peer_review))
 else:obj.update(v5_parallel_monitor_review_path='',v5_parallel_monitor_review_sha256='')
write(root/'BINDING.json',b);write(root/'STAGING.json',s)
r['binding_sha256']=sha(root/'BINDING.json');r['staging_sha256']=sha(root/'STAGING.json');write(root/'ROOT_PRELAUNCH_REVIEW.json',r)
print(json.dumps({'status':'ready' if ready else 'concrete_pending_peer','run_name':run,'fixture_sha256':plan['fixture']['sha256'],'source':plan['candidate_source'],'normal_rows_verified':len(normal_checks),'volumes':storage,'normal_writes':False},indent=2))
