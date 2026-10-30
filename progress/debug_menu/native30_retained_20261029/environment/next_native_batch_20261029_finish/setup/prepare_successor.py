"""Finish only13 unfinished eligible controls from the same24-site cohort."""
from pathlib import Path
import subprocess,json,hashlib,re
R=Path(__file__).resolve().parent;OLD=R.parent/'next_native_batch_20261029_remainder';W=R.parents[2]
completed=[51,52,54,55,56,57,58,59,66,67]
names=['prepare.py','make_driver.py','Case.ps1','Run.py','Preflight.ps1','OfflineChecks.ps1','Analyze.py','Request-HarnessPhaseDone.ps1','REVIEW_PACKET.md','Seal.py','CAPTURE_SOURCE_FIXTURE.json','ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json','ROOT_NORMAL41_ROSTER.json']
for name in names:
    text=(OLD/name).read_text(encoding='utf-8-sig')
    if name not in ['CAPTURE_SOURCE_FIXTURE.json','ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json','ROOT_NORMAL41_ROSTER.json']:text=text.replace('62180','62181')
    if name=='prepare.py':
        text=text.replace("assert site not in verdicts,site", "assert site not in verdicts or (number in [51,52,54,55,56,57,58,59,66,67] and verdicts[site]['state']=='verified'),site")
        text=text.replace("'max_frames':76", "'max_frames':43").replace("'maximum_frames':76", "'maximum_frames':43")
    if name=='make_driver.py':
        start=text.index('function Read-Values(');end=text.index('\nfunction Queries(',start)
        reader=r'''function Read-Values([int]$Cursor,[object[]]$Selected=$controls){
 $until=[DateTime]::UtcNow.AddSeconds(8)
 do{
  Own
  # One complete immutable raw-byte snapshot per poll. Lines still revalidates the
  # entire previously accepted prefix SHA before exposing any rows, unchanged.
  $all=Lines;$proof=@();$values=@{};$at=$Cursor;$complete=$true
  foreach($control in $Selected){
   $ack=$control.alias+': /'+$control.lookup_path;$found=-1
   for($i=$at;$i -lt $all.Count-2;$i++){if($all[$i] -ceq $ack -and $all[$i+2] -ceq $ack){$found=$i;break}}
   if($found -lt 0){$complete=$false;break}
   $value=$all[$found+1].Trim();$number=0.0
   if($control.type -eq 'f32'){
    if(![double]::TryParse($value,[Globalization.NumberStyles]::Float,[cultureinfo]::InvariantCulture,[ref]$number) -or [double]::IsNaN($number) -or [double]::IsInfinity($number)){throw 'Nonfinite native value'}
   }elseif($value -cnotin @('TRUE','FALSE')){throw 'Native bool type mismatch'}
   $values[$control.alias]=$value;$proof+=@{alias=$control.alias;path=$control.lookup_path;value=$value;ack_before=$found;value_line=$found+1;ack_after=$found+2};$at=$found+3
  }
  if($complete){return @{values=$values;proofs=$proof;snapshot_bytes=$script:gameBytes;snapshot_hash=$script:prefixHash}}
  Start-Sleep -Milliseconds 30
 }while([DateTime]::UtcNow -lt $until)
 throw 'Incomplete fresh native alias triplets inside8seconds'
}'''
        text=text[:start]+reader+text[end:]
        text=text.replace("if($value -lt [double]$control.range_min", "if($control.id -in @($plan.retained_complete_ids)){$script:skippedAliases+=$control.alias;$script:skippedControls+=@{id=$control.id;alias=$control.alias;baseline=$baseline[$control.alias];reason='complete PNR retained from predecessor; read-only refresh, no duplicate target or cleanup SET';state='retained_completed_phases'}}elseif($value -lt [double]$control.range_min")
        text=text.replace("$script:eligibleControls.Count -lt 20", "$script:eligibleControls.Count -ne 13").replace('Fewer than20 baseline-restorable controls; no target writes','Exactly13 unfinished restorable controls required; no target writes')
        text=text.replace('command_sha256=$scriptHash;expected=$Expected;proofs=$read.proofs','command_sha256=$scriptHash;expected=$Expected;proofs=$read.proofs;snapshot_bytes=$read.snapshot_bytes;snapshot_hash=$read.snapshot_hash')
    if name=='Case.ps1':text=text.replace('BRN_FRAME_DUMP_MAX=76','BRN_FRAME_DUMP_MAX=43').replace('$r.eligible_control_count -ge 20','$r.eligible_control_count -eq 13')
    if name=='Preflight.ps1':text=text.replace('max_frames=76','max_frames=43')
    if name=='Run.py':text=text.replace('76frame cap','43frame cap').replace('Environment24 bounded restorable controls','Environment24 cohort unfinished13 controls')
    (R/name).write_text(text,encoding='utf-8')
