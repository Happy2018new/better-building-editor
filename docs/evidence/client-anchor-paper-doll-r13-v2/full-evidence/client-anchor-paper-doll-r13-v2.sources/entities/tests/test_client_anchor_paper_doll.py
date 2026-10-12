"""Exercise owned actor failure cleanup and ordinary-before-depth evidence offline."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import execute_frame_item_translation as executor
import probe_client_anchor_paper_doll as probe
import probe_native_item_paper_doll as base
from test_native_item_paper_doll import NativeFixture, RAW, marker_capture


class AnchorFixture(NativeFixture):
    def __init__(self):
        super().__init__()
        self.actor = 'owned-client-anchor'
        self.creation_value, self.creation_error = self.actor, None
        self.created, self.destroyed, self.body_calls = [], [], []
        self.alive, self.destroy_error, self.body_error, self.native_calls = False, None, None, []
        self.foot, self.bone = (20., 64., 20.), [[1., 0., 0., 0.]] * 4
        self.screen_observed = [499., 277.]
        self.native_root.update(width=499., height=277.)
        self.native_viewport.update(width=499., height=277.)
        self.native_doll.update(x=129.5, y=18.5)
        self.factory.CreatePos = lambda identity: SimpleNamespace(GetFootPos=lambda: self.foot)
        self.factory.CreateEngineType = lambda identity: SimpleNamespace(
            GetEngineTypeStr=lambda: 'modern_projection:anchor' if self.alive else None)
        self.factory.CreateActorRender = lambda identity: SimpleNamespace(
            GetQueryableBoneOrientation=lambda bone, client: self.bone,
            AddActorBlockGeometry=lambda *args: self.body_call('add', args),
            SetActorBlockGeometryOffset=lambda *args: self.body_call('offset', args),
            SetActorBlockGeometryVisible=lambda *args: self.body_call('visible', args))
        self.palette_data = None
        self.factory.CreateBlock = lambda level: SimpleNamespace(GetBlankBlockPalette=lambda: SimpleNamespace(
            DeserializeBlockPalette=self.deserialize, SerializeBlockPalette=lambda: copy.deepcopy(self.palette_data)))
        self.factory.CreateBlockGeometry = lambda level: SimpleNamespace(CombineBlockPaletteToGeometry=self.combine)
        self.itemcomp.GetBindItemOffset = lambda *args: (0., 0., 0.)
        self.itemcomp.GetBindItemRotation = lambda *args: (0., 0., 0.)
        self.itemcomp.GetBindItemScale = lambda *args: 1.
        self.namespace['b'].system = SimpleNamespace(CreateClientEntityByTypeStr=self.create,
                                                      DestroyClientEntity=self.destroy)
        self.namespace['basestring'] = (str, bytes)
        self.modules['modern_projection.projection.bridge']._native_palette = lambda value: value

    def create(self, *args):
        self.created.append(args)
        saved = self.namespace['sys']._client_anchor_ui_probe
        if saved['create'] != {'state': 'pending', 'attempted': True}:
            raise AssertionError('Actor creation must be journaled before dispatch')
        if self.creation_error:
            raise self.creation_error
        self.alive = self.creation_value == self.actor
        return self.creation_value

    def destroy(self, actor):
        saved = self.namespace['sys']._client_anchor_ui_probe
        if not saved['destroy_attempted'] or actor != self.actor:
            raise AssertionError('Only exact owned actor destruction may dispatch')
        self.destroyed.append(actor)
        if self.destroy_error:
            raise self.destroy_error
        self.alive = False

    def bind(self, *args):
        row = self.namespace['sys']._client_anchor_ui_probe['attachments'][-1]
        if row['state'] != 'pending' or not row['attempted'] or row['id'] is not None:
            raise AssertionError('Binding must be journaled before dispatch')
        return super().bind(*args)

    def deserialize(self, data):
        self.palette_data = copy.deepcopy(data)
        return True

    def combine(self, palette, name, mode):
        body = self.namespace['sys']._client_anchor_ui_probe['body']
        if not body['combine_attempted']:
            raise AssertionError('Combine must be journaled before dispatch')
        self.body_calls.append(('combine', name))
        return name

    def body_call(self, operation, args):
        saved = self.namespace['sys']._client_anchor_ui_probe
        if saved['journal'][-1]['state'] != 'pending':
            raise AssertionError('Body mutation must be journaled before dispatch')
        self.body_calls.append((operation, args))
        if operation == self.body_error:
            raise TimeoutError('uncertain native ' + operation)
        return True

    def run(self, code):
        self.native_calls.append(code)
        if code.startswith("saved=getattr(sys,'_client_anchor_ui_probe',None)\nowned=") and self.transition_polls:
            self.transition_polls -= 1
            if not self.transition_polls:
                self.nav.is_transitioning = False
        return super().run(code)

    def install(self, nonce='offline-owned'):
        plain = base.item_controls(RAW.read_bytes())[0]['plain']
        programs = probe.snippets(nonce, plain)
        self.run(programs['install_client.py'])
        return self.run(programs['open_ui_client.py'])

    def native_layout(self):
        saved = self.namespace['sys']._client_anchor_ui_probe
        return copy.deepcopy({'root': self.native_root, 'paper_doll': self.native_doll,
            'viewport': self.native_viewport, 'screen_size_api_observed': self.screen_observed,
            'screen_view_api_observed': [1995., 1107., 0., 0.], 'markers': self.native_markers,
            'declared_size': saved['declared_size'], 'size_inputs': saved['size_inputs']})

    def programs(self):
        return probe.snippets('offline-owned', base.item_controls(RAW.read_bytes())[0]['plain'])

    def cleanup(self):
        programs = self.programs()
        self.run(programs['remove_client.py'])
        self.run(programs['pop_client.py'])
        self.run(programs['destroy_client.py'])
        return self.run(programs['verify_client.py'])


class AnchorProbeTests(unittest.TestCase):
    def test_returned_owned_actor_true_root_binding_and_exact_cleanup(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.run(fixture.programs()['plain_client.py'])
        self.assertEqual(('modern_projection:anchor', (20., 65., 20.), (0., 0.)), fixture.created[0])
        args = fixture.binds[0]
        self.assertEqual((fixture.actor, 'root', True), (args[0], args[2], args[3]))
        self.assertEqual(((0., 0., 0.), (0., 0., 0.), 1.), args[4:])
        self.assertFalse(args[1]['isEnchanted'])
        self.assertEqual({}, args[1]['userData'])
        restored = fixture.cleanup()
        self.assertTrue(restored['actor_absent'])
        self.assertEqual([(fixture.actor, 40, '', True)], fixture.removes)
        self.assertEqual([fixture.actor], fixture.destroyed)
        self.assertFalse(hasattr(fixture.namespace['sys'], '_client_anchor_ui_probe'))

    def test_unloaded_height_aborts_before_actor_or_page_mutation(self):
        fixture = AnchorFixture()
        fixture.foot = (0., 32768., 0.)
        with self.assertRaisesRegex(AssertionError, 'physically loaded'):
            fixture.install()
        self.assertFalse(fixture.created)
        self.assertEqual(1, len(fixture.entries))
        self.assertFalse(hasattr(fixture.namespace['sys'], '_client_anchor_ui_probe'))

    def test_unknown_creation_preserves_pending_state_without_guessing_actor(self):
        fixture = AnchorFixture()
        fixture.creation_error = TimeoutError('uncertain create')
        with self.assertRaises(TimeoutError):
            fixture.install()
        saved = fixture.namespace['sys']._client_anchor_ui_probe
        self.assertEqual({'state': 'pending', 'attempted': True}, saved['create'])
        self.assertIsNone(saved['actor'])
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertFalse(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])
        self.assertFalse(fixture.destroyed)
        self.assertTrue(hasattr(fixture.namespace['sys'], '_client_anchor_ui_probe'))

    def test_invalid_creation_cannot_destroy_player_or_non_id(self):
        for value in ('native-player-123', '-1', True):
            with self.subTest(value=value):
                fixture = AnchorFixture()
                fixture.creation_value = value
                with self.assertRaises(AssertionError):
                    fixture.install()
                self.assertIsNone(fixture.namespace['sys']._client_anchor_ui_probe['actor'])
                fixture.run(fixture.programs()['destroy_client.py'])
                self.assertFalse(fixture.destroyed)
                self.assertFalse(fixture.run(fixture.programs()['absent_client.py'])['absent'])

    def test_known_creation_recovers_from_host_timeout_without_second_create(self):
        fixture = AnchorFixture()
        programs = fixture.programs()
        fixture.run(programs['install_client.py'])
        fixture.run(programs['destroy_client.py'])
        self.assertTrue(fixture.run(programs['absent_client.py'])['absent'])
        self.assertTrue(fixture.run(programs['verify_client.py'])['restored'])
        self.assertEqual(1, len(fixture.created))

    def test_known_rejected_creation_needs_no_actor_destruction(self):
        fixture = AnchorFixture()
        fixture.creation_value = None
        with self.assertRaises(AssertionError):
            fixture.install()
        self.assertTrue(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        self.assertTrue(fixture.run(fixture.programs()['verify_client.py'])['restored'])
        self.assertFalse(fixture.destroyed)

    def test_pending_bind_disposed_only_by_proven_owned_actor_absence(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.bind_error = TimeoutError('uncertain bind')
        with self.assertRaises(TimeoutError):
            fixture.run(fixture.programs()['plain_client.py'])
        saved = fixture.namespace['sys']._client_anchor_ui_probe
        self.assertEqual('pending', saved['attachments'][0]['state'])
        fixture.run(fixture.programs()['remove_client.py'])
        self.assertFalse(fixture.removes)
        fixture.run(fixture.programs()['pop_client.py'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])
        fixture.run(fixture.programs()['destroy_client.py'])
        restored = fixture.run(fixture.programs()['verify_client.py'])
        self.assertTrue(restored['attachments'][0]['disposed_by_owned_actor_destruction'])
        self.assertEqual(1, len(fixture.binds))

    def test_failed_exact_remove_is_not_retried_and_owned_actor_still_destroyed(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.run(fixture.programs()['plain_client.py'])
        fixture.remove_error = 40
        result = fixture.run(fixture.programs()['remove_client.py'])
        self.assertTrue(result['errors'])
        fixture.run(fixture.programs()['remove_client.py'])
        self.assertEqual(1, len(fixture.removes))
        fixture.run(fixture.programs()['pop_client.py'])
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertTrue(fixture.run(fixture.programs()['verify_client.py'])['actor_absent'])

    def test_partial_ui_push_can_pop_only_owned_top_once(self):
        fixture = AnchorFixture()
        fixture.push_error = TimeoutError('uncertain push')
        with self.assertRaises(TimeoutError):
            fixture.install()
        fixture.nav.is_transitioning = False
        fixture.run(fixture.programs()['pop_client.py'])
        fixture.run(fixture.programs()['pop_client.py'])
        self.assertEqual(1, fixture.pop_calls)
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertTrue(fixture.run(fixture.programs()['verify_client.py'])['restored'])

    def test_unrelated_page_is_never_popped(self):
        fixture = AnchorFixture()
        fixture.install()
        unrelated = SimpleNamespace(key='unrelated')
        fixture.entries.append(unrelated)
        fixture.nav.top = unrelated
        with self.assertRaisesRegex(AssertionError, 'refuse unrelated'):
            fixture.run(fixture.programs()['pop_client.py'])
        self.assertEqual(0, fixture.pop_calls)
        fixture.run(fixture.programs()['destroy_client.py'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])

    def test_uncertain_body_add_is_journaled_before_setter_and_actor_cleanup_survives(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.run(fixture.programs()['plain_client.py'])
        fixture.body_error = 'add'
        with self.assertRaises(TimeoutError):
            fixture.run(fixture.programs()['body_only_minus_client.py'])
        saved = fixture.namespace['sys']._client_anchor_ui_probe
        self.assertTrue(saved['body']['add_attempted'])
        self.assertEqual('pending', saved['journal'][-1]['state'])
        self.assertTrue(fixture.cleanup()['actor_absent'])

    def test_body_depth_moves_only_z_and_keeps_native_item_transform(self):
        fixture = AnchorFixture()
        fixture.install()
        for label in probe.STATES:
            fixture.run(fixture.programs()[label + '_client.py'])
        self.assertEqual([('combine', 'client_anchor_body_offline-owned'),
            ('add', ('client_anchor_body_offline-owned', (0., 0., -2.), (0., 0., 0.))),
            ('offset', ('client_anchor_body_offline-owned', (0., 0., 2.))),
            ('visible', ('client_anchor_body_offline-owned', False))], fixture.body_calls)
        self.assertEqual(probe.BODY, fixture.palette_data)
        self.assertEqual(3, len(fixture.binds))
        self.assertEqual([((0., 0., 0.), (0., 0., 0.), 1.)] * 3, [args[4:] for args in fixture.binds])
        self.assertTrue(fixture.cleanup()['restored'])

    def test_destroy_is_single_attempt_and_absence_is_required(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.run(fixture.programs()['pop_client.py'])
        fixture.destroy_error = TimeoutError('uncertain destroy')
        with self.assertRaises(TimeoutError):
            fixture.run(fixture.programs()['destroy_client.py'])
        with self.assertRaisesRegex(AssertionError, 'Do not retry'):
            fixture.run(fixture.programs()['destroy_client.py'])
        self.assertFalse(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])
        self.assertEqual(1, len(fixture.destroyed))

    def test_always_none_getter_cannot_prove_absence_or_discard_nonce(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.factory.CreateEngineType = lambda actor: SimpleNamespace(GetEngineTypeStr=lambda: None)
        self.assertFalse(fixture.run(fixture.programs()['actor_ready_client.py'])['ready'])
        fixture.run(fixture.programs()['pop_client.py'])
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertEqual([fixture.actor], fixture.destroyed)
        self.assertFalse(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])
        self.assertTrue(hasattr(fixture.namespace['sys'], '_client_anchor_ui_probe'))

    def test_pre_destroy_getter_error_cannot_prevent_known_owned_destruction(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.run(fixture.programs()['actor_ready_client.py'])
        fixture.run(fixture.programs()['pop_client.py'])
        def getter_error():
            raise RuntimeError('type getter failed')
        fixture.factory.CreateEngineType = lambda actor: SimpleNamespace(GetEngineTypeStr=getter_error)
        result = fixture.run(fixture.programs()['destroy_client.py'])
        self.assertEqual([fixture.actor], fixture.destroyed)
        self.assertIn('getter failed', result['pre_destroy_kind_error'])
        fixture.factory.CreateEngineType = lambda actor: SimpleNamespace(GetEngineTypeStr=lambda: None)
        self.assertTrue(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        self.assertTrue(fixture.run(fixture.programs()['verify_client.py'])['restored'])

    def test_fresh_manifest_and_contract_tamper_rejection(self):
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            plan = probe.prepare(RAW, bundle)
            probe.verify_bundle(bundle)
            self.assertEqual(16, len(plan['states']) * plan['frames_per_state'])
            self.assertFalse(plan['shader_or_material_mutation'])
            with self.assertRaisesRegex(ValueError, 'Preserve existing'):
                probe.prepare(RAW, bundle)
            plan['normal_budget_seconds'] = 91
            (bundle / 'plan.json').write_text(json.dumps(plan), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'contract changed'):
                probe.verify_bundle(bundle)

    def test_capture_collision_stops_before_sdk_dispatch(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
            probe.prepare(RAW, bundle)
            base.capture_path(output, 'combined_plus', 1).with_suffix('.capture_error.json').write_text('{}')
            fixture = AnchorFixture()
            with self.assertRaisesRegex(ValueError, 'Preserve existing'):
                probe.execute_probe(bundle, output, fixture.check(), SimpleNamespace(), time.monotonic() + 120.)
            self.assertFalse(fixture.native_calls)

    def test_actual_executor_module_hash_is_verified(self):
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle'
            probe.prepare(RAW, bundle)
            fake = Path(directory) / 'executor.py'
            fake.write_text('wrong executor', encoding='ascii')
            with patch.object(executor, '__file__', str(fake)), self.assertRaisesRegex(ValueError, 'Actual imported'):
                probe.verify_bundle(bundle)

    def test_native_layout_rejects_wrong_actor_nan_and_marker_color(self):
        fixture = AnchorFixture()
        fixture.install()
        status = fixture.run(fixture.programs()['status_client.py'])
        initial = {'actor': fixture.actor, 'size_inputs': fixture.screen_observed}
        for defect in ('actor', 'nan', 'color'):
            with self.subTest(defect=defect):
                tree, observed = fixture.tree(), copy.deepcopy(status)
                if defect == 'actor':
                    tree['children'][0]['props']['entityId'] = fixture.player
                elif defect == 'nan':
                    observed['native_layout']['paper_doll']['x'] = float('nan')
                else:
                    tree['children'][1]['props']['color']['r'] = .5
                with self.assertRaises(ValueError):
                    probe.layout_readback(tree, observed, initial)

    def test_native_item_pose_drift_stops_control_and_known_binding_is_cleaned(self):
        fixture = AnchorFixture()
        fixture.install()
        fixture.itemcomp.GetBindItemRotation = lambda *args: (1., 0., 0.)
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['plain_client.py'])
        self.assertTrue(fixture.cleanup()['restored'])
        self.assertEqual(1, len(fixture.binds))

    def test_expired_normal_budget_prevents_actual_native_dispatch(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
            probe.prepare(RAW, bundle)
            fixture = AnchorFixture()
            with patch.object(executor.BoundedRuntime, 'capture_adapter', lambda value: None):
                report = probe.execute_probe(bundle, output, fixture.check(),
                    SimpleNamespace(guard=lambda: None), time.monotonic() + 20.)
            self.assertFalse(fixture.created)
            self.assertFalse(any('_client_anchor_ui_probe' in code and 'CreateClientEntityByTypeStr' in code
                for code in fixture.native_calls))
            self.assertFalse(report['completed'])

    def test_actor_readiness_timeout_cleans_exact_created_actor_without_push_retry(self):
        def bounded_wait(runtime, label, predicate, read):
            value = read()
            if not predicate(value):
                raise TimeoutError('bounded actor readiness')
            return value
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
            probe.prepare(RAW, bundle)
            fixture = AnchorFixture()
            fixture.bone = None
            with patch.object(executor.BoundedRuntime, 'capture_adapter', lambda value: None), \
                    patch.object(executor.BoundedRuntime, 'wait', bounded_wait):
                report = probe.execute_probe(bundle, output, fixture.check(),
                    SimpleNamespace(guard=lambda: None), time.monotonic() + 120.)
            self.assertFalse(report['completed'])
            self.assertTrue(report['restored'], report['cleanup_errors'])
            self.assertEqual(1, len(fixture.created))
            self.assertEqual([fixture.actor], fixture.destroyed)
            self.assertEqual(0, fixture.pop_calls)

    def run_matrix(self, directory, ordinary=True, markers=True):
        from PIL import Image, ImageDraw
        fixture = AnchorFixture()
        bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
        probe.prepare(RAW, bundle)

        def capture(runtime, path):
            saved = fixture.namespace['sys']._client_anchor_ui_probe
            status = fixture.run((bundle / 'status_client.py').read_text(encoding='ascii'))
            initial = {'actor': fixture.actor, 'size_inputs': fixture.screen_observed}
            layout = probe.layout_readback(fixture.tree(), status, initial)
            record = marker_capture(path, layout, scale=3.9974978978239917,
                translation=(.12427449291408266, -2.1534588486227904), missing=None if markers else 1)
            with Image.open(path) as source:
                image = source.convert('RGB')
            draw = ImageDraw.Draw(image)
            label = saved['control']
            if label in ('body_only_minus', 'combined_minus', 'body_only_plus', 'combined_plus'):
                draw.rectangle((850, 380, 1050, 580), fill=(130, 130, 130))
            if ordinary and label in ('plain', 'combined_plus', 'plain_restored'):
                draw.rectangle((900, 430, 970, 500), fill=(15, 180, 145))
            image.save(path)
            payload = path.read_bytes()
            record['sha256'], record['bytes'] = probe.digest(payload), len(payload)
            record['capture'].update(sha256=record['sha256'], bytes=record['bytes'])
            return record

        with patch.object(executor.BoundedRuntime, 'capture_adapter', lambda value: None), \
                patch.object(executor.BoundedRuntime, 'capture', capture), patch.object(probe.time, 'sleep', lambda value: None):
            report = probe.execute_probe(bundle, output, fixture.check(), SimpleNamespace(guard=lambda: None), time.monotonic() + 120.)
        return fixture, report

    def test_complete_synthetic_native_matrix_and_depth_scoring(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory)
            self.assertTrue(report['completed'], report['errors'])
            self.assertTrue(report['restored'], report['cleanup_errors'])
            self.assertEqual(16, sum(len(row['frames']) for row in report['states'].values()))
            score = probe.score_probe(report)
            self.assertTrue(score['ordinary_visible_candidate'])
            self.assertTrue(score['depth_occlusion_candidate'])
            self.assertEqual(0, score['depth_controls']['minus']['visible_pixels_on_plain_support'])
            self.assertGreaterEqual(score['depth_controls']['plus']['visible_pixels_on_plain_support'], 80)
            self.assertEqual(1., score['body_silhouette_intersection_over_union'])
            self.assertFalse(score['shared_body_depth_proven'])
            self.assertFalse(score['enchantment_glint_accepted'])
            self.assertEqual(3, len(fixture.binds))

    def test_no_ordinary_item_blocks_body_operations_but_cleans_actor(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory, ordinary=False)
            self.assertFalse(report['completed'])
            self.assertTrue(report['restored'])
            self.assertFalse(report['ordinary_gate']['ordinary_visible_candidate'])
            self.assertFalse(fixture.body_calls)
            self.assertEqual({'empty', 'plain'}, set(report['states']))

    def test_failed_marker_is_preserved_and_cannot_be_passed_by_fixed_roi(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory, markers=False)
            self.assertFalse(report['completed'])
            self.assertTrue(report['restored'])
            self.assertTrue(report['ordinary_gate']['ordinary_visible_candidate'])
            self.assertFalse(report['ordinary_gate']['marker_gate_passed'])
            self.assertFalse(report['ordinary_gate']['body_dispatch_allowed'])
            self.assertFalse(fixture.body_calls)
            self.assertEqual(4, sum(len(row['frames']) for row in report['states'].values()))
            self.assertTrue(all(Path(frame['capture']['path']).is_file()
                for row in report['states'].values() for frame in row['frames']))

    def test_persistent_report_write_failure_cannot_interrupt_owned_cleanup(self):
        original, calls = executor.save_report, []
        def fail_after_dispatch(path, report):
            calls.append(len(calls))
            if len(calls) > 4:
                raise OSError('persistent evidence write failure')
            original(path, report)
        with TemporaryDirectory() as directory, patch.object(executor, 'save_report', fail_after_dispatch):
            fixture, report = self.run_matrix(directory)
            self.assertFalse(report['completed'])
            self.assertTrue(report['cleanup_errors'])
            self.assertEqual([fixture.actor], fixture.destroyed)
            self.assertEqual(1, fixture.pop_calls)
            self.assertFalse(hasattr(fixture.namespace['sys'], '_client_anchor_ui_probe'))


if __name__ == '__main__':
    unittest.main()
