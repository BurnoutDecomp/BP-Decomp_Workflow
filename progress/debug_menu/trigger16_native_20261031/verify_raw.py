"""Join retained native triplets, frame ACKs, CSV rows and original bytes."""
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.with_name('trigger16_prepare_20261031_v3')
RUN = PACKAGE / 'runs/trigger16_62206_20261031_211806_f27e59a0ed0f48fb9b116360133e84c3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    result = read(RUN / 'driver-result.json')
    raw = (RUN / 'flow/BrnGame.log').read_bytes()
    lines = re.sub(r'\r+\n', '\n', raw.decode('utf-8-sig')).splitlines()
    assert not any(re.search(r'\[ASSERT(?:\s+\d+)?\]|\[EXCEPTION\]', s) for s in lines)
    proofs = list(read(RUN / 'NATURAL_BASELINE.json')['readbacks'])
    for phase in result['phases']:
        assert sha(phase['command_file']) == phase['command_sha256']
        proofs.extend(phase['proofs'])
    joins = set()
    for row in proofs:
        before, value, after = row['ack_before'], row['value_line'], row['ack_after']
        assert value == before + 1 and after == before + 2
        expected = row['alias'] + ': /' + row['path']
        assert lines[before] == lines[after] == expected
        assert lines[value].strip() == row['display_value']
        joins.add((before, value, after, row['alias'], row['path']))
    frames = []
    for row in result['frames']:
        path = Path(row['path'])
        assert sha(path) == row['sha256']
        data = path.read_bytes()
        assert data[:2] == b'BM'
        width, height = struct.unpack_from('<ii', data, 18)
        assert (width, abs(height)) == (1280, 720)
        assert len(data) == row['bytes'] <= 3686454
        assert row['pid'] == result['process_id'] and row['slot'] == 62206
        assert lines[row['ack_index']] == row['ack']
        ack = re.fullmatch(r'\[frame-request\] pid=(\d+) slot=(\d+) seq=(\d+) present=(\d+) file=(bb_\d{6}\.bmp)', row['ack'])
        assert ack and tuple(map(int, ack.groups()[:4])) == (result['process_id'], 62206, row['sequence'], row['present'])
        assert ack[5] == path.name
        csv_lines = Path(row['csv_path']).read_text(encoding='utf-8-sig').splitlines()
        csv = [s for s in csv_lines if s.startswith(str(row['present']) + ',')]
        assert csv == [row['csv_row']]
        frames.append({k: row[k] for k in ('phase', 'path', 'sha256', 'sequence', 'present')})
    assert len(frames) == 51 and sorted(r['sequence'] for r in frames) == list(range(1, 52))
    report = {'pass': True, 'run': str(RUN), 'game_log_sha256': hashlib.sha256(raw).hexdigest(),
              'raw_triplet_proofs': len(proofs), 'unique_raw_triplets': len(joins), 'frame_hash_ack_csv_joins': 51,
              'command_files_verified': len(result['phases']), 'zero_asserts_exceptions': True,
              'original_case_result_unchanged': sha(RUN / 'result.json'), 'frames': frames, 'site_credit': 0}
    (HERE / 'RAW_JOINS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print({k: v for k, v in report.items() if k != 'frames'})


if __name__ == '__main__':
    main()
