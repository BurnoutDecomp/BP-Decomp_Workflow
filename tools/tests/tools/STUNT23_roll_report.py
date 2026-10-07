"""STUNT23 roll report -- follow every barrel roll of a Stunt Run log through the scorer.

usage: python tools/tests/tools/STUNT23_roll_report.py <BrnGame.log> [--verdict] [--quiet]

Reads the opt-in PC witnesses of lane STUNT23 (issue #23) out of one BrnGame.log:
  [stunt23] lever takeoff/done/end     BRN_STUNT23_ROLL harness lever (physics side)
  [stunt23] f=... / [stunt23] HELD     StuntModeScoring::Update state-change rung (BRN_STUNT23_DIAG)
  [stunt23] bank ...                   StuntModeScoring::UpdateBufferedScore commit (BRN_STUNT23_DIAG)
  [stunt] combo banked ...             StuntModeScoring::EndCombo (BRN_STUNT_DIAG)
  [stuntair] land ...                  StuntOffencesManager landing edge (BRN_ROLL_PROBE)
  [sweep] shot ...                     the crash-sweep placement that starts each jump

Per jump it prints: how far the car rolled (lever + physics detector), whether it landed clean,
how many frames after touchdown the scorer's in-air rotation cleared (the console clears it on
the first frame all four wheels are attached and gripping), whether the roll was rated
(BARREL_ROLL type bit) and AWESOME, the bank that committed it (rolls / stuntMult / comboMult),
and the combo end that followed. With --verdict it also prints one VERDICT line:

  PASS when at least one clean full-turn lever roll exists and EVERY clean full-turn roll:
    (1) has its scorer rotation cleared after touchdown (never HELD),
    (2) is banked with the BARREL_ROLL bit, the AWESOME roll bit and rolls >= 1,
    (3) raises the combo multiplier at that bank (stuntMult >= 1, comboMult >= 2),
    (4) is followed by a combo end with score > 0 and mult >= 2,
  and some stunt banked AFTER the first roll bank also scored (the next trick is not blocked).
"""
import re
import sys

STUNT_BITS = {0: 'SPIN', 1: 'BARREL_ROLL', 2: 'AIR', 3: 'DRIFT', 4: 'SUPER_JUMP', 5: 'SUPER_SMASH',
              6: 'BILLBOARD', 7: 'BURNOUT', 8: 'BOOST', 9: 'REVERSE_DRIVING', 10: 'HANDBRAKE_TURN',
              11: 'POWER_PARK', 12: 'CRASH_FINISH', 13: 'PROP', 14: 'REVERSE_TAKEOFF', 17: 'TYPE17',
              18: 'ERR_REPEAT', 19: 'ERR_19', 20: 'RATED_GOOD', 21: 'RATED_AWESOME'}

RE_SHOT = re.compile(r'\[sweep\] shot (\d+)/')
RE_LEVER_TO = re.compile(r'\[stunt23\] lever takeoff jump=(\d+) tiltDeg=(\S+)')
RE_LEVER_DONE = re.compile(r'\[stunt23\] lever done jump=(\d+) turnedDeg=(\S+) frames=(\d+) upy=(\S+)')
RE_LEVER_END = re.compile(r'\[stunt23\] lever end jump=(\d+) reason=(\S+) turnedDeg=(\S+) frames=(\d+)')
RE_STATE = re.compile(r'\[stunt23\] (HELD )?f=(\d+) air=(\d) rot=(\S+),(\S+),(\S+) rollMax=(\S+) spinMax=(\S+) '
                      r'inProg=(\d) combo=(\d) valid=(\d) types=(-?\d+) awe=(-?\d+) cur=(-?\d+) bank=(\d) '
                      r'pend=(\d) pendT=(\S+) mult=(-?\d+) comboScore=(\S+) total=(-?\d+) sinceLand=(-?\d+) wheels=(\S+)')
RE_BANK = re.compile(r'\[stunt23\] bank valid=(\d) types=(-?\d+) awe=(-?\d+) spins=(\d+) rolls=(\d+) '
                     r'rollUnits=(\S+) spinUnits=(\S+) recent=(\d) stuntScore=(-?\d+) stuntMult=(-?\d+) '
                     r'comboMult=(-?\d+) comboScore=(\S+)')
