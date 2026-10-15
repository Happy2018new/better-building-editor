"""Install one reversible bitmap override in this pack, preserving native files."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ATLAS_PATH = 'textures/blocks/flower_rose'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(plan_path, snapshot, opaque=False):
    if snapshot.exists():
        raise ValueError('Marker snapshot must be fresh')
    plan_raw = plan_path.read_bytes()
    plan = json.loads(plan_raw)
    if plan['texture_source']['atlas_path'] != ATLAS_PATH:
        raise ValueError('Marker target differs from the declared poppy texture')
    source = Path(plan['texture_source']['installed_path'])
    raw = source.read_bytes()
    if digest(raw) != plan['texture_source']['sha256']:
        raise ValueError('Native marker texture source changed')
    target = ROOT / 'resource_pack' / (ATLAS_PATH + '.png')
    before = target.read_bytes() if target.is_file() else None
    with Image.open(source) as native:
        native = native.convert('RGBA')
        if native.size != (16, 16):
            raise ValueError('Marker requires the predeclared 16x16 texture')
        alpha = native.getchannel('A')
    descriptor = plan['marker_descriptor']
    image = Image.new('RGBA', (16, 16), tuple(descriptor['base_rgb']) + (255,))
    draw = ImageDraw.Draw(image)
    for region in descriptor['regions_in_order']:
        draw.rectangle(region['bounds'], fill=tuple(region['rgb']) + (255,))
    if not opaque:
        image.putalpha(alpha)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate = snapshot.with_name(snapshot.stem + '_candidate.png')
    if candidate.exists():
        raise ValueError('Marker candidate archive must be fresh')
    image.save(candidate)
    record = {'schema': 1, 'project': str(ROOT), 'target': str(target),
              'plan': {'path': str(plan_path.resolve()), 'sha256': digest(plan_raw)},
              'native_source': {'path': str(source), 'sha256': digest(raw)},
              'mode': 'opaque_envelope' if opaque else 'native_alpha_preserved',
              'native_alpha_sha256': digest(alpha.tobytes()),
              'candidate_alpha_sha256': digest(image.getchannel('A').tobytes()),
              'before_hex': before.hex() if before is not None else None,
              'candidate': {'path': str(candidate.resolve()), 'sha256': digest(candidate.read_bytes())},
              'production_acceptance': False}
    snapshot.write_text(json.dumps(record, ensure_ascii=True, indent=2) + '\n', encoding='utf8')
    target.write_bytes(candidate.read_bytes())
    return record


def validate_marker(snapshot, plan_path, stage):
    record = json.loads(snapshot.read_bytes())
    target = ROOT / 'resource_pack' / (ATLAS_PATH + '.png')
    mode = 'native_alpha_preserved' if stage == 'alpha_marker' else 'opaque_envelope'
    if (record['schema'] != 1 or Path(record['project']).resolve() != ROOT or
            Path(record['target']).resolve() != target or record['mode'] != mode):
        raise ValueError('Marker snapshot project, target or stage differs')
    if record['plan']['sha256'] != digest(plan_path.read_bytes()):
        raise ValueError('Marker plan changed since preparation')
    candidate = Path(record['candidate']['path'])
    expected = record['candidate']['sha256']
    if digest(candidate.read_bytes()) != expected or digest(target.read_bytes()) != expected:
        raise ValueError('Marker candidate or pack override changed')
    if (stage == 'alpha_marker' and
            record['candidate_alpha_sha256'] != record['native_alpha_sha256']):
        raise ValueError('Marker did not preserve native alpha')
    return record


def restore(snapshot):
    record = json.loads(snapshot.read_bytes())
    target = Path(record['target'])
    if record['schema'] != 1 or Path(record['project']).resolve() != ROOT:
        raise ValueError('Marker snapshot belongs to another project')
    if target.resolve() != ROOT / 'resource_pack/textures/blocks/flower_rose.png':
        raise ValueError('Marker restore target differs from the declared plant')
    if digest(target.read_bytes()) != record['candidate']['sha256']:
        raise ValueError('Marker candidate changed; refuse to overwrite')
    before = record['before_hex']
    if before is None:
        target.unlink()
    else:
        target.write_bytes(bytes.fromhex(before))
    return {'restored': True, 'target': str(target), 'snapshot': str(snapshot.resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--opaque', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if not args.restore and args.plan is None:
        parser.error('--plan is required before preparation')
    record = restore(args.snapshot) if args.restore else prepare(args.plan, args.snapshot, args.opaque)
    print(json.dumps({key: value for key, value in record.items() if key != 'before_hex'}))


if __name__ == '__main__':
    main()
