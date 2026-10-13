"""Bounded R15 runtime and offline scorer; only a bound owner may execute."""
from copy import deepcopy
import argparse
import importlib
import json
from pathlib import Path
import sys
import time

import prepare_client_anchor_depth_candidate_r15 as candidate


ROOT = candidate.ROOT
ENTITIES = ROOT.parent / 'r11-entities'
sys.path.append(str(ENTITIES / 'tools'))
PINS = {'probe_client_anchor_paper_doll': '2d93d4314e49dadc4bbe6e93b40c9b6c1e7e0ec5ab7b0c3304072f6ba8366a85',
        'probe_native_item_paper_doll': '7d4496ef5d616998d281a802c1dff3ef343808c1e6c1e9f4a26f49a7daf00e1a',
        'execute_frame_item_translation': '7b3d7db8e5d25da97a7b8018a83f40eddc100e0d4c44977581ea98a0ce2a2662',
        'flat_frame_item_visual_checks': '4c479f79ce14d6bd98b899b60d2ebe00351d4ef1d4d64d81c59db9c1c52b0315',
        'verify_snow_plant_visibility': '89840f5f94959b10c608fe3a5a4a8fcecf254a155625a26775f88320191710d4'}


def dependencies():
    modules = {}
    for name, expected in PINS.items():
        choices = [base / 'tools' / (name + '.py') for base in (ROOT, ENTITIES)]
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        if path not in [value.resolve() for value in choices] or candidate.digest(path.read_bytes()) != expected:
            raise ValueError('Pinned actual runtime helper changed: ' + name)
        modules[name] = module
    return modules


def layout_readback(anchor, tree, status, initial):
    # R14's exact layout validator has one fixed -50 prop. Validate the new -15
    # prop explicitly before adapting that one expectation; preserve real props.
    copied, pending, dolls = deepcopy(tree), [], []
    pending.append(copied)
    while pending:
        node = pending.pop()
        pending.extend(node.get('children', []))
        if node.get('key') == 'native_item_probe_doll':
            dolls.append(node)
    if len(dolls) != 1 or dolls[0].get('props', {}).get('renderDepth') != -15:
        raise ValueError('Candidate initial native PaperDoll props changed')
    dolls[0]['props']['renderDepth'] = -50
    result = anchor.layout_readback(copied, status, initial)
    result['props']['renderDepth'] = -15
    return result


def cow_pixels(frame):
    from PIL import Image, ImageChops
    from flat_frame_item_visual_checks import capture_payload
    from verify_snow_plant_visibility import count
    with Image.open(capture_payload(frame['capture'])) as source:
        image = source.convert('RGB').crop(tuple(positive_roi(frame)))
    background = Image.new('RGB', image.size, (247, 249, 252))
    diff = ImageChops.difference(image, background)
    channels = [channel.point(lambda value: 255 if value > 25 else 0) for channel in diff.split()]
    return count(ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2]))


def positive_roi(frame):
    # The prospectively excluded y<111 debug clock crosses the upper PaperDoll
    # bounds. Use the same fixed exclusion for cow controls and sword scoring.
    doll, fixed = frame['paper_doll_roi'], frame['fixed_roi']
    roi = [max(doll[0], fixed[0]), max(doll[1], fixed[1]),
           min(doll[2], fixed[2]), min(doll[3], fixed[3])]
    if roi[0] >= roi[2] or roi[1] >= roi[3]:
        raise ValueError('Candidate positive-control ROI is empty')
    return roi


