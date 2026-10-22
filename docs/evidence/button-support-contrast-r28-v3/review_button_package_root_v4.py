"""Independent R28 T02 package, original-image and exact-release review."""
import ast
import base64
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import lzma
from pathlib import Path
import sys
import zlib

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '.runtime/round-20261023'
HOST = RUN / 'button-support-contrast-v3'
PACKAGE = HOST / 'closeout-v1/candidate-evidence'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def same_except_redaction(original, stored, path='$'):
    if type(original) is dict:
        assert type(stored) is dict and set(original) == set(stored), path
        if set(original) == {'codec', 'base64', 'bytes'}:
            assert original == stored, path
            return
        for key in original:
            sensitive = key.lower().replace('-', '_') in {
                'token', 'api_key', 'apikey', 'authorization', 'password', 'secret',
                'access_key', 'mcp_url', 'access_token', 'refresh_token', 'client_secret'}
            sensitive = sensitive or (key == 'host_run_token' and stored[key] == '[REDACTED]')
            if sensitive:
                assert stored[key] == '[REDACTED]', path
            else:
                same_except_redaction(original[key], stored[key], path + '.' + key)
    elif type(original) is list:
        assert type(stored) is list and len(original) == len(stored), path
        for index, pair in enumerate(zip(original, stored)):
            same_except_redaction(*pair, path + '[' + str(index) + ']')
    else:
        assert type(original) is type(stored) and original == stored, path


def check_index(base, index):
    chunks = defaultdict(list)
    totals = {'files': 0, 'raw_unchanged': 0, 'sanitized_whole_JSON': 0, 'reassembled_JSON': 0}
    for relative, row in index['files'].items():
        path = (base / relative).resolve()
        assert path.is_relative_to(base.resolve())
        data = path.read_bytes()
        assert sha(data) == row['stored_sha256'] and len(data) == row['bytes'] < 240000
        source = Path(row['source_path']).read_bytes()
        assert sha(source) == row['source_sha256']
        decoded = lzma.decompress(data) if row.get('lossless_storage') == 'xz' else data
        expected_content = row.get('content_sha256', row.get('sanitized_content_sha256', row['source_sha256']))
        assert sha(decoded) == expected_content
        totals['files'] += 1
        if 'chunk_index' in row:
            chunks[row['chunked_JSON_name']].append((row, decoded))
        elif row.get('sanitized_JSON_copy_not_original', False):
            same_except_redaction(json.loads(source), json.loads(decoded))
            totals['sanitized_whole_JSON'] += 1
        else:
            assert decoded == source
            totals['raw_unchanged'] += 1
    for name, values in chunks.items():
        values.sort(key=lambda pair: pair[0]['chunk_index'])
        assert [row['chunk_index'] for row, unused in values] == list(range(values[0][0]['chunk_count']))
        offset = 0
        for row, data in values:
            assert row['uncompressed_offset'] == offset and row['uncompressed_bytes'] == len(data)
            offset += len(data)
        combined = b''.join(data for row, data in values)
        assert sha(combined) == values[0][0]['complete_JSON_content_sha256']
        same_except_redaction(read(Path(values[0][0]['source_path'])), json.loads(combined))
        totals['reassembled_JSON'] += 1
    return totals


def thaw(tree):
    tag, *tail = tree
    if tag == 'null':
        assert not tail
        return None
    value, = tail
    if tag == 'bool':
        assert type(value) is bool
        return value
    if tag == 'int': return int(value)
    if tag == 'float': return float.fromhex(value)
    if tag == 'bytes': return base64.b64decode(value, validate=True)
    if tag == 'text': return value
    if tag == 'list': return [thaw(item) for item in value]
    if tag == 'tuple': return tuple(thaw(item) for item in value)
    assert tag == 'dict', tag
    return {thaw(key): thaw(item) for key, item in value}


def wire(value):
    assert set(value) == {'codec', 'base64', 'bytes'}
    assert value['codec'] in ('cell.freeze-repr-utf8-base64', 'cell.freeze-repr-utf8-zlib-base64')
    raw = base64.b64decode(value['base64'], validate=True)
    if value['codec'].endswith('-zlib-base64'): raw = zlib.decompress(raw)
    assert len(raw) == value['bytes']
    return thaw(ast.literal_eval(raw.decode('utf8')))


index = read(PACKAGE / 'index.json')
assert sha((PACKAGE / 'index.json').read_bytes()) == 'b404655516aeb0170a850fe7dfbb930f3fc35fe1649772a9d410f95921630f26'
archive_totals = check_index(PACKAGE, index)
v2_totals = check_index(PACKAGE / 'v2-failed', read(PACKAGE / 'v2-failed/original-package-index.json'))
assert archive_totals['files'] == 104
analysis = read(HOST / 'closeout-v1/analysis/pixel-analysis.json')
roi = (577, 242, 714, 452)
assert analysis['ROI'] == list(roi)
images = {}
for label, row in analysis['originals'].items():
    path = HOST / ('check/button_pair_' + label + '.png')
    assert sha(path.read_bytes()) == row['sha256']
    with Image.open(path) as image:
        assert image.size == (1280, 720)
        images[label] = image.convert('RGB').crop(roi)
