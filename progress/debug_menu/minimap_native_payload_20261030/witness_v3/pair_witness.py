"""Pair one run's exact SatNav sender/receiver records. Never compare pointer values across runs."""
import json, re, sys
PATTERN = re.compile(r'\[satnav-event-witness\] (sender|receiver) seq=(\d+) prefix=([0-9A-F,]+) tail=([0-9A-F,]+)')
PREFIX = re.compile(r'^(?:[0-9A-F]{8},){7}[0-9A-F]{16},[0-9A-F]{16}$')
TAIL = re.compile(r'^[0-9A-F]{16},[0-9A-F]{2},[0-9A-F]{2}$')
def pair(lines):
    pending=[]; counts={'sender':0,'receiver':0}; pairs=[]; errors=[]
    for line_no,line in enumerate(lines,1):
        if '[satnav-event-witness' not in line: continue
        # The native log writes witness records at the start of a line; no
        # arbitrary prefix or suffix is permitted. Strip only line terminators.
        m=PATTERN.fullmatch(line.rstrip('\r\n'))
        if not m or not PREFIX.fullmatch(m[3]) or not TAIL.fullmatch(m[4]):
            errors.append(f'line {line_no}: malformed witness'); continue
        side,seq,prefix,tail=m[1],int(m[2]),m[3],m[4]
        counts[side]+=1
        if seq != counts[side]: errors.append(f'line {line_no}: missing or repeated {side} sequence {seq}')
        if side=='sender': pending.append((prefix,tail,seq,line_no)); continue
        matches=[x for x in pending if x[0]==prefix]
        if not matches:
            errors.append(f'line {line_no}: receiver {seq} has no available sender with this prefix'); continue
        if len({x[1] for x in matches}) != 1:
            errors.append(f'line {line_no}: receiver {seq} has ambiguous same-prefix sender tails'); continue
        if pending[0][0] != prefix:
            errors.append(f'line {line_no}: FIFO gap before receiver {seq}'); continue
        sender=pending.pop(0)
        pairs.append({'sender_seq':sender[2],'receiver_seq':seq,'prefix':prefix,
                      'expected_tail':sender[1],'received_tail':tail,'equal':sender[1]==tail,
                      'sender_line':sender[3],'receiver_line':line_no})
    if pending: errors.append(f'{len(pending)} sender records unmatched')
    if not pairs: errors.append('no paired records')
    if counts['sender']>=3000 or counts['receiver']>=3000: errors.append('witness cap reached; coverage unproven')
    return {'counts':counts,'pairs':pairs,'tail_mismatches':sum(not x['equal'] for x in pairs),'errors':errors}
def main():
    if len(sys.argv)!=2: raise SystemExit('usage: pair_witness.py ONE_RUN_LOG')
    with open(sys.argv[1],encoding='utf8',errors='replace') as f: result=pair(f)
    print(json.dumps(result,indent=2))
    return bool(result['errors'])
if __name__=='__main__': raise SystemExit(main())
