"""Read-only full-byte reconciliation of CRC game chunks and saved native JSON."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zlib

import phase_transport_v5 as transport
import trial_capture_v5 as host


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    folder = args.report.resolve().parent
    raw_report = args.report.read_bytes()
    report = json.loads(raw_report)
    gate = json.loads((folder / 'gate.json').read_bytes())
    assert report['completed'] and report['restored'] and not report['cleanup_errors']
    assert report['transport_preflight']['crc32'] == 'cbf43926'
    assert report['transport_preflight']['engine'] == '3.10.0.420447'
    assert report['runtime_and_host_unchanged'] is True
    chunks = {}
    metadata = {}
    releases = {}
    for row in gate['RPCs']:
        script = folder / ('rpc-%04d.py' % row['number'])
        assert digest(script.read_bytes()) == row['sha256'] and row['acknowledged']
        result = json.loads((folder / ('rpc-%04d-result.json' % row['number'])).read_bytes())
        if not isinstance(result, dict):
            continue
        schema = result.get('schema')
        if schema == 'wire-complete-phase-byte-export-v5-crc32':
            key = result['phase_key']
            assert key not in metadata
            metadata[key] = result
        elif schema == 'wire-complete-phase-chunk-v5-crc32':
            key = (result['phase_key'], result['index'])
            assert key not in chunks
            chunks[key] = result
        elif result.get('released') is True:
            key = result['phase_key']
            assert key not in releases
            releases[key] = result
    phases = []
    used_chunks = set()
    total_records = 0
    for number in range(1, 13):
        receipt_path = folder / ('phase-%02d-transport.json' % number)
        receipt = json.loads(receipt_path.read_bytes())
        raw = (folder / receipt['original_json_path']).read_bytes()
        meta = receipt['metadata']
        key = meta['phase_key']
        assert metadata[key] == meta
        assert len(raw) == meta['bytes'] and '%08x' % (zlib.crc32(raw) & 0xffffffff) == meta['crc32']
        assert digest(raw) == receipt['host_original_json_sha256']
        collector = transport.Collector(meta)
        for index in range(meta['chunks']):
            identity = key, index
            collector.add(chunks[identity])
            used_chunks.add(identity)
        reconstructed, original = collector.finish()
        assert reconstructed == raw and receipt['chunks'] == collector.receipts
        assert releases[key] == receipt['release']
        expected = copy.deepcopy(original)
        host.host_wires(expected)
        native_path = folder / ('phase-%02d-native.json' % number)
        native_raw = native_path.read_bytes()
        assert json.loads(native_raw) == expected
        retirement_row = report['observer_retirement']['phase_files'][number - 1]
        assert retirement_row['path'] == native_path.name
        assert retirement_row['sha256'] == digest(native_raw)
        assert retirement_row['records'] == receipt['native_records'] == len(original['records'])
        total_records += len(original['records'])
        phases.append({'phase': number, 'key': key, 'original_bytes': len(raw),
                       'game_crc32': meta['crc32'], 'host_original_json_sha256': digest(raw),
                       'chunks': meta['chunks'], 'actual_native_records': len(original['records']),
                       'original_bytes_equal_reconstructed_actual_RPC_chunks': True,
                       'all_original_fields_preserved_in_separate_native_JSON': True})
    assert len(metadata) == len(releases) == len(phases) == 12
    assert set(chunks) == used_chunks
    assert total_records == report['observer_retirement']['record_count']
    result = {'schema': 'wire-r27-actual-crc32-full-byte-reconciliation-v5', 'passed': True,
              'report_sha256': digest(raw_report), 'fixture': report['fixture'],
              'actual_game_crc32_preflight': report['transport_preflight'],
              'actual_RPC_chunk_count': len(chunks), 'actual_native_records': total_records,
              'phases': phases, 'runtime_calls': 0, 'MC_started': False,
              'GPU_qualified': False, 'manual_closures': 0,
              'SHA256_origin': 'host-derived after complete actual game CRC32 chunk reconstruction'}
    assert not args.output.exists()
    with args.output.open('xb') as stream:
        stream.write((json.dumps(result, indent=2) + '\n').encode('ascii'))
    print(json.dumps({'passed': True, 'phases': 12, 'chunks': len(chunks),
                      'records': total_records, 'output_sha256': digest(args.output.read_bytes())}))


if __name__ == '__main__':
    main()
