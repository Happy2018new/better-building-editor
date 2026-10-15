"""Freeze structurally verified native content samples for public blueprints."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import zlib

ROOT = Path(__file__).resolve().parents[1]


def output(source):
    raw = source.read_bytes()
    data = json.loads(raw)
    if (data.get('schema') != 1 or data.get('engine_version') != '3.10.0.420447' or
            data.get('native_runtime_version') != '1.21.130.0' or data.get('completed') is not True or
            data.get('restoration', {}).get('restored') is not True):
        raise ValueError('Content sample needs native version, successful use and restoration')
    for row in data['observations']:
        if not all(row['uses']):
            raise ValueError('Content source contains failed item use')
    rows = base64.b64encode(zlib.compress(json.dumps(data['observations'], ensure_ascii=True,
            sort_keys=True, separators=(',', ':')).encode('ascii'), 9)).decode('ascii')
    return ('"""Generated native 3.10 slot samples; pixels remain independently gated."""\n'
            'SCHEMA_VERSION = 1\nENGINE_VERSION = \'3.10.0.420447\'\n'
            'SOURCE_SHA256 = '+repr(hashlib.sha256(raw).hexdigest())+'\n'
            'ROWS = '+repr(rows)+'\n').encode('ascii')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    generated = output(args.source)
    target = ROOT/'behavior_pack/modern_projection/projection/visible_item_slot_data.py'
    if args.check:
        if target.read_bytes() != generated:
            raise SystemExit('Native item slot data is stale')
    else:
        target.write_bytes(generated)
