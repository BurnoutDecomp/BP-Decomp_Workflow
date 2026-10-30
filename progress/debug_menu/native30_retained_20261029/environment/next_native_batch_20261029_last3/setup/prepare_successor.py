"""Finish only81/82/83; all complete predecessor PNRs remain read-only refreshes."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;OLD=R.parent/'next_native_batch_20261029_finish';W=R.parents[2]
completed=[51,52,54,55,56,57,58,59,66,67,68]+list(range(72,81))
names=['prepare.py','make_driver.py','Case.ps1','Run.py','Preflight.ps1','OfflineChecks.ps1','Analyze.py','Request-HarnessPhaseDone.ps1','REVIEW_PACKET.md','Seal.py','CAPTURE_SOURCE_FIXTURE.json','ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json','ROOT_NORMAL41_ROSTER.json','ReaderBenchmark.ps1']
for name in names:
    text=(OLD/name).read_text(encoding='utf-8-sig')
    if name not in ['CAPTURE_SOURCE_FIXTURE.json','ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json','ROOT_NORMAL41_ROSTER.json','ReaderBenchmark.ps1']:text=text.replace('62181','62180')
    if name=='prepare.py':text=text.replace('[51,52,54,55,56,57,58,59,66,67]',repr(completed)).replace("'max_frames':43","'max_frames':13").replace("'maximum_frames':43","'maximum_frames':13")
    if name=='make_driver.py':text=text.replace('$script:eligibleControls.Count -ne 13','$script:eligibleControls.Count -ne 3').replace('Exactly13 unfinished','Exactly3 unfinished')
    if name=='Case.ps1':text=text.replace('BRN_FRAME_DUMP_MAX=43','BRN_FRAME_DUMP_MAX=13').replace('$r.eligible_control_count -eq 13','$r.eligible_control_count -eq 3')
    if name=='Preflight.ps1':text=text.replace('max_frames=43','max_frames=13')
    if name=='Run.py':text=text.replace('unfinished13','unfinished3').replace('43frame cap','13frame cap')
    if name=='Analyze.py':text=text.replace("count==13","count==3")
    (R/name).write_text(text,encoding='utf-8')
subprocess.run(['python',str(R/'make_driver.py')],check=True)
subprocess.run(['python',str(R/'prepare.py')],check=True)
blob=subprocess.check_output(['git','-C',str(W/'b5-decomp'),'show','abbc9047d850a4665d959993012261c55205e5e5:src/pc/gcm/renderengine/device.cpp']);(R/'source/device.cpp').write_bytes(blob)
p=R/'SCOPE.json';scope=json.loads(p.read_text());scope['source_git_blob_sha256']['src/pc/gcm/renderengine/device.cpp']=hashlib.sha256(blob).hexdigest();scope['retained_complete_ids']=[f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{n:04}' for n in completed];scope['expected_unfinished_controls']=3;scope['already_final_excluded']=False;scope['retained_sites_receive_zero_new_credit']=True;p.write_text(json.dumps(scope,indent=2),encoding='utf-8')
retained=json.loads((OLD/'RETAINED_COMPLETE.json').read_text())
run=OLD/'run_62181_game01';result=json.loads((run/'driver-result.json').read_text(encoding='utf-8-sig'));phases={p['phase']:p for p in result['phases']};frames={f['phase']:f for f in result['frames']};log=OLD/'stage/slot/BrnGame.log';rows=[]
for n in [68]+list(range(72,81)):
    states={}
    for state in ['positive','negative','restore']:
        name=f'{n:04}_{state}';assert name in phases and name in frames;assert frames[name]['bytes']==921654
        states[state]={'phase':phases[name],'frame':frames[name]}
    rows.append({'id':f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{n:04}','states':states})
(R/'RETAINED_COMPLETE.json').write_text(json.dumps({'first10':retained,'second10':{'predecessor':str(OLD),'raw_log':str(log),'raw_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'controls':rows},'completed_count':20,'invalid81_restore_frame_preserved':str(run/'frames/bb_015146.bmp'),'credit':'No duplicate new credit; separate independent receipts retain prior aggregate failures'},indent=2),encoding='utf-8')
(R/'REVIEW_PACKET.md').write_text('''# Last3 of the24-site native cohort\n\nOnly81/82/83 DownfillRGB are writable, sameprivate474/source32, newprivate62180. Prior20 completePNRs are read-only refreshes, E53=1.1 skippeduntouched. RETAINED_COMPLETE binds two closedraw predecessors and their validframes; unexpected2560x1440 frame81restore remainsinvalid and noimages arecropped. Exactly3unfinishedeligible gate,13frames12phases; unchanged235sdriver/240scase/64MiBlog; snapshotreader/typed/alias/owner/frame/pose/restore guards unchanged.\n\nLast run's runtimeviewport changed to2560x1440 whileconfigremained640x360; causeunattributed. This successor keeps the strict640x360 contract and noresizeAPI is added. Samepeer must review actualbaseline and all3PNRpixels. All earlierFAILs retained. Freshnormal41/runtime15 remainsunchanged; currentprofileD706between-runexternaldelta isexplicitlyrecorded/protected, neveroverwritten.\n''',encoding='utf-8')
print('Last3 prepared; no game launched')
