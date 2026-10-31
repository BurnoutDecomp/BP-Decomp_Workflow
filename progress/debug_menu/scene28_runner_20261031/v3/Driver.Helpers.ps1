function Lines {
 if(!(Test-Path -LiteralPath $GameLog)){if($script:gameBytes -gt 0){throw 'owned game log disappeared; absolute proof indexes are invalid'};return ,$script:gameLines}
 $fs=[IO.File]::Open($GameLog,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));$hash=[Security.Cryptography.SHA256]::Create()
 try{
  if($fs.Length -lt $script:gameBytes){throw 'owned game log truncated; absolute proof indexes are invalid'}
  $buffer=[byte[]]::new([int]$fs.Length);$read=0
  while($read -lt $buffer.Length){$part=$fs.Read($buffer,$read,$buffer.Length-$read);if($part -eq 0){break};$read+=$part}
  if($read -lt $script:gameBytes){throw 'owned game log truncated during read; absolute proof indexes are invalid'}
  # Verify every already-published byte, not just length/file identity: same-file rewrites and
  # equal-or-larger replacements must never retain stale rows or hide an earlier assertion.
  if($script:gameBytes -gt 0){
   $actual=[BitConverter]::ToString($hash.ComputeHash($buffer,0,[int]$script:gameBytes))
   if($actual -cne $script:prefixHash){throw 'owned game log prefix changed; absolute proof indexes are invalid'}
  }
  if($read -gt $script:gameBytes){
   $last=-1;for($i=$read-1;$i -ge $script:gameBytes;$i--){if($buffer[$i] -eq 10){$last=$i;break}}
   if($last -ge $script:gameBytes){
    $text=[Text.UTF8Encoding]::new($false,$false).GetString($buffer,[int]$script:gameBytes,[int]($last-$script:gameBytes))
    if($script:gameBytes -eq 0 -and $text.StartsWith([string][char]0xFEFF,[StringComparison]::Ordinal)){$text=$text.Substring(1)}
    $complete=[regex]::Replace($text,"`r+(?=`n)",'').TrimEnd([char]13)
    foreach($line in $complete.Split([char]10)){$script:gameLines.Add($line)}
    $script:gameBytes=$last+1;$script:prefixHash=[BitConverter]::ToString($hash.ComputeHash($buffer,0,[int]$script:gameBytes))
   }
  }
  return ,$script:gameLines
 }finally{$hash.Dispose();$fs.Dispose()}
}
function ConvertTo-FiniteF32([object]$Value,[string]$Label='f32 value'){
 $text=[Convert]::ToString($Value,[cultureinfo]::InvariantCulture);$parsed=[single]0
 if(![single]::TryParse($text,[Globalization.NumberStyles]::Float,[cultureinfo]::InvariantCulture,[ref]$parsed)){throw ($Label+' is not an invariant f32')}
 if([single]::IsNaN($parsed)-or[single]::IsInfinity($parsed)){throw ($Label+' is non-finite')}
 return $parsed
}
function Get-F32Bits([single]$Value){return [BitConverter]::ToUInt32([BitConverter]::GetBytes($Value),0).ToString('X8')}
function Get-F32Text([object]$Value,[string]$Label='f32 value'){
 $single=ConvertTo-FiniteF32 $Value $Label
 return $single.ToString('R',[cultureinfo]::InvariantCulture)
}
function Get-ExactSceneDefaultProof([object]$Control,[string]$ObservedDisplay,[string[]]$LogSnapshot){
 $expectedText=Get-F32Text $Control.source_default ($Control.alias+' source default')
 $expectedBits=Get-F32Bits (ConvertTo-FiniteF32 $expectedText ($Control.alias+' source default'))
 if($expectedBits -cne [string]$Control.f32_baseline.source_default_bits){throw ('source-default f32 bit pin mismatch '+$Control.alias)}
 $expectedDisplay=(ConvertTo-FiniteF32 $expectedText).ToString('F3',[cultureinfo]::InvariantCulture)
 if($ObservedDisplay -cne $expectedDisplay){throw ('rounded readback does not display the pinned default '+$Control.alias)}
 $canonicalPath=([string]$Control.lookup_path).Replace([char]92,[char]47).Trim('/').ToLowerInvariant()
 $overrideRows=@()
 foreach($line in $LogSnapshot){
  if($line -match '^\[debug-ini\] (?:applied|rejected) (?<path>[^=]+)='){
   $loggedPath=$Matches.path.Replace([char]92,[char]47).Trim('/').ToLowerInvariant()
   if($loggedPath -ceq $canonicalPath){$overrideRows+=@([string]$line)}
  }
 }
 if($overrideRows.Count -gt 0){throw ('matching typed Debug.ini entry prevents source-default baseline '+$Control.alias)}
 return [ordered]@{alias=$Control.alias;kind='published_constructor_source_default';value=$expectedText;bits=$expectedBits;finite=$true;display=$ObservedDisplay;display_digits=3;matching_debug_ini_rows=@();log_snapshot_lines=$LogSnapshot.Count;source_path=$Control.registration.path;source_line=$Control.registration.line;source_blob=$Control.registration.blob_at_3f}
}
function Command-Codes([int]$Cursor){
 $all=Lines;$codes=[Collections.Generic.List[int]]::new()
 for($i=$Cursor;$i -lt $all.Count;$i++){if($all[$i] -match '^\[debug-ui\].*visible=1 .*key=(\d+)$' -and [int]$Matches[1] -ne 0){$codes.Add([int]$Matches[1])}}
 return ,$codes
}
function Own {
 $activeDeadline=if($script:cleanupMode){$script:cleanupDeadline}else{$deadline}
 if([DateTime]::UtcNow -gt $activeDeadline){throw 'bounded Director driver deadline'}
 if(!$owner -or !$owner.Process -or !$owner.Handle -or $owner.Process.Id -ne $owner.Pid -or $owner.Process.HasExited -or $owner.Process.StartTime.ToUniversalTime().Ticks -ne $owner.Ticks){throw 'exact retained Director owner exited or changed'}
 if([DateTime]::UtcNow -ge $script:nextCim){$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$owner.Pid) -ErrorAction Stop;if(!$c.ExecutablePath -or [IO.Path]::GetFullPath($c.ExecutablePath) -ine $owner.Path){throw 'owned image changed'};$script:nextCim=[DateTime]::UtcNow.AddSeconds(2)}
 if(!$script:cleanupMode -and $script:logAccepted){$all=Lines;for($i=$script:assertCursor;$i -lt $all.Count;$i++){if($all[$i] -match '\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]|Alias not found|Variable not found|Component not found|Unknown command'){throw 'raw assert/exception/native command failure'}};$script:assertCursor=$all.Count}
}
function Wait-Line([string]$Pattern,[int]$Cursor,[int]$Seconds=12){
 $until=[DateTime]::UtcNow.AddSeconds($Seconds)
 do{Own;$all=Lines;for($i=$Cursor;$i -lt $all.Count;$i++){if($all[$i] -match $Pattern){return [pscustomobject]@{line=$all[$i];index=$i}}};Start-Sleep -Milliseconds 50}while([DateTime]::UtcNow -lt $until)
 throw ('missing fresh native receipt: '+$Pattern)
}
function Key-Observed([int]$Code,[string]$Pattern,[bool]$Shift=$false){
 Own;$cursor=(Lines).Count
 try{if($Shift){$keys[16].Set()|Out-Null};$keys[$Code].Set()|Out-Null;return Wait-Line $Pattern $cursor 6}finally{$keys[$Code].Reset()|Out-Null;$keys[16].Reset()|Out-Null}
}
function Console([bool]$Visible){if($null -ne $script:consoleVisible -and $script:consoleVisible -eq $Visible){return};$v=if($Visible){1}else{0};$ev=if($Visible){9}else{0};[void](Key-Observed 192 ('^\[debug-ui\] event='+$ev+' visible='+$v+' .* key=0$'));$script:consoleVisible=$Visible}
function Type-Setup {
 $commandCursor=(Lines).Count;$expectedCodes=@(101,120,101,99,32,98,49,46,99,102,103)
 foreach($ch in 'exec b1.cfg'.ToCharArray()){
  $ascii=[int]$ch;$vk=if($ascii -ge 97 -and $ascii -le 122){$ascii-32}elseif($ascii -eq 46){190}else{$ascii}
  [void](Key-Observed $vk ('^\[debug-ui\] event=0 visible=1 .* key='+$ascii+'$'))
 }
 $actualCodes=Command-Codes $commandCursor
 if(($actualCodes -join ',') -cne ($expectedCodes -join ',')){throw 'exact pre-Enter command sequence differs; no Enter sent'}
 [void](Key-Observed 13 '^\[debug-ui\] event=0 visible=1 .* key=10$')
 $actualCodes=Command-Codes $commandCursor
 if(($actualCodes -join ',') -cne ((@($expectedCodes)+@(10)) -join ',')){throw 'exact command-plus-Enter sequence differs'}
}
function Capture-PhaseRaw([object]$Phase){
 $maxFrames=if($script:maxRawFrames){[int]$script:maxRawFrames}else{90}
 if($frameRows.Count -ge $maxFrames){throw ('raw frame cap exceeded before terminal capture: '+$frameRows.Count+' >= '+$maxFrames)}
 Own;$cursor=(Lines).Count;$frameEvent.Reset()|Out-Null;$frameEvent.Set()|Out-Null
 $ack=Wait-Line '^\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)$' $cursor 15
 $m=[regex]::Match($ack.line,'pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)')
 if([int]$m.Groups[1].Value -ne $owner.Pid -or [int]$m.Groups[2].Value -ne $Slot -or [int]$m.Groups[3].Value -ne ($script:sequence+1)){throw 'frame ACK owner/slot/sequence mismatch'}
 $name=$m.Groups[5].Value;$path=Join-Path $RunDir ('frames/'+$name);$until=[DateTime]::UtcNow.AddSeconds(5)
 while(!(Test-Path -LiteralPath $path)){Own;if([DateTime]::UtcNow -gt $until){throw 'ACK BMP missing'};Start-Sleep -Milliseconds 50}
 $bytes=[IO.File]::ReadAllBytes($path);$width=[BitConverter]::ToInt32($bytes,18);$height=[Math]::Abs([BitConverter]::ToInt32($bytes,22));if($bytes.Length -le 54 -or $bytes[0] -ne 66 -or $bytes[1] -ne 77 -or $width -ne 1280 -or $height -ne 720 -or $bytes.Length -gt 3686454){throw 'invalid 1280x720 BMP or unexpected capture budget'}
 if($frameEvent.WaitOne(0)){throw 'game did not consume frame event'}
 $present=[int]$m.Groups[4].Value;$csvPath=Join-Path $RunDir 'frames/frames.csv';$csvRows=@();$csvUntil=[DateTime]::UtcNow.AddSeconds(5)
 do{
  Own;$csvStream=$null;$csvReader=$null
  try{
   $csvStream=[IO.File]::Open($csvPath,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete));$csvReader=[IO.StreamReader]::new($csvStream);$csvText=$csvReader.ReadToEnd();$csvLines=$csvText.Split([char]10)
   $csvRows=@();for($j=0;$j -lt $csvLines.Length-1;$j++){if($csvLines[$j] -match ('^'+$present+',')){$csvRows+=([string]$csvLines[$j]).TrimEnd([char]13)}}
  }catch [IO.IOException]{}finally{if($csvReader){$csvReader.Dispose()}elseif($csvStream){$csvStream.Dispose()}}
  if($csvRows.Count -gt 1){throw 'duplicate CSV present row'}
  if($csvRows.Count -eq 1){break};Start-Sleep -Milliseconds 50
 }while([DateTime]::UtcNow -lt $csvUntil)
 if($csvRows.Count -ne 1){throw 'frame CSV did not finish its exact ACK present row inside the bound'}
 $script:sequence++;$row=[ordered]@{phase=$Phase.name;path=$path;name=$name;bytes=$bytes.Length;max_bytes=3686454;width=$width;height=$height;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();pid=$owner.Pid;slot=$Slot;sequence=$script:sequence;present=$present;ack=$ack.line;ack_index=$ack.index;request_cursor=$cursor;csv_path=$csvPath;csv_row=[string]$csvRows[0]};$frameRows.Add($row)
}
function Read-ExactClip([string]$Alias){
 Own
 if((Get-FileHash -LiteralPath $owner.Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedSha256){throw 'owned process image file hash changed'}
 if((Get-FileHash -LiteralPath (Join-Path $stage.exe_dir 'Burnout_PC.map') -Algorithm SHA256).Hash.ToLowerInvariant() -cne '8604a5b8c23a031dcd773e1fbe2570402df385b869354215db243aeb5cbf646f'){throw 'Source41 linker map hash changed'}
 if($null -eq ('DirectorExactClipReader' -as [type])){
  Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class DirectorExactClipReader {
 [DllImport("kernel32.dll", SetLastError=true)]
 private static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] buffer, UIntPtr size, out UIntPtr read);
 public static byte[] Read(IntPtr process, IntPtr address) {
  byte[] b = new byte[4]; UIntPtr n;
  if (!ReadProcessMemory(process,address,b,(UIntPtr)4,out n) || n.ToUInt64()!=4) throw new Win32Exception(Marshal.GetLastWin32Error());
  return b;
 }
}
"@
 }
 $rvas=@{E43=0xAB7E18;E44=0xAB7E1C;E45=0xAB7E20};if(!$rvas.ContainsKey($Alias)){throw 'Unknown clip address'}
 $moduleBase=$owner.Process.MainModule.BaseAddress.ToInt64();$address=[IntPtr]::new($moduleBase+[long]$rvas[$Alias])
 $bytes=[DirectorExactClipReader]::Read($owner.Handle,$address);$value=[BitConverter]::ToSingle($bytes,0)
 $finite= !([single]::IsNaN($value) -or [single]::IsInfinity($value))
 return @{alias=$Alias;address=('0x{0:X}' -f $address.ToInt64());rva=('0x{0:X}' -f $rvas[$Alias]);bits=[BitConverter]::ToUInt32($bytes,0).ToString('X8');bytes_le=[BitConverter]::ToString($bytes).Replace('-','');value=$value.ToString('R',[cultureinfo]::InvariantCulture);finite=$finite}
}
function Read-Values([int]$Cursor,[object[]]$Selected=$controls){
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
    $value=$all[$found+1].Trim()
    if($control.type -eq 'f32'){
     [void](ConvertTo-FiniteF32 $value ($control.alias+' native readback'))
   }elseif($value -cnotin @('TRUE','FALSE')){throw 'Native bool type mismatch'}
   $values[$control.alias]=$value;$proof+=@{alias=$control.alias;path=$control.lookup_path;value=$value;ack_before=$found;value_line=$found+1;ack_after=$found+2};$at=$found+3
  }
  if($complete){return @{values=$values;proofs=$proof;snapshot_bytes=$script:gameBytes;snapshot_hash=$script:prefixHash}}
  Start-Sleep -Milliseconds 30
 }while([DateTime]::UtcNow -lt $until)
 throw 'Incomplete fresh native alias triplets inside8seconds'
}
function Queries([object[]]$Selected=$controls){$commands=@();foreach($control in $Selected){$commands+=('alias '+$control.alias);$commands+=$control.alias;$commands+=('alias '+$control.alias)};return $commands}
function Execute([string]$Name,[string[]]$Commands,[hashtable]$Expected,[bool]$Capture=$true,[object[]]$Selected=$controls){
 Own
 $file=Join-Path $stage.cwd 'q62190.cfg'
 $emitted=$Commands+@(Queries $Selected)
 $temp=Join-Path $stage.cwd ('q62190.'+[guid]::NewGuid().ToString('N')+'.tmp')
 [IO.File]::WriteAllLines($temp,$emitted,[Text.Encoding]::ASCII)
 if((Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant() -cne $script:phaseHash){throw 'F11 owned phase file changed'}
 [IO.File]::Move($temp,$file,$true);$script:phaseHash=(Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant()
 $retained=Join-Path $RunDir ('phase_'+$Name+'.cfg')
 if(Test-Path $retained){throw 'Refusing phase command receipt overwrite'}
 [IO.File]::WriteAllBytes($retained,[IO.File]::ReadAllBytes($file))
 $scriptHash=(Get-FileHash -LiteralPath $retained -Algorithm SHA256).Hash.ToLowerInvariant()
 $cursor=(Lines).Count
 try{$keys[122].Set()|Out-Null;$read=Read-Values $cursor $Selected}finally{$keys[122].Reset()|Out-Null}
 foreach($key in $Expected.Keys){
  if(!$read.values.ContainsKey($key)){throw 'Missing expected value'}
  $want=[string]$Expected[$key];$actual=[string]$read.values[$key]
  if($want -in @('TRUE','FALSE')){if($actual -cne $want){throw "Value mismatch $Name $key $actual != $want"}}
  else{
   $wantSingle=ConvertTo-FiniteF32 $want ($Name+' expected '+$key);$actualSingle=ConvertTo-FiniteF32 $actual ($Name+' actual '+$key)
   $wantDisplay=$wantSingle.ToString('F3',[cultureinfo]::InvariantCulture)
   if($actualSingle.ToString('F3',[cultureinfo]::InvariantCulture) -cne $wantDisplay){throw "Value mismatch $Name $key $actual != $wantDisplay"}
  }
 }
 $phaseRows.Add(@{phase=$Name;cursor=$cursor;commands=$Commands;command_file=$retained;command_sha256=$scriptHash;expected=$Expected;proofs=$read.proofs;snapshot_bytes=$read.snapshot_bytes;snapshot_hash=$read.snapshot_hash})
 if($Capture){Start-Sleep -Milliseconds 400;Capture-PhaseRaw @{name=$Name}}
 return $read.values
}
function Commands-For([hashtable]$Values){
 $known=@{};foreach($control in $controls){$known[[string]$control.alias]=$true}
 foreach($alias in $Values.Keys){if($alias -match '=' -or !$known.ContainsKey([string]$alias)){throw ('emergency restore alias is not declared '+$alias)}}
 $lines=@();foreach($control in $controls){if($Values.ContainsKey($control.alias)){$lines+=('set '+$control.alias+' '+$Values[$control.alias])}}
 return $lines
}