subprocess.run(['python',str(R/'make_driver.py')],check=True)
subprocess.run(['python',str(R/'prepare.py')],check=True)
blob=subprocess.check_output(['git','-C',str(W/'b5-decomp'),'show','abbc9047d850a4665d959993012261c55205e5e5:src/pc/gcm/renderengine/device.cpp'])
(R/'source/device.cpp').write_bytes(blob)
p=R/'SCOPE.json';scope=json.loads(p.read_text());scope['source_git_blob_sha256']['src/pc/gcm/renderengine/device.cpp']=hashlib.sha256(blob).hexdigest();scope['retained_complete_ids']=[f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{n:04}' for n in completed];scope['expected_unfinished_controls']=13;scope['already_final_excluded']=False;scope['retained_sites_receive_zero_new_credit']=True;p.write_text(json.dumps(scope,indent=2),encoding='utf-8')
oldrun=OLD/'run_62180_game01';result=json.loads((oldrun/'driver-result.json').read_text(encoding='utf-8-sig'));phases={p['phase']:p for p in result['phases']};frames={f['phase']:f for f in result['frames']};log=OLD/'stage/slot/BrnGame.log';retained=[]
for n in completed:
    states={}
    for state in ['positive','negative','restore']:
        name=f'{n:04}_{state}';assert name in phases and name in frames
        states[state]={'phase':phases[name],'frame':frames[name]}
    retained.append({'id':f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{n:04}','states':states})
(R/'RETAINED_COMPLETE.json').write_text(json.dumps({'predecessor':str(OLD),'raw_log':str(log),'raw_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'controls':retained,'previous_aggregate':'FAIL235sdeadline; strictflowcleanup/profilefixture passed','credit':'Independent reviewer settles individual pixels; no duplicate new credit'},indent=2),encoding='utf-8')
(R/'REVIEW_PACKET.md').write_text('''# Finish13 of the24-site native cohort\n\nSame private474/source32, new private62181, RootV8 normal41guard. Prior actualrun collected completePNR for51/52/54/55/56/57/58/59/66/67 before the235sdeadline; RETAINED_COMPLETE binds those windows/frames to the now-closed rawlog. Those ten are read-only refreshes here, no target or cleanup SET. E53 remains skipped dueoriginal1.1outside0..1. Only13 unfinished controls68/72-83 are written.43frames,42phases, unchanged235sdriver/240scase,64MiBlog and250MiBoutput envelope.\n\nOnly reader algorithm change: Read-Values now takes one complete immutable rawsnapshot perpoll and decodes all28 ordered triplets from it. Original Lines byte-prefixSHA revalidation is unchanged, as are Own/Wait/assert/ACK/frame/pose guards. Previous code re-read/copied/hashed the entire file for every alias, causing latephase slowdown. Exact snapshot bytecount/hash is now retained with every accepted phase. Review actualold/new function benchmark and typed/prefixrewrite fixtures. No snapshots or missing values are synthesized.\n\nActualworldscene gate and all remaining13 independent P/N/R/companion assertions still required. Previouslycompleted10 and out-of-range53 are not new proofcounts. Root settles canonical per-site credit after independent raw+pixel review. All prior FAILs retained.\n''',encoding='utf-8')
print('Finish13 packet prepared; no game launched')
