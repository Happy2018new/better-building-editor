"""Verify the exact player target and finite probe cleanup without a game."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import execute_frame_item_translation as executor
import probe_native_item_paper_doll as probe

RAW = ROOT / 'tools/data/native_item_contents_r11_raw.json'


def calibrated_test_mapping(layout, size, scale=2.):
    return {'passed': True, 'calibration': {'scale': scale, 'translation': [0., 0.],
                                          'physical_size': list(size)}}


def marker_capture(path, layout, scale=4., translation=(0., 0.), moved=None, missing=None, duplicate=None, resize=None):
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (1994, 1105), (247, 249, 252))
    draw = ImageDraw.Draw(image)
    for index, marker in enumerate(layout['native_readback']['markers']):
        if index == missing:
            continue
        rect = marker['rect']
        dx, dy = (moved or {}).get(index, (0., 0.))
        bounds = [round(rect['x'] * scale + translation[0] + dx),
                  round(rect['y'] * scale + translation[1] + dy),
                  round((rect['x'] + rect['width']) * scale + translation[0] + dx),
                  round((rect['y'] + rect['height']) * scale + translation[1] + dy)]
        if index in (resize or {}):
            bounds[2] += resize[index][0]
            bounds[3] += resize[index][1]
        draw.rectangle((bounds[0], bounds[1], bounds[2] - 1, bounds[3] - 1), fill=tuple(marker['rgb']))
        if index == duplicate:
            draw.rectangle((300, 300, 310, 310), fill=tuple(marker['rgb']))
    image.save(path)
    payload = path.read_bytes()
    record = {'path': str(path), 'sha256': probe.digest(payload), 'bytes': len(payload),
              'mime': 'image/png', 'size': [1994, 1105]}
    record['capture'] = dict(record, width=1994, height=1105, frame={'width': 1994, 'height': 1105})
    return record


def canonical(value):
    if isinstance(value, dict):
        return tuple((key, canonical(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(canonical(item) for item in value)
    return value


class NativeFixture:
    def __init__(self):
        self.binds, self.removes, self.renders = [], [], []
        self.bind_error, self.remove_error, self.bind_value = None, None, 40
        self.clock, self.frozen_clock = 100., False
        self.model_reads = 0
        self.push_error, self.transition_polls, self.pop_calls = None, 0, 0
        self.native_root = {'x': 0., 'y': 0., 'width': 997., 'height': 552.5, 'path': '/probe'}
        self.native_doll = {'x': 378.5, 'y': 156.25, 'width': 240., 'height': 240., 'path': '/probe/doll'}
        self.native_viewport = dict(self.native_root, path='/root')
        self.screen_observed, self.ref_calls = [997., 552.5], 0
        self.native_markers = []
        self.entries = [SimpleNamespace(key='modern_projection_workspace')]
        self.control = self.native_control(self.native_doll)
        self.control.asNeteasePaperDoll = lambda: self.doll
        self.root_control = self.native_control(self.native_root)
        self.viewport_control = self.native_control(self.native_viewport)
        self.host = SimpleNamespace(_root_path='/root', GetBaseUIControl=lambda path: self.viewport_control)
        self.doll = SimpleNamespace(RenderEntity=self.render, GetModelId=self.model_id)
        self.itemcomp = SimpleNamespace(BindItemToMinecraftModel=self.bind,
                                       SetBindBoneForBindItem=self.remove)
        self.player = 'native-player-123'
        self.factory = SimpleNamespace(CreateItem=lambda level: self.itemcomp,
                                       CreateGame=lambda level: SimpleNamespace(GetScreenSize=lambda: self.screen_observed,
                                           GetScreenViewInfo=lambda: [1995., 1107., 0., 0.]),
                                       CreateActorRender=lambda player: SimpleNamespace(
                                           GetQueryableBoneOrientation=lambda bone, client: [[1, 0, 0, 0]] * 4))
        self.nav = SimpleNamespace(is_transitioning=False, is_ready=True, top=self.entries[-1],
                                   get_entries=lambda: self.entries, push=self.push, pop=self.pop,
                                   contains=lambda key: any(entry.key == key for entry in self.entries))
        self.session = SimpleNamespace(busy=False, projection_active=False, camera_pose=[1, 2, 3],
                                       camera_pivot=[4, 5, 6], camera_pan=[7, 8], camera_depth_pose=0.,
                                       editor=SimpleNamespace(document=SimpleNamespace(
                                           to_data=lambda: {'typed': {'__type__': 'Short', '__value__': 9}})))
        self.profiles = ModuleType('modern_projection.projection.static_frame_item_data')
        self.profiles.FRAME_ITEMS = {'plain': {'accepted': False}}
        self.primitives = []
        pyreact = ModuleType('modern_projection.pyreact')
        pyreact.Component = lambda function: function
        pyreact.Image = lambda **props: SimpleNamespace(type='Image', props=props)
        pyreact.PaperDoll = self.paper_doll
        pyreact.Color = lambda value: value
        pyreact.Style = lambda **values: values
        pyreact.use_ref = self.use_ref
        pyreact.AlignItems = SimpleNamespace(center='center')
        pyreact.JustifyContent = SimpleNamespace(center='center')
        pyreact.PaperDollRenderType = SimpleNamespace(entity='entity')
        pyreact.Position = SimpleNamespace(absolute='absolute')
        bridge = ModuleType('modern_projection.projection.bridge')
        bridge._stable_palette = canonical
        projection = ModuleType('modern_projection.projection')
        projection.__path__ = []
        projection.static_frame_item_data = self.profiles
        modern = ModuleType('modern_projection')
        modern.__path__ = []
        self.modules = {'modern_projection': modern, 'modern_projection.projection': projection,
                        'modern_projection.pyreact': pyreact, 'modern_projection.projection.bridge': bridge,
                        'modern_projection.projection.static_frame_item_data': self.profiles}
        self.namespace = {'sys': SimpleNamespace(), 'json': json, 'long': int,
                          'time': SimpleNamespace(time=self.now), 'navigator': self.nav, 's': self.session,
                          'b': SimpleNamespace(factory=self.factory, level='native-level', preparing_entity=False),
                          'api': SimpleNamespace(GetLocalPlayerId=lambda: self.player,
                                                 GetTopScreen=lambda: self.host,
                                                 GetMinecraftVersion=lambda: '1.21.120.0')}

    def now(self):
        if not self.frozen_clock:
            self.clock += .2
        return self.clock

    def paper_doll(self, **props):
        self.primitives.append(props)
        return SimpleNamespace(type='PaperDoll', props=props)

    def use_ref(self, value):
        self.ref_calls += 1
        index = (self.ref_calls - 1) % 6
        if index == 0: control = self.root_control
        elif index == 1: control = self.control
        else:
            spec = probe.marker_specs(self.screen_observed)[index - 2]
            rect = {'x': spec['x'], 'y': spec['y'], 'width': 6., 'height': 6., 'path': '/' + spec['key']}
            self.native_markers.append(dict(spec, rect=rect))
            control = self.native_control(rect)
        return SimpleNamespace(current=control)

    @staticmethod
    def native_control(rect):
        return SimpleNamespace(GetGlobalPosition=lambda: (rect['x'], rect['y']),
                               GetSize=lambda: (rect['width'], rect['height']), GetPath=lambda: rect['path'])

    def native_layout(self):
        saved = self.namespace['sys']._native_item_ui_probe
        return copy.deepcopy({'root': self.native_root, 'paper_doll': self.native_doll,
                              'viewport': self.native_viewport, 'screen_size_api_observed': self.screen_observed,
                              'screen_view_api_observed': [1995., 1107., 0., 0.], 'markers': self.native_markers,
                              'declared_size': saved['declared_size'], 'size_inputs': saved['size_inputs']})

    def layout(self, tree=None, native=None):
        saved = self.namespace['sys']._native_item_ui_probe
        return probe.paper_doll_layout(tree or self.tree(), self.player, native or self.native_layout(),
                                      saved['declared_size'], saved['size_inputs'])

    def model_id(self):
        self.model_reads += 1
        return -1

    def bind(self, *args):
        self.binds.append(copy.deepcopy(args))
        if self.bind_error:
            raise self.bind_error
        identity = self.bind_value
        if isinstance(identity, int):
            self.bind_value += 1
        return identity

    def remove(self, *args):
        self.removes.append(args)
        if args[1] == self.remove_error:
            raise RuntimeError('exact attachment removal failed')
        return True

    def render(self, params):
        self.renders.append(copy.deepcopy(params))
        return True

    def push(self, element, key):
        self.entries.append(SimpleNamespace(key=key, _host=self.host))
        self.nav.top = self.entries[-1]
        if self.push_error:
            self.nav.is_transitioning = True
            raise self.push_error
        return True

    def pop(self):
        self.pop_calls += 1
        self.entries.pop()
        self.nav.top = self.entries[-1] if self.entries else None
        return True

    def run(self, code):
        if code.startswith("saved=getattr(sys,'_native_item_ui_probe',None)\nowned=") and self.transition_polls:
            self.transition_polls -= 1
            if not self.transition_polls:
                self.nav.is_transitioning = False
        with patch.dict(sys.modules, self.modules):
            exec(compile(code, '<prepared-native-probe>', 'exec'), self.namespace)
        result = self.namespace['_result']
        return json.loads(result) if isinstance(result, str) else result

    def install(self, nonce='offline-owned'):
        controls, actor = probe.item_controls(RAW.read_bytes())
        return self.run(probe.INSTALL % (nonce, nonce, json.dumps(controls)))

    def tree(self):
        props = copy.deepcopy(self.primitives[-1])
        props.pop('ref')
        props.pop('style')
        return {'type': 'Image', 'id': '/probe', 'key': 'native_item_probe_root',
                'opacity': 1.,
                'props': {'color': {'r': 247 / 255., 'g': 249 / 255., 'b': 252 / 255., 'a': 1.}},
                'layout': dict((key, self.native_root[key]) for key in ('x', 'y', 'width', 'height')),
                'children': [{'type': 'PaperDoll', 'id': '/probe/doll', 'key': 'native_item_probe_doll',
                              'props': props, 'opacity': 1., 'layout': dict((key, self.native_doll[key])
                                  for key in ('x', 'y', 'width', 'height')), 'children': []}] + [
                    {'type': 'Image', 'id': marker['rect']['path'], 'key': marker['key'], 'opacity': 1.,
                     'props': {'color': dict(zip(('r', 'g', 'b', 'a'),
                                                [value / 255. for value in marker['rgb']] + [1.]))},
                     'layout': dict((key, marker['rect'][key]) for key in ('x', 'y', 'width', 'height')),
                     'children': []} for marker in self.native_markers]}

    def check(self):
        return SimpleNamespace(run=self.run, wait=lambda *args: None, client=SimpleNamespace(timeout=10.),
                               command=lambda name: {'tree': self.tree()}, navigation=lambda: {
                                   'transition': False, 'top': self.nav.top.key if self.nav.top else None})


class NativeItemProbeTests(unittest.TestCase):
    def test_controls_preserve_native_typed_data_and_do_not_mutate_source(self):
        raw = RAW.read_bytes()
        controls, actor = probe.item_controls(raw)
        self.assertEqual(raw, RAW.read_bytes())
        self.assertEqual('minecraft:diamond_sword', controls['plain']['newItemName'])
        self.assertEqual(dict(controls['plain'], isEnchanted=True), controls['flag_enchanted'])
        self.assertEqual({}, controls['plain']['userData'])
        self.assertTrue(controls['actual_enchanted']['isEnchanted'])
        self.assertEqual(actor['Item']['tag'], controls['actual_enchanted']['userData'])
        self.assertEqual({'__type__': 2, '__value__': 9}, controls['actual_enchanted']['userData']['ench'][0]['id'])
        with self.assertRaisesRegex(ValueError, 'exact preserved'):
            probe.item_controls(raw + b' ')

    def test_fresh_bundle_contract_and_tamper_rejection(self):
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            plan = probe.prepare(RAW, bundle)
            self.assertEqual(15, len(plan['states']) * plan['frames_per_state'])
            self.assertFalse(plan['sdk_dispatch_authorized'])
            probe.verify_bundle(bundle)
            with self.assertRaisesRegex(ValueError, 'Preserve existing probe bundle'):
                probe.prepare(Path(directory) / 'absent.json', bundle)
            snippet = bundle / 'plain_client.py'
            original = snippet.read_bytes()
            snippet.write_bytes(original + b'\n')
            with self.assertRaisesRegex(ValueError, 'Frozen native item probe changed'):
                probe.verify_bundle(bundle)
            snippet.write_bytes(original)
            plan['frames_per_state'] = 4
            (bundle / 'plan.json').write_text(json.dumps(plan), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'Finite native item probe contract changed'):
                probe.verify_bundle(bundle)

    def test_all_capture_files_checked_before_native_dispatch(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
            probe.prepare(RAW, bundle)
            old = probe.capture_path(output, 'empty_restored', 2).with_suffix('.capture.json')
            old.write_bytes(b'retained native evidence')
            check = SimpleNamespace(run=lambda code: self.fail('SDK dispatched before capture preflight'))
            with self.assertRaisesRegex(ValueError, 'Preserve existing native capture'):
                probe.execute_probe(bundle, output, check, None, 0.)
            self.assertFalse(output.exists())
            self.assertEqual(b'retained native evidence', old.read_bytes())
            output.write_bytes(b'retained runtime evidence')
            with self.assertRaisesRegex(ValueError, 'Preserve existing native item evidence'):
                probe.preflight(Path(directory) / 'absent', output)

    def test_player_head_false_target_and_exact_owned_cleanup(self):
        fixture = NativeFixture()
        initial = fixture.install()
        self.assertEqual(fixture.player, initial['ui_params']['entity_id'])
        props = fixture.primitives[0]
        self.assertEqual('entity', props['renderType'])
        self.assertEqual({'width': 240, 'height': 240}, props['style'])
        self.assertEqual(fixture.player, props['entityId'])
        for label in probe.STATES:
            fixture.run(probe.CONTROL % ('offline-owned', label))
        self.assertEqual(3, len(fixture.binds))
        self.assertEqual([40, 41, 42], [call[1] for call in fixture.removes])
        for call in fixture.binds:
            self.assertEqual((fixture.player, 'head', False, (0., 0., 0.), (0., 0., 0.), 1.),
                             (call[0],) + call[2:])
        self.assertTrue(all(call == (fixture.player, call[1], '', False) for call in fixture.removes))
        fixture.run(probe.REMOVE % 'offline-owned')
        self.assertEqual(3, len(fixture.removes))
        fixture.run(probe.POP % 'offline-owned')
        restored = fixture.run(probe.VERIFY_RESTORE % 'offline-owned')
        self.assertTrue(restored['restored'])
        self.assertFalse(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))

    def test_uncertain_bind_and_invalid_return_keep_pending_state(self):
        for bind_error, returned in ((RuntimeError('uncertain bind'), 40), (None, None), (None, True)):
            with self.subTest(error=bind_error, returned=returned):
                fixture = NativeFixture()
                fixture.install()
                fixture.bind_error, fixture.bind_value = bind_error, returned
                with self.assertRaises((RuntimeError, AssertionError)):
                    fixture.run(probe.CONTROL % ('offline-owned', 'actual_enchanted'))
                removed = fixture.run(probe.REMOVE % 'offline-owned')
                self.assertEqual([], fixture.removes)
                self.assertEqual('pending', removed['attachments'][0]['state'])
                self.assertEqual(1, len(removed['errors']))
                fixture.run(probe.POP % 'offline-owned')
                with self.assertRaises(AssertionError):
                    fixture.run(probe.VERIFY_RESTORE % 'offline-owned')
                self.assertTrue(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))

    def test_model_read_is_deferred_after_mount_and_render(self):
        fixture = NativeFixture()
        fixture.install()
        status = fixture.run(probe.STATUS % 'offline-owned')
        self.assertTrue(status['ready'])
        self.assertIsNone(status['model_id'])
        self.assertEqual(0, fixture.model_reads)
        status = fixture.run(probe.STATUS % 'offline-owned')
        self.assertEqual(-1, status['model_id'])
        self.assertEqual(1, fixture.model_reads)
        fixture.frozen_clock = True
        fixture.run(probe.CONTROL % ('offline-owned', 'plain'))
        status = fixture.run(probe.STATUS % 'offline-owned')
        self.assertIsNone(status['model_id'])
        self.assertEqual(1, fixture.model_reads)
        fixture.clock += .15
        status = fixture.run(probe.STATUS % 'offline-owned')
        self.assertEqual(-1, status['model_id'])
        self.assertEqual(2, fixture.model_reads)

    def test_remove_failure_continues_only_other_owned_ids(self):
        fixture = NativeFixture()
        fixture.install()
        saved = fixture.namespace['sys']._native_item_ui_probe
        saved['attachments'] = [{'state': 'bound', 'id': 40}, {'state': 'bound', 'id': 41}]
        fixture.remove_error = 40
        result = fixture.run(probe.REMOVE % 'offline-owned')
        self.assertEqual([40, 41], [call[1] for call in fixture.removes])
        self.assertEqual(['bound', 'removed'], [row['state'] for row in result['attachments']])
        self.assertEqual(1, len(result['errors']))
        fixture.run(probe.POP % 'offline-owned')
        with self.assertRaises(AssertionError):
            fixture.run(probe.VERIFY_RESTORE % 'offline-owned')

    def test_pop_refuses_unrelated_page_and_camera_snapshot_is_independent(self):
        fixture = NativeFixture()
        initial = fixture.install()
        fixture.session.camera_pose[0] = 99
        self.assertEqual([1, 2, 3], initial['camera']['camera_pose'])
        fixture.entries.append(SimpleNamespace(key='unrelated'))
        fixture.nav.top = fixture.entries[-1]
        with self.assertRaisesRegex(AssertionError, 'refuse unrelated pop'):
            fixture.run(probe.POP % 'offline-owned')
        self.assertEqual('unrelated', fixture.nav.top.key)

    def test_layout_targets_only_owned_doll_and_rejects_resized_or_wrong_entity(self):
        fixture = NativeFixture()
        fixture.install()
        tree = fixture.tree()
        layout = fixture.layout(tree)
        self.assertEqual([757, 312, 1237, 793], probe.frame_crop(layout, [1994, 1105],
                                                            calibrated_test_mapping(layout, [1994, 1105])))
        tree['children'][0]['layout']['width'] = 239
        with self.assertRaisesRegex(ValueError, 'resized'):
            fixture.layout(tree)
        tree = fixture.tree()
        tree['children'][0]['props']['entityId'] = 'unrelated-entity'
        with self.assertRaisesRegex(ValueError, 'props changed'):
            fixture.layout(tree)

    def test_status_reads_native_rectangles_independently_of_snapshots(self):
        fixture = NativeFixture()
        fixture.install()
        tree = fixture.tree()
        fixture.native_doll['width'] = 239.
        status = fixture.run(probe.STATUS % 'offline-owned')
        self.assertEqual(239., status['native_layout']['paper_doll']['width'])
        self.assertEqual(240, tree['children'][0]['layout']['width'])
        self.assertEqual([997., 552.5], status['native_layout']['screen_size_api_observed'])
        with self.assertRaisesRegex(ValueError, 'Native paper_doll bounds differ'):
            fixture.layout(tree, status['native_layout'])

    def test_install_freezes_viewport_derived_square_for_every_item_state(self):
        for screen, expected in (([499., 277.], 240.), ([280., 200.], 168.), ([100., 90.], 58.)):
            with self.subTest(screen=screen):
                fixture = NativeFixture()
                fixture.screen_observed = screen
                for rect in (fixture.native_root, fixture.native_viewport):
                    rect.update(width=screen[0], height=screen[1])
                fixture.native_doll.update(width=expected, height=expected,
                                          x=(screen[0] - expected) / 2., y=(screen[1] - expected) / 2.)
                initial = fixture.install()
                self.assertEqual(expected, initial['declared_size'])
                self.assertEqual(screen, initial['size_inputs'])
                self.assertEqual({'width': expected, 'height': expected}, fixture.primitives[0]['style'])
                for label in probe.STATES:
                    fixture.run(probe.CONTROL % ('offline-owned', label))
                    layout = fixture.layout()
                    self.assertEqual(expected, layout['paper_doll']['width'])
                    self.assertGreaterEqual(layout['paper_doll']['x'], 16.)
                    self.assertGreaterEqual(layout['paper_doll']['y'], 16.)
                fixture.run(probe.REMOVE % 'offline-owned')
                fixture.run(probe.POP % 'offline-owned')
                self.assertTrue(fixture.run(probe.VERIFY_RESTORE % 'offline-owned')['restored'])

    def test_declared_size_and_native_center_must_match_installation_rule(self):
        fixture = NativeFixture()
        fixture.install()
        native = fixture.native_layout()
        native['declared_size'] = 239.
        with self.assertRaisesRegex(ValueError, 'changed since installation'):
            fixture.layout(native=native)
        fixture.native_doll['x'] += 1.
        with self.assertRaisesRegex(ValueError, 'centered bounds changed'):
            fixture.layout()
        fixture = NativeFixture()
        fixture.screen_observed = [32., 100.]
        with self.assertRaises(AssertionError):
            fixture.install()
        self.assertEqual([], fixture.binds)
        self.assertFalse(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))

    def test_observed_small_viewport_keeps_existing_physical_mapping_gate(self):
        fixture = NativeFixture()
        fixture.screen_observed = [499., 277.]
        for rect in (fixture.native_root, fixture.native_viewport):
            rect.update(width=499., height=277.)
        fixture.native_doll.update(x=129.5, y=18.5)
        fixture.install()
        layout = fixture.layout()
        with self.assertRaisesRegex(ValueError, 'physical capture mapping is not uniform'):
            probe.physical_mapping(layout, [1994, 1105])

    def small_marker_fixture(self):
        fixture = NativeFixture()
        fixture.screen_observed = [499., 277.]
        for rect in (fixture.native_root, fixture.native_viewport):
            rect.update(width=499., height=277.)
        fixture.native_doll.update(x=129.5, y=18.5)
        fixture.install()
        return fixture, fixture.layout()

    def test_marker_calibration_proves_common_scale_with_holdouts_and_keeps_api_failure(self):
        with TemporaryDirectory() as directory:
            fixture, layout = self.small_marker_fixture()
            capture = marker_capture(Path(directory) / 'first.png', layout)
            mapping = probe.marker_mapping(capture, layout)
            self.assertTrue(mapping['passed'])
            self.assertEqual(4., mapping['calibration']['scale'])
            self.assertEqual([0., 0.], mapping['calibration']['translation'])
            self.assertEqual([False, True, True, False], [row['holdout'] for row in mapping['markers']])
            self.assertFalse(mapping['legacy_api_uniform_mapping']['passed'])
            self.assertEqual(1., mapping['legacy_api_uniform_mapping']['maximum_residual_pixels'])
            self.assertEqual([518, 74, 1478, 1034], probe.frame_crop(layout, [1994, 1105], mapping))
            repeated = probe.marker_mapping(capture, layout, mapping['calibration'])
            self.assertEqual(mapping, repeated)

    def test_marker_calibration_rejects_missing_ambiguous_holdout_and_frozen_drift(self):
        with TemporaryDirectory() as directory:
            fixture, layout = self.small_marker_fixture()
            capture = marker_capture(Path(directory) / 'first.png', layout)
            frozen = probe.marker_mapping(capture, layout)['calibration']
            for label, args, pattern in (
                    ('missing', {'missing': 2}, 'components=0'),
                    ('ambiguous', {'duplicate': 0}, 'components=2'),
                    ('holdout', {'moved': {1: (4., 0.)}}, 'one physical pixel'),
                    ('size_changed', {'resize': {2: (3, 0)}}, 'one physical pixel'),
                    ('drift', {'translation': (4., 0.)}, 'one physical pixel')):
                with self.subTest(label=label):
                    changed = marker_capture(Path(directory) / (label + '.png'), layout, **args)
                    with self.assertRaisesRegex(ValueError, pattern):
                        probe.marker_mapping(changed, layout, frozen)

    def test_marker_predictions_reject_nonuniform_scaling_and_receipt_tamper(self):
        with TemporaryDirectory() as directory:
            fixture, layout = self.small_marker_fixture()
            moved = {index: (0., marker['rect']['y'] * .03) for index, marker in enumerate(layout['native_readback']['markers'])}
            capture = marker_capture(Path(directory) / 'anisotropic.png', layout, moved=moved)
            with self.assertRaisesRegex(ValueError, 'one physical pixel'):
                probe.marker_mapping(capture, layout)
            capture = marker_capture(Path(directory) / 'valid.png', layout)
            Path(capture['path']).write_bytes(Path(capture['path']).read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                probe.marker_mapping(capture, layout)

    def test_marker_native_positions_color_and_root_opacity_are_fixed(self):
        fixture, layout = self.small_marker_fixture()
        tree = fixture.tree()
        tree['children'][1]['props']['color']['a'] = .5
        with self.assertRaisesRegex(ValueError, 'marker color'):
            fixture.layout(tree)
        tree = fixture.tree()
        tree['opacity'] = .5
        with self.assertRaisesRegex(ValueError, 'root is not unique'):
            fixture.layout(tree)
        fixture.native_markers[0]['rect']['x'] += 1.
        with self.assertRaisesRegex(ValueError, 'marker bounds'):
            fixture.layout()
        fixture.native_markers[0]['rect'].update(x=fixture.native_doll['x'], y=fixture.native_doll['y'])
        with self.assertRaisesRegex(ValueError, 'marker bounds'):
            fixture.layout()

    def test_full_native_evidence_matrix_calibrates_before_binding_and_scores_same_mapping(self):
        from PIL import Image, ImageDraw
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
            probe.prepare(RAW, bundle)
            fixture = NativeFixture()
            fixture.screen_observed = [499., 277.]
            for rect in (fixture.native_root, fixture.native_viewport):
                rect.update(width=499., height=277.)
            fixture.native_doll.update(x=129.5, y=18.5)
            check, capture_labels = fixture.check(), []

            def capture(runtime, path):
                saved = fixture.namespace['sys']._native_item_ui_probe
                label = saved['control']
                capture_labels.append(label)
                if label == 'empty':
                    self.assertEqual([], fixture.binds)
                layout = fixture.layout()
                record = marker_capture(path, layout)
                with Image.open(path) as source:
                    image = source.convert('RGB')
                draw = ImageDraw.Draw(image)
                draw.rectangle((800, 350, 1150, 900), fill=(40, 40, 40))
                if label not in ('empty', 'empty_restored'):
                    draw.rectangle((950, 160, 1009, 279), fill=(40, 160, 190))
                    if label != 'plain':
                        index = len(capture_labels) % 3
                        draw.rectangle((955 + index * 12, 180, 964 + index * 12, 259), fill=(140, 70, 190))
                image.save(path)
                payload = path.read_bytes()
                for row in (record, record['capture']):
                    row.update(sha256=probe.digest(payload), bytes=len(payload))
                return record

            with patch.object(executor.BoundedRuntime, 'capture_adapter', return_value=(None, None)), \
                    patch.object(executor.BoundedRuntime, 'capture', capture), patch.object(executor.time, 'sleep'):
                report = probe.execute_probe(bundle, output, check, SimpleNamespace(guard=lambda: None),
                                             executor.time.monotonic() + 150.)
            self.assertTrue(report['completed'], report)
            self.assertTrue(report['restored'], report)
            self.assertEqual([label for label in probe.STATES for index in range(3)], capture_labels)
            self.assertEqual(3, len(fixture.binds))
            self.assertEqual(4., report['frozen_marker_calibration']['scale'])
            self.assertTrue(all(not frame['marker_mapping']['legacy_api_uniform_mapping']['passed']
                                for row in report['states'].values() for frame in row['frames']))
            score = probe.score_probe(report)
            self.assertTrue(score['stable_plain_difference_candidate'])
            self.assertFalse(score['enchantment_glint_accepted'])
            self.assertFalse(score['native_bound_item_ui_inclusion_proven'])
            self.assertEqual([518, 74, 1478, 1034], score['crop'])

    def test_native_crop_rejects_bounds_aspect_and_physical_dpi_mismatches(self):
        fixture = NativeFixture()
        fixture.install()
        native = fixture.native_layout()
        native['paper_doll']['x'] += .5
        with self.assertRaisesRegex(ValueError, 'Native paper_doll bounds differ'):
            fixture.layout(native=native)
        native = fixture.native_layout()
        native['viewport']['x'] = 1.
        with self.assertRaisesRegex(ValueError, 'Native full-screen viewport'):
            fixture.layout(native=native)
        native = fixture.native_layout()
        native['screen_size_api_observed'][1] += 40.
        with self.assertRaisesRegex(ValueError, 'changed since installation'):
            fixture.layout(native=native)
        native = fixture.native_layout()
        layout = fixture.layout(native=native)
        self.assertEqual([757, 312, 1237, 793], probe.frame_crop(layout, [1994, 1105],
                                                            calibrated_test_mapping(layout, [1994, 1105])))
        self.assertEqual(2., probe.physical_mapping(layout, [1994, 1105])['game_to_physical_scale'])
        with self.assertRaisesRegex(ValueError, 'physical capture mapping is not uniform'):
            probe.physical_mapping(layout, [1994, 1205])

    def test_partial_push_settles_before_the_single_owned_cleanup_pop(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
            probe.prepare(RAW, bundle)
            fixture = NativeFixture()
            fixture.push_error = RuntimeError('partial owned navigation push')
            fixture.transition_polls = 3
            check = fixture.check()
            with patch.object(executor.BoundedRuntime, 'capture_adapter', return_value=(None, None)), \
                    patch.object(executor.time, 'sleep'):
                report = probe.execute_probe(bundle, output, check, SimpleNamespace(guard=lambda: None),
                                             executor.time.monotonic() + 150.)
            self.assertFalse(report['completed'])
            self.assertTrue(report['restored'], report)
            self.assertEqual(1, fixture.pop_calls)
            self.assertEqual([], fixture.binds)
            self.assertFalse(report['navigation_before_pop']['transition'])
            self.assertTrue(report['navigation_before_pop']['contains_owned'])
            self.assertEqual('modern_projection_workspace', fixture.nav.top.key)
            self.assertFalse(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))
            self.assertEqual(report, json.loads(output.read_bytes()))

    def test_partial_push_timeout_preserves_owned_page_without_pop_or_bind_retry(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
            probe.prepare(RAW, bundle)
            fixture, host_clock, polls = NativeFixture(), [100.], []
            fixture.push_error = RuntimeError('partial owned navigation push')
            original_run = fixture.run

            def run(code):
                if code.startswith("saved=getattr(sys,'_native_item_ui_probe',None)\nowned="):
                    host_clock[0] += 1.
                    polls.append(host_clock[0])
                return original_run(code)

            fixture.run = run
            check = fixture.check()
            original_init = executor.BoundedRuntime.__init__

            def init(runtime, check, guard, deadline):
                original_init(runtime, check, guard, deadline, clock=lambda: host_clock[0])

            with patch.object(executor.BoundedRuntime, '__init__', init), \
                    patch.object(executor.BoundedRuntime, 'capture_adapter', return_value=(None, None)), \
                    patch.object(executor.time, 'sleep'):
                report = probe.execute_probe(bundle, output, check, SimpleNamespace(guard=lambda: None), 250.)
            self.assertFalse(report['completed'])
            self.assertFalse(report['restored'])
            self.assertEqual(10, len(polls))
            self.assertEqual(0, fixture.pop_calls)
            self.assertEqual([], fixture.binds)
            self.assertTrue(any('Readiness budget exhausted' in error for error in report['cleanup_errors']))
            self.assertTrue(fixture.nav.top.key.startswith('native_item_ui_'))
            self.assertTrue(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))
            self.assertEqual(report, json.loads(output.read_bytes()))

    def test_finite_fifteen_frames_and_clock_failure_restore_without_retry(self):
        for fail_clock in (False, True):
            with self.subTest(fail_clock=fail_clock), TemporaryDirectory() as directory:
                bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
                probe.prepare(RAW, bundle)
                fixture, captures = NativeFixture(), []
                fixture.frozen_clock = fail_clock
                check = fixture.check()
                original_run, original_wait = check.run, check.wait

                def capture(runtime, path):
                    captures.append(path)
                    return {'path': str(path), 'size': [1994, 1105]}

                with patch.object(executor.BoundedRuntime, 'capture_adapter', return_value=(None, None)), \
                        patch.object(executor.BoundedRuntime, 'capture', capture), \
                        patch.object(probe, 'marker_mapping', side_effect=lambda shot, layout, frozen: calibrated_test_mapping(layout, shot['size'])), \
                        patch.object(executor.time, 'sleep'):
                    report = probe.execute_probe(bundle, output, check, SimpleNamespace(guard=lambda: None),
                                                 executor.time.monotonic() + 150.)
                self.assertEqual(not fail_clock, report['completed'], report)
                self.assertTrue(report['restored'], report)
                self.assertEqual(0 if fail_clock else 15, len(captures))
                self.assertEqual(0 if fail_clock else 3, len(fixture.binds))
                self.assertFalse(report['production_rendering_accepted'])
                self.assertFalse(report['enchantment_glint_accepted'])
                self.assertEqual(original_run, check.run)
                self.assertEqual(original_wait, check.wait)
                self.assertEqual(report, json.loads(output.read_bytes()))
                self.assertFalse(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))

    def test_host_uncertain_bind_keeps_failed_evidence_and_owned_state(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'runtime.json'
            probe.prepare(RAW, bundle)
            fixture, captures = NativeFixture(), []
            fixture.bind_error = RuntimeError('uncertain native attachment ID')
            check = fixture.check()

            def capture(runtime, path):
                captures.append(path)
                return {'path': str(path), 'size': [1994, 1105]}

            with patch.object(executor.BoundedRuntime, 'capture_adapter', return_value=(None, None)), \
                    patch.object(executor.BoundedRuntime, 'capture', capture), \
                    patch.object(probe, 'marker_mapping', side_effect=lambda shot, layout, frozen: calibrated_test_mapping(layout, shot['size'])), \
                    patch.object(executor.time, 'sleep'):
                report = probe.execute_probe(bundle, output, check, SimpleNamespace(guard=lambda: None),
                                             executor.time.monotonic() + 150.)
            self.assertFalse(report['completed'])
            self.assertFalse(report['restored'])
            self.assertEqual(3, len(captures))
            self.assertEqual(1, len(fixture.binds))
            self.assertEqual([], fixture.removes)
            self.assertEqual('pending', report['owned attachments']['attachments'][0]['state'])
            self.assertTrue(report['cleanup_errors'])
            self.assertEqual('modern_projection_workspace', fixture.nav.top.key)
            self.assertTrue(hasattr(fixture.namespace['sys'], '_native_item_ui_probe'))
            self.assertEqual(report, json.loads(output.read_bytes()))

    def test_offline_pixels_separate_stable_item_from_baseline_motion(self):
        from PIL import Image, ImageDraw
        for included in (False, True):
            with self.subTest(included=included), TemporaryDirectory() as directory:
                report = {'completed': True, 'restored': True, 'errors': [], 'cleanup_errors': [], 'states': {}}
                for label in probe.STATES:
                    row = report['states'][label] = {'state': 'captured', 'frames': []}
                    for index in range(3):
                        image = Image.new('RGB', (200, 160), 'white')
                        draw = ImageDraw.Draw(image)
                        draw.rectangle((75, 65, 105, 140), fill='black')
                        draw.rectangle((65 + index * 8, 100, 75 + index * 8, 110), fill='gray')
                        if included and label in ('plain', 'flag_enchanted', 'actual_enchanted'):
                            draw.rectangle((110, 35, 139, 64), fill='blue')
                            if label != 'plain':
                                draw.rectangle((112 + index * 6, 40, 118 + index * 6, 59), fill='magenta')
                        path = Path(directory) / (label + str(index) + '.png')
                        image.save(path)
                        payload = path.read_bytes()
                        capture = {'path': str(path), 'sha256': probe.digest(payload), 'bytes': len(payload),
                                   'mime': 'image/png', 'size': [200, 160]}
                        capture['capture'] = dict(capture, width=200, height=160, frame={'width': 200, 'height': 160})
                        rect = {'x': 0, 'y': 0, 'width': 200, 'height': 160}
                        layout = {'screen_to_ui_scale': 1., 'native_readback': {
                            'viewport': rect, 'paper_doll': rect, 'screen_size_api_observed': [200, 160]}}
                        row['frames'].append({'capture': capture, 'crop': [0, 0, 200, 160], 'layout': layout,
                                              'marker_mapping': calibrated_test_mapping(layout, [200, 160], 1.)})
                with patch.object(probe, 'marker_mapping', side_effect=lambda shot, layout, frozen: calibrated_test_mapping(layout, shot['size'], 1.)):
                    score = probe.score_probe(report)
                self.assertEqual(included, score['stable_plain_difference_candidate'])
                self.assertGreater(score['baseline_temporal_pixels'], 0)
                self.assertFalse(score['enchantment_glint_accepted'])
                self.assertFalse(score['native_bound_item_ui_inclusion_proven'])
                self.assertEqual(900 if included else 0,
                                 score['controls']['plain']['stable_pixels_outside_baseline_motion'])
                self.assertEqual(included, score['controls']['actual_enchanted'][
                    'temporal_pixels_in_shared_item_interior_excluding_plain_motion'] > 0)
                report['restored'] = False
                self.assertEqual('inconclusive', probe.score_probe(report)['interpretation'])
                report['restored'] = True
                path.write_bytes(payload + b' ')
                with patch.object(probe, 'marker_mapping', side_effect=lambda shot, layout, frozen: calibrated_test_mapping(layout, shot['size'], 1.)):
                    with self.assertRaisesRegex(ValueError, 'bytes differ'):
                        probe.score_probe(report)


if __name__ == '__main__':
    unittest.main()
