from pathlib import Path
from pair_witness import pair
P='00000000,00000000,00000000,00000000,3F800000,00000000,00000000,11111111ABCDEF01,22222222ABCDEF01'
Q=P.replace('3F800000','3F800001')
A='0000000000000000,00,01'; B='0000000000000000,01,00'
def line(side,n,p,t): return f'[satnav-event-witness] {side} seq={n} prefix={p} tail={t}'
r=pair([line('sender',1,P,A),line('sender',2,P,A),line('receiver',1,P,A),line('receiver',2,P,B)])
assert not r['errors'] and r['tail_mismatches']==1 and len(r['pairs'])==2
r=pair([line('sender',1,P,A),line('sender',2,P,B),line('receiver',1,P,A)])
assert any('ambiguous' in x for x in r['errors'])
r=pair([line('sender',1,P,A),line('sender',2,Q,A),line('receiver',1,Q,A)])
assert any('FIFO gap' in x for x in r['errors'])
r=pair([line('receiver',1,P,A)])
assert any('no available sender' in x for x in r['errors'])
r=pair([line('sender',2,P,A),line('receiver',1,P,A)])
assert any('sequence' in x for x in r['errors'])
for fixture in ('interleaved_sender_fixture.txt', 'malformed_suffix_fixture.txt', 'unexpected_prefix_fixture.txt'):
    lines = (Path(__file__).parent / fixture).read_text(encoding='utf8').splitlines(keepends=True)
    result = pair(lines)
    assert any('malformed witness' in x for x in result['errors']), (fixture, result)
    print(f'PASS: {fixture} rejected: {result["errors"][0]}')
# The actual log contains records starting at column one, with CRLF on Windows.
result=pair([line('sender',1,P,A)+'\r\n', line('receiver',1,P,A)+'\r\n'])
assert not result['errors'] and len(result['pairs'])==1
records=[]
for n in range(1,20000): records += [line('sender',n,P,A), line('receiver',n,P,A)]
assert not pair(records,20000)['errors']
records += [line('sender',20000,P,A), line('receiver',20000,P,A)]
assert any('cap reached' in x for x in pair(records,20000)['errors'])
print('PASS: FIFO, mismatch, ambiguity, missing, sequence, suffix, interleave, CRLF and cap checks')
