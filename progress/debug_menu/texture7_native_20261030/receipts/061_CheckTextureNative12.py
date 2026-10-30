"""Read-only Texture7 evidence validation; no launch and no canonical credit edits."""
from pathlib import Path
import argparse,hashlib,json,re,runpy,sys
sys.dont_write_bytecode=True
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def profile_progress_witness(lines,patterns):
 rows=[]
 for pattern in patterns:
  matches=[{'line_index_zero_based':i,'line':line} for i,line in enumerate(lines) if re.search(pattern,line)]
  if not matches:raise ValueError('missing native current-profile witness: '+pattern)
  rows.append({'pattern':pattern,'matches':matches})
 return rows
def check(packet,run,pixel=None):
 failures=[];pending=[]
 def need(value,text):
  if not value:failures.append(text)
 plan=read(packet/'CASE_PLAN.json');scope=plan['candidate_execution_scope']['suites']['resource_windows'];expected=plan['shipping_build']['exe_sha256']
 need(expected=='ccdbfa54ca4f51a776f525ccd3760ff020307cbb33b509a700237f841bc21b54' and plan['candidate_source']=='22e673523a69a7a710d53a2bbba61efa0824700c','candidate/source differs from new private baseline')
 need(scope['site_ids']==['CgsResource::DebugComponent::InitWindows#'+str(i).zfill(4) for i in [7,8,9,11,12,13,14]],'selected Texture7 sites differ')
 manifest=read(packet/'MANIFEST.json');seal=read(packet/'SEAL.json')
 need(seal['manifest_sha256']==digest(packet/'MANIFEST.json'),'packet seal differs')
 for row in manifest['files']:
  path=(packet/row['path']).resolve()
  need(path.is_relative_to(packet.resolve()) and path.is_file() and path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],'frozen code/evidence differs: '+row['path'])
 names=['PRELAUNCH.json','STAGING_RECEIPT.json','RESOURCE_DRIVER_RECEIPT.json','RESOURCE_RESTORE_RECEIPT.json','RESOURCE_PHASE_DONE.json','RESOURCE_PHASE_DONE_REQUEST.json','RESOURCE_PHASE_REQUEST_MONITOR_RECEIPT.json','flow-terminal.json','result.json','POSTCHECK.json','DATA_SOURCE_MANIFEST.json','DATA_STAGE_PRELAUNCH_MANIFEST.json','DATA_COPY_RECEIPT.json','TEXTURE_PROVIDER_PROBE.json','TEXTURE_PROVIDER_GATE.json','TEXTURE_PROVIDER_GATE_VALIDATED.json','NORMAL_PROTECTION_BEFORE.json','NORMAL_PROTECTION_AFTER.json']
 missing=[name for name in names if not (run/name).is_file()]
 if missing:return {'status':'FAIL','failures':['missing native evidence: '+x for x in missing],'pending':[]}
 docs={name:read(run/name) for name in names};driver=docs['RESOURCE_DRIVER_RECEIPT.json'];pre=docs['PRELAUNCH.json'];stage=docs['STAGING_RECEIPT.json'];restore=docs['RESOURCE_RESTORE_RECEIPT.json'];post=docs['POSTCHECK.json'];terminal=docs['flow-terminal.json'];result=docs['result.json'];done=docs['RESOURCE_PHASE_DONE.json'];request=docs['RESOURCE_PHASE_DONE_REQUEST.json'];monitor=docs['RESOURCE_PHASE_REQUEST_MONITOR_RECEIPT.json']
 proc=driver['process'];slotdir=Path(stage['staged_exe_path']).parent
 need(driver['status']=='complete' and driver['restore_complete'] and driver['phase_names']==scope['phase_names'] and driver['phase_count']==11,'driver/actions/restoration did not complete exact11phase scope')
 need(proc['slot']==62144 and stage['slot']==62144 and pre['slot']==62144 and Path(proc['image_path']).resolve()==(slotdir/'Burnout_PC.exe').resolve() and digest(slotdir/'Burnout_PC.exe')==expected and proc['start_ticks']>0,'owned PID/start/slot/image differs')
 need(result['verdict']=='PASS' and result['as_expected'] is True and result.get('asserts')==0,'strict native case failed or asserted')
 need(terminal['success'] and terminal['helper_cleanup_complete'] and terminal['profile_restoration_complete'] and terminal['flow_status']['owned_cleanup_complete'] and terminal['flow_status']['input_reset_complete'],'terminal owned input/process/helper/profile cleanup incomplete')
 need(post['status']=='normal_files_and_profiles_unchanged' and post['no_owned_game'] and post['profile_restored'] and post['private_config_unchanged'] and post['source_assets_unchanged'] and post['immutable_assets_unchanged'] and post['shipping_payload_unchanged'] and post['runtime_overlay_unchanged'] and post['phase_stop_complete'],'private postconditions failed')
 need(post['dump_cleanup_receipt_complete'] and driver['dump_cleanup']=='deleted_hash_match_under_mutex','serialized Dump Stats cleanup failed')
 normal_before=docs['NORMAL_PROTECTION_BEFORE.json'];normal_after=docs['NORMAL_PROTECTION_AFTER.json']
 need(len(normal_before['rows'])==len(normal_after['rows'])==36 and normal_after['pass'] and normal_after['nonlog_drift']==[] and normal_before['normal_writes_performed'] is False and normal_after['normal_writes_performed'] is False,'current normal36 nonlogs not independently protected')
 fixture=plan['fixture'];snapshot=Path(fixture['path']);copy_receipt=read(packet/fixture['snapshot_receipt_path'])
 need(fixture['kind']=='current_normal_profile_copy' and snapshot.drive.upper()=='C:' and not snapshot.resolve().is_relative_to(packet.resolve()) and snapshot.is_file() and snapshot.stat().st_size==fixture['bytes'] and digest(snapshot)==fixture['sha256'] and digest(packet/fixture['snapshot_receipt_path'])==fixture['snapshot_receipt_sha256'] and copy_receipt['independent_copy'] and copy_receipt['same_file'] is False and copy_receipt['source_before_after_stable'] and copy_receipt['normal_original_written'] is False and pre['profile_fixture_sha256']==fixture['sha256'],'current normal profile was not the exact independent per-run private copy')
 need(done['driver_receipt_sha256']==digest(run/'RESOURCE_DRIVER_RECEIPT.json') and done['restore_receipt_sha256']==digest(run/'RESOURCE_RESTORE_RECEIPT.json') and done['phase_actions_complete'] and done['restoration_complete'] and done['driver_process_exit_verified'],'phase completion not bound to exact restored driver')
 need(request['status']=='exact_owned_phase_completion_stop_requested' and request['event_set'] and request['process_id']==proc['pid'] and request['slot']==62144 and monitor['status']=='exact_owned_phase_event_requested' and monitor['request_receipt_sha256']==digest(run/'RESOURCE_PHASE_DONE_REQUEST.json'),'owned phase-event stop/request evidence differs')
 need(pre['candidate_source']==plan['candidate_source'] and pre['candidate_workflow_source']==plan['candidate_workflow_source'] and pre['candidate_exe_sha256']==expected,'runtime and executable provenance conflated')
 need(Path(run).parent.resolve()==Path(plan['runtime_output_root']).resolve() and Path(stage['stage_root']).drive.upper()=='D:' and run.drive.upper()=='C:','split C output/D paired stage changed')
 for key in ['storage_budget_before_data_copy','storage_budget_before_run_case']:
  records=pre.get(key,{}).get('records',[])
  need(len(records)==2 and {x['volume'] for x in records}=={'C','D'} and all(x['pass'] and x['floor_bytes']==2147483648 and x['available_bytes']>=x['required_bytes'] for x in records),'fresh two-volume planned budget proof missing: '+key)
 source=docs['DATA_SOURCE_MANIFEST.json'];copied=docs['DATA_COPY_RECEIPT.json'];before=docs['DATA_STAGE_PRELAUNCH_MANIFEST.json']
 frozen=read(Path('D:/Reverse/BP-Decomp_Workflow')/plan['frozen_data_source']['snapshot_receipt_path'])['roster']
 expected_rows={k.replace('\\','/'):(v['bytes'],v['sha256']) for k,v in frozen.items()}
 for name,rows in [('source',source['files']),('copy',copied['copied_files']),('stage',before['files'])]:
  actual={x['path']:(x['bytes'],x['sha256']) for x in rows}
  need(len(rows)==len(actual)==5622 and actual==expected_rows,'exact immutable roster paths/size/hash differ: '+name)
 need(copied['same_file_identity_count']==copied['source_target_readonly_count']==5622 and copied['source_identity_proof_sha256']==plan['readonly_source_identities']['sha256'] and copied['whole_volume_delta_used_for_pass_fail'] is False,'readonly asset same-ID/actual metadata strategy differs')
 need(copied['excluded_runtime_files']==source['selection']['excluded_runtime_files'] and before['mutable_count']==0,'mutable source exclusions not separately recorded/absent')
 base=runpy.run_path(str(packet/'CheckResourceNativeBatch.py'),run_name='texture_validation_library')
 values=base['validate_readback_groups'](packet,'resource_windows',run,driver,stage,failures)
 need(restore['status']=='restored' and len(restore['comparisons'])==3 and all(x['matches'] and x['baseline']==x['restored'] for x in restore['comparisons']),'captured three control baseline not exactly restored')
 scripts={x['name']:x for x in driver['source_script_receipts']}
 for row in scripts.values():
  p=Path(row['evidence_path']);need(p.is_file() and digest(p)==row['sha256'],'retained actual script differs: '+row['name'])
  need(not any(re.match(r'\s*SAVE\s',line,re.I) or 'Replay State' in line for line in row['lines']),'unapproved whole SAVE/Replay stimulus')
 callbacks={'texture_next_callback':('N','Next Texture'),'texture_previous_callback':('P','Prev Texture'),'texture_next_page_callback':('G','Next Texture Page'),'texture_previous_page_callback':('R','Prev Texture Page')}
 actions=[x for x in driver['input_receipts'] if x.get('kind')=='bound_phase']
 need([x['phase'] for x in actions]==scope['phase_names'],'bound native actions differ')
 for index,action in enumerate(actions,1):
  need(action['virtual_key']==112 and action['binding']=='F1' and action['slot']==62144 and action['phase_sequence']==index,'unscoped/misordered phase input')
  if action['phase'] in callbacks:
   alias,leaf=callbacks[action['phase']];lines=scripts[action['script']+'.txt']['lines'];definition='ALIAS '+alias+' "Core/Resource/'+leaf+'"';call='CALL '+alias
   need(definition in lines and call in lines and lines.index(definition)<lines.index(call),'actual callback not named/defined before call: '+leaf)
 frames=driver['frame_receipts'];need(len(frames)==28,'exact28 owner-bound captures missing')
 rawlog=(slotdir/'BrnGame.log').read_text(encoding='utf-8-sig',errors='replace').splitlines();frame_names={x['name'] for x in frames}
 profile_rows=[]
 try:profile_rows=profile_progress_witness(rawlog,plan['native_profile_witness']['required_patterns'])
 except ValueError as error:need(False,str(error))
 for seq,frame in enumerate(frames,1):
  path=run/'frames'/frame['name'];ack=frame['ack_line'];m=re.fullmatch(r'\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)',ack)
  need(m is not None and ack in rawlog and int(m[1])==proc['pid'] and int(m[2])==62144 and int(m[3])==seq==frame['sequence'] and int(m[4])==frame['present'] and m[5]==frame['name'],'frame owner/sequence/ACK differs: '+frame['name'])
  need(path.is_file() and digest(path)==frame['sha256'] and base['validate_native_bmp'](path.read_bytes(),frame),'exact native BMP hash/orientation/extent differs: '+frame['name'])
 probe=docs['TEXTURE_PROVIDER_PROBE.json'];gate=docs['TEXTURE_PROVIDER_GATE.json'];validated=docs['TEXTURE_PROVIDER_GATE_VALIDATED.json'];total=gate.get('visible_texture_total',0)
 need(gate['pid']==proc['pid'] and gate['start_ticks']==proc['start_ticks'] and gate['image_path']==proc['image_path'] and gate['slot']==62144 and gate['selected_pool']==driver['selected_pool']==probe['selected_pool'],'readiness belongs to another game/pool')
 need(gate['status']=='actual_native_provider_ready' and gate['index_base']==0 and gate['visible_texture_index']==0 and total>=65 and gate['visible_caption']=='Texture 0 of '+str(total) and gate['texture_pixels_present'] and gate['console_absent'] and gate['visible_width']>0 and gate['visible_height']>0,'provider gate has no actual zero-based populated caption/image')
 need(validated['status']=='validated_actual_provider_readiness' and validated['frame_sha256']==gate['frame_sha256'] and gate['frame_name'] in {x['name'] for x in probe['frames']},'provider gate validation not tied to exact probe')
 if pixel is None:pending.append('final personally viewed pixel review not supplied; gate is readiness only, not seven-site credit')
 else:
  review=read(pixel)
  need(review['status']=='reviewed' and review.get('personally_viewed') is True and review['driver_sha256']==digest(run/'RESOURCE_DRIVER_RECEIPT.json'),'pixel review not personally/exactly bound')
  rows={x['name']:x for x in review['frames']}
  for frame in frames:need(frame['name'] in rows and rows[frame['name']]['sha256']==frame['sha256'] and bool(rows[frame['name']]['observation']),'each actual BMP needs an independent observation')
  for site in scope['site_ids']:
   row=review['sites'].get(site,{})
   need(row.get('status')=='verified' and row.get('observed_effect') and row.get('restore_observation') and row.get('frame_names') and set(row['frame_names'])<=frame_names,'bounded native site lacks actual pixels+restore: '+site)
  indices=review.get('visible_indices',{})
  need(indices.get('texture_bank_open')==0 and indices.get('texture_next_callback')==1 and indices.get('texture_previous_callback')==0 and indices.get('texture_next_page_callback')==64 and indices.get('texture_previous_page_callback')==0,'native zero-based step/page changed/restored indices not observed')
  need(review.get('sort_order_changed') is True and review.get('draw_modes_changed') is True and review.get('window_off_observed') is True and review.get('initial_three_controls_restored') is True,'sort/draw/off/exact restore consumer witnesses incomplete')
 return {'status':'FAIL' if failures else ('PENDING' if pending else 'PASS'),'failures':failures,'pending':pending,'selected_site_count':7,'frame_count':len(frames),'native_case':result['verdict'],'profile_snapshot_sha256':fixture['sha256'],'actual_native_profile_witnesses':profile_rows,'no_canonical_edits':True}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--run-dir',type=Path,required=True);ap.add_argument('--pixel-review',type=Path);args=ap.parse_args();out=check(args.packet.resolve(),args.run_dir.resolve(),args.pixel_review);print(json.dumps(out,indent=2));raise SystemExit(0 if out['status']=='PASS' else (2 if out['status']=='PENDING' else 1))
