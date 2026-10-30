import os,subprocess,json,hashlib,re
from pathlib import Path
W=Path('D:/Reverse/BP-Decomp_Workflow');B=W/'b5-decomp';S=W/'scratch/DEBUG_MENU_1011';R=Path(__file__).resolve().parent;H=S/'source_next_followon40_20261029/post'
BASE='d85e2d5e2526783406d69fedc0ab17b219eb69bc';PUBLIC32='abbc9047d850a4665d959993012261c55205e5e5';E=dict(os.environ,GIT_INDEX_FILE=str(R/'source.index'))
def g(*args,input=None,env=E):
 p=subprocess.run(['git','-C',str(B),*args],input=input,env=env,capture_output=True)
 if p.returncode:raise RuntimeError(str(args)+'\n'+p.stderr.decode(errors='replace'))
 return p.stdout
def sha(b):return hashlib.sha256(b).hexdigest()
def oid(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def save(n,d):(R/n).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
review=S/'review_scoring_cpu_sourcebatch_20261029/REVIEW_REPORT.md';assert sha(review.read_bytes())=='c12d82377569851aa5a5e57614f48f1bda375eb730353b1fd362c60964e4f141'
integrity=[]
for name in ['scoring_resume_20261029','scoring_resume_20261029_exact_eol']:
 root=S/name;m=json.loads((root/'MANIFEST.json').read_text())
 for f in m['files']:assert sha((root/f['path']).read_bytes())==f['sha256'],f['path']
 integrity.append({'packet':name,'members':len(m['files']),'manifest_sha256':sha((root/'MANIFEST.json').read_bytes()),'seal_sha256':sha((root/'SEAL.json').read_bytes())})
root=S/'cpu_perfmon_graph_math_witness_20261029';mf=root/'MANIFEST.sha256';assert sha(mf.read_bytes())=='ef8d25dce8ddb790e872f5fb1a1d5df5c48c043fe04ec89c2ebf924d902f0ada'
members=0
for line in mf.read_text().splitlines():
 h,p=line.split('  ',1);assert sha((root/p).read_bytes())==h,p;members+=1
integrity.append({'packet':root.name,'members':members,'manifest_sha256':sha(mf.read_bytes()),'seal_sha256':sha((root/'SEAL.json').read_bytes())})
g('read-tree',BASE);records=[]
for name,patch,expected in [('scoring','scoring_resume_20261029_exact_eol/changes_exact_eol.patch','366091b144f4b38a86de939d739d03c338f792e3c8e4ce59a1ce66cb0c9d44e4'),('cpu','cpu_perfmon_graph_math_witness_20261029/changes.patch','92fd33a0d2586d0d425d4a61d27a36a19185be6c971fcccef0c351de0196dddb')]:
 raw=(S/patch).read_bytes();assert sha(raw)==expected;paths=re.findall(r'^\+\+\+ b/(.+)$',raw.decode(),re.M);paths=[p.rstrip('\r') for p in paths];files=[]
 for p in paths:
  pre=g('show',':'+p);assert pre==g('show',PUBLIC32+':'+p),'source41 preimage drift '+p;files.append({'path':p,'pre_sha256':sha(pre),'pre_blob':oid(pre)})
 g('-c','core.autocrlf=false','apply','--cached','--check',str(S/patch));g('-c','core.autocrlf=false','apply','--cached',str(S/patch))
 for f in files:
  post=g('show',':'+f['path']);f.update(post_sha256=sha(post),post_blob=oid(post))
 (R/(name+'.patch')).write_bytes(raw);records.append({'packet_id':name,'patch_path':patch,'patch_sha256':expected,'review_path':str(review.relative_to(S)),'review_sha256':sha(review.read_bytes()),'files':files,'raw_cached_apply_check':0,'raw_cached_apply':0,'native_credit':0,'site_credit':0})
tree=g('write-tree').decode().strip();paths=g('diff','--cached','--name-only',BASE).decode().splitlines();(R/'SOURCE_DIFF.patch').write_bytes(g('diff','--cached',BASE));save('COMPOSITION.json',{'source_base':BASE,'source32':PUBLIC32,'source_tree':tree,'records':records,'source_diff_paths':paths})
maps={}
for target in [BASE,tree]:
 maps[target]={}
 for line in g('ls-tree','-r',target,'--','src').decode().splitlines():
  info,p=line.split('\t');maps[target][p]=info.split()[2]
headers=[p for p in maps[BASE] if p.endswith(('.h','.hpp','.inl','.inc','.def'))];cpps=[p for p in paths if p.endswith('.cpp')]
for side,target in [('pre',BASE),('post',tree)]:
 for p in headers:
  dest=R/side/p;dest.parent.mkdir(parents=True,exist_ok=True);prior=H/p
  if p not in paths and prior.is_file() and oid(prior.read_bytes())==maps[target][p]:
   if not dest.exists():os.link(prior,dest)
  else:dest.write_bytes(g('show',target+':'+p))
 for p in cpps:
  dest=R/side/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(g('show',target+':'+p))
flags=' '.join(x.strip() for x in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#'));incs=[x.strip() for x in (W/'tools/build/msvc_includes.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
commands=['@echo off',f'call "{W}/tools/build/msvc_env.bat"','if errorlevel 1 exit /b 1']
for side in ['pre','post']:
 for p in cpps:
  name=side+'_'+Path(p).stem;rp=R/(name+'.rsp');inc=[]
  for x in incs:
   rel=x.replace('\\','/');ip=R/side/rel[len('b5-decomp/'):] if rel.startswith('b5-decomp/src') else W/x;inc.append('/I"'+str(ip)+'"')
  rp.write_text(flags+'\n/c\n/showIncludes\n'+'\n'.join(inc)+f'\n/Fo"{R}/{name}.obj"\n"{R/side/p}"\n',encoding='utf-8')
  commands += [f'cl @"{rp}" > "{R}/{name}.log" 2>&1',f'echo %errorlevel% > "{R}/{name}.exit"','if errorlevel 1 exit /b 1']
(R/'compile.cmd').write_text('\r\n'.join(commands)+'\r\n',encoding='utf-8',newline='');save('INPUT_INTEGRITY.json',{'status':'PASS','review_sha256':sha(review.read_bytes()),'author_packets':integrity,'all_five_preimages_equal_source41_and_source32':True,'no_shared_source_modified':True});print(json.dumps({'tree':tree,'paths':paths,'headers':len(headers),'compile_count':len(cpps)*2},indent=2))
