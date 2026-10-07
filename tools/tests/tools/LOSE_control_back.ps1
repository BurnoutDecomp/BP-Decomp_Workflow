# LOSE_control_back.ps1 -- did the player get the car back after an event ended? (GW4 lane LOSE)
#
# Reads the game log lines of a run whose throttle script RELEASES the throttle after the event
# should be over, and judges the [motion] probe (BRN_MOTION_PROBE, -MotionProbe) samples:
#   * the event must have been torn down (`[evt-finish] ExitCurrentMode: TEARING DOWN`);
#   * after the teardown the car must come to rest with no gas: the last -Tail samples all read
#     gas 0 and the last one is below -MaxMph. While the AI owns the player car (the issue #32
#     symptom: action 7 selector 2 never undone) the AI keeps the car at speed. ([motion] gas is the
#     player's own pedal, so it reads 0 after the release either way; the speed is the oracle.)
#   * -CoastWindow N: also accept a car still rolling at the end of the run if its speed fell to
#     half of its peak over the last N samples.
# The verdict is independent of the GUI/mode witnesses: it only looks at the car.
#
# Usage (from a case's Script check):
#   & tools\tests\tools\LOSE_control_back.ps1 -Lines $ctx.LogLines [-Tail 4] [-MaxMph 4]
# Standalone on a run dir:
#   powershell -File tools\tests\tools\LOSE_control_back.ps1 -Log <run>\flow\BrnGame.log
param(
  [string[]]$Lines = $null,
  [string]$Log = '',
  [int]$Tail = 4,
  [double]$MaxMph = 4.0,
  [int]$CoastWindow = 0,
  [string]$TeardownPattern = '\[evt-finish\] ExitCurrentMode: TEARING DOWN'
)

if ($null -eq $Lines -or $Lines.Count -eq 0) {
  if (-not $Log -or -not (Test-Path $Log)) { return @{ Pass = $false; Detail = 'no log lines and no -Log file' } }
  $Lines = Get-Content $Log
}

$inv = [System.Globalization.CultureInfo]::InvariantCulture
$liTeardown = -1
for ($i = 0; $i -lt $Lines.Count; $i++) {
  if ($Lines[$i] -match $TeardownPattern) { $liTeardown = $i; break }
}

$laAll = @()
for ($i = 0; $i -lt $Lines.Count; $i++) {
  if ($Lines[$i] -match '^\[motion\] n (?<n>\d+) .* mph (?<mph>-?[\d.eE+-]+) .* gas (?<gas>-?[\d.eE+-]+)') {
    $laAll += [pscustomobject]@{
      Line = $i; N = [int]$Matches['n']
      Mph = [double]::Parse($Matches['mph'], $inv); Gas = [double]::Parse($Matches['gas'], $inv)
    }
  }
}
if ($laAll.Count -eq 0) { return @{ Pass = $false; Detail = 'no [motion] samples (was -MotionProbe set?)' } }
$lLast = $laAll[-1]

if ($liTeardown -lt 0) {
  return @{ Pass = $false; Detail = ("event NEVER torn down; final [motion] n {0} mph {1:f1} gas {2:f2} ({3} samples)" -f $lLast.N, $lLast.Mph, $lLast.Gas, $laAll.Count) }
}

$laAfter = @($laAll | Where-Object { $_.Line -gt $liTeardown })
if ($laAfter.Count -lt $Tail) {
  return @{ Pass = $false; Detail = ("only {0} [motion] sample(s) after the teardown, need {1}" -f $laAfter.Count, $Tail) }
}
$laTail = @($laAfter | Select-Object -Last $Tail)
$liGas = @($laTail | Where-Object { $_.Gas -gt 0.001 }).Count
$lfMaxAfter = ($laAfter | Measure-Object -Property Mph -Maximum).Maximum
$lbPass = ($liGas -eq 0) -and ($lLast.Mph -le $MaxMph)
$lsCoast = ''
if (-not $lbPass -and $CoastWindow -gt 0 -and $liGas -eq 0 -and $laAfter.Count -ge $CoastWindow) {
  # -CoastWindow: the run ended while the released car was still rolling. Accept it when, over the
  # last N samples, the speed fell to at most half of its peak in that window -- the AI holds its
  # speed (and boosts) while it owns the car, a coasting car does not.
  $laWin = @($laAfter | Select-Object -Last $CoastWindow)
  $lfWinMax = ($laWin | Measure-Object -Property Mph -Maximum).Maximum
  $lbPass = ($lfWinMax -gt 0) -and ($lLast.Mph -le 0.5 * $lfWinMax)
  $lsCoast = ("; coasting: last {0} samples peak {1:f1} -> {2:f1} mph" -f $CoastWindow, $lfWinMax, $lLast.Mph)
}
return @{
  Pass   = $lbPass
  Detail = ("{0} samples after teardown (max {1:f1} mph); last {2}: gas>0 in {3}, final n {4} mph {5:f2} gas {6:f2}, want gas 0 and <= {7} mph{8}" -f
            $laAfter.Count, $lfMaxAfter, $Tail, $liGas, $lLast.N, $lLast.Mph, $lLast.Gas, $MaxMph, $lsCoast)
}
