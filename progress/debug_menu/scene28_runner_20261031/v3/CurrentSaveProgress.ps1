function Test-BrnPrivateFixtureProgress([string[]]$Lines,$Expected,[string]$PrivateSha256) {
    $problem=[Collections.Generic.List[string]]::new()
    $ref=$Expected.runtime_reference
    if($PrivateSha256 -cne [string]$Expected.source_sha256){$problem.Add('private current-save hash differs')}
    $loads=@();$profiles=@();$deserialised=@()
    for($i=0;$i -lt $Lines.Count;$i++){
        if($Lines[$i] -ceq '[profile-save] deserialised: isNewProfile=0 -> playIntroVideo=0'){$deserialised+=@{line=$Lines[$i];line_index=$i}}
        if($Lines[$i] -match '^\[GameStateModule::OnProfileLoaded\].*profileCar=(?<car>\S+) rank=(?<rank>-?\d+) maxCars=(?<max>\d+) '){$loads+=@{line=$Lines[$i];line_index=$i;rank=[int]$Matches.rank;max_cars=[int]$Matches.max;profile_car=[string]$Matches.car}}
        if($Lines[$i] -match '^\[one-profile\].* same=(?<same>\d+) \| isNewProfile gs=(?<gs>\d+) pm=(?<pm>\d+) \| medalsFromTheStart gs=(?<medals>\d+) pm=(?<pmmedals>\d+) \| eventCount gs=(?<events>\d+) pm=(?<pmevents>\d+) \| spawnCarId gs=(?<car>[0-9A-F]+) pm=(?<pmcar>[0-9A-F]+).*maxCars gs=(?<max>\d+)'){$profiles+=@{line=$Lines[$i];line_index=$i;same=[int]$Matches.same;new_gs=[int]$Matches.gs;new_pm=[int]$Matches.pm;car=[string]$Matches.car;pmcar=[string]$Matches.pmcar;medals=[int]$Matches.medals;pmmedals=[int]$Matches.pmmedals;events=[int]$Matches.events;pmevents=[int]$Matches.pmevents;max_cars=[int]$Matches.max}}
    }
    if(-not ($Lines -contains 'Signin state changed: signed-in')){$problem.Add('no actual signed-in witness')}
    if($deserialised.Count -eq 0){$problem.Add('no actual non-new profile deserialisation witness')}
    if($loads.Count -eq 0){$problem.Add('no actual native OnProfileLoaded witness')}
    else{
        $p=$loads[-1]
        if($p.rank -ne [int]$ref.rank -or $p.max_cars -ne [int]$ref.max_cars_catalog){$problem.Add('loaded rank/catalog differs from normal reference')}
    }
    if($profiles.Count -eq 0){$problem.Add('no actual native one-profile progress witness')}
    else{
        $p=$profiles[-1]
        if($p.same -ne 1 -or $p.new_gs -ne 0 -or $p.new_pm -ne 0){$problem.Add('actual gameplay profile is new or not shared consistently')}
        if($p.car -cne [string]$ref.spawn_car_id -or $p.pmcar -cne [string]$ref.spawn_car_id){$problem.Add('actual loaded spawn-car identity differs from copied progress')}
        if($p.medals -ne [int]$ref.medals_from_start -or $p.pmmedals -ne [int]$ref.medals_from_start -or $p.events -ne [int]$ref.event_count -or $p.pmevents -ne [int]$ref.event_count -or $p.max_cars -ne [int]$ref.max_cars_catalog){$problem.Add('actual medals/events/catalog differ from normal runtime reference')}
    }
    return [pscustomobject]@{schema=3;pass=($problem.Count -eq 0);private_fixture_sha256=$PrivateSha256;expected_fixture_sha256=[string]$Expected.source_sha256;
        expected_native_reference=$ref;raw_container_representation=$Expected.decoded_container_progress;numeric_representation_equivalence_claimed=$false;
        fixture_only=$true;live_profile_read_or_written=$false;live_game_log_hash_required=$false;
        deserialised_rows=$deserialised;profile_loaded_rows=$loads;one_profile_rows=$profiles;problems=@($problem.ToArray());native_setters_before_gate=0;normal_written=$false}
}
