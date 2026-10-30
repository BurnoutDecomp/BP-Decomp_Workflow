function Test-Source45Captures($ctx) {
 try {
  $dir=[IO.Path]::GetFullPath([string]$ctx.RunDir)
  if(Test-Path -LiteralPath (Join-Path $dir 'CAPTURE_ERROR.json')){throw 'capture helper reported failure'}
  $capturePath=Join-Path $dir 'CAPTURES.json';$stopPath=Join-Path $dir 'PHASE_STOP_REQUEST.json';$ownerPath=Join-Path $dir 'CAPTURE_OWNER.json';$terminalPath=Join-Path $dir 'flow-terminal.json'
  foreach($p in @($capturePath,$stopPath,$ownerPath,$terminalPath,$ctx.Log)){if(!(Test-Path -LiteralPath $p -PathType Leaf)){throw "missing evidence: $p"}}
  $captures=@(Get-Content -Raw -LiteralPath $capturePath|ConvertFrom-Json);$stop=Get-Content -Raw -LiteralPath $stopPath|ConvertFrom-Json;$owner=Get-Content -Raw -LiteralPath $ownerPath|ConvertFrom-Json;$terminal=Get-Content -Raw -LiteralPath $terminalPath|ConvertFrom-Json
  $flow=$terminal.flow_status;$statusPath=Join-Path (Join-Path $dir 'flow') 'terminal-status.json';if(!(Test-Path -LiteralPath $statusPath) -or (Get-FileHash -LiteralPath $statusPath -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$terminal.flow_status_sha256){throw 'original flow status hash mismatch'};$stage=Get-Content -Raw -LiteralPath (Join-Path $ctx.Case.OwnerDir 'STAGING.json')|ConvertFrom-Json
  if($captures.Count -ne 10 -or $stop.captures -ne 10 -or $terminal.slot -ne 62185 -or $flow.owned_pid -ne $owner.pid -or !$flow.phase_collection_stop_requested -or !$flow.owned_cleanup_complete -or !$flow.input_reset_complete -or !$terminal.success){throw 'capture count or strict phase-stop/cleanup mismatch'}
  $ticks=if($flow.owned_start_utc -is [DateTime]){$flow.owned_start_utc.ToUniversalTime().Ticks}else{[DateTimeOffset]::Parse([string]$flow.owned_start_utc,[Globalization.CultureInfo]::InvariantCulture).UtcDateTime.Ticks}
  $image=[IO.Path]::GetFullPath((Join-Path $stage.exe_dir 'Burnout_PC.exe'))
  if($owner.pid -le 0 -or [long]$owner.start_utc_ticks -ne $ticks -or [IO.Path]::GetFullPath([string]$owner.image) -ine $image -or [IO.Path]::GetFullPath([string]$flow.owned_image) -ine $image){throw 'capture owner differs from exact terminal owner'}
  $event=('Local\BurnoutPC_HarnessPhaseDone_{0}_62185_{1}' -f $owner.pid,$ticks)
  if($stop.event -cne $event -or $stop.owner.pid -ne $owner.pid -or [long]$stop.owner.start_utc_ticks -ne $ticks -or [IO.Path]::GetFullPath([string]$stop.owner.image) -ine $image){throw 'phase-stop witness not bound to owner/slot/start'}
  $log=[IO.File]::ReadAllText([string]$ctx.Log);$labels=@{};$seen=@{};$previousPresent=-1
  $allowed=@('ea_movie_2s','ea_movie_5s','criterion_movie_2s','criterion_movie_5s','title_ready','profile_ready','car_select','world_exit','drive_8s','drive_15s','drive_25s','drive_35s')
  for($i=0;$i -lt 10;$i++){
   $c=$captures[$i];$label=[string]$c.label;if($label -notin $allowed -or $labels.ContainsKey($label)){throw 'unknown or duplicate capture label'};$labels[$label]=$true
   if([int]$c.sequence -ne ($i+1) -or $c.owner.pid -ne $owner.pid -or [long]$c.owner.start_utc_ticks -ne $ticks -or [IO.Path]::GetFullPath([string]$c.owner.image) -ine $image){throw 'capture sequence or owner mismatch'}
   $m=[regex]::Match([string]$c.ack,'^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)\r?$')
   if(!$m.Success -or [int]$m.Groups[1].Value -ne $owner.pid -or [int]$m.Groups[2].Value -ne 62185 -or [int]$m.Groups[3].Value -ne ($i+1) -or [int]$m.Groups[4].Value -le $previousPresent){throw 'invalid frame ACK'}
   $previousPresent=[int]$m.Groups[4].Value;$name=$m.Groups[5].Value;if([int]$name.Substring(3,6) -ne $previousPresent){throw 'frame filename/present mismatch'};$file=[IO.Path]::GetFullPath((Join-Path (Join-Path $dir 'frames') $name))
   if([IO.Path]::GetFullPath([string]$c.file) -ine $file -or $seen.ContainsKey($file)){throw 'capture path or uniqueness mismatch'};$seen[$file]=$true
   if(!(Test-Path -LiteralPath $file -PathType Leaf) -or (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$c.sha256){throw 'frame missing or hash mismatch'}
   $bytes=[IO.File]::ReadAllBytes($file);if($bytes.Length -le 54 -or $bytes[0] -ne 66 -or $bytes[1] -ne 77 -or [BitConverter]::ToInt32($bytes,18) -ne 1280 -or [Math]::Abs([BitConverter]::ToInt32($bytes,22)) -ne 720 -or $c.width -ne 1280 -or $c.height -ne 720){throw 'bad capture dimensions or bytes'}
   $cursor=[int]$c.log_cursor_chars;if($cursor -lt 0 -or $cursor -gt $log.Length){throw 'bad raw log cursor'}
   $ackIndex=$log.IndexOf([string]$c.ack,$cursor,[StringComparison]::Ordinal);if($ackIndex -lt 0 -or $log.IndexOf([string]$c.ack,$ackIndex+$c.ack.Length,[StringComparison]::Ordinal) -ge 0){throw 'frame ACK absent or duplicated in owned log'}
   $prefix=$log.Substring(0,$cursor);$pattern=switch -Regex ($label){'^ea_movie_' {'(?im)^\[Movie\] prepared [^\r\n]*EAFRANCHISE'} '^criterion_movie_' {'(?im)^\[Movie\] prepared [^\r\n]*CRITERION'} '^title_ready$' {'(?m)^\[BootLegal\] stage -?\d+ -> 7'} '^profile_ready$' {'\[BootProfile\] stage 3 -> 4'} '^car_select$' {'Entering Car Select'} default {'signalling StreamingFinished'}}
   $markers=@([regex]::Matches($prefix,$pattern));if(!$markers.Count){throw ('phase label lacks prior native marker '+$label)}
   if($label -match '^(ea|criterion)_movie_'){$marker=$markers[-1];$between=$log.Substring($marker.Index,$ackIndex-$marker.Index);if($between -match '\[GuiModule\] video finished -> menu stream cleared, fed 510 to the flow\.'){throw 'movie label ACK after video finished'}}
  }
  foreach($required in @('ea_movie_2s','criterion_movie_2s','title_ready','profile_ready','car_select','world_exit','drive_8s','drive_15s')){if(!$labels.ContainsKey($required)){throw ('missing required capture '+$required)}}
  return @{Pass=$true;Detail=('10 owned hash/ACK/phase-bound captures and exact owned phase-stop; labels='+($labels.Keys -join ','))}
 } catch {return @{Pass=$false;Detail=$_.Exception.Message}}
}
