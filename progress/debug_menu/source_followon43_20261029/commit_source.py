exec((__import__('pathlib').Path(__file__).parent/'prepare.py').read_text().split("g('read-tree',BASE)")[0])
C=json.loads((R/'COMPOSITION.json').read_text());receipt=json.loads((R/'COMPILE_RECEIPT.json').read_text());assert receipt['source_tree']==C['source_tree'] and receipt['verdict']=='PASS_COMPILE_ONLY'
env=dict(os.environ,GIT_INDEX_FILE=str(R/'source-commit.index'));g('read-tree',BASE,env=env);parent=BASE;records=[]
for row in C['records']:
 for f in row['files']:
  assert g('rev-parse',':'+f['path'],env=env).decode().strip()==f['pre_blob']
  g('update-index','--cacheinfo','100644,'+f['post_blob']+','+f['path'],env=env)
 tree=g('write-tree',env=env).decode().strip()
 title='Restore full network stunt multiplier payload and ordered distance gate' if row['packet_id']=='scoring' else 'Restore original CPU performance graph floating-point operation order'
 body='Preserve the signed64 payload through event143 and store both named32-bit words; reject unordered squared distances with the original ordered comparison.' if row['packet_id']=='scoring' else 'Use the original fused background endpoint and separately rounded segment multiply/add/subtract operations, retaining the finite witness values.'
 msg=(title+'\n\n'+body+'\n\nExact independent source review, negative/post controls and fresh delivered41 pre/post owning-TU compiles pass. No native or site credit.\n\nCo-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>\n').encode()
 commit=g('commit-tree',tree,'-p',parent,input=msg).decode().strip();assert b'Co-Authored-By: Codex GPT-6.1 Sol <noreply@openai.com>' in g('show','-s','--format=%B',commit)
 records.append({**row,'source_commit':commit,'source_parent':parent,'source_tree':tree});parent=commit
assert tree==C['source_tree'];g('-c','core.whitespace=cr-at-eol','diff','--check',BASE,parent)
save('SOURCE_COMMITS.json',{'source41':BASE,'source43':parent,'source_tree':tree,'records':records,'refs_created':False,'public_or_normal_modified':False});print(json.dumps({'source43':parent,'source_tree':tree,'source_commits':[r['source_commit'] for r in records],'refs_created':False},indent=2))