RE_COMBO = re.compile(r'\[stunt\] combo banked score=(-?\d+) mult=(-?\d+) total=(-?\d+)')
RE_LAND = re.compile(r'\[stuntair\] land n=(\d+) .*completedRollDeg=(\S+) rolls=(-?\d+) complete=\S+ crashing=(\d)')


def bits(v):
    v = int(v)
    return '+'.join(STUNT_BITS.get(i, str(i)) for i in range(32) if v >> i & 1) or '-'


def fnum(s):
    try:
        return float(s)
    except ValueError:
        return float('nan')


def parse(path):
    jumps = []          # one dict per lever takeoff
    cur = None
    combos = []
    banks = []
    held = []
    last_state = None
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for ln, line in enumerate(fh, 1):
            if '[stunt23]' not in line and '[stunt]' not in line and '[stuntair]' not in line \
                    and '[sweep]' not in line:
                continue
            m = RE_LEVER_TO.search(line)
            if m:
                cur = {'jump': int(m.group(1)), 'line': ln, 'tilt': fnum(m.group(2)), 'turned': None,
                       'lever': None, 'landed': False, 'crash': None, 'phys_roll_deg': None,
                       'rated_roll': False, 'awesome_roll': False, 'max_roll_units': 0.0,
                       'land_frame': None, 'clear_frame': None, 'held': False,
                       'bank': None, 'combo_end': None, 'mult_before': None}
                jumps.append(cur)
                continue
            m = RE_LEVER_DONE.search(line)
            if m and cur is not None and int(m.group(1)) == cur['jump']:
                cur['turned'] = fnum(m.group(2))
                cur['lever'] = 'done'
                continue
            m = RE_LEVER_END.search(line)
            if m and cur is not None and int(m.group(1)) == cur['jump']:
                if cur['lever'] is None:
                    cur['lever'] = m.group(2)
                    cur['turned'] = fnum(m.group(3))
                continue
            m = RE_LAND.search(line)
            if m and cur is not None and not cur['landed']:
                cur['landed'] = True
                cur['crash'] = int(m.group(4))
                cur['phys_roll_deg'] = fnum(m.group(2))
                continue
            m = RE_STATE.search(line)
            if m:
                st = {'held': bool(m.group(1)), 'f': int(m.group(2)), 'air': int(m.group(3)),
                      'rot': (fnum(m.group(4)), fnum(m.group(5)), fnum(m.group(6))),
                      'rollMax': fnum(m.group(7)), 'inProg': int(m.group(9)), 'combo': int(m.group(10)),
                      'types': int(m.group(12)), 'awe': int(m.group(13)), 'mult': int(m.group(18)),
                      'sinceLand': int(m.group(21)), 'wheels': m.group(22), 'line': ln}
                if st['held']:
                    held.append(st)
                if cur is not None:
                    if cur['mult_before'] is None:
                        cur['mult_before'] = st['mult']
                    cur['max_roll_units'] = max(cur['max_roll_units'], abs(st['rot'][2]), st['rollMax'])
                    if st['types'] >> 1 & 1:
                        cur['rated_roll'] = True
                    if st['awe'] >> 1 & 1:
                        cur['awesome_roll'] = True
                    if last_state is not None and last_state['air'] == 1 and st['air'] == 0 \
                            and cur['land_frame'] is None:
                        cur['land_frame'] = st['f']
                    rot_zero = st['rot'] == (0.0, 0.0, 0.0)
                    if cur['land_frame'] is not None and cur['clear_frame'] is None and rot_zero \
                            and st['air'] == 0:
                        cur['clear_frame'] = st['f']
                    if st['held']:
                        cur['held'] = True
                last_state = st
                continue
            m = RE_BANK.search(line)
            if m:
                b = {'valid': int(m.group(1)), 'types': int(m.group(2)), 'awe': int(m.group(3)),
                     'spins': int(m.group(4)), 'rolls': int(m.group(5)), 'rollUnits': fnum(m.group(6)),
                     'recent': int(m.group(8)), 'stuntScore': int(m.group(9)),
                     'stuntMult': int(m.group(10)), 'comboMult': int(m.group(11)),
                     'comboScore': fnum(m.group(12)), 'line': ln,
                     'jump': cur['jump'] if cur is not None else None}
                banks.append(b)
                if cur is not None and cur['bank'] is None:
                    cur['bank'] = b
                continue
            m = RE_COMBO.search(line)
            if m:
                c = {'score': int(m.group(1)), 'mult': int(m.group(2)), 'total': int(m.group(3)), 'line': ln}
                combos.append(c)
                if cur is not None and cur['combo_end'] is None and cur['bank'] is not None:
                    cur['combo_end'] = c
                continue
    return jumps, banks, combos, held


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    want_verdict = '--verdict' in argv
    quiet = '--quiet' in argv
    jumps, banks, combos, held = parse(path)

    full = []
    for j in jumps:
        clean_full = (j['lever'] == 'done' and j['turned'] is not None and j['turned'] >= 330.0
                      and j['landed'] and j['crash'] == 0)
        j['clean_full'] = clean_full
        if clean_full:
            full.append(j)
        if not quiet:
            b = j['bank']
            c = j['combo_end']
            clear = (j['clear_frame'] - j['land_frame']) if (j['clear_frame'] is not None
                                                             and j['land_frame'] is not None) else None
            print('JUMP %d: lever=%s turned=%sdeg landed=%s crash=%s physRoll=%sdeg | scorer maxRollUnits=%.1f '
                  'rated=%d awesome=%d rotClearFrames=%s held=%d | bank=%s | comboEnd=%s%s'
                  % (j['jump'], j['lever'], ('%.0f' % j['turned']) if j['turned'] is not None else '-',
                     int(j['landed']), j['crash'], j['phys_roll_deg'], j['max_roll_units'],
                     int(j['rated_roll']), int(j['awesome_roll']), clear, int(j['held']),
                     ('types=%s awe=%s rolls=%d spins=%d stuntScore=%d stuntMult=%d comboMult=%d'
                      % (bits(b['types']), bits(b['awe']), b['rolls'], b['spins'], b['stuntScore'],
                         b['stuntMult'], b['comboMult'])) if b else '-',
                     ('score=%d mult=%d' % (c['score'], c['mult'])) if c else '-',
                     '  <-- CLEAN FULL ROLL' if clean_full else ''))
    if not quiet:
        print('BANKS %d, COMBO ENDS %d (scored %d), HELD lines %d'
              % (len(banks), len(combos), sum(1 for c in combos if c['score'] > 0), len(held)))

    if not want_verdict:
        return 0

    fails = []
    if not full:
        fails.append('no clean full-turn lever roll in the log')
    for j in full:
        tag = 'jump %d' % j['jump']
        if j['held']:
            fails.append(tag + ': HELD (rotation still live 90 frames after touchdown)')
        if j['land_frame'] is not None and j['clear_frame'] is None:
            fails.append(tag + ': scorer rotation never cleared after touchdown')
        b = j['bank']
        if b is None:
            fails.append(tag + ': never banked')
        else:
            if not (b['types'] >> 1 & 1):
                fails.append(tag + ': banked without the BARREL_ROLL bit')
            if not (b['awe'] >> 1 & 1) or b['rolls'] < 1:
                fails.append(tag + ': banked but not as an AWESOME roll (awe=%s rolls=%d)' % (bits(b['awe']), b['rolls']))
            if b['stuntMult'] < 1 or b['comboMult'] < 2:
                fails.append(tag + ': multiplier did not go up (stuntMult=%d comboMult=%d)' % (b['stuntMult'], b['comboMult']))
        c = j['combo_end']
        if c is None:
            fails.append(tag + ': no combo end after the bank')
        elif c['score'] <= 0 or c['mult'] < 2:
            fails.append(tag + ': combo ended without the roll (score=%d mult=%d)' % (c['score'], c['mult']))
    first_roll_bank = next((b for b in banks if b['types'] >> 1 & 1 and b['rolls'] >= 1), None)
    later = [b for b in banks if first_roll_bank is not None and b['line'] > first_roll_bank['line']
             and b['valid'] == 1 and b['stuntScore'] > 0]
    if first_roll_bank is not None and not later:
        fails.append('no stunt scored after the first roll bank')

    summary = ('clean full rolls %d; banks %d; later-scored banks %d; combo ends %s'
               % (len(full), len(banks), len(later),
                  ','.join('%d/x%d' % (c['score'], c['mult']) for c in combos[:8])))
    print('SUMMARY ' + summary + ((' | ' + '; '.join(fails)) if fails else ''))
    print('VERDICT ' + ('PASS' if not fails else 'FAIL'))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
