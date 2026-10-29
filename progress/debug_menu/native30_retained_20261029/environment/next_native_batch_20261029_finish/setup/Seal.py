from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
names=['prepare.py','make_driver.py','Case.ps1','Driver.ps1','Run.py','Preflight.ps1','OfflineChecks.ps1','Analyze.py','Request-HarnessPhaseDone.ps1','REVIEW_PACKET.md','SCOPE.json','STAGING.json','ASSETS.json','Profile.seed.sav','NORMAL_BEFORE.json','HISTORICAL_NORMAL_LOG_DRIFT.json']
files=[R/n for n in names]+[R/'CAPTURE_SOURCE_FIXTURE.json',R/'ROOT_NATIVE_EXECUTION_DELEGATION_V8_20261029.json',R/'ROOT_NORMAL41_ROSTER.json',R/'RETAINED_COMPLETE.json',R/'ReaderBenchmark.ps1']+list((R/'source').glob('*'))+list((R/'runtime_harness').rglob('*.ps1'))
manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(R/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(hashlib.sha256((R/'MANIFEST.json').read_bytes()).hexdigest())
