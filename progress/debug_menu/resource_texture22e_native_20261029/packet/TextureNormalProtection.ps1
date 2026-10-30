function Assert-TextureOrdinaryFileChain([string]$Path) {
  $full=[IO.Path]::GetFullPath($Path);$item=Get-Item -LiteralPath $full -Force -ErrorAction Stop
  if($item.PSIsContainer){throw 'Current-save source/snapshot leaf is a directory.'}
  $current=$full
  while($current){
    $part=Get-Item -LiteralPath $current -Force -ErrorAction Stop
    if($part.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Current-save source/snapshot chain contains a reparse point.'}
    $next=[IO.Path]::GetDirectoryName($current);if($next -ceq $current){break};$current=$next
  }
}
function Get-TextureNormalSnapshot([object]$Roster,[string]$NormalRoot,[object]$CandidateRecord) {
  $rows=@($Roster.runtime_payloads)+@($Roster.profile_config_log_preserved)
  if($rows.Count -ne 36 -or @($Roster.runtime_payloads).Count -ne 15 -or @($Roster.profile_config_log_preserved).Count -ne 21){throw 'Texture normal guard requires exact15+21 rows.'}
  $seen=@{};$out=@();$root=[IO.Path]::GetFullPath($NormalRoot).TrimEnd('\')
  foreach($row in $rows){
    $rel=([string]$row.relative_path).Replace('/','\');$path=[IO.Path]::GetFullPath((Join-Path $root $rel))
    if(!$path.StartsWith(($root+'\'),[StringComparison]::OrdinalIgnoreCase) -or $seen.ContainsKey($rel)){throw 'Normal guard row escaped or duplicated.'};$seen[$rel]=$true
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw ('Normal guard row is not an ordinary file: '+$rel)}
    $hash=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    $log=$rel -cin @('BrnGame.log','BrnGame.emergency.log')
    $profile=($rel -ceq 'Memcard\Profile.sav' -and $CandidateRecord.normal_profile_observation_sha256 -ceq $hash -and [long]$item.Length -eq [long]$row.bytes)
    if(!$log -and !$profile -and ($hash -cne [string]$row.sha256 -or [long]$item.Length -ne [long]$row.bytes)){throw ('Protected current normal row differs: '+$rel)}
    $out+=@([ordered]@{relative_path=$rel;path=$path;sha256=$hash;bytes=[long]$item.Length;historical_sha256=[string]$row.sha256;mutable_log=$log;recorded_current_profile=$profile})
  }
  return ,@($out)
}
function Compare-TextureNormalSnapshot([object[]]$Before) {
  $out=@();$bad=@();$logChanges=@()
  foreach($row in $Before){
    $path=[string]$row.path;$exists=Test-Path -LiteralPath $path -PathType Leaf
    $hash=if($exists){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}else{''}
    $bytes=if($exists){[long](Get-Item -LiteralPath $path).Length}else{-1}
    $changed=(!$exists -or $hash -cne [string]$row.sha256 -or $bytes -ne [long]$row.bytes)
    if($changed){if($row.mutable_log){$logChanges+=@([string]$row.relative_path)}else{$bad+=@([string]$row.relative_path)}}
    $out+=@([ordered]@{relative_path=$row.relative_path;before_sha256=$row.sha256;after_sha256=$hash;after_bytes=$bytes;changed=$changed;mutable_log=[bool]$row.mutable_log})
  }
  return [ordered]@{status=$(if($bad.Count){'protected_normal_nonlog_drift'}else{'protected_normal_nonlogs_unchanged'});pass=($bad.Count -eq 0);nonlog_drift=$bad;mutable_log_changes=$logChanges;rows=$out;normal_writes_performed=$false;writer_attribution='none; V8 logs are observations, never restored';checked_utc=[DateTime]::UtcNow.ToString('o')}
}
