# reflect_envmap_faces -- b5-decomp#5 "graphics: reflections are weird ... they were working
# before. They don't reflect the environment properly."
#
# WHAT IT MEASURES. Not the screenshot -- the CUBE. Car paint samples a 128x128 A8R8G8B8 cube
# render target at sampler 13; a reflection that "looks wrong" is equally explained by six good
# faces sampled wrongly and by some faces good and some frozen / black / duplicated. So the
# engine reads the six RESOLVED faces back off the GPU (Target::PCReadBackFaceStats, armed by
# BRN_ENVMAP_STATS=1) and prints, every 30 env-map passes for the first 20 samples:
#   [envmap] update <n> face <i> mean=(r,g,b) std=<s> lum=<l> rendered=<0|1> meshes=<m> read=<0|1>
# Face order is the console's KAV_ENV_MAP_LOOK_DIRECTIONS = +X,-X,+Y,-Y,+Z,-Z (index-for-index
# D3D9's D3DCUBEMAP_FACE_POSITIVE_X..NEGATIVE_Z), so face 2 is UP (sky), face 3 is DOWN (ground)
# and 0/1/4/5 are the sides.
#
# Run it:
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case reflect_envmap_faces -ExpectFail -Label pre-fix
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case reflect_envmap_faces -Label post-fix

# --- the [envmap] witness parser, shared by the Script checks below -------------------------
# GLOBAL on purpose: run_case.ps1 loads a case with `& $casePath`, so anything defined in this
# file's own scope is gone by the time a Script check is invoked. A `global:` function survives
# for the runner process, which is exactly the lifetime the checks need.
function global:Parse-EnvMapSamples($ctx) {
  $out = @{}
  $re = '^\[envmap\] update (?<n>\d+) face (?<f>\d+) mean=\((?<r>[-\d.eE+]+),(?<g>[-\d.eE+]+),(?<b>[-\d.eE+]+)\) std=(?<s>[-\d.eE+]+) lum=(?<l>[-\d.eE+]+) rendered=(?<rd>\d+) meshes=(?<m>\d+) read=(?<ok>\d+)'
  foreach ($line in $ctx.LogLines) {
    if ($line -match $re) {
      $n = [int]$Matches.n
      $f = [int]$Matches.f
      if (-not $out.ContainsKey($n)) { $out[$n] = @{} }
      $out[$n][$f] = @{
        r = [double]$Matches.r; g = [double]$Matches.g; b = [double]$Matches.b
        std = [double]$Matches.s; lum = [double]$Matches.l
        rendered = [int]$Matches.rd; meshes = [int]$Matches.m; read = [int]$Matches.ok
      }
    }
  }
  return $out
}

function global:Get-LastEnvMapSample($samples) {
  $keys = @($samples.Keys | Where-Object { $samples[$_].Count -eq 6 } | Sort-Object)
  if ($keys.Count -eq 0) { return $null }
  return $samples[$keys[-1]]
}

