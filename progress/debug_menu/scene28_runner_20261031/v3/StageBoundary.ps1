# Read-only physical checks run before the case wrapper can copy/move a profile.
function Assert-BrnSceneStageBoundary($Stage,[string]$ApprovedRoot,[string]$Fixture,[string]$FixtureSha256) {
    $root=[IO.Path]::GetFullPath($ApprovedRoot).TrimEnd('\')
    $exe=[IO.Path]::GetFullPath([string]$Stage.exe_dir)
    $data=[IO.Path]::GetFullPath([string]$Stage.cwd)
    if($exe -ine (Join-Path $root 'slot') -or $data -ine (Join-Path $root 'data')){throw 'Stage is outside the approved private root'}
    [void](Assert-BrnNoReparsePath $root 'approved stage root' -RequireLeaf)
    [void](Assert-BrnNoReparsePath $exe 'private exe directory' -RequireLeaf)
    [void](Assert-BrnNoReparsePath $data 'private data directory' -RequireLeaf)
    $profile=[IO.Path]::GetFullPath([string]$Stage.profile)
    $wanted=[IO.Path]::GetFullPath((Join-Path $data 'Memcard_62190\Profile.sav'))
    $fixtureFull=[IO.Path]::GetFullPath($Fixture)
    if($profile -ine $wanted -or $profile -ieq $fixtureFull){throw 'Profile is not the approved private slot file'}
    $identity=Assert-BrnPrivateProfile $profile 'pre-invocation private profile'
    $source=Assert-BrnPrivateProfile $fixtureFull 'independent fixture snapshot'
    if($source.status -cne 'regular_single_link_private_file' -or $source.sha256 -cne $FixtureSha256){throw 'Fixture snapshot identity mismatch'}
    if($identity.status -cne 'absent_before_fixture_copy' -and $identity.sha256 -cne $FixtureSha256){throw 'Existing private profile differs from the fixture'}
    return @{pass=$true;approved_root=$root;profile_identity=$identity;fixture_identity=$source;profile_mutations=0}
}