def validate_state(label, status, initial, native, binding_id):
    expected = dict(initial['ui_params'])
    expected['render_depth'] = -50 if label == 'ui_plain_depth50' else -15
    if label.startswith('ui_cow_'):
        del expected['entity_id']
        expected.update(entity_identifier='minecraft:cow', init_rot_y=60.)
    if (status['control'] != label or status['last_submission'] != expected or
            status['ui_params'] != initial['ui_params'] or
            status['attachments'] != native['attachments'] or
            native['control'] != label or native['actor'] != initial['actor'] or
            native['journal'] != status['journal']):
        raise ValueError('Candidate actual submission or attachment readback changed')
    renders = [row for row in native['journal'] if row['operation'] == 'RenderEntity:' + label]
    if len(renders) != 1 or renders[0].get('state') != 'returned' or renders[0].get('value') is not True:
        raise ValueError('Candidate native RenderEntity result changed')
    attachments = status['attachments']
    if label in ('ui_cow_positive', 'ui_empty'):
        if attachments or native['native_item'] is not None:
            raise ValueError('Unexpected item before the positive gate')
        return binding_id
    if len(attachments) != 1:
        raise ValueError('Exactly one owned attachment is required')
    row = attachments[0]
    identity = row['id']
    if type(identity) is not int or identity < 0 or (binding_id is not None and identity != binding_id):
        raise ValueError('Shared owned attachment identity changed')
    if (row['offset'] != [0., 0., 0.] or row['rotation'] != [0., 0., 0.] or
            row['scale'] != 1. or not row['item_nonmutation']):
        raise ValueError('Owned item parameters changed')
    plain = label in ('ui_plain_depth15', 'ui_plain_depth50', 'ui_plain_depth15_repeat')
    if plain:
        expected_item = {'id': identity, 'offset': [0., 0., 0.], 'rotation': [0., 0., 0.], 'scale': 1.}
        if row['state'] != 'bound' or native['native_item'] != expected_item or row.get('remove_attempted'):
            raise ValueError('Owned native binding readback changed')
    elif (row['state'] != 'removed' or row.get('remove_result') is not True or
          native['native_item'] is not None):
        raise ValueError('Owned binding restoration changed')
    return identity


def preflight(bundle, output):
    plan = candidate.verify(bundle)
    output = Path(output)
    paths = [output, output.with_name(output.name + '.tmp')]
    anchor = dependencies()['probe_client_anchor_paper_doll']
    for label in candidate.STATES:
        for index in range(2):
            shot = anchor.base.capture_path(output, label, index)
            paths.extend((shot, shot.with_suffix('.capture.json'), shot.with_suffix('.capture_error.json'),
                          shot.with_name(shot.name + '.tmp')))
    if any(path.exists() for path in paths):
        raise ValueError('Preserve previous depth runtime evidence')
    return plan


