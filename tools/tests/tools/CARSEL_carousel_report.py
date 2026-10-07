"""CARSEL_carousel_report.py -- lane CARSEL (GW4): junkyard carousel A/B report.

Reads every run dir of the junkyard_carousel (pre-stream ON) and junkyard_carousel_noprestream
(pre-stream withheld) cases under scratch\\bugtest\\runs and prints, per run:
  * the carousel action-69 requests (count / selectable),
  * the per-car-change wait "[carsel] car change done ... secondsSinceRequest=<s>" (game seconds
    from the change request to the car being streamed in and dropped onto the podium),
  * the number of streamer adds into carousel slots 1..7 before the junkyard exit,
then the mean change wait per side.

Run (from the repo root):
  C:\\Python310\\python.exe tools\\tests\\tools\\CARSEL_carousel_report.py [--runs <dir>] [--last N]
"""
import argparse
import os
import re
import statistics

RE_DONE = re.compile(r'\[carsel\] car change done car=(\d+) modScreen=(\d) secondsSinceRequest=([-\d.eE+]+)')
RE_REQ = re.compile(r'\[carsel\] carousel action69 car=(\S+)\s+listIndex=(-?\d+) selectable=(\d+) count=(\d+)')
RE_ADD = re.compile(r'STRM: Adding racecar for streaming: car=([1-7]), model=(\S+)')
RE_EXIT = re.compile(r'=== CarSelectManager: Start Exit state')


def scan(log_path):
    waits, reqs, adds = [], [], 0
    exited = False
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = RE_DONE.search(line)
            if m and m.group(2) == '0':
                waits.append(float(m.group(3)))
                continue
            m = RE_REQ.search(line)
            if m:
                reqs.append((m.group(1), int(m.group(3)), int(m.group(4))))
                continue
            if not exited and RE_ADD.search(line):
                adds += 1
                continue
            if RE_EXIT.search(line):
                exited = True
    return waits, reqs, adds


def main():
    ap = argparse.ArgumentParser()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    ap.add_argument('--runs', default=os.path.join(root, 'scratch', 'bugtest', 'runs'))
    ap.add_argument('--last', type=int, default=0, help='only the newest N runs per case (0 = all)')
    args = ap.parse_args()

    for case in ('junkyard_carousel', 'junkyard_carousel_noprestream'):
        cdir = os.path.join(args.runs, case)
        if not os.path.isdir(cdir):
            print(f'{case}: no runs')
            continue
        runs = sorted(d for d in os.listdir(cdir) if os.path.isdir(os.path.join(cdir, d)))
        if args.last:
            runs = runs[-args.last:]
        all_waits = []
        print(f'== {case}')
        for r in runs:
            log = os.path.join(cdir, r, 'flow', 'BrnGame.log')
            if not os.path.isfile(log):
                continue
            waits, reqs, adds = scan(log)
            all_waits += waits
            req_s = ', '.join(f'{c}/{n}' for _, n, c in reqs) or '-'
            wait_s = ', '.join(f'{w:.2f}' for w in waits) or '-'
            print(f'  {r}: requests(count/selectable)=[{req_s}] slot1..7 adds={adds} change waits s=[{wait_s}]')
        if all_waits:
            print(f'  mean change wait {statistics.mean(all_waits):.3f} s over {len(all_waits)} change(s)'
                  f' (min {min(all_waits):.2f}, max {max(all_waits):.2f})')


if __name__ == '__main__':
    main()
