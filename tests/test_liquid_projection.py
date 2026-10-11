"""Logical neighbors, publication and cleanup across world liquid updates."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.liquid_projection import LiquidProjection
from projection.liquid_render import WorldLiquidRenderer
from projection.liquid_render_plan import LiquidSurface
from projection.model import Document, Editor
from test_liquid_render import Runtime as ModelRuntime
import test_bridge as bridge_tests


def profile(sources, budget=16):
    class Provider(object):
        def surface(self, document, pos, layer, value):
            sources.append((document, pos, layer))
            return LiquidSurface(pos, layer, (.5,) * 4, 63, 'still_water_grey')
    return SimpleNamespace(provider_factory=lambda document: Provider(),
        models={('still_water_grey', None): 'registered_water'}, max_groups=budget,
        world_models={('still_water_grey', None): 'registered_world_water'},
        world_scale=(16.,) * 3, world_rotation=(0., 180., 0.))


class LiquidProjectionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ModelRuntime()
        self.runtime.session = SimpleNamespace(opacity=.4)
        self.source = Document((8, 3, 8), {(1, 1, 1): material('water'),
            (2, 1, 1): make_cell(material('oak_fence'), material('water')),
            (5, 2, 5): material('water')})
        self.sources = []
        self.controller = LiquidProjection(self.runtime, self.source, (10, 64, 20),
                                           profile(self.sources), 0)
        self.now = 0.

    def finish(self):
        for unused in range(200):
            self.now += .1
            with patch('projection.liquid_projection.time.time', return_value=self.now):
                if self.controller.advance():
                    return
        self.fail('Liquid projection did not finish')

    def test_initial_models_stay_hidden_until_published_and_keep_world_origin(self):
        self.controller.request(self.source.palette_data())
        self.finish()
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.controller.publish()
        self.assertTrue(all(not self.runtime.hidden(model) for model in self.runtime.models))
        self.assertEqual({(12., 66., 22.), (16., 66., 26.)}, set(self.runtime.positions.values()))
        self.assertTrue(all(data['scale'] == (16.,) * 3 for data in self.runtime.models.values()))
        self.assertTrue(all(data['name'] == 'registered_world_water' for data in self.runtime.models.values()))

    def test_occupied_cell_changes_draws_without_deleting_neighbors_or_logical_layers(self):
        self.controller.request(self.source.palette_data())
        self.finish()
        self.controller.publish()
        occupied = bytearray(self.source.volume)
        occupied[(1 * 8 + 1) * 8 + 1] = 2
        self.sources.clear()
        self.controller.request(occupied=occupied)
        occupied[:] = bytearray(self.source.volume)
        self.finish()
        self.assertEqual({((2, 1, 1), 1), ((5, 2, 5), 0)},
                         {(pos, layer) for document, pos, layer in self.sources})
        self.assertTrue(all(document.get((1, 1, 1)) == material('water')
                            for document, pos, layer in self.sources))
        self.assertTrue(all(not self.runtime.hidden(model) for model in self.runtime.models))

    def test_targets_visibility_and_source_are_independent_and_source_is_snapshot(self):
        controller = LiquidProjection(self.runtime, self.source, (10, 64, 20),
                                      profile(self.sources), 0, hidden=(2,))
        targets = self.source.palette_data(lambda pos: pos == (2, 1, 1))
        controller.request(targets)
        self.source.set_cell((1, 1, 1), AIR)
        self.controller = controller
        self.finish()
        self.assertEqual([((2, 1, 1), 1)], [(pos, layer) for doc, pos, layer in self.sources])
        self.assertEqual(material('water'), self.sources[0][0].get((1, 1, 1)))

    def test_biome_replacement_retains_old_models_until_new_payload_is_ready(self):
        self.controller.request()
        self.finish()
        self.controller.publish()
        old = dict(self.runtime.models)
        old_payload = [record['uniforms'][4] for record in old.values()]
        self.controller.set_biome('swampland')
        self.assertEqual(old, self.runtime.models)
        self.finish()
        self.assertNotEqual(old_payload, [record['uniforms'][4] for record in self.runtime.models.values()])
        self.assertEqual('swampland', self.sources[-1][0].biome)

    def test_plan_failure_latches_and_preserves_previously_published_water(self):
        self.controller.request()
        self.finish()
        self.controller.publish()
        old = dict(self.runtime.models)
        self.controller.profile.world_models = {}
        self.controller.request()
        self.assertFalse(self.controller.advance())
        self.assertIsInstance(self.controller.error, ValueError)
        requests = len(self.sources)
        for unused in range(10):
            self.assertFalse(self.controller.advance())
        self.assertEqual(requests, len(self.sources))
        self.assertEqual(old, self.runtime.models)
        self.assertTrue(all(not self.runtime.hidden(model) for model in self.runtime.models))

    def test_close_cancels_unfinished_plan_and_retries_failed_owned_release(self):
        self.controller.request()
        self.finish()
        self.controller.publish()
        self.runtime.remove_ok = False
        self.assertFalse(self.controller.close())
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.runtime.remove_ok = True
        self.assertTrue(self.controller.close())
        self.assertEqual({}, self.runtime.models)
        self.assertFalse(self.controller.advance())

    def test_invalid_occupancy_cannot_replace_an_inflight_request(self):
        self.controller.request()
        iterator = self.controller.iterator
        for invalid in (bytearray(1), bytearray([3]) * self.source.volume):
            with self.assertRaises(ValueError):
                self.controller.request(occupied=invalid)
            self.assertIs(iterator, self.controller.iterator)


class ProjectionRuntime(bridge_tests.Runtime):
    def __init__(self):
        super().__init__()
        self.liquid_models = ModelRuntime()

    def CreateModel(self, entity):
        return self.liquid_models if entity == 'level' else super().CreateModel(entity)

    def GetCurrentDimension(self):
        return 0


class WorldLiquidIntegrationTests(unittest.TestCase):
    def setUp(self):
        bridge_tests.ProjectionLifecycleTests.setUp(self)
        previous_runtime = self.runtime
        self.runtime = ProjectionRuntime()
        self.runtime.timers = previous_runtime.timers
        self.bridge.factory = self.bridge.system = self.runtime
        self.sources = []
        self.bridge.session.liquid_profile = profile(self.sources)
        self.bridge.session.editor = Editor(Document((4, 3, 4),
            {(1, 1, 1): make_cell(material('oak_fence'), material('water'))}))
        self.bridge.geometry = lambda *a, **k: k.get('name') or 'body_model'
        self.settle = patch.object(WorldLiquidRenderer, 'SETTLE_SECONDS', 0.)
        self.settle.start()

    def tearDown(self):
        self.settle.stop()
        bridge_tests.ProjectionLifecycleTests.tearDown(self)

    def drain(self):
        bridge_tests.ProjectionLifecycleTests.drain_projection(self, limit=400)

    def test_public_build_publishes_water_and_close_releases_both_native_owners(self):
        self.bridge.project_large((10, 64, 20))
        self.drain()
        work = self.bridge.projection_work
        self.assertTrue(work.ready)
        self.assertIsNone(work.error)
        self.assertIs(work.liquid, self.bridge.projection_liquid)
        models = self.runtime.liquid_models
        self.assertEqual(1, len(models.models))
        self.assertTrue(all(not models.hidden(model) for model in models.models))
        self.bridge.stop_projection()
        self.drain()
        self.assertEqual({}, models.models)
        self.assertIsNone(self.bridge.projection_liquid)
        self.assertTrue(work.liquid.closed)

    def test_failed_body_attachment_retains_previous_water_and_cleans_new_water(self):
        self.bridge.project_large((10, 64, 20))
        self.drain()
        old = self.bridge.projection_liquid
        old_ids = set(self.runtime.liquid_models.models)
        self.runtime.success = False
        self.bridge.project_large((20, 64, 20))
        self.drain()
        self.assertIsNotNone(self.bridge.projection_work.error)
        self.assertIs(old, self.bridge.projection_liquid)
        self.assertEqual(old_ids, set(self.runtime.liquid_models.models))
        self.assertTrue(all(not self.runtime.liquid_models.hidden(model) for model in old_ids))

    def test_stop_and_repeated_manual_build_cancel_unpublished_water(self):
        self.bridge.project_large((10, 64, 20))
        first = self.bridge.projection_work
        first.liquid.renderer.SETTLE_SECONDS = 60.
        for unused in range(400):
            self.runtime.timers.pop(0)()
            if first.liquid.renderer.staging:
                break
        self.assertTrue(first.liquid.renderer.staging)
        self.bridge.project_large((20, 64, 20))
        self.assertTrue(first.liquid.closed)
        self.bridge.stop_projection()
        self.drain()
        self.assertEqual({}, self.runtime.liquid_models.models)

    def test_missing_projection_commits_occupancy_to_water_without_mutating_source(self):
        self.bridge.session.projection_missing = True
        self.bridge.project_large((10, 64, 20))
        self.drain()
        tracker, water = self.bridge.projection_occupancy, self.bridge.projection_liquid
        state = tracker.rendered[:]
        state[tracker.index((1, 1, 1))] = 2
        tracker.snapshot = state
        tracker.replace(tracker.model, tracker.anchor)
        for unused in range(100):
            self.bridge.update_projection_occupancy()
            if water.ready:
                break
        self.assertTrue(water.ready)
        self.assertEqual({}, self.runtime.liquid_models.models)
        self.assertEqual(material('water'), water.document.get_layer((1, 1, 1), 1))
