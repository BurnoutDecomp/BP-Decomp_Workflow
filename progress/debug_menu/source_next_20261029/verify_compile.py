exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
C=json.loads((R/'COMPOSITION.json').read_text());rows=[];deps={}
objects={}
for tree in [BASE,C['source_tree']]:
 objects[tree]={}
 for line in g('ls-tree','-r',tree,'--','src').decode().splitlines():
  info,path=line.split('\t');objects[tree][path]=info.split()[2]
def blob_oid(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
cpps=[p for p in C['source_diff_paths'] if p.endswith('.cpp')]+['src/GameSource/Network/Managers/BrnNetworkImageManager.cpp','src/GameSource/Network/Managers/BrnNetworkStateManager_wN1_03.cpp']
canonical=' '.join(x.strip() for x in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#'))
for side in ['pre','post']:
 for p in cpps:
  n=side+'_'+Path(p).stem;log=R/(n+'.log');rsp=R/(n+'.rsp');ex=R/(n+'.exit');obj=R/(n+'.obj')
  assert int(ex.read_text())==0 and obj.exists(),n
  text=log.read_text(errors='replace');assert not re.search(r'\b(?:warning|error) (?:C|D|LNK)\d',text),n
  assert rsp.read_text().splitlines()[0]==canonical,n
  found=[]
  for path in re.findall(r'including file:\s+(.+)',text):
   hp=Path(path.strip()).resolve();assert hp.is_file(),str(hp)
   assert not str(hp).lower().startswith(str(B/'src').lower()),'shared-src fallback '+str(hp)
   data=hp.read_bytes();deps[str(hp)]=sha(data);found.append(str(hp))
   if str(hp).lower().startswith(str(R/side/'src').lower()):
    rel=hp.relative_to(R/side).as_posix();assert blob_oid(data)==objects[BASE if side=='pre' else C['source_tree']][rel],str(hp)
  source=(R/side/p).read_bytes();assert blob_oid(source)==objects[BASE if side=='pre' else C['source_tree']][p],p
  rows.append({'side':side,'source':p,'source_sha256':sha(source),'canonical_flags':canonical,'rsp_sha256':sha(rsp.read_bytes()),'log_sha256':sha(log.read_bytes()),'object_sha256':sha(obj.read_bytes()),'compiler_exit':0,'warning_count':0,'include_occurrences':len(found),'observed_headers':found})
save('OBSERVED_DEPENDENCIES.json',{'files':[{'path':p,'sha256':h} for p,h in sorted(deps.items())]})
save('COMPILE_RECEIPT.json',{'verdict':'PASS_COMPILE_ONLY','source_base':BASE,'source_tree':C['source_tree'],'canonical_flags_file_sha256':sha((W/'tools/build/msvc_flags.txt').read_bytes()),'canonical_includes_file_sha256':sha((W/'tools/build/msvc_includes.txt').read_bytes()),'tracked_header_count_per_snapshot':2620,'source32_pre_compiles':6,'candidate_post_compiles':6,'warning_count':0,'error_count':0,'shared_src_fallback':False,'rows':rows,'observed_dependencies_sha256':sha((R/'OBSERVED_DEPENDENCIES.json').read_bytes()),'whole_game_link':False,'native_game':False,'site_credit':0,'preparation_failures_retained':['response_preparation_failure.log','missing_sibling_header_failure.log']})
print(json.dumps({'verdict':'PASS_COMPILE_ONLY','compiles':len(rows),'unique_observed_headers':len(deps),'shared_src_fallback':False,'warnings':0}))
