"""Join bounded native evidence without relabeling failed aggregate runs."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parent;BASE=R.parent;W=R.parents[2]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
groups=[('next_native_batch_20261029_remainder','run_62180_game01',[51,55,57,58,59,66,67]),
 ('next_native_batch_20261029_finish','run_62181_game01',[68]+list(range(72,81))),
 ('next_native_batch_20261029_last3','run_62180_game01',[81,82,83])]
common=load(BASE/groups[0][0]/'SCOPE.json');scope={c['id']:c for c in common['controls']}
cases=[];sites=[]
for package,runname,numbers in groups:
    p=BASE/package;run=p/runname;stage=load(p/'STAGING.json');driver=load(run/'driver-result.json')
    raw=Path(stage['exe_dir'])/'BrnGame.log';data=raw.read_bytes();lines=data.decode('utf-8-sig').splitlines()
    assert sha(Path(stage['exe_dir'])/'Burnout_PC.exe')==common['candidate']['exe_sha256']
    assert load(p/'NORMAL_POSTCHECK.json')['all_unchanged']
    assert load(p/'RUN_EXIT.json')['profile_restored']
    frames={f['phase']:f for f in driver['frames']};phases={f['phase']:f for f in driver['phases']}
    reviews=sorted(run.glob('INDEPENDENT*REVIEW*.json'))+sorted(run.glob('INDEPENDENT*CLOSED*.json'))
    case={'id':package,'path':str(p),'run_dir':str(run),'slot':stage['slot'],'pid':driver['process_id'],
      'start_ticks':driver['process_start_ticks'],'manifest':str(p/'MANIFEST.json'),'manifest_sha256':sha(p/'MANIFEST.json'),
      'raw_log':str(raw),'raw_log_sha256':sha(raw),'raw_log_bytes':len(data),
      'driver_status':driver['status'],'driver_error':driver['error'],'frame_count':len(driver['frames']),
      'canonical_result':str(run/'result.json'),'canonical_report':str(run/'REPORT.md'),
      'run_exit':load(p/'RUN_EXIT.json'),'normal36_unchanged':True,'normal_postcheck':str(p/'NORMAL_POSTCHECK.json'),
      'peer_receipts':{str(f):sha(f) for f in dict.fromkeys(reviews)},'full_aggregate_pass':package.endswith('_last3')}
    cases.append(case)
    for number in numbers:
        site=f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{number:04}';entry=dict(scope[site])
        entry['consumer']=entry['consumer'].replace('BrnIm3d SetShaderConstants','BrnGraphics::Im3dSkyDome::SetConstants')
        if number in [57,58,59]:
            entry['consumer']='DebugToManager -> CloudsData.mav3LayerDarkColour[0] RGB lane -> GenerateShaderConstants CloudDarkColour0 (white-level RGB scale) -> SkyDomeManager colour x2 -> BrnGraphics::Im3dSkyDome::SetConstants handle[11]/g_darkColour -> actual cloud sky pixels'
            entry['mapping_note']='Precise colour-uniform chain; historical scope used the cloud-family scalar-uniform summary.'
        states={}
        for state in ['positive','negative','restore']:
            name=f'{number:04}_{state}';phase=phases[name];frame=frames[name];target=next(x for x in phase['proofs'] if x['alias']==entry['alias'])
            assert lines[target['ack_before']]==lines[target['ack_after']]==entry['alias']+': /'+entry['lookup_path']
            assert lines[target['value_line']].strip()==target['value']
            bitmap=Path(frame['path']);assert sha(bitmap)==frame['sha256'];header=bitmap.read_bytes()[:54]
            assert struct.unpack_from('<i',header,18)[0]==640 and abs(struct.unpack_from('<i',header,22)[0])==360
            assert lines[frame['ack_index']]==frame['ack'] and frame['slot']==stage['slot'] and frame['pid']==driver['process_id']
            assert sha(Path(phase['command_file']))==phase['command_sha256']
            states[state]={'requested':phase['expected'][entry['alias']],'typed_native_triplet':target,
              'phase_script':phase['command_file'],'phase_script_sha256':phase['command_sha256'],
              'all_companion_triplets_reference':str(run/'driver-result.json')+'#phases/'+name,
              'frame':frame,'raw_snapshot_bytes':phase.get('snapshot_bytes'),'raw_snapshot_hash':phase.get('snapshot_hash')}
        assert states['positive']['typed_native_triplet']['value']!=states['negative']['typed_native_triplet']['value']
        sites.append({'id':site,'caption':entry['caption'],'proposed_state':'verified','case':package,
          'source_registration':entry,'states':states,'scope':'This completed P/N/R contrast, captured scene and original consumer only; no entire-domain/hardware/fullmenu claim.'})
for number,reason in [(52,'No observable layer1 density effect even with explicit opacity companion; original-noop closure not established.'),
 (53,'Loaded1.100 exceeds original0..1 setter range; original restore clamped1.000. Later runs never SET this alias.'),
 (54,'No observable layer1 feather effect even with explicit opacity companion; original-noop closure not established.'),
 (56,'No observable layer1 opacity effect even with explicit density companion; original-noop closure not established.')]:
    site=f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{number:04}'
    sites.append({'id':site,'caption':scope[site]['caption'],'proposed_state':'pending','reason':reason})
assert len(sites)==24 and len({s['id'] for s in sites})==24
current=load(W/'progress/debug_menu/verdicts.json')
report={'status':'independently_reviewed_bounded_native_cohort_ready_for_Root_canonical_publication',
 'candidate':common['candidate'],'selected_controls':24,'unique_completed_PNR_controls':23,
 'proposed_verified':20,'pending':4,'original_noop':0,'sites':sites,'cases':cases,
 'source_git_blob_sha256':common['source_git_blob_sha256'],'original_export_sha256':common['original_export_sha256'],
 'already_canonical_verified_at_handoff':[s['id'] for s in sites if current.get(s['id'],{}).get('state')=='verified'],
 'canonical_mutation_by_this_task':False,'game_source_changed':False,'normal_installed_or_written_by_this_task':False,
 'normal_history':'Normal41 authorized external payload transition recorded in scene/AUTHORIZED_NORMAL_TRANSITION.json. A later normalProfile AFDC->D706 delta occurred between completed own runs; explicitly snapshotted, never overwritten. All three primary retained/final runs preserve their respective fresh normal36.',
 'failure_history':['original62180 intro508assert beforetargetwrites','skipvideo62181 wrongCRIGcategory beforetargetwrites','aliasfix62180 mistakenCSVboostmask-as-engineguard','scene62181 E53out-of-range restoreclamp','remainder62180 bounded235sdeadline','finish62181 unexpected2560x1440 frame81restore'],
 'invalid_image_preserved':str(BASE/'next_native_batch_20261029_finish/run_62181_game01/frames/bb_015146.bmp'),
 'limits':'Private source32/exe474 only. Prior FAILs remain FAIL. Last3 is canonical GREEN. No duplicated51 or retained refresh credit; pendinglayer1 controls are not originalnoops.'}
(R/'COHORT_RESULT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['selected_controls','unique_completed_PNR_controls','proposed_verified','pending','original_noop','already_canonical_verified_at_handoff']},indent=2))
