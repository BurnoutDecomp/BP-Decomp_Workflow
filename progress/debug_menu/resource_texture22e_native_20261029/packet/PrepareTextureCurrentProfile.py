"""Make a stable, independent per-run copy of the user's current normal save."""
import datetime,hashlib,json,os,re,time
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=Path('D:/Reverse/BP-Decomp_Workflow');OUT=Path('C:/Users/adri1/Documents/Codex/resource_texture_source22e_62144_20261029')
SOURCE=ROOT/'build/game/Memcard/Profile.sav'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
identity=P/'pre/TEXTURE_RUN_IDENTITY.json'
if identity.exists():v=json.loads(identity.read_text());run=v['run_name']
else:
 run='resource_windows_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')
 v={'run_name':run,'suite':'resource_windows','slot':62144,'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};identity.write_text(json.dumps(v,indent=2))
assert re.fullmatch(r'resource_windows_\d{8}_\d{6}',run)
dest=OUT/'profile_snapshots'/run/'Profile.sav';assert dest.resolve().is_relative_to((OUT/'profile_snapshots').resolve())
dest.parent.mkdir(parents=True,exist_ok=True)
if not dest.exists():
 for attempt in range(3):
  before=sha(SOURCE);data=SOURCE.read_bytes();after=sha(SOURCE)
  if before==after==hashlib.sha256(data).hexdigest():break
  time.sleep(.1)
 else:raise RuntimeError('Current normal profile changed during three read-only snapshot attempts')
 with dest.open('xb') as f:f.write(data)
assert not os.path.samefile(SOURCE,dest)
h=sha(dest);assert h==sha(SOURCE),'Current save evolved after this snapshot; retain it and prepare a new per-run successor'
fixture={'kind':'current_normal_profile_copy','path':str(dest),'source_normal_path':str(SOURCE),'sha256':h,'bytes':dest.stat().st_size,'snapshot_receipt_path':'evidence/CURRENT_PROFILE_COPY_RECEIPT.json','normal_source_payload_exe_sha256':'5d2b9994ba54521930d9d526e34e7ea6796c47d0d963ee376d2cb0ecffd7feb6'}
receipt={'schema':1,'generated_by':'/root/playable_refresh_builder','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_name':run,'fixture':fixture,'normal_original_written':False,'independent_copy':True,'same_file':False,'source_before_after_stable':True,'source_volume':'D:','snapshot_volume':'C:','authority':'Explicit human instruction forwarded by Root: routine tests use a current normal-save copy per run; never live original or a hardlink','save_bytes_in_packet_or_Git':False,'successful_native_load_and_progress_witness':'pending actual run; no claim from copy readiness'}
path=P/'evidence/CURRENT_PROFILE_COPY_RECEIPT.json';path.write_text(json.dumps(receipt,indent=2))
print(json.dumps({'run_name':run,'fixture':fixture,'receipt':str(path),'receipt_sha256':sha(path)},indent=2))
