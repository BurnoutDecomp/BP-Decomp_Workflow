# vw_showtime_bounce_car -- upstream FxCrashVfxShowtimeBounceLive on a seat whose wreck reaches traffic
# (lane SHOWTIME, visual wave VW).
#
# The upstream case drives ShowtimeContacts' seat; on the 15:29 exe that wreck bounced 32 times and not one
# bounce landed on a car (run fxcrashvfx_showtime_bounce\20261008_173713: "0 fired, 32 not on a car"), so its
# two "fired" checks cannot be evaluated there. Same checks, unchanged, on vw_showtime_cash's seat
# (2886,1,-2020 heading 180, traffic within a few seconds of the launch), with bounces pulsed from DRIVING+24.
#   powershell -ExecutionPolicy Bypass -File tools\tests\run_case.ps1 -Case vw_showtime_bounce_car
$case = & (Join-Path $PSScriptRoot '..\..\..\b5-decomp\tests\FxCrashVfxShowtimeBounceLive.ps1')
$case.Name = 'vw_showtime_bounce_car'
$case.Remove('FreshProfile')
$case.ProfileFixture = 'scratch\gameplay_wave\profile_backup\Profile.sav.pose250700'
$case.Run.Teleport = '2886.0,1.0,-2020.0,180'
$case.Run.ThrottleScript = '0:accel,16:none'
$case.Run.Showtime = '20:3'
$case.Run.Boost = '24'
$case.Run.MaxSeconds = 105
$case
