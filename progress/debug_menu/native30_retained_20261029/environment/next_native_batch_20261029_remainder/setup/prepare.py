"""Prepare one bounded, private Environment21 run; never starts a game."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess

R=Path(__file__).resolve().parent
W=R.parents[2]
OLD=W/'scratch/DEBUG_MENU_1011/swarm_source32_delivery_20261029/native_62171'
SOURCE='abbc9047d850a4665d959993012261c55205e5e5'
EXE='474ba5bb1a72efe0f06ccf71aae98b1b332ca7399715af83da2fa4c4d2666a44'
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,indent=2),encoding='utf-8')

def main():
    assert W==Path('D:/Reverse/BP-Decomp_Workflow')
    old=load(OLD/'STAGING.json')
    assert old['source']==SOURCE and old['exe_sha256']==EXE
    entries=load(W/'progress/debug_menu/entries.json')['entries']
    verdicts=load(W/'progress/debug_menu/verdicts.json')
    numbers=list(range(51,60))+list(range(66,69))+list(range(72,84))
    controls=[]
    source_path='src/GameSource/World/DebugComponents/BrnSkyDebugComponent.cpp'
    source=subprocess.check_output(['git','-C',str(W/'b5-decomp'),'show',SOURCE+':'+source_path]).decode()
    for number in numbers:
        site=f'BrnWorld::EnvironmentSettings::DebugComponent::OnActivate#{number:04}'
        row=next(e for e in entries if e['id']==site)
        assert site not in verdicts,site
        pattern=r'RegisterFloat\(([^;]*"'+re.escape(row['caption'])+r'"[^;]*)\);'
        match=re.search(pattern,source)
        assert match,site
        group=row['path']
        controls.append({'id':site,'alias':f'E{number:02}','caption':row['caption'],
          'lookup_path':'Environment/'+group+'/'+row['caption'],'type':'f32','range_min':0.0,'range_max':(1.0 if number<=59 else 10.0),
          'original_call':row['original_call'],'original_export':row['original_export'],
          'source_call':match.group(0),'source_commit':SOURCE,'source_path':source_path,
          'positive':0.85 if number<=59 else 6.0,'negative':0.15 if number<=59 else 0.0,
          'consumer':('DebugToManager -> CloudsData pair -> GenerateShaderConstants -> '
            'BrnIm3d SetShaderConstants g_layerCloudiness/g_layerInvFeather/g_layerAlphas -> sky sampler pixels'
            if number<=59 else 'DebugToManager -> LightingData named fill channel -> GenerateShaderConstants -> '
            'ComputeIrradiance direction,key,shadow,right,left,up,down -> RGB irradiance matrices -> world/vehicle lighting'),
          'roi':([0,0,1,0.60] if number<=59 else [0.08,0.25,0.92,0.95])})
    contexts=[
      {'alias':'CSIM','lookup_path':'Environment/Simulate time of day','type':'bool','source_call':'RegisterVariable(&mbSimulateTimeOfDay, KPC_ROOT, "Simulate time of day");'},
      {'alias':'CTOOL','lookup_path':'Environment/Update values from Tool','type':'bool','source_call':'RegisterVariable(&mbUpdateValuesFromTool, KPC_ROOT, "Update values from Tool");'},
      {'alias':'CRIG','lookup_path':'Environment/Set Irradiance rig from Sky','type':'bool','source_call':'RegisterVariable(&mpEnvironmentManager->mbSetIrradianceFromSky, KPC_ROOT, "Set Irradiance rig from Sky");'},
      {'alias':'CCLOUD','lookup_path':'Environment/Clouds seconds per frame','type':'f32','source_call':'RegisterFloat(&mfCloudDelta, KPC_ROOT, "Clouds seconds per frame", 0.0f, 2000.0f, 1.0f);'}]
    normalized=' '.join(source.split())
    for c in contexts:assert c['source_call'] in normalized,c['alias']
    paths=[source_path,'src/GameSource/World/EnvironmentManager/BrnEnvironmentManager.cpp',
      'src/GameSource/World/EnvironmentManager/BrnGlobalIrradianceManager.cpp',
      'src/GameSource/Graphics/ImmediateMode/BrnIm3d.cpp',
      'src/GameSource/Graphics/BrnSkyDomeManager.cpp',
      'src/GameSource/World/BrnWorldModule.cpp',
      'src/GameSource/Graphics/BrnRendererModule.cpp']
    pins={}
    evidence=R/'source';evidence.mkdir(exist_ok=True)
    for path in paths:
        blob=subprocess.check_output(['git','-C',str(W/'b5-decomp'),'show',SOURCE+':'+path])
        dest=evidence/Path(path).name;dest.write_bytes(blob)
        pins[path]=hashlib.sha256(blob).hexdigest()
    original={}
    for addr in ['827B2408','827B3B28','827BFC80','827C7760','827D0098','827D1410']:
        p=W/f'.ida-exports/BURNOUT_X360_ARTIST.XEX/0x{addr}.json'
        assert p.is_file();original[str(p)]=sha(p)
    save(R/'SCOPE.json',{'candidate':{'b5':SOURCE,'workflow':old['build_workflow'],'exe_sha256':EXE},
      'slot':62180,'controls':controls,'context_aliases':contexts,'control_count':24,
      'already_final_excluded':True,'source_git_blob_sha256':pins,'original_export_sha256':original,
      'semantics':'Tool FALSE plus Simulate FALSE invokes original DebugToManager. Tool TRUE invokes ManagerToDebug and would invalidate all setter proofs.',
      'max_frames':76,'max_log_mib':64,'max_seconds':240,'site_credit':0})
    stage=R/'stage';assert not (R/'GAME_RUN_STARTED.json').exists(),'Never overwrite a launched packet'
    (stage/'slot').mkdir(parents=True,exist_ok=True);(stage/'data').mkdir(exist_ok=True)
    assets=load(OLD/'DATA_SNAPSHOT.json');asset_source=Path(assets['source'])
    for name,meta in assets['roster'].items():
        p=asset_source/name
        assert p.is_file() and p.stat().st_size==meta['bytes'] and sha(p)==meta['sha256'],p
        dest=stage/'data'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():os.link(p,dest)
        assert os.path.samefile(p,dest)
    save(R/'ASSETS.json',{'source':str(asset_source),'roster':assets['roster'],'method':'Every immutable source hash reverified now; NTFS same-file identity verified for every new private link. Run holds READ-only sharing handles.'})
    for name,h in old['launch_files'].items():
        p=Path(old['exe_dir'])/name;assert sha(p)==h
        shutil.copy2(p,stage/'slot'/name)
    (stage/'slot/config.ini').write_text('[Display]\nWidth=640\nHeight=360\nAdapterIndex=0\nVSync=1\nDecoupleSimulation=1\nFullscreen=0\n',encoding='ascii')
    shutil.copy2(OLD/'Profile.seed.sav',R/'Profile.seed.sav')
    profile=stage/'data/Memcard_62180/Profile.sav';profile.parent.mkdir(exist_ok=True);shutil.copy2(R/'Profile.seed.sav',profile)
    for path in ['tools/tests/run_case.ps1','tools/diagnostics/flow_run.ps1']:
        dest=R/'runtime_harness'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(OLD/'runtime_harness'/path,dest)
    normal={};drift=[]
    # The installed source32 normal roster supersedes historical source24 receipts.
    roster=load(W/'scratch/DEBUG_MENU_1011/root_normal_identity_source41_20261029/NORMAL_POST_INSTALL_ROSTER.json')
    for row in roster['runtime_payloads']+roster['profile_config_log_preserved']:
        p=W/'build/game'/row['relative_path'];actual=sha(p)
        if actual!=row['sha256']:
            assert row['relative_path'].lower().endswith('.log'),'Unexpected normal nonlog drift '+str(p)
            drift.append({'path':str(p),'historical_sha256':row['sha256'],'current_sha256':actual})
        normal[str(p)]={'sha256':actual,'bytes':p.stat().st_size}
    assert len(normal)==36
    save(R/'NORMAL_BEFORE.json',normal)
    save(R/'HISTORICAL_NORMAL_LOG_DRIFT.json',{'normal_written':False,'historical_roster':str(W/'scratch/DEBUG_MENU_1011/playable_refresh_20261029/delivery/NORMAL_POST_INSTALL_ROSTER.json'),'differences':drift})
    save(R/'STAGING.json',{'slot':62180,'source':SOURCE,'build_workflow':old['build_workflow'],
      'exe_sha256':EXE,'exe_dir':str(stage/'slot'),'cwd':str(stage/'data'),'profile':str(profile),
      'profile_seed_sha256':sha(R/'Profile.seed.sav'),'launch_files':old['launch_files'],
      'config_sha256':sha(stage/'slot/config.ini'),'runtime_shared_readonly_dependencies':old['runtime_shared_readonly_dependencies'],
      'runtime_overlay_files':{str(R/'runtime_harness'/p):sha(R/'runtime_harness'/p) for p in ['tools/tests/run_case.ps1','tools/diagnostics/flow_run.ps1']},
      'active_run_dir':str(R/'run_62180_game01'),'normal_protected_count':36,
      'storage':{'planned_output_peak_bytes':262144000,'protected_free_floor_bytes':1073741824,
        'required_free_at_launch_bytes':1335885824,'maximum_frames':76,'frame_bytes_at_640x360':921654,
        'game_log_cap_bytes':67108864}})
    print(json.dumps({'prepared':str(R),'selected_controls':24,'slot':62180,'game_launched':False}))

if __name__=='__main__':main()
