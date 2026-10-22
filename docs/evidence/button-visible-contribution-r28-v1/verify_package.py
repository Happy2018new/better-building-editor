"""Verify this portable small package without runtime folders, MC or sockets."""
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import sys
from PIL import Image

HERE = Path(__file__).resolve().parent
index = json.loads((HERE / 'index.json').read_bytes())
rows = {row['path']: row for row in index['entries']}


def read(name):
    row = rows[name]
    stored = (HERE / name).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == row['stored_sha256']
    assert len(stored) == row['stored_bytes'] < 240000
    content = lzma.decompress(stored) if row['compression'] == 'xz' else stored
    assert hashlib.sha256(content).hexdigest() == row['content_sha256']
    assert len(content) == row['content_bytes']
    if not row['declared_redactions']:
        assert hashlib.sha256(content).hexdigest() == row['original_sha256']
    return content


def proof(name):
    if name not in rows:
        name += '.xz'
    return json.loads(read(name))


def sensitive(key):
    return 'token' in key.lower() or key.lower() in ('api_key', 'authorization', 'mcp_url', 'password', 'secret', 'access_key')


def clean(value):
    if isinstance(value, dict):
        for key, item in value.items():
            assert not sensitive(key) or item == '[REDACTED]'
            clean(item)
    elif isinstance(value, list):
        for item in value:
            clean(item)
    elif isinstance(value, str) and value.strip()[:1] in ('{', '['):
        try:
            parsed = json.loads(value)
        except ValueError:
            return
        clean(parsed)


for name in rows:
    content = read(name)
    if '.json' in name:
        clean(json.loads(content))
sys.path.insert(0, str(HERE / 'proof'))
from lineage_host import decode

for rawname, serial, support in [('0022', 60, True), ('0025', 61, False), ('0028', 60, True)]:
    raw = proof('proof/r27-' + rawname + '.json')
    record = next(row for row in raw['lineage']['records'] if row['serial'] == serial)
    native = decode(record['deserialize_input'])
    assert decode(record['native_serialized']) == native
    assert native[b'volume'] == (16, 16, 10) and native[b'eliminateAir'] is True and native[b'void'] is False
    expected = {(b'minecraft:stone_button', 0): [827]}
    if support:
        expected[(b'minecraft:stone', 0)] = [1083]
    assert native[b'common'] == expected and not native[b'extra'] and not native[b'actor']
report = proof('proof/r28-button-separate-report.json')
for record in report['creations']:
    native = decode(record['deserialize_input'])
    assert native == decode(record['native_serialized'])
    assert native[b'volume'] == (16, 16, 10)
    if record['label'] == 'combined':
        assert native[b'common'] == {(b'minecraft:stone_button', 0): [827], (b'minecraft:stone', 0): [1083]}
    if record['label'] == 'support':
        assert native[b'common'] == {(b'minecraft:stone', 0): [1083]}
images = {}
for stem in ('button_pair_full_baseline', 'button_pair_support_before', 'button_pair_support_after', 'button_pair_original_source_restored', 'pair_B_single_y3'):
    name = 'originals/' + stem + '.png'
    assert rows[name]['qualification'] == 'exact_original'
    metadata = proof('originals/' + stem + '.capture.json')
    assert metadata['ok'] and metadata['background_safe'] and metadata['native_resolution']
    assert metadata['sha256'] == hashlib.sha256(read(name)).hexdigest()
    image = Image.open(HERE / name).convert('RGB')
    assert image.size == (1280, 720)
    images[stem] = image
roi = (577, 242, 714, 452)
assert images['button_pair_full_baseline'].crop(roi).tobytes() == images['button_pair_original_source_restored'].crop(roi).tobytes()
assert images['button_pair_support_before'].crop(roi).tobytes() == images['button_pair_support_after'].crop(roi).tobytes()
nonzero = high = inside = 0
for y in range(roi[1], roi[3]):
    for x in range(roi[0], roi[2]):
        point = (x, y)
        delta = max(abs(images['button_pair_full_baseline'].getpixel(point)[i] - images['button_pair_support_before'].getpixel(point)[i]) for i in range(3))
        nonzero += delta > 0
        high += delta > 12
        if delta > 12 and max(abs(images['pair_B_single_y3'].getpixel(point)[i] - (247, 249, 252)[i]) for i in range(3)) > 20:
            inside += 1
assert (nonzero, high, inside) == (264, 82, 82)
assert index['manual_issues_closed'] == 0 and not index['pixels_qualified']
print(json.dumps({'passed': True, 'original_pngs': 5, 'all_files_below_240000': True,
    'original_native_inputs_checked': True, 'ROI_nonzero_gt12_inside': [nonzero, high, inside],
    'manual_issues_closed': 0, 'MC_started': False}))
