"""Bundle immutable before/after native rewrite reports with their file hashes."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; preserve evidence and choose a new path')
    before, after = args.before.read_bytes(), args.after.read_bytes()
    positive = json.loads(after)
    result = {'schema_version': 1, 'game_version': positive['game_version'],
              'palette_sha256': positive['palette_sha256'],
              'aux_values': [0,1,2,3],
              'rules': {'minecraft:decorated_pot': {'dry': [['minecraft:air',0],['minecraft:air',0]],
                                                   'wet': [['minecraft:oak_fence',0]]}},
              'scope': 'Decorated pot four directions, typed NBT dry/wet rewrites only; other native entities are unverified; visual acceptance is separate',
              'report_sha256': {'before': hashlib.sha256(before).hexdigest(),
                                'after': hashlib.sha256(after).hexdigest()},
              'before': json.loads(before), 'after': positive}
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
