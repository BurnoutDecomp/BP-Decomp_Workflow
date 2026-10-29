exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
C=json.loads((R/'COMPOSITION.json').read_text());rows=[];deps={};objects={}
for tree in [BASE,C['source_tree'],PUBLIC]:
 objects[tree]={}
 for line in g('ls-tree','-r',tree,'--','src').decode().splitlines():
  info,path=line.split('\t');objects[tree][path]=info.split()[2]
cpps=[p for p in C['source_diff_paths'] if p.endswith('.cpp')]+['src/GameSource/Director/Arbitrator/States/BrnArbStateTestbed.cpp']
canonical=' '.join(x.strip() for x in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#'));drift=[]
for side in ['pre','post']:
 for path in cpps:
  n=side+'_'+Path(path).stem;log=R/(n+'.log');rsp=R/(n+'.rsp');ex=R/(n+'.exit');obj=R/(n+'.obj')
  assert int(ex.read_text())==0 and obj.exists(),n
  text=log.read_text(errors='replace');assert not re.search(r'\b(?:warning|error) (?:C|D|LNK)\d',text),n
  assert rsp.read_text().splitlines()[0]==canonical,n
  found=[]
  for p in re.findall(r'including file:\s+(.+)',text):
   hp=Path(p.strip()).resolve();assert hp.is_file();assert not str(hp).lower().startswith(str(B/'src').lower()),'shared source fallback'
   data=hp.read_bytes();deps[str(hp)]=sha(data);found.append(str(hp))
   if str(hp).lower().startswith(str(R/side/'src').lower()):
    rel=hp.relative_to(R/side).as_posix();assert oid(data)==objects[BASE if side=='pre' else C['source_tree']][rel],rel
    if side=='pre' and objects[BASE][rel]!=objects[PUBLIC][rel]:drift.append({'path':rel,'source32_blob':objects[PUBLIC][rel],'source38_blob':objects[BASE][rel]})
  data=(R/side/path).read_bytes();assert oid(data)==objects[BASE if side=='pre' else C['source_tree']][path],path
  rows.append({'side':side,'source':path,'source_sha256':sha(data),'canonical_flags':canonical,'rsp_sha256':sha(rsp.read_bytes()),'log_sha256':sha(log.read_bytes()),'object_sha256':sha(obj.read_bytes()),'compiler_exit':0,'warnings':0,'include_occurrences':len(found),'observed_headers':found})
save('OBSERVED_DEPENDENCIES.json',{'files':[{'path':p,'sha256':h} for p,h in sorted(deps.items())]})
save('DEPENDENCY_DRIFT.json',{'source32_to_source38_observed_pre_headers':list({x['path']:x for x in drift}.values()),'all_source_headers_equal_exact_Git_blobs':True,'shared_src_fallback':False})
prior=json.loads((P/'COMPILE_RECEIPT.json').read_text());prior_deps=json.loads((P/'OBSERVED_DEPENDENCIES.json').read_text())['files'];new_headers=[p for p in C['source_diff_paths'] if p.endswith(('.h','.hpp','.inl','.inc','.def'))]
for row in prior['rows']:
 if row['side']=='post':assert not any(p.replace('\\','/').endswith('/'+h) for p in row['observed_headers'] for h in new_headers),'prior compiled source reads new header'
for f in prior_deps:assert sha(Path(f['path']).read_bytes())==f['sha256'],'prior compile dependency drift '+f['path']
save('PRIOR38_COMPILE_REUSE.json',{'prior_compile_receipt_sha256':sha((P/'COMPILE_RECEIPT.json').read_bytes()),'prior_observed_dependencies_sha256':sha((P/'OBSERVED_DEPENDENCIES.json').read_bytes()),'prior_all1278_dependency_hashes_still_match':True,'new_header_intersection_with_prior_six_post_compiles':[],'prior_six_sources_and_dependency_headers_unchanged':True,'scope':'Reuse prior six postcompile receipts because no new header is read by them; all prior physical input hashes are reverified'})
save('COMPILE_RECEIPT.json',{'verdict':'PASS_COMPILE_ONLY','source_base':BASE,'source_tree':C['source_tree'],'canonical_flags_file_sha256':sha((W/'tools/build/msvc_flags.txt').read_bytes()),'canonical_includes_file_sha256':sha((W/'tools/build/msvc_includes.txt').read_bytes()),'tracked_headers_per_snapshot':2620,'pre_compiles':3,'post_compiles':3,'warning_count':0,'error_count':0,'shared_src_fallback':False,'rows':rows,'observed_dependencies_sha256':sha((R/'OBSERVED_DEPENDENCIES.json').read_bytes()),'whole_game_link':False,'native_game':False,'site_credit':0})
print(json.dumps({'verdict':'PASS_COMPILE_ONLY','compiles':len(rows),'unique_headers':len(deps),'source32_source38_observed_header_drift':len({x['path'] for x in drift})}))