def score_probe(report, allow_partial=False):
    from PIL import Image
    from flat_frame_item_visual_checks import capture_payload
    from verify_snow_plant_visibility import count
    anchor = dependencies()['probe_client_anchor_paper_doll']
    if report.get('plan_sha256') != '533521976e014d1c7606010060c2ad111e40aac8b3f1dcea64cd8f58a720e55a':
        raise ValueError('Exact prospective candidate report plan changed')
    if not allow_partial and (not report.get('completed') or not report.get('restored') or report.get('cleanup_errors')):
        raise ValueError('Complete restored depth report required')
    images, doll_images, marker_passed, cow, binding_id = {}, {}, True, {}, None
    if list(report['states']) != list(candidate.STATES)[:len(report['states'])]:
        raise ValueError('Candidate prospective state ordering changed')
    last_clock, fixed = report['actor_ready']['clock'], None
    for label, row in report['states'].items():
        if label not in candidate.STATES:
            raise ValueError('Unknown candidate state')
        if len(row['frames']) != 2:
            raise ValueError('Two fresh frames per recorded candidate state required')
        images[label] = []
        doll_images[label] = []
        for frame in row['frames']:
            if frame['fixed_roi'] != [0, 111, 1994, 1105]:
                raise ValueError('Prospective UI ROI changed')
            status = frame['status']
            binding_id = validate_state(label, status, report['initial'], row['native'], binding_id)
            if status['clock'] <= last_clock:
                raise ValueError('Candidate capture clock did not advance')
            last_clock = status['clock']
            if (not status['camera_matches'] or not status['player_foot_matches'] or
                    status['actor'] != report['initial']['actor'] or not status['root_visible']):
                raise ValueError('Candidate capture identity or camera changed')
            layout = layout_readback(anchor, frame['tree'], status, report['initial'])
            if layout != frame['layout'] or (fixed is not None and layout != fixed):
                raise ValueError('Candidate frozen layout changed')
            fixed = layout
            mapping = anchor.base.marker_mapping(frame['capture'], layout, report['frozen_marker_calibration'])
            marker_passed = marker_passed and mapping['passed'] and mapping == frame['marker_mapping']
            if anchor.base.frame_crop(layout, frame['capture']['size'], mapping) != frame['paper_doll_roi']:
                raise ValueError('Native PaperDoll ROI changed')
            with Image.open(capture_payload(frame['capture'])) as source:
                if list(source.size) != [1994, 1105]:
                    raise ValueError('Native capture dimensions changed')
                images[label].append(source.convert('RGB').crop(tuple(frame['fixed_roi'])))
                doll_images[label].append(source.convert('RGB').crop(tuple(positive_roi(frame))))
        if label.startswith('ui_cow_'):
            cow[label] = [cow_pixels(frame) for frame in row['frames']]
    positive = marker_passed and cow and all(value >= 80 for values in cow.values() for value in values)
    score = {'schema': 1, 'ui_marker_gate_passed': marker_passed, 'cow_positive_pixels': cow,
             'positive_cow_gate_passed': bool(positive), 'classification': 'partial_controls',
             'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
             'shared_depth_accepted': False, 'enchantment_glint_accepted': False}
    if not all(label in images for label in candidate.STATES):
        return score
    references = images['ui_empty'] + images['ui_empty_restored']
    values = {label: count(anchor.stable_difference(images[label], references)) for label in
              ('ui_plain_depth15', 'ui_plain_depth50', 'ui_plain_depth15_repeat')}
    restored = count(anchor.stable_difference(images['ui_empty_restored'], images['ui_empty']))
    doll_empty = doll_images['ui_empty'] + doll_images['ui_empty_restored']
    cow_stable = {label: count(anchor.stable_difference(doll_images[label], doll_empty))
                  for label in ('ui_cow_positive', 'ui_cow_positive_restored')}
    controls_valid = positive and restored < 80 and all(value >= 80 for value in cow_stable.values())
    if not controls_valid:
        classification = 'invalid_controls'
    elif values['ui_plain_depth15'] >= 80 and values['ui_plain_depth15_repeat'] >= 80 and values['ui_plain_depth50'] < 80:
        classification = 'depth15_positive_depth50_zero_repeat_positive_requires_visual_review'
    elif all(value < 80 for value in values.values()):
        classification = 'custom_anchor_ui_zero_with_ordinary_renderer_positive'
    else:
        classification = 'paired_depth_observation_requires_visual_review'
    score.update(stable_plain_pixels=values, restored_difference_pixels=restored, stable_cow_pixels=cow_stable,
                 classification=classification, visual_review_required=True)
    return score


