exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
C=json.loads((R/'COMPOSITION.json').read_text());rows=[];deps={};maps={}
for tree in [BASE,C['source_tree'],PUBLIC32]:
 maps[tree]={}
 for line in g('ls-tree','-r',tree,'--','src').decode().splitlines():
  info,path=line.split('\t');maps[tree][path]=info.split()[2]
cpps=[p for p in C['source_diff_paths'] if p.endswith('.cpp')];drift={};flags=' '.join(x.strip() for x in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#'))
for side in ['pre','post']:
 for path in cpps:
  name=side+'_'+Path(path).stem;log=R/(name+'.log');text=log.read_text(errors='replace');rsp=R/(name+'.rsp');obj=R/(name+'.obj')
  assert int((R/(name+'.exit')).read_text())==0 and obj.is_file(),name
  assert not re.search(r'\b(?:warning|error) (?:C|D|LNK)\d',text),name
  assert rsp.read_text().splitlines()[0]==flags,name
  found=[]
  for p in re.findall(r'including file:\s+(.+)',text):
   hp=Path(p.strip()).resolve();assert hp.is_file();assert not str(hp).lower().startswith(str(B/'src').lower()),'shared source fallback'
   data=hp.read_bytes();deps[str(hp)]=sha(data);found.append(str(hp))
   if str(hp).lower().startswith(str(R/side/'src').lower()):
    rel=hp.relative_to(R/side).as_posix();assert oid(data)==maps[BASE if side=='pre' else C['source_tree']][rel],rel
    if side=='pre' and maps[BASE][rel]!=maps[PUBLIC32][rel]:drift[rel]={'path':rel,'source32_blob':maps[PUBLIC32][rel],'delivered41_blob':maps[BASE][rel]}
  data=(R/side/path).read_bytes();assert oid(data)==maps[BASE if side=='pre' else C['source_tree']][path],path
  rows.append({'side':side,'source':path,'source_sha256':sha(data),'compiler_exit':0,'warning_count':0,'rsp_sha256':sha(rsp.read_bytes()),'log_sha256':sha(log.read_bytes()),'object_sha256':sha(obj.read_bytes()),'observed_headers':found,'include_occurrences':len(found)})
save('OBSERVED_DEPENDENCIES.json',{'files':[{'path':p,'sha256':h} for p,h in sorted(deps.items())]});save('DEPENDENCY_DRIFT.json',{'review32_to_delivered41_observed_header_drift':list(drift.values()),'all_source_headers_equal_pinned41_or_candidate_Git_blobs':True,'shared_src_fallback':False})
save('COMPILE_RECEIPT.json',{'verdict':'PASS_COMPILE_ONLY','source_base':BASE,'source_tree':C['source_tree'],'canonical_flags':flags,'canonical_flags_file_sha256':sha((W/'tools/build/msvc_flags.txt').read_bytes()),'canonical_includes_file_sha256':sha((W/'tools/build/msvc_includes.txt').read_bytes()),'pre_compiles':4,'post_compiles':4,'warnings':0,'errors':0,'rows':rows,'observed_dependency_manifest_sha256':sha((R/'OBSERVED_DEPENDENCIES.json').read_bytes()),'whole_game_link':False,'native_or_site_credit':False})
print(json.dumps({'verdict':'PASS_COMPILE_ONLY','compile_count':8,'unique_observed_headers':len(deps),'source32_to41_drift_paths':list(drift)},indent=2))
