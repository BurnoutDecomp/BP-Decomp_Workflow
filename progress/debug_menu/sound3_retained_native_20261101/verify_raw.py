import csv
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

parser=argparse.ArgumentParser(description='Read-only verification of exact retained Sound V4 raw logs, bytes and native receipt joins.')
parser.add_argument('--output',type=Path)
args=parser.parse_args()
C=Path(__file__).resolve().parent
failure=json.loads((C/'FAILED_AGGREGATE.json').read_text(encoding='utf-8-sig'))
R=Path(failure['run_dir'])
P=R.parent.parent
archive=Path(failure['archive_path'])
assert hashlib.sha256(archive.read_bytes()).hexdigest()==failure['archive_sha256']
def file_bytes(p):
    if p.exists():return p.read_bytes()
    with zipfile.ZipFile(archive) as z:return z.read(p.relative_to(P).as_posix())
def read(p):return json.loads(file_bytes(p).decode('utf-8-sig'))
def sha(p):return hashlib.sha256(file_bytes(p)).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8',newline='\n')
d=read(R/'driver-result.json')
raw=file_bytes(R/'flow/BrnGame.log')
lines=raw.decode('utf-8',errors='replace').splitlines()
base=read(R/'NATURAL_BASELINE.json')
assert d['process_id']==base['owner_pid']==54460
assert d['slot']==62207 and d['completed_target_count']==4
terminal=read(R/'flow-terminal.json')
flow=terminal['flow_status']
assert terminal['success'] and flow['success'] and flow['owned_cleanup_complete'] and flow['input_reset_complete']
assert terminal['helper_cleanup_complete'] and terminal['profile_restoration_complete'] and flow['phase_collection_stop_requested']
assert flow['owned_pid']==d['process_id'] and Path(flow['owned_image'])==Path(d['process_path'])
start=flow['owned_start_utc'].removesuffix('Z')
whole,frac=start.split('.')
dt=datetime.datetime.fromisoformat(whole)
ticks=((dt.toordinal()-1)*86400+dt.hour*3600+dt.minute*60+dt.second)*10000000+int(frac.ljust(7,'0'))
assert str(ticks)==d['process_start_ticks']
assert read(R/'CURRENT_SAVE_LOAD_GATE.json')['pass']
assert read(P/'ROOT_EXIT.json')['normal_unchanged']
used=set()
proofs=[]
for phase in [{'phase':'natural_baseline','cursor':base['bootstrap_query_cursor'],'proofs':base['readbacks'],'expected':base['values']},*d['phases']]:
    ps=phase['proofs']
    assert len(ps)==33 and len({p['alias'] for p in ps})==33
    for proof in ps:
        a,v,b=(proof[k] for k in ('ack_before','value_line','ack_after'))
        assert phase['cursor']<=a<v<b<len(lines)
        assert lines[a]==lines[b]==proof['alias']+': /'+proof['path']
        assert lines[v]==proof['display_value']
        assert str(proof['value'])==str(phase['expected'][proof['alias']])
        assert (a,v,b) not in used
        used.add((a,v,b))
    if 'command_file' in phase:
        cfg=Path(phase['command_file'])
        assert sha(cfg)==phase['command_sha256']
        assert hashlib.sha256(raw[:phase['snapshot_bytes']]).hexdigest()==phase['snapshot_hash'].replace('-','').lower()
    proofs.append({'phase':phase['phase'],'aliases':33,'first_ack':min(p['ack_before'] for p in ps),'last_ack':max(p['ack_after'] for p in ps)})
frame_rows=[]
csv_text=file_bytes(R/'frames/frames.csv').decode('utf-8-sig').splitlines()
for frame in d['frames']:
    f=Path(frame['path'])
    assert sha(f)==frame['sha256'] and len(file_bytes(f))==frame['bytes']==3686454
    width,height=struct.unpack_from('<ii',file_bytes(f),18)
    assert (width,abs(height))==(1280,720)
    assert lines[frame['ack_index']]==frame['ack']
    expected_ack=f"[frame-request] pid=54460 slot=62207 seq={frame['sequence']} present={frame['present']} file={frame['name']}"
    assert frame['ack']==expected_ack and f.name==frame['name']
    assert sum(frame['ack']==line for line in lines)==1
    assert frame['ack_index']>=frame['request_cursor']
    assert csv_text.count(frame['csv_row'])==1
    assert frame['csv_row'].split(',')[0]==str(frame['present'])
    frame_rows.append({'phase':frame['phase'],'file':frame['name'],'sha256':frame['sha256'],'ack_index':frame['ack_index'],'sequence':frame['sequence']})
assert len(frame_rows)==13
acks=[]
rx=re.compile(r'\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$')
for i,line in enumerate(lines):
    m=rx.search(line)
    if m:
        assert int(m[1])==54460 and int(m[2])==62207
        acks.append({'line':i,'column':m.start(),'sequence':int(m[3]),'present':int(m[4]),'file':m[5]})
assert [a['sequence'] for a in acks]==list(range(1,15))
assert acks[-1]['column']>0
extra=R/'frames'/acks[-1]['file']
assert len(file_bytes(extra))==3686454
patterns={'engine_info':r'\[raw_rpm\]','closest_ai':r'\[AI Inst\]','rpm_info':r'\[HybGinsuRPM\]','loop_info':r'\[Eng\]|\[Exh\]','loop_dump':r'---------- \[(?:Eng|Exh)\]'}
windows=[]
for i,phase in enumerate(d['phases']):
    start=max(p['ack_after'] for p in phase['proofs'])+1
    end=d['phases'][i+1]['cursor'] if i+1<len(d['phases']) else len(lines)
    assert end>=start
    text='\n'.join(lines[start:end])
    windows.append({'phase':phase['phase'],'start':start,'end_exclusive':end,'counts':{k:len(re.findall(v,text)) for k,v in patterns.items()}})
out={'schema':1,'status':'raw_retained_partial_verified_no_site_credit','original_driver_status':d['status'],'original_error':d['error'],'run_dir':str(R),'raw_log_sha256':sha(R/'flow/BrnGame.log'),'unique_raw_triplets':len(used),'proof_groups':proofs,'frames':frame_rows,'orphan_frame_ack':acks[-1],'orphan_frame_sha256':sha(extra),'all14_exact_native_ack_tokens_found':True,'anchored_ack_missed_original_audio_prefix':True,'terminal_target_restore_verified':d['terminal_restore_verified'],'completed_targets':[r['alias'] for r in d['target_results']],'assert_exception_count':sum(bool(re.search(r'\[ASSERT|\[EXCEPTION\]',s)) for s in lines),'output_windows':windows,'behavior_review':'pending source/native output and pixel review; no whole32 or orphan-target completion claim'}
if args.output:write(args.output,out)
print(json.dumps({k:out[k] for k in ('unique_raw_triplets','completed_targets','assert_exception_count','orphan_frame_ack','terminal_target_restore_verified')}))
print(json.dumps(windows))
