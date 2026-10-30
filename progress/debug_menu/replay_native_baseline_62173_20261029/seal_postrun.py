"""Retain raw native outcomes and exact build attribution; do not promote the normal game."""
from pathlib import Path
import datetime,hashlib,json,re
R=Path(__file__).resolve().parent;N=R/'native';RUN=R/'run_game01'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')
s=load(N/'STAGING.json');raw=load(RUN/'result.json');term=load(RUN/'flow/terminal-status.json');captures=load(RUN/'CAPTURES.json');owner=load(RUN/'CAPTURE_OWNER.json')
assert raw['verdict']=='PASS' and len(raw['checks'])==17 and all(row['pass'] for row in raw['checks'])
assert term['success'] and term['owned_cleanup_complete'] and term['input_reset_complete'] and term['phase_collection_stop_requested'] and not term['foreign_game']
assert owner['pid']==term['owned_pid'] and owner['image']==term['owned_image']==str(Path(s['exe_dir'])/'Burnout_PC.exe')
assert load(R/'RUN_EXIT.json')['exit_code']==0 and load(R/'RUN_EXIT.json')['asset_handles_held']==5622
assert not load(R/'NORMAL_AFTER.json')['nonlog_drift']
for name,h in s['launch_files'].items():assert sha(Path(s['exe_dir'])/name)==h,name
log=(RUN/'flow/BrnGame.log').read_text(errors='replace');marks=(RUN/'flow/marks.txt').read_text(errors='replace')
assert 'SKIPINTRO (not armed)' in ' '.join(marks.split()) and len(captures)==10
assert not (RUN/'CAPTURE_ERROR.json').exists()
for row in captures:
 assert row['owner']==owner and sha(Path(row['file']))==row['sha256']
 assert len(re.findall(re.escape(row['ack'].strip())+r'\r?$',log,re.M))==1
 assert row['width']==1280 and row['height']==720
labels={row['label']:row['file'] for row in captures}
for required in ['ea_logo','criterion_logo','title_ready','profile_ready','car_select','world_exit','drive_8s','drive_15s']:assert required in labels
receipt={'verdict':'PASS_PRIVATE_STARTUP_BASELINE_PENDING_ROOT_PIXEL_REVIEW','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':s['source'],'build_workflow_commit':s['build_workflow'],'metadata_workflow_commit':s['metadata_workflow'],'exe_sha256':s['exe_sha256'],'slot':62173,'owner':owner,'case_checks_with_terminal':17,'asserts':raw['asserts'],'skip_intro':False,'ordinary_sequence':'EA ->510 ->Criterion ->510 ->legalstage7 ->scopedStart ->profile/world ->driving','captures':captures,'selected_frames':{k:labels[k] for k in ['ea_logo','criterion_logo','title_ready','drive_15s']},'normal_guard_before':str(R/'NORMAL_BEFORE.json'),'normal_guard_after':str(R/'NORMAL_AFTER.json'),'normal_nonlog_drift':[],'normal_deployment':False,'normal_payload_source':s['normal_payload_source'],'normal_payload_exe_sha256':s['normal_payload_exe_sha256'],'owned_cleanup_complete':True,'input_reset_complete':True,'raw_result_git_context':raw['provenance'],'actual_build_attribution':'Staged and output EXE hashes + copied clean build provenance; raw harness shared-tree Git context retained unchanged','limitations':['Private baseline only; no Replay recording/playback/open state forced or certified','No ResourceTexture/site disposition from this baseline','Returning-profile seed and scoped place-on-track/throttle; no organic-route or complete-gameplay claim','Mastering voice muted; no audible playback or physical-controller certification','Automatic lateCriterion capture may show title transition; Root inspects actual pixels']}
save(R/'NATIVE_RECEIPT.json',receipt)
files=[R/'NATIVE_RECEIPT.json',R/'NORMAL_BEFORE.json',R/'NORMAL_AFTER.json',R/'RUN_EXIT.json',N/'STAGING.json',N/'PREFLIGHT_MANIFEST.json',RUN/'result.json',RUN/'REPORT.md',RUN/'CAPTURES.json',RUN/'CAPTURE_OWNER.json',RUN/'PHASE_STOP_REQUEST.json',RUN/'flow/terminal-status.json',RUN/'flow/marks.txt',RUN/'flow/BrnGame.log']+[Path(row['file']) for row in captures]
save(R/'NATIVE_MANIFEST.json',{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in files});save(R/'NATIVE_SEAL.json',{'receipt_sha256':sha(R/'NATIVE_RECEIPT.json'),'manifest_sha256':sha(R/'NATIVE_MANIFEST.json'),'members':len(files)})
print(json.dumps({'verdict':receipt['verdict'],'checks':17,'owner':owner,'selected_frames':receipt['selected_frames'],'seal':load(R/'NATIVE_SEAL.json')},indent=2))