#
# ⭐⭐ SHORTENED 2026-09-06 (lane harness2). WHAT CHANGED AND WHAT DID NOT.
#   The Run block below now carries `SkipIntro` and `AcceptGap`, and a smaller `MaxSeconds`.
#   Nothing else about the scenario moved and NO CHECK was touched.
#     SkipIntro  passes the CONSOLE's own "-skipvideos" command-line latch (BrnMain.cpp:434 ->
#                BootVideos::Update's soft-reboot exit) so the EA-Franchise and Criterion VP6
#                logos are not played. It is not a harness bypass and it is not new game code.
#     AcceptGap  is HARNESS latency, not a game gate: the Accept pump used to press every 3.0 s
#                at car select, and the junkyard leg of a returning boot was measurably two
#                consecutive pump periods long (carsel 16.5s -> livery 19.9s -> accept 23.0s).
#   MEASURED, same build, same scenario: boot-to-DRIVING 23.0 s -> 16.2 s.
#   MaxSeconds is cut by that saving plus the slack this case's own schedule shows it never used.
#
@{
  Name    = 'reflect_envmap_faces'
  Area    = 'graphics'
  Bug     = 'BurnoutDecomp/b5-decomp#5 -- reflections are weird; they do not reflect the environment properly (regression since 2026-08-17)'
  Frames  = $false
  Run     = @{
    Drive       = $true
    MotionProbe = $true
    MaxSeconds  = 55
    SkipIntro  = $true      # the console -skipvideos latch (see the banner)
    AcceptGap  = 1.0        # harness pump latency, not a game gate
    Teleport    = '3040.7,-5.8,-1937.9,180'   # the road outside the junkyard exit
  }
  DiagEnv = 'BRN_ENVMAP_STATS=1'
  Checks  = @(
    @{ Kind = 'NewAsserts'; Name = 'no NEW assert families' }
    @{ Kind = 'LogCount';   Name = 'no exceptions'; Pattern = '\[EXCEPTION\]'; Max = 0 }
    @{ Kind = 'Mark';       Name = 'reached DRIVING'; Phase = 'DRIVING' }

    @{ Kind = 'Script'; Name = 'the env-map witness produced samples'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $full = @($s.Keys | Where-Object { $s[$_].Count -eq 6 })
        $d = ("{0} [envmap] samples, {1} with all six faces" -f $s.Count, $full.Count)
        return @{ Pass = ($full.Count -ge 3); Detail = $d }
      } }

    @{ Kind = 'Script'; Name = 'all six faces read back'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $last = Get-LastEnvMapSample $s
        if (-not $last) { return @{ Pass = $false; Detail = 'no complete [envmap] sample' } }
        $bad = @(0..5 | Where-Object { $last[$_].read -ne 1 })
        return @{ Pass = ($bad.Count -eq 0); Detail = ("faces whose GetRenderTargetData failed: [{0}]" -f ($bad -join ',')) }
      } }

    @{ Kind = 'Script'; Name = 'no face is degenerate (black / white / flat)'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $last = Get-LastEnvMapSample $s
        if (-not $last) { return @{ Pass = $false; Detail = 'no complete [envmap] sample' } }
        $bad = @()
        foreach ($i in 0..5) {
          $f = $last[$i]
          if ($f.lum -lt 2.0)   { $bad += ("face $i BLACK lum={0:N1}" -f $f.lum) }
          if ($f.lum -gt 250.0) { $bad += ("face $i WHITE lum={0:N1}" -f $f.lum) }
          if ($f.std -lt 1.0)   { $bad += ("face $i FLAT std={0:N2}" -f $f.std) }
        }
        $d = ((0..5 | ForEach-Object { "f{0} lum={1:N1} std={2:N1}" -f $_, $last[$_].lum, $last[$_].std }) -join ' | ')
        if ($bad.Count -gt 0) { return @{ Pass = $false; Detail = (($bad -join '; ') + '  ||  ' + $d) } }
        return @{ Pass = $true; Detail = $d }
      } }

    # A real duplicate is a face that carries ANOTHER face's pixels -- it matches in EVERY
    # sample, not in one. Two genuinely different views can coincide in the mean for a frame:
    # measured on the 20260906_100937 run, |mean(f0)-mean(f4)| walked 12.77 -> 2.90 -> 0.54 over
    # three consecutive samples. So the test is "within 0.05 in every sample", not "close once".
    @{ Kind = 'Script'; Name = 'the six faces are distinct (no duplicated face)'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $keys = @($s.Keys | Where-Object { $s[$_].Count -eq 6 } | Sort-Object)
        if ($keys.Count -lt 3) { return @{ Pass = $false; Detail = ("only {0} complete samples" -f $keys.Count) } }
        $dupes = @()
        $worst = 1e9
        foreach ($i in 0..4) {
          foreach ($j in ($i + 1)..5) {
            $maxD = 0.0
            foreach ($k in $keys) {
              $a = $s[$k][$i]; $b = $s[$k][$j]
              $d = [Math]::Abs($a.r - $b.r) + [Math]::Abs($a.g - $b.g) + [Math]::Abs($a.b - $b.b)
              if ($d -gt $maxD) { $maxD = $d }
            }
            if ($maxD -lt $worst) { $worst = $maxD }
            if ($maxD -lt 0.05) { $dupes += ("{0}=={1} (max dmean over {2} samples = {3:N3})" -f $i, $j, $keys.Count, $maxD) }
          }
        }
        if ($dupes.Count -gt 0) { return @{ Pass = $false; Detail = ('duplicated faces: ' + ($dupes -join ', ')) } }
        return @{ Pass = $true; Detail = ("closest pair separates by {0:N2} at its widest sample" -f $worst) }
      } }

    @{ Kind = 'Script'; Name = 'face 2 (+Y) is sky and face 3 (-Y) is ground'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $last = Get-LastEnvMapSample $s
        if (-not $last) { return @{ Pass = $false; Detail = 'no complete [envmap] sample' } }
        $up = $last[2]; $dn = $last[3]
        $ok = ($up.lum -gt $dn.lum) -and ($up.b -gt $up.r)
        $d = ("+Y lum={0:N1} rgb=({1:N1},{2:N1},{3:N1}) | -Y lum={4:N1} rgb=({5:N1},{6:N1},{7:N1})" -f $up.lum, $up.r, $up.g, $up.b, $dn.lum, $dn.r, $dn.g, $dn.b)
        return @{ Pass = $ok; Detail = $d }
      } }

    @{ Kind = 'Script'; Name = 'every face is refreshed at least once'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        if ($s.Count -eq 0) { return @{ Pass = $false; Detail = 'no [envmap] samples' } }
        $seen = @{}
        foreach ($k in $s.Keys) { foreach ($i in $s[$k].Keys) { if ($s[$k][$i].rendered -eq 1) { $seen[$i] = $true } } }
        $missing = @(0..5 | Where-Object { -not $seen.ContainsKey($_) })
        return @{ Pass = ($missing.Count -eq 0); Detail = ("faces never scheduled: [{0}]" -f ($missing -join ',')) }
      } }

    @{ Kind = 'Script'; Name = 'no face is frozen while the car drives'; Script = {
        param($ctx)
        $s = Parse-EnvMapSamples $ctx
        $keys = @($s.Keys | Where-Object { $s[$_].Count -eq 6 } | Sort-Object)
        if ($keys.Count -lt 3) { return @{ Pass = $false; Detail = ("only {0} complete samples" -f $keys.Count) } }
        $a = $s[$keys[0]]; $b = $s[$keys[-1]]
        $frozen = @(); $moves = @()
        foreach ($i in 0..5) {
          $d = [Math]::Abs($a[$i].r - $b[$i].r) + [Math]::Abs($a[$i].g - $b[$i].g) + [Math]::Abs($a[$i].b - $b[$i].b)
          $moves += ("f{0}={1:N2}" -f $i, $d)
          if ($d -lt 1.0) { $frozen += $i }
        }
        $d = ("mean drift sample {0}->{1}: {2}" -f $keys[0], $keys[-1], ($moves -join ' '))
        if ($frozen.Count -gt 0) { return @{ Pass = $false; Detail = (("FROZEN faces [{0}]  ||  " -f ($frozen -join ',')) + $d) } }
        return @{ Pass = $true; Detail = $d }
      } }
  )
}
