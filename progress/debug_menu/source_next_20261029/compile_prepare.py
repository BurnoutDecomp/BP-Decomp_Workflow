exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
C=json.loads((R/'COMPOSITION.json').read_text());TREE=C['source_tree']
entries={}
for line in g('ls-tree','-r',TREE,'--','src').decode().splitlines():
 info,p=line.split('\t');mode,typ,oid=info.split()
 if typ=='blob': entries[p]=oid
headers={p:o for p,o in entries.items() if p.endswith(('.h','.hpp','.inl','.inc','.def'))}
cpps=[p for p in C['source_diff_paths'] if p.endswith('.cpp')]+['src/GameSource/Network/Managers/BrnNetworkImageManager.cpp','src/GameSource/Network/Managers/BrnNetworkStateManager_wN1_03.cpp']
needed={**headers,**{p:entries[p] for p in cpps}}
proc=subprocess.Popen(['git','-C',str(B),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for p,oid in needed.items():
 proc.stdin.write((oid+'\n').encode());proc.stdin.flush();head=proc.stdout.readline();n=int(head.split()[2]);b=proc.stdout.read(n);assert proc.stdout.read(1)==b'\n'
 dest=R/'post'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
proc.stdin.close();proc.wait();assert proc.returncode==0
for p in C['source_diff_paths']+cpps:
 dest=R/'pre'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(g('show',BASE+':'+p))
for p in headers:
 dest=R/'pre'/p
 if not dest.exists():
  dest.parent.mkdir(parents=True,exist_ok=True);os.link(R/'post'/p,dest)
drift=[];total=0;physical_bad=[]
depfile=S/'swarm_traffic_source_backlog_20261028/chunk24_crashed_articulated_pairing/COMPILE_DEPENDENCIES.json'
for row in json.loads(depfile.read_text())['files']:
 p=Path(row['path']);b=p.read_bytes();assert sha(b)==row['sha256'],str(p)
 s=p.as_posix();marker='/src/'
 if marker not in s:continue
 rel='src/'+s.split(marker,1)[1];cp=R/'post'/rel
 if not cp.exists():continue
 total+=1;cur=cp.read_bytes()
 if lf(cur)!=lf(b):
  drift.append({'packet_path':str(p),'path':rel,'packet_sha256':sha(b),'candidate_sha256':sha(cur),'diff':''.join(difflib.unified_diff(lf(b).decode(errors='replace').splitlines(keepends=True),lf(cur).decode(errors='replace').splitlines(keepends=True),fromfile='packet/'+rel,tofile='candidate/'+rel))})
save('DEPENDENCY_DRIFT.json',{'reviewed_dependency_manifest':str(depfile),'reviewed_dependency_manifest_sha256':sha(depfile.read_bytes()),'all_physical_pins_verified':True,'source_headers_compared':total,'drift':drift})
flags=' '.join(line.strip() for line in (W/'tools/build/msvc_flags.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))
incs=[line.strip() for line in (W/'tools/build/msvc_includes.txt').read_text().splitlines() if line.strip() and not line.startswith('#')]
commands=['@echo off',f'call "{W}/tools/build/msvc_env.bat"','if errorlevel 1 exit /b 1']
for side in ['pre','post']:
 for p in cpps:
  n=side+'_'+Path(p).stem;rp=R/(n+'.rsp');sp=R/side/p
  inc=['/I"'+str(R/side/'src')+'"']
  for line in incs:
   path=W/line
   if line.replace('\\','/').startswith('b5-decomp/src'):
    suffix=line.replace('\\','/')[len('b5-decomp/'):];path=R/side/suffix
    if suffix=='src':continue
    if not path.exists():path=R/'post'/suffix
   inc+=['/I"'+str(path)+'"']
  rp.write_text(flags+'\n/c\n/showIncludes\n'+'\n'.join(inc)+f'\n/Fo"{R}/{n}.obj"\n"{sp}"\n',encoding='utf-8')
  commands += [f'cl @"{rp}" > "{R}/{n}.log" 2>&1',f'echo %errorlevel% > "{R}/{n}.exit"','if errorlevel 1 exit /b 1']
(R/'compile.cmd').write_text('\n'.join(commands)+'\n',encoding='utf-8')
print(json.dumps({'header_count':len(headers),'cpp_count':len(cpps),'source_headers_compared':total,'dependency_drift_paths':sorted(set(x['path'] for x in drift))},indent=2))
