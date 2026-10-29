exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
results=[]
for n in ['chunk21_reinsert_caller','chunk22_car_streamer_policy','chunk23_pressure_split_occupancy','chunk24_crashed_articulated_pairing']:
 root=S/'swarm_traffic_source_backlog_20261028'/n;mp=root/'MANIFEST.json';seal=root/'SEAL.json';m=json.loads(mp.read_text());assert sha(mp.read_bytes())==json.loads(seal.read_text())['manifest_sha256']
 for f in m['files']:
  b=(root/f['path']).read_bytes();assert sha(b)==f['sha256'],str(root/f['path'])
 results.append({'packet':n,'manifest_sha256':sha(mp.read_bytes()),'seal_sha256':sha(seal.read_bytes()),'verified_members':len(m['files'])})
for n,manifest,seal in [('review_traffic_chunk21_reinsert_caller_sol_20261029','INTEGRATION_SUPPLEMENT_MANIFEST.json','INTEGRATION_SUPPLEMENT_SEAL.json'),('review_traffic_chunk22_policy_sol_cc2b2c953e','MANIFEST.json','SEAL.json')]:
 root=S/n;mp=root/manifest;m=json.loads(mp.read_text());se=json.loads((root/seal).read_text());assert sha(mp.read_bytes()) in str(se)
 for f in m['files']:assert sha((root/f['path']).read_bytes())==f['sha256'],str(root/f['path'])
 results.append({'review':n,'manifest_sha256':sha(mp.read_bytes()),'seal_sha256':sha((root/seal).read_bytes()),'verified_members':len(m['files'])})
root=S/'swarm_camera_x360_compressed_picture_recovery_20261029';m=json.loads((root/'PINS.json').read_text());mutable=[]
for f in m['files']:
 p=W/f['path'];assert sha(p.read_bytes())==f['sha256'],str(p)
results.append({'packet':'camera','pins_sha256':sha((root/'PINS.json').read_bytes()),'seal_sha256':sha((root/'SEAL.json').read_bytes()),'verified_members':len(m['files'])})
root=S/'review_camera_x360_compressed_picture_20261029_independent';m=json.loads((root/'REVIEW_SEAL.json').read_text())
for f in m['review_artifacts']:assert sha((root/f['path']).read_bytes())==f['sha256'],str(root/f['path'])
results.append({'review':'camera','seal_sha256':sha((root/'REVIEW_SEAL.json').read_bytes()),'verified_members':len(m['review_artifacts'])})
root=S/'review_effects_arbitrator_bound32_20261029_73e60d3f';m=json.loads((root/'SEAL.json').read_text())
for key,value in m.items():
 if key.endswith('_sha256'):
  names={'review_sha256':'REVIEW.md','evidence_sha256':'REVIEW_EVIDENCE.json','strict_patch_sha256':'strict-bound32.patch'}
  if key in names:assert sha((root/names[key]).read_bytes())==value
ev=json.loads((root/'REVIEW_EVIDENCE.json').read_text())
for name,row in ev['author_artifacts'].items():assert sha((root/'author'/name).read_bytes())==row['sha256'],name
results.append({'review':'effects32','seal_sha256':sha((root/'SEAL.json').read_bytes()),'verified_author_members':len(ev['author_artifacts'])})
save('INPUT_INTEGRITY.json',{'status':'PASS','results':results,'no_author_or_reviewer_artifacts_changed':True})
print(json.dumps({'status':'PASS','groups':len(results),'members':sum(x.get('verified_members',x.get('verified_author_members',0)) for x in results)}))
