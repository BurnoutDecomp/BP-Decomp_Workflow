import os,subprocess,json,hashlib,re
from pathlib import Path
W=Path('D:/Reverse/BP-Decomp_Workflow');B=W/'b5-decomp';S=W/'scratch/DEBUG_MENU_1011';R=Path(__file__).resolve().parent
P=S/'source_next_20261029';BASE='8d71beb96e0cf681be78e235987bdbfce3c45dd9';WB='0a0c06dd9718d08fdbbddf02e3579d5db6d8be02';PUBLIC='abbc9047d850a4665d959993012261c55205e5e5'
E=dict(os.environ,GIT_INDEX_FILE=str(R/'source.index'))
def g(*args,env=E,input=None):
 p=subprocess.run(['git','-C',str(B),*args],input=input,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stderr.decode(errors='replace'))
 return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
def oid(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def save(n,d):(R/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
report=S/'review_source_leafbatch_20261029/REVIEW_REPORT.md';assert sha(report.read_bytes())=='7815216d3e67f5b82b19bf27df699e9d4ecf61e01aa1fcda43880d7089dd0285'
sound=S/'swarm_sound_debug_controls_31_40_source_recovery_20261029_revision03';manifest=sound/'MANIFEST.sha256';assert sha(manifest.read_bytes())=='a57a87458c91a4a876b1a69666c9f4c5aa9458e33e51088bd72a2e52b8c6b141'
for line in manifest.read_text().splitlines():
 h,n=line.split('  ',1);assert sha((sound/n).read_bytes())==h,n
arb=S/'swarm_arb_state_testbed_ice_anims_recovery_20261029';pins={'manifest.json':'580535f67ff0ee65dc0f1c56071bc54dfdb9a6eda5d1d8f3847b2373e2dcd19b','source_integrity.json':'72ff35800856d0b94e875a30b62db6a9a6e2d769f1521597ec8150b8c346fa64','candidate_tree_integrity.json':'f8d544bd2481fb49e6f37b91afc4190b42e49296458ba686b78e0c1c96af5248','validation/result.json':'da0aa8175702534b6f88eba07f5bed3644d872737bc405eaaa278547c3955e7f'}
for n,h in pins.items():assert sha((arb/n).read_bytes())==h,n
g('read-tree',BASE);rows=[]
for name,p,h in [('sound31_40',S/'review_source_leafbatch_20261029/sound_baseline_to_post_lf.patch','1fab34c32ada3dc625074805f6126f44214292e5a3996d208d20da6e0fe53b78'),('arb_testbed',arb/'candidate.patch','4ec24a3ac65f892c44cc3fa039b062800607ac8279bd6057655c4bef99f7ce8a')]:
 raw=p.read_bytes();assert sha(raw)==h and b'\r' not in raw,name
 paths=re.findall(r'^\+\+\+ b/(.+)$',raw.decode(),re.M);files=[]
 for path in paths:
  pre=g('show',':'+path);assert pre==g('show',PUBLIC+':'+path),'source38/source32 preimage drift '+path
  files.append({'path':path,'pre_sha256':sha(pre),'pre_blob':oid(pre)})
 (R/(name+'.patch')).write_bytes(raw);g('-c','core.autocrlf=false','apply','--cached','--check',str(p));g('-c','core.autocrlf=false','apply','--cached',str(p))
 for f in files:
  post=g('show',':'+f['path']);f.update(post_sha256=sha(post),post_blob=oid(post))
 rows.append({'packet_id':name,'review_path':str(report.relative_to(S)),'review_sha256':sha(report.read_bytes()),'patch_path':str(p.relative_to(S)),'patch_sha256':h,'integration_patch':name+'.patch','files':files,'raw_cached_apply_check':0,'raw_cached_apply':0,'native_credit':0,'site_credit':0})
tree=g('write-tree').decode().strip();diff=g('diff','--cached',BASE);(R/'SOURCE_DIFF.patch').write_bytes(diff)
paths=g('diff','--cached','--name-only',BASE).decode().splitlines();save('COMPOSITION.json',{'source_base':BASE,'workflow_base':WB,'source32':PUBLIC,'source_tree':tree,'source_diff_paths':paths,'records':rows,'sound_manifest_members_verified':125,'arb_author_has_no_seal':True,'arb_integrity_pins':pins})
headers=[p.relative_to(P/'post').as_posix() for p in (P/'post/src').rglob('*') if p.is_file() and p.suffix in ('.h','.hpp','.inl','.inc','.def')]
cpps=[p for p in paths if p.endswith('.cpp')]+['src/GameSource/Director/Arbitrator/States/BrnArbStateTestbed.cpp']
for side,target in [('pre',BASE),('post',tree)]:
 for p in headers:
  dest=R/side/p;dest.parent.mkdir(parents=True,exist_ok=True)
  if p in paths:dest.write_bytes(g('show',target+':'+p))
  elif not dest.exists():os.link(P/'post'/p,dest)
 for p in cpps:
  dest=R/side/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(g('show',target+':'+p))
flags=' '.join(x.strip() for x in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#'));incs=[x.strip() for x in (W/'tools/build/msvc_includes.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
cmd=['@echo off',f'call "{W}/tools/build/msvc_env.bat"','if errorlevel 1 exit /b 1']
for side in ['pre','post']:
 for p in cpps:
  name=side+'_'+Path(p).stem;inc=[]
  for x in incs:
   rel=x.replace('\\','/');path=R/side/rel[len('b5-decomp/'):] if rel.startswith('b5-decomp/src') else W/x
   inc.append('/I"'+str(path)+'"')
  rsp=R/(name+'.rsp');rsp.write_text(flags+'\n/c\n/showIncludes\n'+'\n'.join(inc)+f'\n/Fo"{R}/{name}.obj"\n"{R/side/p}"\n')
  cmd += [f'cl @"{rsp}" > "{R}/{name}.log" 2>&1',f'echo %errorlevel% > "{R}/{name}.exit"','if errorlevel 1 exit /b 1']
(R/'compile.cmd').write_text('\n'.join(cmd)+'\n');save('INPUT_INTEGRITY.json',{'status':'PASS','sound125_manifest_verified':True,'review_report_sha256':sha(report.read_bytes()),'arb_integrity_files_verified':pins,'all_four_source_preimages_equal_source32_and_source38':True,'native':False})
print(json.dumps({'source_tree':tree,'paths':paths,'compile_count':len(cpps)*2,'header_count':len(headers)},indent=2))