def execute_probe(bundle, output, check, guard, deadline):
    modules = dependencies()
    executor, anchor = modules['execute_frame_item_translation'], modules['probe_client_anchor_paper_doll']
    plan = preflight(bundle, output)
    output, bundle = Path(output), Path(bundle)
    runtime = executor.BoundedRuntime(check, guard, deadline)
    runtime.capture_adapter()
    report = {'schema': 1, 'plan_sha256': candidate.digest((bundle / 'plan.json').read_bytes()),
              'completed': False, 'restored': False, 'sdk_dispatch_attempted': False,
              'states': {}, 'errors': [], 'cleanup_errors': [], 'production_rendering_accepted': False,
              'editor_frame_content_accepted': False, 'shared_depth_accepted': False, 'enchantment_glint_accepted': False}
    original_run, original_wait = check.run, check.wait
    def preserve():
        try:
            executor.save_report(output, report)
        except Exception as error:
            report['cleanup_errors'].append('report persistence: ' + repr(error))
            report['restored'] = False
            if not runtime.cleanup:
                raise

    def run(name):
        report['attempted_operation'] = name
        preserve()
        return check.run((bundle / name).read_text(encoding='ascii'))

    preserve()
    try:
        check.run, check.wait = runtime.run, runtime.wait
        report['sdk_dispatch_attempted'] = True
        report['initial'] = run('install_client.py')
        report['actor_ready'] = runtime.wait('owned root', lambda row: row['ready'], lambda: run('actor_ready_client.py'))
        report['ui_opened'] = run('open_ui_client.py')
        runtime.wait('mounted candidate UI', lambda row: row['ready'], lambda: run('status_client.py'))
        last_clock, frozen, fixed, binding_id = report['actor_ready']['clock'], None, None, None
        for label in candidate.STATES:
            row = report['states'][label] = {'state': 'pending', 'frames': []}
            row['native'] = run(label + '_client.py')
            time.sleep(min(.2, runtime.remaining()))
            for index in range(2):
                status = runtime.wait(label, lambda value: value['ready'], lambda: run('status_client.py'))
                binding_id = validate_state(label, status, report['initial'], row['native'], binding_id)
                tree = check.command('dump_tree')['tree']
                if (status['control'] != label or status['clock'] <= last_clock or
                        status['actor'] != report['initial']['actor'] or not status['root_visible'] or
                        not status['camera_matches'] or not status['player_foot_matches'] or
                        status['ui_params'] != report['initial']['ui_params']):
                    raise ValueError('Candidate identity, camera or clock changed')
                layout = layout_readback(anchor, tree, status, report['initial'])
                if fixed is None:
                    fixed = layout
                elif layout != fixed:
                    raise ValueError('Candidate native UI layout changed')
                capture = runtime.capture(anchor.base.capture_path(output, label, index))
                frame = {'status': status, 'tree': tree, 'capture': capture,
                         'fixed_roi': [0, 111, 1994, 1105], 'layout': layout}
                row['frames'].append(frame)
                preserve()
                mapping = anchor.base.marker_mapping(capture, layout, frozen)
                if not mapping['passed']:
                    raise ValueError('Candidate marker gate failed')
                if frozen is None:
                    frozen = report['frozen_marker_calibration'] = mapping['calibration']
                frame['marker_mapping'] = mapping
                frame['paper_doll_roi'] = anchor.base.frame_crop(layout, capture['size'], mapping)
                last_clock = status['clock']
                preserve()
                if index == 0:
                    time.sleep(min(.4, runtime.remaining()))
            row['state'] = 'captured'
            if label == 'ui_cow_positive':
                report['positive_gate'] = score_probe(report, allow_partial=True)
                if not report['positive_gate']['positive_cow_gate_passed']:
                    raise ValueError('Ordinary cow positive control failed before sword binding')
            preserve()
        report['completed'] = True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        runtime.cleanup = True
        for key, name in (('cleanup_remove', 'remove_client.py'),):
            try:
                report[key] = run(name)
                if isinstance(report[key], dict):
                    report['cleanup_errors'].extend(report[key]['errors'])
            except Exception as error:
                report['cleanup_errors'].append(key + ': ' + repr(error))
        try:
            runtime.wait('owned transition settled', lambda row: not row['owned'] or not row['transition'], lambda: run('navigation_client.py'))
            report['cleanup_pop'] = run('pop_client.py')
            runtime.wait('owned page absent', lambda row: not row['transition'] and not row['contains_owned'], lambda: run('navigation_client.py'))
        except Exception as error:
            report['cleanup_errors'].append('owned page: ' + repr(error))
        try:
            report['cleanup_destroy'] = run('destroy_client.py')
        except Exception as error:
            report['cleanup_errors'].append('owned destroy: ' + repr(error))
        try:
            report['actor_absence'] = runtime.wait('owned actor absent', lambda row: row['absent'], lambda: run('absent_client.py'))
            report['restore'] = run('verify_client.py')
            report['restored'] = report['restore'].get('restored') is True and not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append('restore verification: ' + repr(error))
        check.run, check.wait = original_run, original_wait
        preserve()
    return report


def main():
    parser = argparse.ArgumentParser(description='Offline score only; no SDK calls or capture')
    parser.add_argument('report')
    parser.add_argument('--output', required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() or output.with_name(output.name + '.tmp').exists():
        raise ValueError('Preserve existing score evidence')
    source = Path(args.report)
    score = score_probe(json.loads(source.read_bytes()), args.allow_partial)
    score.update(runtime_report={'path': str(source.resolve()), 'sha256': candidate.digest(source.read_bytes())},
                 scorer_sha256=candidate.digest(Path(__file__).read_bytes()))
    dependencies()['execute_frame_item_translation'].save_report(output, score)
    print(json.dumps(score))


if __name__ == '__main__':
    main()