measurements = {}
for name, expected in analysis['comparisons'].items():
    left, right = name.split('__vs__')
    difference = ImageChops.difference(images[left], images[right])
    pixels = list(difference.getdata())
    count = sum(any(pixel) for pixel in pixels)
    bbox = difference.getbbox()
    bbox = None if bbox is None else [bbox[0] + roi[0], bbox[1] + roi[1], bbox[2] + roi[0], bbox[3] + roi[1]]
    maximum = max(max(pixel) for pixel in pixels)
    total = sum(sum(pixel) for pixel in pixels)
    assert (count, bbox, maximum, total) == (
        expected['changed_pixels'], expected['changed_bbox_in_original_image'],
        expected['maximum_channel_delta'], expected['sum_absolute_channel_delta']), name
    measurements[name] = {'ROI_changed_pixels': count, 'bbox_in_original': bbox, 'max_RGB_delta': maximum, 'sum_RGB_delta': total}

report = read(HOST / 'check/report.json')
pair = report['button_separate']
assert report['completed'] and report['restored'] and report['source_unchanged']
assert pair['completed'] and pair['all60_restored'] and len(pair['creations']) == 4 and len(pair['stages']) == 6
models = {}
names = set()
for row in pair['creations']:
    before, after = wire(row['deserialize_input']), wire(row['native_serialized'])
    assert before == after and row['name'] == row['result'] and row['unsupported_mode'] == 0
    models[row['label']] = after
    names.add(row['name'])
assert len(names) == 4
for material in ('stone', 'white'):
    remainder = dict(models['combined_' + material])
    remainder[b'common'] = dict(remainder[b'common'])
    remainder[b'states'] = dict(remainder[b'states'])
    assert remainder[b'common'].pop((b'minecraft:stone_button', 0)) == [827]
    assert remainder[b'states'].pop((b'minecraft:stone_button', 0)) == {b'button_pressed_bit': False, b'facing_direction': 0}
    assert remainder == models['support_' + material]
for kind in ('combined', 'support'):
    stone = dict(models[kind + '_stone'])
    stone[b'common'] = dict(stone[b'common'])
    assert stone[b'common'].pop((b'minecraft:stone', 0)) == [1083]
    stone[b'common'][(b'minecraft:white_concrete', 0)] = [1083]
    stone[b'states'] = dict(stone[b'states'])
    assert stone[b'states'].pop((b'minecraft:stone', 0)) == {}
    stone[b'states'][(b'minecraft:white_concrete', 0)] = {}
    assert stone == models[kind + '_white']
for row in pair['stages']:
    state = row['latest_state']
    assert state['settled_gate'] and state['frame_opportunities'] >= 6 and .25 <= state['age'] <= 2.
    drawing, = state['stage']['drawings']
    assert drawing['result'] is True and drawing['params']['block_geometry_model_name'] in names
    assert drawing['slot'] == 0 and state['surface_visibility'] == [True, False]
    assert row['capture']['sha256'] == analysis['originals'][row['label']]['sha256']
release = read(HOST / 'owned-release.json')
assert sha((HOST / 'owned-release.json').read_bytes()) == 'a24ba360c057f1181af69df8775f480dfc7d04f82292f063e376937d04fa91bf'
assert release['completed'] and release['source_unchanged'] and release['registry_state'] == 'stopped'
identities = []
for kind, row in release['independent_identities'].items():
    current = process_identity(row['pid'])
    assert current != row['expected']
    identities.append({'kind': kind, 'pid': row['pid'], 'expected': row['expected'], 'current': current})
receipt = {
    'at': datetime.now(timezone.utc).isoformat(), 'completed': True,
    'package_index_sha256': sha((PACKAGE / 'index.json').read_bytes()),
    'all_original_archive_sources_rehashed': archive_totals, 'nested_V2_sources_rehashed': v2_totals,
    'actual_typed_native_inputs_and_Serialize_independently_decoded': 4,
    'six_actual_Render_calls_and_settle_gates_checked': True,
    'PIL_independent_original_ROI_measurements': measurements,
    'root_original_images_visually_opened': list(analysis['originals']),
    'original_object_ROI_only_not_full_screenshot_RGB_identity': True,
    'support_material_change_renames_common_key_and_corresponding_empty_states_key': True,
    'root_preparation_notes': [
        'Nested V2 index uses original-package-index.json and sanitized_content_sha256, not the V3 schema.',
        'V2 also redacted diagnostic host_run_token nonces; V3 preserves those non-credential source nonces.',
        'Initial A/B comparison changed common but omitted the corresponding empty states material key; corrected the independent decoder assertion, not candidate or original native input.',
    ],
    'exact_owned_release_rechecked': identities, 'manual_issues_closed': 0,
    'correct_thickness_contact_or_native_UV_or_GPU_path_qualified': False,
}
target = HOST / 'root-package-review-v1.json'
assert not target.exists()
target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf8')
print(json.dumps({'completed': True, 'archive_files': archive_totals['files'], 'nested_V2_files': v2_totals['files'],
                  'original_image_ROI_comparisons': len(measurements), 'native_models': len(models),
                  'exact_release': identities, 'receipt_sha256': sha(target.read_bytes())}))
