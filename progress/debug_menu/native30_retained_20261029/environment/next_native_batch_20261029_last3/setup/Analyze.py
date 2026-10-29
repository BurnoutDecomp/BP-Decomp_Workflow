"""Independently decode retained raw native triplets, scripts and frames; no site credit."""
from pathlib import Path
import hashlib,json,math
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    stage=load(R/'STAGING.json');scope=load(R/'SCOPE.json');run=Path(stage['active_run_dir'])
    result=load(run/'driver-result.json')
    log=Path(stage['exe_dir'])/'BrnGame.log'
    raw=log.read_bytes();lines=raw.decode('utf-8-sig').splitlines()
    assert result['status']=='machine_complete_awaiting_independent_pixels'
    count=result['eligible_control_count'];assert count==3
    assert len(result['frames'])==3*count+4 and len(result['phases'])==3*count+3
    assert result['exe_sha256']==scope['candidate']['exe_sha256'] and result['slot']==62180
    assert not any('[ASSERT' in line or '[EXCEPTION]' in line for line in lines)
    controls=scope['controls']+scope['context_aliases'];by_alias={c['alias']:c for c in controls}
    decoded={};script_count=0;skipped={row['id']:row for row in result['skipped_controls']};skipped_aliases={row['alias'] for row in skipped.values()}
    for phase in result['phases']:
        assert hashlib.sha256(raw[:phase['snapshot_bytes']]).hexdigest().upper()==phase['snapshot_hash'].replace('-','')
        emitted=Path(phase['command_file']);assert sha(emitted)==phase['command_sha256']
        expected_commands=list(phase['commands'])
        assert not any(line.startswith('set '+alias+' ') for line in expected_commands for alias in skipped_aliases)
        selected=controls if phase['phase']!='context_restore' else scope['context_aliases']
        for c in selected:expected_commands+=['alias '+c['alias'],c['alias'],'alias '+c['alias']]
        assert emitted.read_text(encoding='ascii').splitlines()==expected_commands
        values={};cursor=phase['cursor']
        for proof,c in zip(phase['proofs'],selected,strict=True):
            before=proof['ack_before'];after=proof['ack_after'];value_line=proof['value_line']
            assert before>=cursor and value_line==before+1 and after==before+2
            ack=c['alias']+': /'+c['lookup_path'];assert lines[before]==lines[after]==ack
            value=lines[value_line].strip();assert value==proof['value']
            if c['type']=='bool':assert value in ['TRUE','FALSE']
            else:assert math.isfinite(float(value))
            values[c['alias']]=value;cursor=after+1
        for alias,want in phase['expected'].items():
            actual=values[alias]
            assert (actual==want if str(want) in ['TRUE','FALSE'] else abs(float(actual)-float(want))<=0.00051)
        decoded[phase['phase']]=values;script_count+=1
    baseline=decoded['frozen_baseline'];index=[]
    actual_skips={c['id'] for c in scope['controls'] if not c['range_min']<=float(baseline[c['alias']])<=c['range_max']}
    assert actual_skips|set(scope['retained_complete_ids'])==set(skipped)
    frames={f['phase']:f for f in result['frames']}
    for f in frames.values():
        p=Path(f['path']);assert sha(p)==f['sha256']
        assert f['slot']==62180 and f['pid']==result['process_id']
        assert lines[f['ack_index']]==f['ack'] and f['ack_index']>f['request_cursor']
        assert f['displacement_from_baseline']<=2
        assert lines[f['motion_index']]==f['motion_line'] and f['motion_line'].endswith(' engine 2')
        assert int(f['csv_row'].split(',')[-1])==f['boost_effect_mask']
        import re
        motion=re.search(r' pos ([^ ]+) ([^ ]+) ([^ ]+) at ',f['motion_line']);assert motion
        assert all(abs(float(motion.group(i+1))-float(f['csv_row'].split(',')[i+20]))<=0.002 for i in range(3))
    for c in scope['controls']:
        suffix=c['id'].split('#')[-1];row={'id':c['id'],'caption':c['caption'],'consumer':c['consumer'],'states':{}}
        if c['id'] in skipped:
            row.update({'state':skipped[c['id']]['state'],'reason':skipped[c['id']]['reason'],'baseline':baseline[c['alias']],'target_writes':0});index.append(row);continue
        for state in ['positive','negative','restore']:
            name=suffix+'_'+state;values=decoded[name]
            expected=float(baseline[c['alias']]) if state=='restore' else c[state]
            assert abs(float(values[c['alias']])-expected)<=0.00051
            companion='E56' if suffix in ['0052','0054'] else ('E52' if suffix=='0056' else None)
            for alias,want in baseline.items():
                if alias==c['alias']:continue
                if alias==companion and state!='restore':want='0.5'
                assert (values[alias]==want if want in ['TRUE','FALSE'] else abs(float(values[alias])-float(want))<=0.00051),(c['id'],state,alias,values[alias],want)
            row['states'][state]={'value':values[c['alias']],'frame':frames[name]}
        assert row['states']['positive']['value']!=row['states']['negative']['value']
        index.append(row)
    report={'verdict':'pass_raw_machine_collection_only','site_credit':0,'raw_log':str(log),'raw_log_sha256':sha(log),'independent_decoded_phase_scripts':script_count,'controls':index,'frame_count':len(frames),'note':'Actual native consumer pixels still require independent review; missing or ambiguous effects stay pending.'}
    (run/'INDEPENDENT_RAW_CHECK.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='controls'},indent=2))
if __name__=='__main__':main()
