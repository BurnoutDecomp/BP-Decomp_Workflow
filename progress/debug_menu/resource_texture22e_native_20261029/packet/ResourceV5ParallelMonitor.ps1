function Get-ResourceV5Path([string]$Root,[string]$RelativePath) {
  if([string]::IsNullOrWhiteSpace($Root) -or [string]::IsNullOrWhiteSpace($RelativePath) -or [IO.Path]::IsPathRooted($RelativePath)){
    throw 'V5 authority paths must be non-empty repository-relative paths.'
  }
  $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\')
  $full=[IO.Path]::GetFullPath((Join-Path $rootFull ($RelativePath -replace '/','\')))
  if(!$full.StartsWith(($rootFull+'\'),[StringComparison]::OrdinalIgnoreCase)){
    throw "V5 authority path escaped the repository root: $RelativePath"
  }
  return $full
}

function Read-ResourceV5Json([string]$Root,[string]$Path) {
  $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\')
  $full=[IO.Path]::GetFullPath($Path)
  if(!$full.StartsWith(($rootFull+'\'),[StringComparison]::OrdinalIgnoreCase)){throw "V5 receipt escaped the repository root: $full"}
  $item=Get-Item -LiteralPath $full -Force -ErrorAction Stop
  if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw "V5 receipt is not a regular non-reparse file: $full"}
  $raw=[IO.File]::ReadAllText($full)
  return [pscustomobject]@{
    path=$full
    sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    value=($raw|ConvertFrom-Json -ErrorAction Stop)
  }
}

function ConvertTo-ResourceV5UtcTime([object]$Value) {
  if($Value -is [DateTime]){return $Value.ToUniversalTime()}
  $parsed=[DateTime]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
  return $parsed.ToUniversalTime()
}

function Assert-ResourceV5ParallelAuthority([string]$RepoRoot,[object]$Spec) {
  if($null -eq $Spec -or [int]$Spec.schema -ne 1 -or $Spec.status -cne 'bound_root_v5_parallel_policy' -or
     [string]::IsNullOrWhiteSpace([string]$Spec.policy_path) -or [string]::IsNullOrWhiteSpace([string]$Spec.policy_sha256) -or
     [string]::IsNullOrWhiteSpace([string]$Spec.delegation_path) -or [string]::IsNullOrWhiteSpace([string]$Spec.delegation_sha256) -or
     [string]::IsNullOrWhiteSpace([string]$Spec.policy_parent_delegation_path) -or [string]::IsNullOrWhiteSpace([string]$Spec.policy_parent_delegation_sha256) -or
     [string]::IsNullOrWhiteSpace([string]$Spec.normal_identity_roster_sha256) -or [string]::IsNullOrWhiteSpace([string]$Spec.normal_install_exe_sha256)){
    throw 'CASE_PLAN must bind the exact Root V5 policy, current V6 delegation, V5 policy parent, and V6 normal identity.'
  }
  $policyPath=Get-ResourceV5Path $RepoRoot ([string]$Spec.policy_path)
  $delegationPath=Get-ResourceV5Path $RepoRoot ([string]$Spec.delegation_path)
  $policyParentPath=Get-ResourceV5Path $RepoRoot ([string]$Spec.policy_parent_delegation_path)
  $policyFile=Read-ResourceV5Json $RepoRoot $policyPath
  $delegationFile=Read-ResourceV5Json $RepoRoot $delegationPath
  $policyParentFile=Read-ResourceV5Json $RepoRoot $policyParentPath
  if($policyFile.sha256 -cne [string]$Spec.policy_sha256 -or
     $delegationFile.sha256 -cne [string]$Spec.delegation_sha256 -or
     $policyParentFile.sha256 -cne [string]$Spec.policy_parent_delegation_sha256){
    throw 'Root V5 policy, V6 delegation, or V5 policy-parent bytes differ from the immutable CASE_PLAN binding.'
  }
  $policy=$policyFile.value;$delegation=$delegationFile.value
  $immediateParent=Read-ResourceV5Json $RepoRoot (Get-ResourceV5Path $RepoRoot ([string]$Spec.immediate_parent_delegation_path))
  if($immediateParent.sha256 -cne [string]$Spec.immediate_parent_delegation_sha256){throw 'Immediate parent delegation hash differs.'}
  $ancestryPointer=[string]$immediateParent.value.supersedes_delegation_sha256
  foreach($ancestor in $Spec.additional_ancestor_delegations){
    $ancestorReceipt=Read-ResourceV5Json $RepoRoot (Get-ResourceV5Path $RepoRoot ([string]$ancestor.path))
    if($ancestorReceipt.sha256 -cne [string]$ancestor.sha256 -or $ancestryPointer -cne $ancestorReceipt.sha256){throw 'Explicit normal-authority delegation ancestry differs.'}
    $ancestryPointer=[string]$ancestorReceipt.value.supersedes_delegation_sha256
  }
  if($ancestryPointer -cne $policyParentFile.sha256){throw 'Delegation ancestry does not reach the exact retained V4 policy parent.'}
  if([int]$policy.schema -ne 5 -or $policy.status -cne 'root_authorized_parallel_native_policy' -or
     $policy.parent_sha256 -cne $policyParentFile.sha256 -or
     $delegation.supersedes_delegation_sha256 -cne [string]$Spec.immediate_parent_delegation_sha256 -or
     $policy.other_game_policy.census -notmatch 'Informational' -or
     $policy.other_game_policy.foreign_game -notmatch 'May coexist' -or
     $policy.other_game_policy.known_campaign_peer -notmatch 'actual owned handoff' -or
     $policy.other_game_policy.monitor -notmatch 'not classify'){
    throw 'Root V5 policy does not contain the exact informational-census, dynamic-handoff, foreign-coexistence terms.'
  }
  if($delegation.authorizes_reviewed_successors -ne $true){throw 'Current delegation does not authorize reviewed successors.'}
  $effectiveSource=[string]$delegation.root_build_attestation.source_commit
  $effectiveWorkflow=[string]$delegation.root_build_attestation.workflow_build_commit
  if($delegation.root_build_attestation.executable_sha256 -cne [string]$Spec.candidate_exe_sha256){
    $supplement=$Spec.candidate_authority_supplement
    $record=Read-ResourceV5Json $RepoRoot (Get-ResourceV5Path $RepoRoot ([string]$supplement.path))
    $value=$record.value
    if($record.sha256 -cne [string]$supplement.sha256 -or $value.record_kind -cne 'receiver_record_of_existing_direct_Root_delegation_not_a_new_Root_signed_grant' -or $value.generated_by -cne '/root/playable_refresh_builder' -or $value.executable_sha256 -cne [string]$Spec.candidate_exe_sha256 -or $value.source_commit -cne [string]$supplement.source_commit -or $value.build_workflow -cne [string]$supplement.build_workflow -or $value.native_link_receipt_sha256 -cne [string]$supplement.canonical_link_sha256 -or $value.baseline_receipt_sha256 -cne [string]$supplement.startup_baseline_sha256 -or [int]$supplement.slot -notin @($value.Resource_slots) -or $value.normal_deployment -ne $false -or @($value.authority_basis).Count -ne 3){throw 'Exact received direct Root follow-on candidate/slot/baseline record differs; no claim of a new Root-signed grant is made.'}
  }
  if($delegation.root_build_attestation.executable_sha256 -cne [string]$Spec.candidate_exe_sha256){$effectiveSource=[string]$value.source_commit;$effectiveWorkflow=[string]$value.build_workflow}
  $normalIdentity=$delegation.post_install_normal_identity
  if($null -eq $normalIdentity -or $normalIdentity.roster_sha256 -cne [string]$Spec.normal_identity_roster_sha256 -or
     $normalIdentity.executable_sha256 -cne [string]$Spec.normal_install_exe_sha256){
    throw 'Current Root V6 delegation does not bind the selected merged-GUI normal identity.'
  }
  $normalRosterPath=[IO.Path]::GetFullPath([string]$normalIdentity.roster)
  $normalRoster=Read-ResourceV5Json $RepoRoot $normalRosterPath
  if($normalRoster.sha256 -cne [string]$normalIdentity.roster_sha256){throw 'Root V6 normal-install roster bytes differ from its delegated identity hash.'}
  $actors=@()
  foreach($source in @($Spec.campaign_actors)){
    $actorName=[string]$source.executor_key
    if([string]::IsNullOrWhiteSpace($actorName) -or [string]::IsNullOrWhiteSpace([string]$source.actor) -or
       [string]::IsNullOrWhiteSpace([string]$source.discovery_kind) -or [string]::IsNullOrWhiteSpace([string]$source.discovery_root)){
      throw 'V5 campaign actor row is incomplete.'
    }
    $executorProperty=$delegation.executors.PSObject.Properties[$actorName]
    if($null -eq $executorProperty){throw "V5 campaign actor $actorName is absent from the Root delegation."}
    $executor=$executorProperty.Value
    foreach($slotValue in @($source.slots)){
      if([int]$slotValue -le 0 -or @($executor.slots|Where-Object {[int]$_ -eq [int]$slotValue}).Count -ne 1){
        throw "V5 campaign actor $actorName contains a slot not authorized by the Root delegation: $slotValue"
      }
    }
    $actorPath=Get-ResourceV5Path $RepoRoot ([string]$source.discovery_root)
    $actors+=@([pscustomobject]@{actor=$source.actor;executor_key=$actorName;executor=$executor;discovery_kind=$source.discovery_kind;discovery_root=$actorPath;slots=@($source.slots)})
  }
  return [pscustomobject]@{
    policy=$policy
    policy_path=$policyFile.path
    policy_sha256=$policyFile.sha256
    delegation=$delegation
    delegation_path=$delegationFile.path
    delegation_sha256=$delegationFile.sha256
    policy_parent_delegation_path=$policyParentFile.path
    policy_parent_delegation_sha256=$policyParentFile.sha256
    normal_identity_roster_path=$normalRoster.path
    normal_identity_roster_sha256=$normalRoster.sha256
    normal_install_exe_sha256=[string]$normalIdentity.executable_sha256
    actor_sources=@($actors)
    candidate_exe_sha256=[string]$Spec.candidate_exe_sha256
    source_commit=$effectiveSource
    workflow_commit=$effectiveWorkflow
  }
}

function Get-ResourceV5ProfilePath([string]$StageRoot,[int]$Slot) {
  return [IO.Path]::GetFullPath((Join-Path $StageRoot ("data\Memcard_{0}\Profile.sav" -f $Slot)))
}

function Get-ResourceV5PeerAuthorityRows([string]$RepoRoot,[object]$Authority,[object[]]$Processes=@()) {
  $rows=@()
  foreach($source in @($Authority.actor_sources)){
    foreach($slotValue in @($source.slots)){
      $peerSlot=[int]$slotValue
      $slotRoot=$null
      $handoffFiles=@()
      if($source.discovery_kind -ceq 'props_run_directories'){
        $slotRoot=Join-Path $source.discovery_root ("props_physical_native_{0}" -f $peerSlot)
        if(Test-Path -LiteralPath $slotRoot -PathType Container){
          $runDirectories=@()
          try{$runDirectories=@(Get-ChildItem -LiteralPath $slotRoot -Directory -Force -ErrorAction Stop)}catch{$runDirectories=@()}
          foreach($runDirectory in $runDirectories){
            if($runDirectory.Attributes -band [IO.FileAttributes]::ReparsePoint){continue}
            $handoffPath=Join-Path $runDirectory.FullName 'ROOT_HANDOFF.json'
            if(Test-Path -LiteralPath $handoffPath -PathType Leaf){$handoffFiles+=@([pscustomobject]@{path=$handoffPath;run_root=$runDirectory.FullName})}
          }
        }
      }elseif($source.discovery_kind -ceq 'deformation_slot_binding'){
        $slotRoot=Join-Path $source.discovery_root ([string]$peerSlot)
        $handoffPath=Join-Path $slotRoot 'ROOT_HANDOFF.json'
        if(Test-Path -LiteralPath $handoffPath -PathType Leaf){$handoffFiles+=@([pscustomobject]@{path=$handoffPath;run_root=$slotRoot})}
      }else{throw "Unsupported V5 campaign peer discovery kind: $($source.discovery_kind)"}
      foreach($handoffFile in $handoffFiles){
        try{
        $handoffRecord=Read-ResourceV5Json $RepoRoot $handoffFile.path
        $handoff=$handoffRecord.value
        $handoffPid=if($source.discovery_kind -ceq 'props_run_directories'){[int]$handoff.process_id}else{[int]$handoff.pid}
        $handoffStartValue=if($source.discovery_kind -ceq 'props_run_directories'){$handoff.process_start_time_utc}else{$handoff.start_utc}
        $handoffImageText=if($source.discovery_kind -ceq 'props_run_directories'){[string]$handoff.process_image_path}else{[string]$handoff.image}
        try{$handoffStart=ConvertTo-ResourceV5UtcTime $handoffStartValue;$handoffImage=[IO.Path]::GetFullPath($handoffImageText)}catch{continue}
        $exactLiveMatches=@()
        $pidCandidates=@($Processes|Where-Object {[int]$_.pid -eq $handoffPid})
        foreach($liveProcess in $pidCandidates){
          if([long]$liveProcess.start_ticks -ne $handoffStart.Ticks -or [string]::IsNullOrWhiteSpace([string]$liveProcess.image_path)){continue}
          try{$liveImage=[IO.Path]::GetFullPath([string]$liveProcess.image_path)}catch{continue}
          if($liveImage -ieq $handoffImage){$exactLiveMatches+=@($liveProcess)}
        }
        if($exactLiveMatches.Count -ne 1){continue}
        if($source.discovery_kind -ceq 'props_run_directories'){
          if($handoff.status -cne 'owned' -or [int]$handoff.slot -ne $peerSlot){continue}
          $runRoot=[IO.Path]::GetFullPath([string]$handoff.run_dir)
          if($runRoot -ine [IO.Path]::GetFullPath([string]$handoffFile.run_root)){continue}
          $runPrefix=[IO.Path]::GetFullPath($slotRoot).TrimEnd('\')+'\'
          if(!$runRoot.StartsWith($runPrefix,[StringComparison]::OrdinalIgnoreCase)){continue}
          $preflightPath=Join-Path $runRoot 'RUN_PREFLIGHT_BINDING.json'
          if(!(Test-Path -LiteralPath $preflightPath -PathType Leaf)){continue}
          $preflightRecord=Read-ResourceV5Json $RepoRoot $preflightPath
          $preflight=$preflightRecord.value
          if($preflight.status -cne 'launch-authorized-by-receipts' -or [int]$preflight.slot -ne $peerSlot -or
             $preflight.allow_concurrent_games -ne $true -or [int]$preflight.max_concurrent_other_games -lt 1 -or
             [int]$preflight.max_concurrent_other_games -gt 100 -or
             $preflight.source_b5_commit -cne $Authority.delegation.root_build_attestation.source_commit -or
             $preflight.workflow_commit -cne $Authority.delegation.root_build_attestation.workflow_build_commit -or
             $preflight.executable_sha256 -cne $Authority.candidate_exe_sha256){continue}
          $image=$handoffImage
          $imageHash=(Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()
          $stageRoot=[IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent $image)))
          $profile=[IO.Path]::GetFullPath([string]$handoff.profile_path)
          $stagePrefix=$stageRoot.TrimEnd('\')+'\'
          if($imageHash -cne [string]$handoff.process_image_sha256 -or $imageHash -cne $Authority.candidate_exe_sha256 -or
             !$image.StartsWith($stagePrefix,[StringComparison]::OrdinalIgnoreCase) -or
             !$profile.StartsWith($stagePrefix,[StringComparison]::OrdinalIgnoreCase) -or
             [IO.Path]::GetFullPath([string]$preflight.stage_root) -ine $stageRoot -or
             [IO.Path]::GetFullPath([string]$preflight.private_profile_preflight.path) -ine $profile){continue}
          $start=$handoffStart
          $runtimeFields=[ordered]@{
            runtime_workflow_commit=[string]$handoff.runtime_workflow_commit
            runtime_run_case_sha256=[string]$handoff.runtime_run_case_sha256
            runtime_flow_run_sha256=[string]$handoff.runtime_flow_run_sha256
            phase_done_requester_sha256=[string]$handoff.phase_done_helper_sha256
          }
          if($runtimeFields.runtime_workflow_commit -cne [string]$preflight.runtime_workflow_commit -or
             $runtimeFields.runtime_run_case_sha256 -cne [string]$preflight.runtime_run_case_sha256 -or
             $runtimeFields.runtime_flow_run_sha256 -cne [string]$preflight.runtime_flow_run_sha256 -or
             $runtimeFields.phase_done_requester_sha256 -cne [string]$preflight.phase_done_helper_sha256){continue}
          $statusPath=Join-Path $runRoot 'ROOT_HANDOFF_STATUS.json'
          $statusSha=if(Test-Path -LiteralPath $statusPath -PathType Leaf){(Get-FileHash -LiteralPath $statusPath -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null}
          $inputHandles=@();if($handoff.PSObject.Properties['input_handles']){$inputHandles=@($handoff.input_handles|Where-Object {!([string]::IsNullOrWhiteSpace([string]$_))})}
          $sharedOutputPaths=@();if($handoff.PSObject.Properties['shared_output_paths']){$sharedOutputPaths=@($handoff.shared_output_paths|Where-Object {!([string]::IsNullOrWhiteSpace([string]$_))})}
          $rows+=@([pscustomobject]@{
            actor=[string]$source.actor;executor_key=[string]$source.executor_key
            pid=[int]$handoff.process_id;start_ticks=[long]$start.Ticks;start_time_utc=$start.ToString('o')
            name='Burnout_PC.exe';image_path=$image;image_sha256=$imageHash;slot=$peerSlot
            stage_root=$stageRoot;profile_path=$profile;input_handles=$inputHandles
            shared_output_paths=$sharedOutputPaths
            shared_output_mutex=[string]$handoff.shared_output_mutex
            suite=[string]$preflight.case;run_name=[string]$preflight.case
            handoff_path=$handoffRecord.path;handoff_sha256=$handoffRecord.sha256
            preflight_path=$preflightRecord.path;preflight_sha256=$preflightRecord.sha256
            packet_manifest_sha256=[string]$preflight.packet_manifest_sha256
            handoff_status_path=$(if($statusSha){$statusPath}else{$null});handoff_status_sha256=$statusSha
            authority_receipts=@([ordered]@{path=$handoffRecord.path;sha256=$handoffRecord.sha256},
                                 [ordered]@{path=$preflightRecord.path;sha256=$preflightRecord.sha256})
            runtime_workflow_commit=$runtimeFields.runtime_workflow_commit
            runtime_run_case_sha256=$runtimeFields.runtime_run_case_sha256
            runtime_flow_run_sha256=$runtimeFields.runtime_flow_run_sha256
            phase_done_requester_sha256=$runtimeFields.phase_done_requester_sha256
          })
        }else{
          if([int]$handoff.slot -ne $peerSlot){continue}
          $reviewPath=Join-Path $slotRoot 'ROOT_PRELAUNCH_REVIEW.json'
          $bindingPath=Join-Path $slotRoot 'BINDING.json'
          if(!(Test-Path -LiteralPath $reviewPath -PathType Leaf) -or !(Test-Path -LiteralPath $bindingPath -PathType Leaf)){continue}
          $reviewRecord=Read-ResourceV5Json $RepoRoot $reviewPath
          $bindingRecord=Read-ResourceV5Json $RepoRoot $bindingPath
          $review=$reviewRecord.value;$binding=$bindingRecord.value
          if($review.status -cne 'ready' -or [int]$review.slot -ne $peerSlot -or
             $review.root_delegation_sha256 -notin @($Authority.policy.parent_sha256,$Authority.delegation_sha256) -or
             $review.execution_exe_sha256 -cne $Authority.candidate_exe_sha256 -or
             $binding.status -cne 'root_reviewed_ready' -or [int]$binding.slot -ne $peerSlot){continue}
          $image=$handoffImage
          $stageRoot=[IO.Path]::GetFullPath([string]$review.private_stage_root)
          $expectedImage=[IO.Path]::GetFullPath((Join-Path $stageRoot 'slot\Burnout_PC.exe'))
          if($image -ine $expectedImage -or [IO.Path]::GetFullPath([string]$binding.private_stage_root) -ine $stageRoot){continue}
          $imageHash=(Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()
          if($imageHash -cne $Authority.candidate_exe_sha256){continue}
          $start=$handoffStart
          $ownerRecords=@()
          foreach($runDirectory in @(Get-ChildItem -LiteralPath $slotRoot -Directory -Force -ErrorAction Stop|Where-Object {$_.Name -like 'run_*' -and !($_.Attributes -band [IO.FileAttributes]::ReparsePoint)})){
            $ownerPath=Join-Path $runDirectory.FullName 'deformation-native-owner.json'
            if(!(Test-Path -LiteralPath $ownerPath -PathType Leaf)){continue}
            $ownerRecord=Read-ResourceV5Json $RepoRoot $ownerPath
            $owner=$ownerRecord.value
            if([int]$owner.pid -eq [int]$handoff.pid -and [int]$owner.slot -eq $peerSlot -and
               [IO.Path]::GetFullPath([string]$owner.image) -ieq $image -and
               (ConvertTo-ResourceV5UtcTime $owner.start_utc).Ticks -eq $start.Ticks -and
               [string]$owner.exe_sha256 -ceq $imageHash){$ownerRecords+=@([pscustomobject]@{record=$ownerRecord;value=$owner;run_dir=$runDirectory.FullName})}
          }
          if($ownerRecords.Count -ne 1){continue}
          $owner=$ownerRecords[0].value
          $profile=Get-ResourceV5ProfilePath $stageRoot $peerSlot
          $rows+=@([pscustomobject]@{
            actor=[string]$source.actor;executor_key=[string]$source.executor_key
            pid=[int]$handoff.pid;start_ticks=[long]$start.Ticks;start_time_utc=$start.ToString('o')
            name='Burnout_PC.exe';image_path=$image;image_sha256=$imageHash;slot=$peerSlot
            stage_root=$stageRoot;profile_path=$profile;input_handles=@($handoff.input_handles)
            shared_output_paths=@($handoff.shared_output_paths);shared_output_mutex=[string]$handoff.shared_output_mutex
            suite='deformation_native';run_name=[string]$ownerRecords[0].run_dir
            handoff_path=$handoffRecord.path;handoff_sha256=$handoffRecord.sha256
            preflight_path=$reviewRecord.path;preflight_sha256=$reviewRecord.sha256
            binding_path=$bindingRecord.path;binding_sha256=$bindingRecord.sha256
            packet_manifest_sha256=''
            handoff_status_path=(Join-Path $slotRoot 'ROOT_HANDOFF_RESULT.json')
            handoff_status_sha256=$(if(Test-Path -LiteralPath (Join-Path $slotRoot 'ROOT_HANDOFF_RESULT.json') -PathType Leaf){(Get-FileHash -LiteralPath (Join-Path $slotRoot 'ROOT_HANDOFF_RESULT.json') -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null})
            authority_receipts=@([ordered]@{path=$handoffRecord.path;sha256=$handoffRecord.sha256},
                                 [ordered]@{path=$reviewRecord.path;sha256=$reviewRecord.sha256},
                                 [ordered]@{path=$bindingRecord.path;sha256=$bindingRecord.sha256},
                                 [ordered]@{path=$ownerRecords[0].record.path;sha256=$ownerRecords[0].record.sha256})
            runtime_workflow_commit=[string]$owner.runtime_upstream_commit
            runtime_run_case_sha256=[string]$review.run_case_sha256
            runtime_flow_run_sha256=[string]$review.flow_run_sha256
            phase_done_requester_sha256=[string]$review.phase_done_requester_sha256
          })
        }
        }catch{
          continue
        }
      }
    }
  }
  return ,@($rows)
}

function Get-ResourceV5InferredSlot([string]$ImagePath) {
  if([string]::IsNullOrWhiteSpace($ImagePath)){return 0}
  foreach($pattern in @(
    '(?i)[\\/]slot_bindings[\\/](?<slot>[0-9]{5,})(?:[\\/]|$)',
    '(?i)[\\/]props_physical_stage_(?<slot>[0-9]{5})(?:_[^\\/]*)?[\\/]',
    '(?i)[\\/]Memcard_(?<slot>[0-9]{5})(?:[\\/]|$)',
    '(?i)[\\/]slot[_-](?<slot>[0-9]{5})(?:[\\/]|$)'
  )){
    $match=[regex]::Match($ImagePath,$pattern)
    if($match.Success){try{return [int]$match.Groups['slot'].Value}catch{return 0}}
  }
  return 0
}

function Get-ResourceV5OwnedInputHandles([int]$Slot,[int]$ProcessId,[long]$StartTicks) {
  $handles=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  for($key=0;$key -lt 256;$key++){
    [void]$handles.Add(('Local\BurnoutPC_DebugKey_{0:X2}_{1}' -f $key,$Slot))
  }
  if($ProcessId -gt 0){[void]$handles.Add(('Local\BurnoutPC_FrameRequest_{0}_{1}' -f $ProcessId,$Slot))}
  [void]$handles.Add(('Local\BurnoutPC_Input_Accept_{0}' -f $Slot))
  if($ProcessId -gt 0 -and $StartTicks -gt 0){[void]$handles.Add(('Local\BurnoutPC_HarnessPhaseDone_{0}_{1}_{2}' -f $ProcessId,$Slot,$StartTicks))}
  return ,@($handles)
}

function Resolve-ResourceV5ProcessObservations(
  [object[]]$Processes,
  [object[]]$CampaignPeers,
  [string]$OwnedImagePath,
  [string]$OwnedStageRoot,
  [string]$OwnedProfilePath,
  [int]$OwnedSlot,
  [int]$OwnedProcessId,
  [long]$OwnedStartTicks,
  [string]$NormalInstallRoot,
  [string[]]$NormalProfilePaths,
  [string]$SharedOutputPath,
  [string]$SharedOutputMutex,
  [int]$MaxKnownPeers=100
) {
  $ownedImage=[IO.Path]::GetFullPath($OwnedImagePath)
  $ownedStage=[IO.Path]::GetFullPath($OwnedStageRoot).TrimEnd('\')
  $ownedProfile=[IO.Path]::GetFullPath($OwnedProfilePath)
  $normalRoot=[IO.Path]::GetFullPath($NormalInstallRoot).TrimEnd('\')
  $normalPrefix=$normalRoot+'\'
  $ownedPrefix=$ownedStage+'\'
  $ownHandles=Get-ResourceV5OwnedInputHandles $OwnedSlot $OwnedProcessId $OwnedStartTicks
  $known=@();$foreign=@();$all=@();$knownSlots=@{}
  foreach($process in @($Processes)){
    $pidValue=[int]$process.pid
    $name=[string]$process.name
    $imagePath=[string]$process.image_path
    $startTicks=[long]$process.start_ticks
    if($pidValue -le 0 -or $startTicks -le 0){throw "Live game process row lacks a retained PID/start identity: PID $pidValue"}
    $normalizedImage=$null
    if(![string]::IsNullOrWhiteSpace($imagePath)){
      try{$normalizedImage=[IO.Path]::GetFullPath($imagePath)}catch{$normalizedImage=$null}
    }
    if($pidValue -eq $OwnedProcessId -and $OwnedProcessId -gt 0){
      if($startTicks -ne $OwnedStartTicks -or $null -eq $normalizedImage -or $normalizedImage -ine $ownedImage){throw 'Owned game PID/start/image identity changed in the V5 process census.'}
    }
    if($null -ne $normalizedImage -and $normalizedImage -ieq $ownedImage){
      if($OwnedProcessId -le 0){throw 'A live process already uses the exact Resource-owned executable path before owned-process adoption.'}
      if($pidValue -ne $OwnedProcessId -or $startTicks -ne $OwnedStartTicks){throw 'Another live process uses the exact Resource-owned executable path.'}
      $row=[pscustomobject]@{pid=$pidValue;name=$name;image_path=$normalizedImage;start_ticks=$startTicks;slot=$OwnedSlot;classification='resource_owned_process';actor='resource_recovery_swarm';stage_root=$ownedStage;profile_path=$ownedProfile;handoff_path=$null;handoff_sha256=$null;authority_receipts=@()}
      $all+=@($row);continue
    }
    $peerMatches=@($CampaignPeers|Where-Object {
      [int]$_.pid -eq $pidValue -and [long]$_.start_ticks -eq $startTicks -and
      $null -ne $normalizedImage -and [IO.Path]::GetFullPath([string]$_.image_path) -ieq $normalizedImage
    })
    if($peerMatches.Count -eq 1){
      $peer=$peerMatches[0]
      if([int]$peer.slot -le 0 -or [int]$peer.slot -eq $OwnedSlot){throw "Known campaign peer PID $pidValue collides with Resource slot $OwnedSlot."}
      $stage=[IO.Path]::GetFullPath([string]$peer.stage_root).TrimEnd('\')
      $stagePrefix=$stage+'\'
      $profilePath=if([string]::IsNullOrWhiteSpace([string]$peer.profile_path)){Get-ResourceV5ProfilePath $stage ([int]$peer.slot)}else{[IO.Path]::GetFullPath([string]$peer.profile_path)}
      if($normalizedImage -ieq $ownedImage -or $stage -ieq $ownedStage -or $normalizedImage.StartsWith($ownedPrefix,[StringComparison]::OrdinalIgnoreCase)){throw "Known campaign peer PID $pidValue collides with the Resource private image/stage."}
      if($profilePath -ieq $ownedProfile -or $profilePath.StartsWith($ownedPrefix,[StringComparison]::OrdinalIgnoreCase)){throw "Known campaign peer PID $pidValue collides with the Resource private profile or stage."}
      foreach($normalProfile in @($NormalProfilePaths)){
        if(![string]::IsNullOrWhiteSpace([string]$normalProfile) -and $profilePath -ieq [IO.Path]::GetFullPath([string]$normalProfile)){throw "Known campaign peer PID $pidValue uses a protected normal profile."}
      }
      $peerHandles=@($peer.input_handles)
      if($peerHandles.Count -gt 0){
        $peerHandleSet=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach($handle in $peerHandles){if(![string]::IsNullOrWhiteSpace([string]$handle)){[void]$peerHandleSet.Add([string]$handle)}}
        foreach($handle in $ownHandles){if($peerHandleSet.Contains([string]$handle)){throw "Known campaign peer PID $pidValue shares a Resource scoped input handle."}}
      }
      $sharedCollision=@($peer.shared_output_paths|Where-Object {
        ![string]::IsNullOrWhiteSpace([string]$_) -and [IO.Path]::GetFullPath([string]$_) -ieq [IO.Path]::GetFullPath($SharedOutputPath)
      })
      if($sharedCollision.Count -gt 0 -and [string]$peer.shared_output_mutex -cne $SharedOutputMutex){throw "Known campaign peer PID $pidValue shares the Resource dump output without the exact Resource action mutex."}
      $slotKey=[string][int]$peer.slot
      if($knownSlots.ContainsKey($slotKey)){throw "Multiple active campaign peers claim private slot $slotKey."}
      $knownSlots[$slotKey]=$pidValue
      $row=[pscustomobject]@{
        pid=$pidValue;name=$name;image_path=$normalizedImage;start_ticks=$startTicks
        slot=[int]$peer.slot;classification='known_campaign_peer';actor=[string]$peer.actor
        suite=[string]$peer.suite;run_name=[string]$peer.run_name;stage_root=$stage;profile_path=$profilePath
        image_sha256=[string]$peer.image_sha256;handoff_path=[string]$peer.handoff_path;handoff_sha256=[string]$peer.handoff_sha256
        preflight_path=[string]$peer.preflight_path;preflight_sha256=[string]$peer.preflight_sha256
        packet_manifest_sha256=[string]$peer.packet_manifest_sha256;authority_receipts=@($peer.authority_receipts)
        runtime_workflow_commit=[string]$peer.runtime_workflow_commit;runtime_run_case_sha256=[string]$peer.runtime_run_case_sha256
        runtime_flow_run_sha256=[string]$peer.runtime_flow_run_sha256;phase_done_requester_sha256=[string]$peer.phase_done_requester_sha256
        shared_output_paths=@($peer.shared_output_paths);shared_output_mutex=[string]$peer.shared_output_mutex
      }
      $known+=@($row);$all+=@($row);continue
    }
    if($null -ne $normalizedImage -and ($normalizedImage -ieq $ownedImage -or $normalizedImage.StartsWith($ownedPrefix,[StringComparison]::OrdinalIgnoreCase))){
      throw "Unowned process PID $pidValue collides with the exact Resource private image/stage."
    }
    $normalInstallImage=$null -ne $normalizedImage -and ($normalizedImage -ieq $normalRoot -or $normalizedImage.StartsWith($normalPrefix,[StringComparison]::OrdinalIgnoreCase))
    $inferredSlot=Get-ResourceV5InferredSlot ([string]$normalizedImage)
    if($inferredSlot -eq $OwnedSlot){throw "Unclassified live game PID $pidValue advertises Resource private slot $OwnedSlot."}
    $reason=if($null -eq $normalizedImage){'unknown_missing_image_path'}elseif($normalInstallImage){'foreign_normal_install_without_exact_owned_handoff'}else{'foreign_game_without_exact_owned_handoff'}
    $row=[pscustomobject]@{pid=$pidValue;name=$name;image_path=$normalizedImage;start_ticks=$startTicks;slot=$inferredSlot;normal_install_image_observed=$normalInstallImage;classification=$reason;actor=$null;stage_root=$null;profile_path=$null;handoff_path=$null;handoff_sha256=$null;authority_receipts=@()}
    $foreign+=@($row);$all+=@($row)
  }
  if($known.Count -gt $MaxKnownPeers){throw "V5 known campaign peer count $($known.Count) exceeds the Root-authorized limit $MaxKnownPeers."}
  return [pscustomobject]@{
    census_policy='informational'
    known_campaign_peer_count=$known.Count
    foreign_game_count=$foreign.Count
    max_known_campaign_peers=$MaxKnownPeers
    processes=@($all|Sort-Object pid)
    known_campaign_peers=@($known|Sort-Object pid)
    foreign_games=@($foreign|Sort-Object pid)
    collisions=@()
  }
}

function Add-ResourceV5FirstObservation([string]$RepoRoot,[string]$LedgerPath,[string]$Phase,[object]$Observation,[hashtable]$Seen,[string]$PolicySha256,[string]$OwnedRunRoot,[string]$OwnedSuite,[string]$OwnedRunName) {
  $repoFull=[IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $ledgerFull=[IO.Path]::GetFullPath($LedgerPath)
  if($OwnedRunRoot){
    if($OwnedSuite -notin @('resource_windows','resource_stats_allocator') -or $OwnedRunName -notmatch ('^'+[regex]::Escape($OwnedSuite)+'_[0-9]{8}_[0-9]{6}$')){throw 'Private observation ledger lacks its exact suite/run identity.'}
    $outputPlan=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'CASE_PLAN.json') -Raw|ConvertFrom-Json
    $expectedPrivateRun=[IO.Path]::GetFullPath((Join-Path ([string]$outputPlan.runtime_output_root) $OwnedRunName))
    $ownedFull=[IO.Path]::GetFullPath($OwnedRunRoot)
    if($OwnedRunRoot.Replace('\','/') -match '(^|/)\.\.(/|$)' -or $LedgerPath.Replace('\','/') -match '(^|/)\.\.(/|$)' -or $ownedFull -ine $expectedPrivateRun -or $ledgerFull -ine (Join-Path $expectedPrivateRun 'CAMPAIGN_PEER_FIRST_OBSERVATIONS.jsonl')){throw 'Private observation ledger escaped its exact owned suite/run/filename.'}
    $ancestor=Split-Path -Parent $ledgerFull
    while($ancestor){
      if(Test-Path -LiteralPath $ancestor){$ancestorItem=Get-Item -LiteralPath $ancestor -Force;if($ancestorItem.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Private observation ledger ancestor is a reparse point.'}}
      $next=Split-Path -Parent $ancestor;if($next -ceq $ancestor){break};$ancestor=$next
    }
  }elseif(!$ledgerFull.StartsWith(($repoFull+'\'),[StringComparison]::OrdinalIgnoreCase)){throw 'V5 first-observation ledger escaped the repository run tree.'}
  if(Test-Path -LiteralPath $ledgerFull){
    $ledgerItem=Get-Item -LiteralPath $ledgerFull -Force
    if($ledgerItem.PSIsContainer -or ($ledgerItem.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Observation ledger leaf must be an ordinary non-reparse file.'}
  }
  $parent=Split-Path -Parent $ledgerFull
  if(!(Test-Path -LiteralPath $parent -PathType Container)){throw "V5 observation ledger parent is missing: $parent"}
  $parentItem=Get-Item -LiteralPath $parent -Force
  if($parentItem.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'V5 observation ledger parent is a reparse point.'}
  $newEvents=[Collections.Generic.List[object]]::new()
  foreach($row in $Observation.processes){
    if([string]$row.classification -eq 'resource_owned_process'){continue}
    $key=('{0}:{1}' -f [int]$row.pid,[long]$row.start_ticks)
    $classification=[string]$row.classification
    if(!$Seen.ContainsKey($key)){
      $Seen[$key]=$classification
      $newEvents.Add([ordered]@{schema=1;event='first_observation';phase=$Phase;observed_utc=[DateTime]::UtcNow.ToString('o');policy_sha256=$PolicySha256;pid=[int]$row.pid;name=[string]$row.name;image_path=$row.image_path;start_ticks=[long]$row.start_ticks;classification=$classification;actor=$row.actor;slot=[int]$row.slot;stage_root=$row.stage_root;profile_path=$row.profile_path;handoff_path=$row.handoff_path;handoff_sha256=$row.handoff_sha256;preflight_path=$row.preflight_path;preflight_sha256=$row.preflight_sha256;packet_manifest_sha256=$row.packet_manifest_sha256;authority_receipts=@($row.authority_receipts)})
    }elseif($Seen[$key] -cne $classification){
      $Seen[$key]=$classification
      $newEvents.Add([ordered]@{schema=1;event='classification_changed';phase=$Phase;observed_utc=[DateTime]::UtcNow.ToString('o');policy_sha256=$PolicySha256;pid=[int]$row.pid;name=[string]$row.name;image_path=$row.image_path;start_ticks=[long]$row.start_ticks;classification=$classification;actor=$row.actor;slot=[int]$row.slot;stage_root=$row.stage_root;profile_path=$row.profile_path;handoff_path=$row.handoff_path;handoff_sha256=$row.handoff_sha256;preflight_path=$row.preflight_path;preflight_sha256=$row.preflight_sha256;packet_manifest_sha256=$row.packet_manifest_sha256;authority_receipts=@($row.authority_receipts)})
    }
  }
  if(!(Test-Path -LiteralPath $ledgerFull -PathType Leaf)){
    $header=[ordered]@{schema=1;event='v5_parallel_policy_bound';policy_path=$Observation.policy_path;policy_sha256=$PolicySha256;delegation_path=$Observation.delegation_path;delegation_sha256=$Observation.delegation_sha256;created_utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText($ledgerFull,((ConvertTo-Json -InputObject $header -Compress -Depth 8)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))
  }
  if($newEvents.Count -gt 0){
    $builder=[Text.StringBuilder]::new()
    foreach($event in $newEvents){[void]$builder.Append((ConvertTo-Json -InputObject $event -Compress -Depth 10)).Append([Environment]::NewLine)}
    [IO.File]::AppendAllText($ledgerFull,$builder.ToString(),[Text.UTF8Encoding]::new($false))
  }
}
