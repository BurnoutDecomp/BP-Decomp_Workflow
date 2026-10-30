"""Prepare bounded remaining cloud/irradiance controls; un-restorable baselines are read-only."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;OLD=R.parent/'next_native_batch_20261029_scene';W=R.parents[2]
names=['prepare.py','make_driver.py','Case.ps1','Run.py','Preflight.ps1','OfflineChecks.ps1','Analyze.py','Request-HarnessPhaseDone.ps1','REVIEW_PACKET.md','Seal.py','CAPTURE_SOURCE_FIXTURE.json']
for name in names:
    text=(OLD/name).read_text(encoding='utf-8-sig')
    if name!='CAPTURE_SOURCE_FIXTURE.json':text=text.replace('62181','62180')
    if name=='prepare.py':
        text=text.replace('numbers=list(range(51,57))','numbers=list(range(51,60))').replace('number<=56','number<=59')
        text=text.replace("'type':'f32',\n          'original_call'", "'type':'f32','range_min':0.0,'range_max':(1.0 if number<=59 else 10.0),\n          'original_call'")
        text=text.replace("'control_count':21", "'control_count':24").replace("'max_frames':67", "'max_frames':76").replace("'maximum_frames':67", "'maximum_frames':76").replace("'selected_controls':21", "'selected_controls':24")
        text=text.replace('progress/debug_menu/reviewed_source32_integration_20261029/NORMAL_POST_INSTALL_ROSTER.json','scratch/DEBUG_MENU_1011/playable_refresh_20261029/delivery/NORMAL_POST_INSTALL_ROSTER.json')
    if name=='make_driver.py':
        text=text.replace("$plan.control_count -ne 21 -or $controls.Count -ne 25", "$plan.control_count -ne 24 -or $controls.Count -ne 28")
        text=text.replace("$frameRows.Count -ne 67 -or $phaseRows.Count -ne 66", "$frameRows.Count -ne (3*$script:eligibleControls.Count+4) -or $phaseRows.Count -ne (3*$script:eligibleControls.Count+3)")
        text=text.replace("if(!$owner){throw 'no exact", "if(!$owner){throw 'no exact")
        text=text.replace("$baselineFrame=$frameRows[$frameRows.Count-1]", """$script:eligibleControls=[Collections.Generic.List[object]]::new();$script:skippedAliases=@();$script:skippedControls=@()
 foreach($control in $plan.controls){
  $value=[double]::Parse($baseline[$control.alias],[cultureinfo]::InvariantCulture)
  if($value -lt [double]$control.range_min -or $value -gt [double]$control.range_max){$script:skippedAliases+=$control.alias;$script:skippedControls+=@{id=$control.id;alias=$control.alias;baseline=$baseline[$control.alias];reason='captured value outside original setter range; no target or cleanup SET permitted';state='pending'}}else{$script:eligibleControls.Add($control)}
 }
 if($script:eligibleControls.Count -lt 20){throw 'Fewer than20 baseline-restorable controls; no target writes'}
 $baselineFrame=$frameRows[$frameRows.Count-1]""")
        text=text.replace("owner_pid=$owner.Pid;slot=$Slot;controls=21", "owner_pid=$owner.Pid;slot=$Slot;selected_controls=24;eligible_controls=$script:eligibleControls.Count;skipped_controls=$script:skippedControls")
        text=text.replace('foreach($control in $plan.controls){\n  foreach($state', 'foreach($control in $script:eligibleControls){\n  foreach($state')
        text=text.replace("[void](Execute (($control.id -replace '^.*#','')+'_'+$state) @('set '+$control.alias+' '+$value) $expected)", """$commands=@();$companion=$null
   if($control.id -match '#005[24]$'){$companion='E56'}elseif($control.id -match '#0056$'){$companion='E52'}
   if($companion){
    if($companion -in $script:skippedAliases){throw 'Companion original baseline is not setter-restorable'}
    $companionValue=if($state -eq 'restore'){$baseline[$companion]}else{'0.5'}
    $commands+=('set '+$companion+' '+$companionValue);$expected[$companion]=$companionValue
   }
   $commands+=('set '+$control.alias+' '+$value)
   [void](Execute (($control.id -replace '^.*#','')+'_'+$state) $commands $expected)""")
        text=text.replace("foreach($k in $baseline.Keys){$restore[$k]=$baseline[$k]}", "foreach($k in $baseline.Keys){if($k -notin $script:skippedAliases){$restore[$k]=$baseline[$k]}}")
        text=text.replace("foreach($k in $baseline.Keys){$cleanup[$k]=$baseline[$k]}", "foreach($k in $baseline.Keys){if($k -notin $script:skippedAliases){$cleanup[$k]=$baseline[$k]}}")
        text=text.replace("terminal_restore_verified=$script:terminalRestoreVerified;site_credit=0", "terminal_restore_verified=$script:terminalRestoreVerified;selected_controls=24;eligible_control_count=$script:eligibleControls.Count;skipped_controls=$script:skippedControls;site_credit=0")
    if name=='Case.ps1':
        text=text.replace('environment21_','environment24_').replace('Twenty-one','Twenty-four').replace('exact21','exact selected restorable controls').replace('BRN_FRAME_DUMP_MAX=67','BRN_FRAME_DUMP_MAX=76')
        text=text.replace("$r.frames.Count -eq 67 -and $r.phases.Count -eq 66", "$r.eligible_control_count -ge 20 -and $r.frames.Count -eq (3*$r.eligible_control_count+4) -and $r.phases.Count -eq (3*$r.eligible_control_count+3)")
    if name=='Preflight.ps1':
        text=text.replace('$scope.controls.Count -ne 21','$scope.controls.Count -ne 24').replace('$aliases.Count -ne 25','$aliases.Count -ne 28').replace('.Count -ne 25','.Count -ne 28').replace('controls=21;aliases=25;max_frames=67','controls=24;aliases=28;max_frames=76')
    if name=='OfflineChecks.ps1':
        text=text.replace('$actual.Count -ne 75','$actual.Count -ne 84').replace('$i -lt 25','$i -lt 28').replace('$read.proofs.Count -ne 25 -or $read.values.Count -ne 25','$read.proofs.Count -ne 28 -or $read.values.Count -ne 28').replace('$commands.Count -ne 25','$commands.Count -ne 28')
        text=text.replace('actual_native_alias_triplets=25;actual_query_commands=75;actual_restore_commands=25','actual_native_alias_triplets=28;actual_query_commands=84;actual_restore_commands=28')
    (R/name).write_text(text,encoding='utf-8')
subprocess.run(['python',str(R/'make_driver.py')],check=True)
subprocess.run(['python',str(R/'prepare.py')],check=True)
blob=subprocess.check_output(['git','-C',str(W/'b5-decomp'),'show','abbc9047d850a4665d959993012261c55205e5e5:src/pc/gcm/renderengine/device.cpp'])
(R/'source/device.cpp').write_bytes(blob)
p=R/'SCOPE.json';scope=json.loads(p.read_text());scope['source_git_blob_sha256']['src/pc/gcm/renderengine/device.cpp']=hashlib.sha256(blob).hexdigest();scope['csv_field24']='live boost-effect mask, not engine state';scope['layer1_companions']={'0052':'E56 opacity=.5 during P/N; both original values restored in R','0054':'E56 opacity=.5 during P/N; both original values restored in R','0056':'E52 density=.5 during P/N; both original values restored in R'};p.write_text(json.dumps(scope,indent=2),encoding='utf-8')
(R/'REVIEW_PACKET.md').write_text('''# Bounded24 native remainder\n\nSame source32/exe474, private62180, original skipvideo latch. Selected24 sites are Environment0051-0059 plus0066-0068/0072-0083. Original Restore1.1 failure is preserved; this successor never normalizes captured baselines. It checks all selected values against the original RegisterFloat ranges before any target writes, skips un-restorable values explicitly as pending, and excludes their aliases from cleanup/emergency SET. At least20 restorable actual controls are required before target writes. E53=1.1 was observed and is expected to remain pending, untouched.\n\nSource-backed layer1 visibility prerequisites are explicit: for0052density/0054feather P/N only, E56opacity=.5; for0056opacity P/N only, E52density=.5. Each R returns both target and companion to their natural frozen values. Companions get no extra credit. All28 aliases are read after every target; all unmodified values including skippedE53 must retain captured baseline. New0057-59 darkRGB are layer0 sky shader inputs with original0..1ranges, same source/render chain.\n\nMax76frames640x360,64MiBlog,240s. Expected actual23controls if onlyE53 is skipped:73frames and72phases. Machine completion does not grant site credit. Actualscene review and individual P/N/R pixels remain required. Density51 already has a bounded proposal from retained prior run, so no duplicate new credit.\n\nNormal guard is a fresh36-file snapshot against Root-authorized normal41 roster7108e64001a5cbd33b402cf4de471393b61cc576b535bfdcbe128edfc012658c; private474 is unchanged. Exact raw reader/ACK/pose/image safeguards and official owned-only phase completion are retained. See current SCOPE/Driver/Case/Analyze and all original failed predecessors; no failure is relabeled.\n''',encoding='utf-8')
print('Bounded remainder prepared; no game launched')
