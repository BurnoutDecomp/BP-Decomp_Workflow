# _box_lock.ps1 -- ONE GAME HARNESS AT A TIME ON THIS BOX.
#
# Dot-source this and call Enter-BoxLock BEFORE the script's kill sweep:
#
#     . "$PSScriptRoot\_box_lock.ps1"
#     Enter-BoxLock
#
# ⛔⛔ WHY THIS EXISTS (measured 2026-08-27, not theorised).
# Every harness in this directory begins by killing EVERY Burnout_PC on the box and, in most cases,
# deleting build\game\BrnGame.log. So two harnesses running at once do not merely contend for the
# GPU -- they DESTROY each other's measurements. On 2026-08-27 two parallel decomp waves cost FOUR
# runs between them, and one wave's launch killed a run of the other's mid-measurement.
#
# ⭐ THE REASON THIS IS WORTH A SHARED FILE: the victim gets no error. It sees a game process that
# vanished and a log that stops mid-line -- which reads exactly like an engine crash or a boot
# regression IN THE BUILD UNDER TEST. A harness that can be destroyed by another copy of itself
# reports the destruction as a property of the game. That is the same failure the stale-instance
# block inside flow_run.ps1 already guards against, one level up: there it was leftovers of ITSELF,
# here it is a sibling script.
#
# ⛔ There are NINE scripts in this directory that kill or launch the game. Locking only some of
# them is barely better than locking none -- an unlocked script still stomps a locked one, and the
# locked one's careful refusal to stomp others buys nothing. If you add another harness that
# touches Burnout_PC or BrnGame.log, ADD THE TWO LINES ABOVE TO IT.
#
# The lock is released IMPLICITLY on process exit: Windows abandons a mutex whose owner died and
# the next waiter acquires it (AbandonedMutexException still means WE HOLD IT). So no try/finally
# is needed at any call site, and no crash -- or Ctrl-C -- of a harness can wedge the box
# permanently. The handle is parked in the caller's script scope so the GC cannot collect it
# mid-run, which WOULD release it early.

$script:BrnBoxLock = $null

function Enter-BoxLock {
  param(
    [int]$TimeoutSec = 1800,   # generous: a full flow_run is ~400 s and waves queue behind each other
    [switch]$NoLock,           # ⛔ escape hatch only -- restores the mutually-destructive behaviour
    [string]$Label = ""        # optional caller name, for the acquired/waiting lines
  )
  if ($NoLock) {
    Write-Host "[box] ⛔ -NoLock: NOT serializing. A concurrent harness will kill this run."
    return
  }
  if ($null -ne $script:BrnBoxLock) { return }   # idempotent: dot-sourced twice is not an error

  $tag = if ($Label -ne "") { " ($Label)" } else { "" }
  $m = New-Object System.Threading.Mutex($false, "Local\BurnoutPC_FlowRun")

  # Try once without blocking, so the common case stays silent and a WAIT is announced. A wave that
  # sees nothing for twenty minutes assumes it has hung; tell it what it is actually doing.
  $got = $false
  try { $got = $m.WaitOne([TimeSpan]::Zero) }
  catch [System.Threading.AbandonedMutexException] { $got = $true }

  if (-not $got) {
    Write-Host "[box] waiting for the box$tag -- another harness holds it (up to $TimeoutSec s)."
    Write-Host "[box] this is NOT a hang. Launching now would kill their run and truncate their log."
    try { $got = $m.WaitOne([TimeSpan]::FromSeconds($TimeoutSec)) }
    catch [System.Threading.AbandonedMutexException] { $got = $true }
  }

  if (-not $got) {
    Write-Host "[box] FAIL: the box stayed busy for $TimeoutSec s.$tag"
    Write-Host "[box]       Refusing to run rather than destroy a live measurement."
    Write-Host "[box]       Wait for the other harness, or raise -LockTimeoutSec."
    exit 1
  }

  $script:BrnBoxLock = $m
  Write-Host "[box] box lock acquired$tag"

  # ⛔⛔ RELEASE ANY STUCK INPUT HOLD -- the box is ours, so nothing legitimate is holding one.
  #   (showtime cross-run hazard, 2026-08-29.)
  #   The seven harness input channels are SESSION-GLOBAL, MANUAL-RESET named events in the
  #   `Local\` namespace -- the game opens them by fixed name, so every process in the session
  #   shares one object per channel. Manual-reset means SIGNALLED IS A HOLD: it stays down until
  #   something clears it. flow_run clears them at creation and after its poll loop, but a run
  #   that is Ctrl+C'd, killed, or dies on a terminating error between Set() and that clear leaves
  #   the channel DOWN -- and the next harness to launch the game inherits a button that is being
  #   held by nobody.
  #   ⚠️ WHY THIS IS NOT COSMETIC. Measured by the pause wave: LB+RB held tips the pause screen
  #   into CN_SETTINGS, an empty shell whose OnEnter/Update/OnLeave all fall through to the base
  #   -- a PERMANENT soft-lock that looks exactly like the game silently dying, and it was
  #   reported as a game defect before the mechanism was found. -Showtime is the only switch that
  #   holds the two shoulder channels, so it is the one that can strand them.
  #   ⭐ WHY HERE and not in flow_run: this file is dot-sourced by EVERY harness on the box, and
  #   the other seven neither create nor clear these events -- so a per-harness fix would leave
  #   them all exposed. Clearing at LOCK ACQUISITION is also the one instant it is provably safe:
  #   the lock means no other harness is live, and the caller is about to end every Burnout_PC on
  #   the box anyway. It cannot cancel a legitimate hold, because a legitimate hold belongs to a
  #   run that no longer exists.
  #   [[gates-are-stale-not-dead]] -- state that outlives its owner is the same defect class.
  foreach ($lsChannel in @('Accelerate','Brake','HandBrake','SteerLeft','SteerRight',
                           'ShoulderL','ShoulderR')) {
    try {
      $lEvent = New-Object System.Threading.EventWaitHandle(
                  $false, [System.Threading.EventResetMode]::ManualReset,
                  "Local\BurnoutPC_Input_$lsChannel")
      $lEvent.Reset() | Out-Null
      $lEvent.Close()
    } catch {
      # A channel we cannot open is a channel nothing can be holding. Never fatal.
    }
  }
}
