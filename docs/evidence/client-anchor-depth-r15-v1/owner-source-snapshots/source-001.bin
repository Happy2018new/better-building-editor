"""Freeze an offline-only frame vertex discriminator; never connect to a game."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADER = 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex'
AFTER_PACKET = '    bool localContextActor = taggedWorld'
AFTER_DECODE = '    if (layoutPacket) logicalPosition.y -= logicalHeight*0.5;\n'
PREDICATE = '''    // Diagnostic only: the frozen 8x8x17 editor contains one item overlay.
    bool diagnosticFrameItem = layoutPacket && logicalHeight == 8.0 &&
        overlayBase == 9.0 && logicalPosition.y >= 8.5 && logicalPosition.y <= 16.5;
'''

# These snippets are emitted for review. This host tool never executes them.
PALETTE_CAPTURE = '''from modern_projection.projection.bridge import _stable_palette
import hashlib
assert not hasattr(sys, '_frame_translation_factory_saved')
sys._frame_translation_factory_saved = b.factory
sys._frame_translation_palettes = []
class FrameTranslationGeometryCapture(object):
 def __init__(self, target): self.target = target
 def __getattr__(self, name): return getattr(self.target, name)
 def CombineBlockPaletteToGeometry(self, palette, name, mode=0):
  data = palette.SerializeBlockPalette()
  canonical = repr(_stable_palette(data))
  row = {'name': name, 'mode': mode, 'nonce': sys._blueprint_qa_nonce,
   'control': sys._frame_editor_control, 'volume': data.get('volume'),
   'canonical_format': 'repr(_stable_palette(serialized_native_dict)).encode(utf8)',
   'canonical': canonical, 'sha256': hashlib.sha256(canonical.encode('utf8')).hexdigest(),
   'state': 'pending', 'native_palette_nonmutation': None}
  sys._frame_translation_palettes.append(row)
  try:
   result = self.target.CombineBlockPaletteToGeometry(palette, name, mode)
   row.update(state='returned', result=result)
  except Exception as error:
   row.update(state='failed', error=repr(error))
   raise
  finally:
   row['native_palette_nonmutation'] = repr(_stable_palette(palette.SerializeBlockPalette())) == canonical
  assert row['native_palette_nonmutation'], 'Native palette changed during Combine'
  return result
class FrameTranslationFactoryCapture(object):
 def __init__(self, target): self.target = target
 def __getattr__(self, name): return getattr(self.target, name)
 def CreateBlockGeometry(self, level):
  return FrameTranslationGeometryCapture(self.target.CreateBlockGeometry(level))
b.factory = FrameTranslationFactoryCapture(b.factory)
_result = True
'''
RESTORE_CAPTURE = '''b.factory = sys._frame_translation_factory_saved
del sys._frame_translation_factory_saved
del sys._frame_translation_palettes
_result = True
'''
RELOAD_SHADER = "_result = api.ReloadOneShader('modern_projection_biome_blocks.vertex')\n"


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')


def generated_shader(source, shift):
    if shift not in (0, 2):
        raise ValueError('Only the reviewed zero and two-block variants are supported')
    text = source.decode('utf8')
    if text.count(AFTER_PACKET) != 1:
        raise ValueError('The frozen virtual-Y decoder anchors changed')
    if 'diagnosticFrameItem' in text:
        raise ValueError('The input already contains a diagnostic')
    newline = '\r\n' if '\r\n' in text else '\n'
    decode = AFTER_DECODE.replace('\n', newline)
    if text.count(decode) != 1:
        raise ValueError('The frozen decoder newline changed')
    text = text.replace(AFTER_PACKET, PREDICATE.replace('\n', newline) + AFTER_PACKET, 1)
    text = text.replace(decode, decode +
                        ('    if (diagnosticFrameItem) logicalPosition.x += %.1f;\n' % shift).replace('\n', newline), 1)
    return text.encode('utf8')


def baseline_contract(report):
    if not report.get('completed') or not report.get('restored') or report.get('passed'):
        raise ValueError('Use the completed, restored, failing native baseline')
    if report.get('production_rendering_accepted') is not False:
        raise ValueError('Production acceptance must remain false')
    controls = report['controls']
    original = ('combined', 'body', 'combined_repeat', 'item_only', 'blank', 'positive')
    if any(name not in controls for name in original + ('same_volume_body',)):
        raise ValueError('The original six controls and same-volume body are required')
    expected = [
        {'material': ['minecraft:frame', 2], 'indices': [219]},
        {'material': ['modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0],
         'indices': [795]}]
    document = controls['combined']['loaded']['document']
    for name in ('combined', 'combined_repeat'):
        row = controls[name]
        if row['submission']['submitted_materials'] != expected or row['submission']['item_cells'] != 1:
            raise ValueError('The baseline frame/item placement changed')
        if row['submission']['layouts'] != [[[8, 8, 8], [8, 8, 17]]]:
            raise ValueError('The baseline logical/native volume changed')
        if row['loaded']['document'] != document or row['item_pixels'] != 0:
            raise ValueError('The baseline document or missing-item result changed')
    if controls['item_only']['geometry_pixels'] < 80 or controls['positive']['geometry_pixels'] < 80:
        raise ValueError('Baseline positive controls are unavailable')
    fixed = report['same_volume_body_diagnostic']
    if fixed['body_vs_same_volume_body']['pixels'] or any(
            row['pixels'] for row in fixed['combined_vs_same_volume_body'].values()):
        raise ValueError('Same-volume body is not the frozen zero-difference control')
    return document, original


def prepare(source_root, baseline_path, output, source_index_path=None):
    source_root, baseline_path, output = (path.resolve() for path in (source_root, baseline_path, output))
    if output.exists():
        raise ValueError('Preserve existing bundle: ' + str(output))
    baseline = baseline_path.read_bytes()
    report = json.loads(baseline)
    document, original = baseline_contract(report)
    paths = {name.replace('\\', '/') for name in report['source_sha256']}
    index_bytes = None
    indexed = []
    if source_index_path is not None:
        index_bytes = source_index_path.read_bytes()
        indexed = json.loads(index_bytes)['sources']
        paths.update(row['source'].replace('\\', '/') for row in indexed)
    baseline_paths = set(paths)
    paths.update(('resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment',
                  'tools/flat_frame_item_visual_contract.md',
                  'tools/verify_biome_shader.py',
                  'behavior_pack/modern_projection/projection/camera.py',
                  'behavior_pack/modern_projection/projection/debug_appearance_blueprints.py',
                  'behavior_pack/modern_projection/projection/appearance_defaults_data.py'))
    inputs = {}
    for name in sorted(paths):
        path = source_root / name
        if not path.is_file() and name not in baseline_paths:
            path = ROOT / name
        inputs[name] = path.read_bytes()
    for name, expected in report['source_sha256'].items():
        if sha256(inputs[name.replace('\\', '/')]) != expected:
            raise ValueError('Baseline source changed: ' + name)
    for row in indexed:
        if sha256(inputs[row['source'].replace('\\', '/')]) != row['sha256']:
            raise ValueError('Indexed native source changed: ' + row['source'])
    generated = {'original.vertex': inputs[SHADER],
                 'nooffset.vertex': generated_shader(inputs[SHADER], 0),
                 'translated.vertex': generated_shader(inputs[SHADER], 2),
                 'palette_capture_client.py': PALETTE_CAPTURE.encode('ascii'),
                 'restore_capture_client.py': RESTORE_CAPTURE.encode('ascii'),
                 'reload_shader_client.py': RELOAD_SHADER.encode('ascii'),
                 'baseline.json': baseline, 'document.json': json_bytes(document)}
    if index_bytes is not None:
        generated['baseline-source-index.json'] = index_bytes
    for path in (Path(__file__), ROOT / 'tools/verify_frame_item_translation.py',
                 ROOT / 'tests/test_frame_item_translation.py',
                 ROOT / 'docs/FRAME_ITEM_TRANSLATION_DIAGNOSTIC_R11.md'):
        inputs['preparation/' + path.relative_to(ROOT).as_posix()] = path.read_bytes()
    plan = {
        'schema': 1, 'scope': 'Editor-only two-block rigid vertex displacement discriminator',
        'production_rendering_accepted': False, 'sdk_dispatch_authorized': False,
        'source_root': str(source_root), 'baseline_report': str(baseline_path),
        'baseline_source_index': None if source_index_path is None else str(source_index_path.resolve()),
        'supplemental_offline_source_root': str(ROOT),
        'baseline_report_sha256': sha256(baseline), 'baseline_original_controls': original,
        'session_file': report['session_file'], 'owner': 'frame-r11-background',
        'fixture': {'public': 'test.entities.appearances', 'case': 'frame_filled',
                    'public_position': [21, 1, 19], 'isolated_focus': [3, 3, 3],
                    'logical_size': [8, 8, 8], 'native_volume_zxy': [8, 8, 17],
                    'frame_index': 219, 'item_index': 795, 'facing': 2, 'rotation': 0},
        'mapping': {'axis': 'decoded native model X', 'units': 'blocks', 'delta': [2., 0., 0.],
                    'packet': 8 + 9 * 256, 'logical_height': 8, 'native_height': 17,
                    'overlay_base': 9, 'predecode_y_inclusive': [8.5, 16.5],
                    'predicate_captured': 'after nativeHeight/2, before virtual-Y decoding',
                    'translation_applied': 'after logicalHeight/2, before WORLDVIEWPROJ and previewClip',
                    'changes_view_depth_at_nonzero_yaw': True,
                    'expected_screen_motion_per_cell_unit': [1.6383040886, .4848077530],
                    'expected_view_depth_motion_blocks': 1.0396735815,
                    'screen_prediction_source': 'OrbitCamera.basis, yaw35 pitch25; confirm native item-only pixels'},
        'control_matrix': [
            {'phase': 'native_baseline', 'shader': 'original.vertex',
             'controls': ['combined', 'same_volume_body', 'item_only', 'blank'], 'shift': 0},
            {'phase': 'instrumented_nooffset', 'shader': 'nooffset.vertex',
             'controls': ['combined', 'item_only'], 'shift': 0},
            {'phase': 'translated', 'shader': 'translated.vertex',
             'controls': ['combined', 'same_volume_body', 'item_only', 'blank'], 'shift': 2},
            {'phase': 'restored', 'shader': 'original.vertex',
             'controls': ['combined', 'item_only'], 'shift': 0}],
        'execution': {'status': 'pending root review; no execution entry point in this tool',
                      'loaded_shader_path': None, 'resolve_loaded_shader_before_dispatch': True,
                      'reject_loaded_shader_alias_to_repository': True,
                      'reload_api': 'clientApi.ReloadOneShader(modern_projection_biome_blocks.vertex)',
                      'reload_success_is_visual_proof': False,
                      'install_capture_before_blueprint_probe': True,
                      'restore_capture_after_blueprint_restore': True,
                      'capture': 'owner-bound fresh native-resolution WGC; foreground unchanged',
                      'all_auto_hot_reload_flags': False},
        'invariants': [
            'combined canonical bytes equal across all shader phases, including actor/state/extra data',
            'item_only canonical bytes equal across all shader phases; item index and volume retained',
            'full serialized native dict captured at final Combine boundary; native call does not mutate it',
            'document/profile/camera/render packet/scale/UI bounds unchanged for each paired control',
            'only provisional in-memory accepted flag changes required by existing six controls',
            'generated model/material/texture and native actor shaders unchanged',
            'translation stays within the frozen eight-block X extent: frame cell3 becomes item cell5'],
        'equality_format': 'repr(_stable_palette(serialized_native_dict)).encode(utf8); not a native mesh dump',
        'interpretation': {
            'item_only_must_move': '>=80 pixels, expected screen displacement, outside original body ROI',
            'combined_item_appears': 'item triangles survived Combine; overlap or draw/depth behavior remains',
            'combined_item_missing': 'with valid translated item-only, generation/routing suppression remains possible',
            'limitations': 'No result identifies native frame material or proves depth/Combine cause'},
        'restoration_required': [
            'restore exact loaded shader bytes and explicitly reload the original shader in finally',
            'fresh restored combined/item-only pixels reproduce baseline',
            'restore factory/workspace/editor/camera/profile snapshot and remove probe state',
            'all protected repository source hashes unchanged; no world writes or new entity owners',
            'record failed binding/reload/capture/restore without retrying or upgrading acceptance'],
        'acceptance_contract_sha256': sha256(inputs['tools/flat_frame_item_visual_contract.md']),
        'original_six_controls_unchanged': True,
        'sources': [{'source': name, 'path': 'sources/' + name,
                     'native_baseline_source': name in baseline_paths, 'bytes': len(payload),
                     'sha256': sha256(payload)} for name, payload in sorted(inputs.items())],
        'generated': [{'path': name, 'bytes': len(payload), 'sha256': sha256(payload)}
                      for name, payload in sorted(generated.items())]}
    output.mkdir(parents=True)
    for name, payload in inputs.items():
        target = output / 'sources' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    for name, payload in generated.items():
        (output / name).write_bytes(payload)
    (output / 'plan.json').write_bytes(json_bytes(plan))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--baseline-report', type=Path, required=True)
    parser.add_argument('--baseline-source-index', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(args.source_root, args.baseline_report, args.output, args.baseline_source_index)
    print(json.dumps({'plan': str((args.output / 'plan.json').resolve()),
                      'sources': len(plan['sources']), 'sdk_dispatch_authorized': False,
                      'production_rendering_accepted': False}))


if __name__ == '__main__':
    main()
