"""Finite runtime adapter for the reviewed frame bundle; CLI only validates.

The frame owner supplies an already bound SignCheck and swapped SessionPackStage.
Importing or running this file never opens a client, stages a pack or calls SDK.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace
import uuid

from verify_frame_item_translation import check_bundle

PLAN_SHA256 = 'eb874b326b4def3dc39639f138cbb52281f9d99c3aeb884c15f6969e64ad4673'
CAPTURE_WRAPPER_SHA256 = 'b008a23aaf53411e2fdda2752d43f2b4c219cfbb9b22ceff3cefa973b9c92754'

SNAPSHOT = '''from modern_projection.projection.widgets import Theme
from modern_projection.projection import static_frame_item_data
from modern_projection.projection.bridge import _stable_palette
def frame_translation_walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for descendant in frame_translation_walk(child):yield descendant
fibers=list(frame_translation_walk(navigator.top._host._root_fiber))
registries=[fiber.props['registry'] for fiber in fibers
 if fiber.key is not None and str(fiber.key).startswith('tile_') and 'registry' in fiber.props]
assert registries and all(registry is registries[0] for registry in registries)
rows=[]
for key,entry in sorted(registries[0].items()):
 dolls,surfaces,preview=entry
 rows.append({'key':key,'pose':preview.poses[preview.front],
  'geometry':getattr(preview,'geometry',None),'packet':getattr(preview,'tint_color',None),
  'clip_offset':getattr(preview,'clip_offset',None),'pending':preview.pending,
  'front_visible':preview.visible[preview.front]})
assert rows and all(row['pose'] is not None and row['packet'] is not None and
 row['geometry'] is not None and row['pending'] is None and row['front_visible'] for row in rows)
_result=json.dumps({'camera':dict((key,getattr(s,key)) for key in
 ('camera_pose','camera_pivot','camera_pan','camera_depth_pose')),
 'scene_size':s.scene_size,'scene_origin':s.scene_origin,'theme_scale':Theme.scale,
 'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),'previews':rows,
 'palettes':[row for row in sys._frame_translation_palettes if row['nonce']==sys._blueprint_qa_nonce]})
'''

SAVE_RUNTIME = '''from modern_projection.projection import static_frame_item_data
from modern_projection.projection.bridge import _stable_palette
assert not any(hasattr(sys,key) for key in ('_frame_translation_runtime_saved',
 '_frame_translation_factory_saved','_blueprint_qa_saved','_frame_editor_profiles_saved'))
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
sys._frame_translation_runtime_saved={'owner_nonce':%r,'document':s.editor.document.to_data(),
 'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),'factory_id':id(b.factory),
 'workspace':navigator.contains('modern_projection_workspace'),
 'camera':dict((key,getattr(s,key)) for key in
 ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))}
_result=json.dumps(sys._frame_translation_runtime_saved)
'''

VERIFY_RESTORE = '''from modern_projection.projection import static_frame_item_data
from modern_projection.projection.bridge import _stable_palette
saved=sys._frame_translation_runtime_saved
actual={'owner_nonce':saved['owner_nonce'],'document':s.editor.document.to_data(),'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'factory_id':id(b.factory),'workspace':navigator.contains('modern_projection_workspace'),
 'camera':dict((key,getattr(s,key)) for key in
 ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))}
assert actual==saved,(saved,actual)
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
assert not any(hasattr(sys,key) for key in ('_frame_translation_factory_saved',
 '_frame_translation_palettes','_blueprint_qa_saved','_frame_editor_profiles_saved',
 '_frame_editor_control','_frame_editor_transforms'))
del sys._frame_translation_runtime_saved
_result=json.dumps(actual)
'''


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def literal_snippets(path, names):
    tree = ast.parse(path.read_text(encoding='utf8'))
    found = {target.id: ast.literal_eval(node.value)
             for node in tree.body if isinstance(node, ast.Assign)
             for target in node.targets if isinstance(target, ast.Name) and target.id in names}
    if set(found) != set(names) or any(not isinstance(value, str) for value in found.values()):
        raise ValueError('Frozen trace snippets changed: ' + str(path))
    return found


def preflight(bundle, output):
    output = Path(output).absolute()
    if output.exists() or output.with_name(output.name + '.tmp').exists():
        raise ValueError('Preserve existing runtime evidence')
    paths = [output, output.with_name(output.name + '.tmp')]
    bundle = Path(bundle).resolve(strict=True)
    plan = check_bundle(bundle)
    if digest((bundle / 'plan.json').read_bytes()) != PLAN_SHA256:
        raise ValueError('Executor requires the reviewed final-v1 plan')
    for phase in plan['control_matrix']:
        for control in phase['controls']:
            shot = output.with_name(output.stem + '_' + phase['phase'] + '_' + control + '_native.png')
            paths.extend((shot, shot.with_suffix('.capture.json')))
    if any(path.exists() for path in paths):
        raise ValueError('Preserve existing runtime evidence')
    trace = literal_snippets(bundle / 'sources/tools/trace_flat_frame_editor.py',
                             ('LOAD', 'SAVE', 'RESTORE_PROFILES', 'INSTALL_CONTROLS'))
    trace.update(literal_snippets(bundle / 'sources/tools/verify_debug_blueprints.py',
                                  ('INSTALL_PROBE', 'RESTORE', 'STATUS')))
    trace.update(literal_snippets(bundle / 'sources/tools/flat_frame_item_visual_checks.py', ('SWITCH',)))
    generated = {row['path']: row for row in plan['generated']}
    return bundle, output, plan, trace, generated


def save_report(path, report):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='ascii') as target:
        json.dump(report, target, ensure_ascii=True, indent=2)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())
    temporary.replace(path)


class BoundedRuntime:
    def __init__(self, check, stage, deadline, clock=time.monotonic):
        self.check, self.stage, self.deadline, self.clock = check, stage, deadline, clock
        self.normal_deadline = deadline - 30.
        self.cleanup = False
        self.original_run = check.run

    def remaining(self):
        remaining = (self.deadline if self.cleanup else self.normal_deadline) - self.clock()
        if remaining <= 0:
            raise TimeoutError('Finite frame diagnostic budget exhausted')
        return remaining

    def run(self, code):
        self.remaining()
        self.stage.guard()
        # Client.call performs a binding read followed by the requested RPC.
        self.check.client.timeout = min(10., self.remaining() / 2.)
        self.check.client.frame_dispatch_deadline = self.deadline if self.cleanup else self.normal_deadline
        return self.original_run(code)

    def wait(self, label, predicate, read):
        until = min(self.clock() + 10., self.deadline if self.cleanup else self.normal_deadline)
        while self.clock() < until:
            result = read()
            if predicate(result):
                return result
            time.sleep(min(.1, self.remaining()))
        raise TimeoutError('Readiness budget exhausted: ' + label)

    def capture_process(self, command, **options):
        self.stage.guard()
        options['timeout'] = min(10., self.remaining())
        # run() kills and waits its direct child when the timeout expires.
        return subprocess.run(command, **options)

    def capture_adapter(self):
        helper = Path(self.check.native_capture_helper).resolve(strict=True)
        if helper != self.stage.source.parent / 'tools/capture_native_window.py':
            raise ValueError('Unexpected native capture wrapper path')
        payload = helper.read_bytes()
        if digest(payload) != CAPTURE_WRAPPER_SHA256:
            raise ValueError('Native capture Python wrapper changed')
        executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
        if digest(executable.read_bytes()) != self.stage.plan['finite_execution']['capture_helper_sha256']:
            raise ValueError('Native WGC executable changed')
        module = ModuleType('reviewed_frame_native_capture')
        module.__file__ = str(helper)
        exec(compile(payload, str(helper), 'exec'), module.__dict__)
        module.subprocess = SimpleNamespace(run=self.capture_process,
                                            CREATE_NO_WINDOW=subprocess.CREATE_NO_WINDOW)
        return module, executable

    def capture(self, path):
        from PIL import Image, ImageStat
        self.stage.guard()
        self.remaining()
        helper, executable = self.capture_adapter()
        started = time.time()
        receipt = helper.capture(self.stage.plan['session_file'], self.stage.plan['owner'], path, executable)
        payload = path.read_bytes()
        if (not receipt.get('ok') or not receipt.get('reliable') or
                receipt.get('backend') != 'Windows.Graphics.Capture' or
                not receipt.get('background_only') or not receipt.get('native_resolution') or
                Path(receipt['path']).resolve() != path.resolve() or
                receipt['sha256'] != digest(payload) or receipt['bytes'] != len(payload) or
                receipt.get('owner') != self.stage.plan['owner'] or
                receipt.get('game_pid') != self.stage.plan['game']['pid'] or
                receipt.get('game_identity') != self.stage.plan['game']['identity'] or
                Path(receipt['session_file']).resolve() != Path(self.stage.plan['session_file']).resolve()):
            raise ValueError('Native capture receipt is invalid')
        with Image.open(path) as image:
            size, variance = list(image.size), ImageStat.Stat(image.convert('RGB')).var
            if image.format != 'PNG' or size != [1994, 1105] or max(variance) <= 1.:
                raise ValueError('Native capture framing or pixels changed')
        self.stage.guard()
        return {'path': str(path), 'sha256': digest(payload), 'bytes': len(payload),
                'size': size, 'mime': 'image/png', 'capture': receipt,
                'host_capture_requested_epoch': started}


def palette_bytes(snapshot):
    rows = snapshot['palettes']
    if len(rows) != 1:
        raise ValueError('Expected exactly one final native Combine palette')
    row = rows[0]
    encoded = row['canonical'].encode('utf8')
    if (row['state'] != 'returned' or not row.get('result') or
            row['native_palette_nonmutation'] is not True or digest(encoded) != row['sha256'] or
            row['volume'] != [8, 8, 17]):
        raise ValueError('Native palette contract failed')
    return encoded


def guarded(code, attribute):
    return "_result=True\nif hasattr(sys,%r):\n" % attribute + ''.join(' ' + line + '\n' for line in code.splitlines())


def verify_native_sources(stage, plan):
    root = stage.source.parent
    for row in plan['sources']:
        if row.get('native_baseline_source'):
            payload = (root / row['source']).read_bytes()
            if len(payload) != row['bytes'] or digest(payload) != row['sha256']:
                raise ValueError('Native baseline source changed: ' + row['source'])


def score_runtime(bundle, report):
    """Offline pixel interpretation, called after owner's link restoration."""
    from PIL import ImageChops, ImageDraw
    from flat_frame_item_visual_checks import capture_payload, content_mask
    from verify_snow_plant_visibility import count
    bundle = Path(bundle).resolve(strict=True)
    baseline = json.loads((bundle / 'baseline.json').read_text(encoding='utf8'))
    crop = baseline['crop']
    controls = report['controls']
    required = ('native_baseline_combined', 'native_baseline_same_volume_body',
                'native_baseline_item_only', 'native_baseline_blank',
                'instrumented_nooffset_combined', 'instrumented_nooffset_item_only',
                'translated_combined', 'translated_same_volume_body',
                'translated_item_only', 'translated_blank', 'restored_combined', 'restored_item_only')
    result = {'production_rendering_accepted': False, 'enchantment_glint_accepted': False,
              'native_reload_visually_proven': False, 'restored_pixels_proven': False,
              'interpretation': 'inconclusive', 'comparisons': {}}
    if not report['completed'] or any(key not in controls or controls[key]['state'] != 'captured' for key in required):
        result['reason'] = 'The finite matrix did not complete'
        return result
    sources = {key: capture_payload(controls[key]['capture']) for key in required}

    def mask(first, second):
        sources[first].seek(0)
        sources[second].seek(0)
        return content_mask(sources[first], sources[second], crop, threshold=25)[1]

    pairs = {'native_combined_vs_body': ('native_baseline_combined', 'native_baseline_same_volume_body'),
             'translated_combined_vs_body': ('translated_combined', 'translated_same_volume_body'),
             'body_unchanged': ('translated_same_volume_body', 'native_baseline_same_volume_body'),
             'blank_unchanged': ('translated_blank', 'native_baseline_blank'),
             'nooffset_combined_unchanged': ('instrumented_nooffset_combined', 'native_baseline_combined'),
             'nooffset_item_unchanged': ('instrumented_nooffset_item_only', 'native_baseline_item_only'),
             'restored_combined_unchanged': ('restored_combined', 'native_baseline_combined'),
             'restored_item_unchanged': ('restored_item_only', 'native_baseline_item_only')}
    masks = {key: mask(*pair) for key, pair in pairs.items()}
    result['comparisons'] = {key: {'pixels': count(value), 'bbox_in_crop': value.getbbox()}
                             for key, value in masks.items()}
    old_item = mask('native_baseline_item_only', 'native_baseline_blank')
    shifted_item = mask('translated_item_only', 'translated_blank')
    old_body = mask('native_baseline_same_volume_body', 'native_baseline_blank')
    body_roi = old_body.getbbox()
    if body_roi is None:
        result['reason'] = 'Native body ROI is unavailable'
        return result

    def centroid(value):
        points = [(index % value.width, index // value.width)
                  for index, signal in enumerate(value.tobytes()) if signal]
        return ([sum(point[axis] for point in points) / float(len(points)) for axis in (0, 1)]
                if points else None)

    def outside(value):
        retained = value.copy()
        # PIL rectangles include their ending coordinate; the mask bbox does not.
        ImageDraw.Draw(retained).rectangle((body_roi[0], body_roi[1], body_roi[2] - 1, body_roi[3] - 1), fill=0)
        return count(retained)

    old_center, shifted_center = centroid(old_item), centroid(shifted_item)
    delta = ([shifted_center[axis] - old_center[axis] for axis in (0, 1)]
             if old_center is not None and shifted_center is not None else None)
    old_pixels, shifted_pixels = count(old_item), count(shifted_item)
    rigid_pixel_area = old_pixels >= 80 and .9 <= shifted_pixels / float(old_pixels) <= 1.1
    # +X projects right and up at the frozen 35/25 camera; allow raster error.
    expected_slope = .484807753 / 1.638304089
    direction = delta is not None and delta[0] > 1. and delta[1] < -1.
    slope_matches = direction and abs((-delta[1] / delta[0]) - expected_slope) <= .08
    result['item_only'] = {'native_pixels': old_pixels, 'translated_pixels': shifted_pixels,
                           'centroid_delta_pixels': delta, 'rigid_pixel_area': rigid_pixel_area,
                           'expected_screen_slope': expected_slope, 'slope_matches': slope_matches,
                           'translated_outside_original_body_roi': outside(shifted_item)}
    fixed = all(count(masks[key]) == 0 for key in ('body_unchanged', 'blank_unchanged',
                'nooffset_combined_unchanged', 'nooffset_item_unchanged'))
    result['native_reload_visually_proven'] = (fixed and rigid_pixel_area and slope_matches and
                                               outside(shifted_item) >= 80)
    result['restored_pixels_proven'] = all(count(masks[key]) == 0 for key in
                                           ('restored_combined_unchanged', 'restored_item_unchanged'))
    combined = masks['translated_combined_vs_body']
    intersection = count(ImageChops.multiply(combined, shifted_item))
    result['translated_combined'] = {'outside_original_body_roi': outside(combined),
                                    'pixels_matching_translated_item_only': intersection}
    if not (result['native_reload_visually_proven'] and result['restored_pixels_proven'] and
            report['runtime_restored'] and not report['cleanup_errors']):
        result['reason'] = 'A fixed-control, reload, or restoration gate failed'
    elif outside(combined) >= 80 and intersection >= 80:
        result['interpretation'] = 'Combined item triangles survive: investigate original overlap and draw/depth relationship'
    elif count(combined) == 0:
        result['interpretation'] = 'Translated item-only draws, combined does not: generation or routing suppression remains possible'
    else:
        result['reason'] = 'Translated combined changes do not establish the item silhouette'
    return result


def execute_runtime(bundle, output, check, shader_access, deadline):
    """Called once by the reviewed owner orchestrator after its staging swap.

    deadline is the absolute monotonic cleanup deadline, 150 seconds from the
    first staging mutation. Filesystem/link restoration remains the caller's duty.
    """
    from verify_debug_blueprints import editor_preview_ready
    bundle, output, plan, snippets, generated = preflight(bundle, output)
    verify_native_sources(shader_access, plan)
    runtime = BoundedRuntime(check, shader_access, deadline)
    nonce = uuid.uuid4().hex
    report = {'schema': 1, 'plan_sha256': PLAN_SHA256, 'owner_nonce': nonce, 'completed': False,
              'runtime_restored': False, 'production_rendering_accepted': False,
              'enchantment_glint_accepted': False, 'controls': {}, 'reloads': [],
              'errors': [], 'cleanup_errors': [], 'sdk_dispatch_attempted': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    save_report(output, report)
    original_run, original_wait = check.run, check.wait
    check.run, check.wait = runtime.run, runtime.wait
    comparisons = {}
    saved = None

    def retain_cleanup_report():
        try:
            save_report(output, report)
        except Exception as error:
            report['cleanup_errors'].append('retain cleanup report: ' + repr(error))

    def owned_cleanup(code, attribute):
        return guarded(code, attribute).replace('if hasattr(sys,',
            "if getattr(sys,'_frame_translation_runtime_saved',{}).get('owner_nonce')==%r and hasattr(sys," % nonce, 1)

    def reload_variant(name, label):
        runtime.remaining()
        payload = (bundle / name).read_bytes()
        shader_access.write_shader(payload, generated[name]['sha256'])
        report['sdk_dispatch_attempted'] = True
        row = {'phase': label, 'shader': name, 'state': 'pending'}
        report['reloads'].append(row)
        save_report(output, report)
        row['result'] = check.run((bundle / 'reload_shader_client.py').read_text(encoding='utf8'))
        row['state'] = 'returned'
        save_report(output, report)
        if row['result'] is not True:
            raise ValueError('Explicit shader reload failed: ' + label)

    def control(phase, name):
        from trace_flat_frame_editor import frame_submission
        label = phase + '_' + name
        row = report['controls'][label] = {'phase': phase, 'control': name, 'state': 'pending'}
        save_report(output, report)
        check.run("sys._frame_editor_control=%r\n_result=True" % name)
        check.run(snippets['SWITCH'] % True)
        loaded = row['loaded'] = check.run(snippets['LOAD'])
        if loaded['document'] != json.loads((bundle / 'document.json').read_text(encoding='ascii')):
            raise ValueError('Diagnostic document differs from frozen source')
        expected_pose = loaded['case']['isolated_camera']['editor']
        runtime.wait(label + ' fixed camera', lambda pose: pose == expected_pose,
                     lambda: check.run('_result=json.dumps(s.camera_pose)'))
        ready = runtime.wait(label, lambda state: editor_preview_ready(
            state, loaded['metadata'], loaded['editor_id'], loaded['document_id']),
            lambda: check.run(snippets['STATUS']))
        time.sleep(min(.15, runtime.remaining()))
        ready = runtime.wait(label + ' stable', lambda state: editor_preview_ready(
            state, loaded['metadata'], loaded['editor_id'], loaded['document_id']),
            lambda: check.run(snippets['STATUS']))
        row['ready'], row['submission'] = ready, frame_submission(ready)
        row['snapshot'] = snapshot = check.run(SNAPSHOT)
        canonical = palette_bytes(snapshot)
        paired = {key: snapshot[key] for key in ('camera', 'scene_size', 'scene_origin',
                                                 'theme_scale', 'profiles', 'previews')}
        prior = comparisons.setdefault(name, (canonical, paired))
        if (canonical, paired) != prior:
            raise ValueError('Palette, profile, camera or native pose changed between shader phases')
        save_report(output, report)
        shot = output.with_name(output.stem + '_' + label + '_native.png')
        row['capture'] = runtime.capture(shot)
        row['state'] = 'captured'
        save_report(output, report)

    try:
        report['sdk_dispatch_attempted'] = True
        save_report(output, report)
        saved = check.run(SAVE_RUNTIME % nonce)
        check.run((bundle / 'palette_capture_client.py').read_text(encoding='utf8'))
        check.run(snippets['INSTALL_PROBE'])
        check.run(snippets['SAVE'])
        check.run(snippets['INSTALL_CONTROLS'])
        check.run('owner.open_workspace()\n_result=True')
        runtime.wait('workspace opened', lambda nav: nav['open'] and not nav['transition'], check.navigation)
        for phase in plan['control_matrix']:
            reload_variant(phase['shader'], phase['phase'])
            for name in phase['controls']:
                control(phase['phase'], name)
        report['completed'] = True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        runtime.cleanup = True
        steps = [('retain final palette evidence', lambda: report.update(final_palettes=check.run(
                     '_result=json.dumps(getattr(sys,"_frame_translation_palettes",[]))'))),
                 ('original staged shader and reload', lambda: reload_variant('original.vertex', 'cleanup')),
                 ('profiles', lambda: check.run(owned_cleanup(snippets['RESTORE_PROFILES'], '_frame_editor_profiles_saved'))),
                 ('blueprint', lambda: check.run(owned_cleanup(snippets['RESTORE'], '_blueprint_qa_saved'))),
                 ('palette capture', lambda: check.run(owned_cleanup(
                     (bundle / 'restore_capture_client.py').read_text(encoding='utf8'),
                     '_frame_translation_factory_saved')))]
        for label, action in steps:
            try:
                action()
            except Exception as error:
                report['cleanup_errors'].append(label + ': ' + repr(error))
            retain_cleanup_report()
        try:
            if saved is None:
                saved = check.run('_result=json.dumps(getattr(sys,"_frame_translation_runtime_saved",None))')
                if saved is not None and saved.get('owner_nonce') != nonce:
                    saved = None
            if saved is not None and not saved['workspace'] and check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                runtime.wait('workspace closed', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
            if saved is not None:
                runtime.wait('camera restored', lambda value: value == saved['camera'], lambda: check.run(
                    '_result=json.dumps(dict((key,getattr(s,key)) for key in '
                    "('camera_pose','camera_pivot','camera_pan','camera_depth_pose')))") )
                report['restored_state'] = check.run(VERIFY_RESTORE)
                report['runtime_restored'] = not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append('verify runtime restore: ' + repr(error))
        check.run, check.wait = original_run, original_wait
        try:
            verify_native_sources(shader_access, plan)
            report['protected_sources_unchanged'] = True
        except Exception as error:
            report['cleanup_errors'].append('protected native sources: ' + repr(error))
            report['runtime_restored'] = False
        retain_cleanup_report()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    _, _, plan, _, _ = preflight(args.bundle, args.output)
    print(json.dumps({'validated': True, 'controls': sum(len(row['controls']) for row in plan['control_matrix']),
                      'sdk_dispatch_attempted': False, 'production_rendering_accepted': False}))


if __name__ == '__main__':
    main()
