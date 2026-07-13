# transcode_x360_video.ps1 -- convert an original Burnout X360 VIDEOS\*.vp6 into the
# PC build's playable H.264/MP4 form (build\game\VIDEOS\*.VP6).
#
# The X360 "*.vp6" files are MP4 containers holding an On2 VP6 video stream that is
# stored as THREE vertically-stacked 1280x240 strips per displayed 1280x720 frame
# (so ffprobe reports 1280x240 and 3x the frame count / duration). The PC movie player
# decodes H.264 (the boot logos criterion/eafranchise were already transcoded to H.264
# 1280x720 and play fine), so the recipe is:
#   * tile=1x3        -- recombine each 3 consecutive 240-high strips into one 720 frame
#   * setpts=N/30/TB  -- retime the recombined frames to 30 fps (fixes the 3x-slow bug a
#                        naive transcode produces: the VP6 stream decodes at the wrong rate)
#   * -r 30, libx264, yuv420p, -an (audio rides the sidecar SOUND\STREAMS\<name>.SNS)
#   * -f mp4 (the .VP6 extension confuses ffmpeg's muxer auto-detect)
#
# Verified: the intro (source 401 MB VP6, 106.7 s once recombined) transcodes to a
# 1280x720 30fps H.264 that plays in-game; a decoded frame is the correct Paradise City
# skyline montage (not sliced/squished). The build had shipped a WRONG 5-second 1080p
# placeholder as INTRO.VP6 -- this recipe replaces it with the real intro.
#
# Usage:
#   powershell -File tools\assets\videos\transcode_x360_video.ps1 `
#       -Src "D:\...\Burnout_tcartwright\VIDEOS\intro.vp6" `
#       -Dst "D:\Reverse\BP-Decomp_Workflow\build\game\VIDEOS\INTRO.VP6"
param(
    [Parameter(Mandatory=$true)][string]$Src,
    [Parameter(Mandatory=$true)][string]$Dst,
    [string]$FFmpeg = ""
)
if (-not $FFmpeg) {
    $cand = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cand) { $FFmpeg = $cand.FullName } else { $FFmpeg = "ffmpeg" }
}
if (-not (Test-Path $Src)) { throw "source not found: $Src" }
Write-Host "transcoding $Src -> $Dst (VP6 3-strip -> H.264 720p30) ..."
& $FFmpeg -y -hide_banner -loglevel error -i $Src -vf "tile=1x3,setpts=N/30/TB" -r 30 `
    -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -an -f mp4 $Dst
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: $([math]::Round((Get-Item $Dst).Length/1MB,1)) MB"
} else {
    throw "ffmpeg failed with exit $LASTEXITCODE"
}
