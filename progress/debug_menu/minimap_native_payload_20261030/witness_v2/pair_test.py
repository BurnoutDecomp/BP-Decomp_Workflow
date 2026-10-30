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
print('PASS: identical tails pair FIFO; corruption counted; ambiguous tails, missing and FIFO gaps rejected')
