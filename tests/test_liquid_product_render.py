"""Water native construction limits preserve shared publication and other owners."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.liquid_product_deployment import candidate_profile
from projection.liquid_product_projection import ProductLiquidProjection
from projection.liquid_product_render import ProductWorldLiquidRenderer
from projection.liquid_projection import LiquidProjection
from projection.liquid_render import WorldLiquidRenderer
from projection.model import Document
from tests.test_liquid_render import ANCHOR, Runtime, group


class ProductLiquidRenderTests(unittest.TestCase):
    def finish(self, renderer, start=0.):
        for index in range(20):
            if renderer.advance(start + index * .1):
                return
            self.assertIsNone(renderer.error)
        self.fail('Bounded water preparation did not complete')

    def test_one_create_per_advance_then_complete_publication(self):
        runtime = Runtime()
        renderer = ProductWorldLiquidRenderer(runtime, 4, 0, (16.,) * 3, (0.,) * 3)
        groups = tuple(group(key=key) for key in range(4))
        self.assertTrue(renderer.begin(groups, ANCHOR, 0.))
        for index in range(4):
            self.assertFalse(renderer.advance(.1 + index * .1))
            self.assertEqual(index + 1, len(runtime.models))
            self.assertTrue(all(runtime.hidden(model) for model in runtime.models))
            self.assertTrue(all(runtime.models[model]['bounds'] == ((-4.,) * 3, (4.,) * 3)
                                for model in runtime.models))
        for now in (.6, .7, .8):
            renderer.advance(now)
        self.assertEqual(4, len(renderer.active))
        self.assertTrue(all(not runtime.hidden(model) for model in runtime.models))
        self.assertTrue(renderer.close())
        self.assertEqual({}, runtime.models)

    def test_cancellation_never_constructs_remaining_models(self):
        runtime = Runtime()
        renderer = ProductWorldLiquidRenderer(runtime, 4, 0, (16.,) * 3, (0.,) * 3)
        renderer.begin(tuple(group(key=key) for key in range(4)), ANCHOR, 0.)
        renderer.advance(.1)
        self.assertEqual(1, len(runtime.models))
        self.assertTrue(renderer.cancel_preparation())
        renderer.advance(.2)
        self.assertEqual({}, runtime.models)
        self.assertEqual(1, runtime.serial)

    def test_product_factory_and_explicit_override_are_independent(self):
        runtime = Runtime()
        profile = candidate_profile()
        document = Document((4, 4, 4))
        owner = profile.projection_factory(runtime, document, ANCHOR, profile, 0)
        self.assertIsInstance(owner, ProductLiquidProjection)
        self.assertIsInstance(owner.renderer, ProductWorldLiquidRenderer)
        self.assertEqual(1, owner.renderer.CREATIONS_PER_FRAME)
        overridden = ProductLiquidProjection(runtime, document, ANCHOR, profile, 0,
                                             renderer_factory=WorldLiquidRenderer)
        self.assertIs(type(overridden.renderer), WorldLiquidRenderer)
        self.assertEqual(8, overridden.renderer.CREATIONS_PER_FRAME)

    def test_shared_owner_keeps_existing_default_even_for_product_profile(self):
        runtime = Runtime()
        profile = candidate_profile()
        owner = LiquidProjection(runtime, Document((4, 4, 4)), ANCHOR, profile, 0)
        self.assertIs(type(owner.renderer), WorldLiquidRenderer)
        self.assertEqual(8, owner.renderer.CREATIONS_PER_FRAME)
        self.assertEqual(8, WorldLiquidRenderer.CREATIONS_PER_FRAME)
        self.assertEqual(((-2.,) * 3, (2.,) * 3), WorldLiquidRenderer.BOUNDING_BOX)
        self.assertEqual(((-4.,) * 3, (4.,) * 3), ProductWorldLiquidRenderer.BOUNDING_BOX)

    def test_slow_replacement_preserves_published_generation_until_explicit_commit(self):
        runtime = Runtime()
        renderer = ProductWorldLiquidRenderer(runtime, 4, 0, (16.,) * 3, (0.,) * 3)
        self.addCleanup(renderer.close)
        first = tuple(group(key=key, height=.7) for key in range(4))
        renderer.begin(first, ANCHOR, 0.)
        self.finish(renderer)
        old_ids = set(runtime.models)
        renderer.begin(tuple(group(key=key, height=.3) for key in range(4)),
                       ANCHOR, 1., deferred=True)
        for index in range(4):
            self.assertFalse(renderer.advance(1. + index * .1))
            self.assertEqual(4 + index + 1, len(runtime.models))
            self.assertTrue(all(not runtime.hidden(model) for model in old_ids))
            self.assertTrue(all(runtime.hidden(model) for model in set(runtime.models) - old_ids))
        self.finish(renderer, 1.4)
        self.assertEqual(old_ids, {record['model_id'] for record in renderer.active.values()})
        self.assertTrue(renderer.prepare_publication())
        self.assertTrue(renderer.finalize_publication())
        self.assertTrue(renderer.retry_retired())
        self.assertTrue(old_ids.isdisjoint(runtime.models))
        self.assertEqual(4, len(runtime.models))
        self.assertTrue(all(not runtime.hidden(model) for model in runtime.models))

    def test_real_owner_cancellation_keeps_old_water_and_never_creates_queued_tail(self):
        runtime = Runtime()
        runtime.session = SimpleNamespace(opacity=.5)
        adapter = candidate_profile()
        planned = [tuple(group(key=key) for key in range(4))]
        owner = adapter.projection_factory(runtime, Document((4, 4, 4)), ANCHOR,
            adapter, 0, plan_factory=lambda *args: iter(planned[0]))
        self.addCleanup(owner.close)
        owner.renderer.SETTLE_SECONDS = 0.
        owner.request()
        for index in range(20):
            with patch('projection.liquid_projection.time.time', return_value=index * .1):
                if owner.advance():
                    break
        self.assertTrue(owner.ready)
        owner.publish()
        old_ids = set(runtime.models)
        planned[0] = tuple(group(key=key, height=.3) for key in range(4))
        revision = owner.request(deferred=True)
        with patch('projection.liquid_projection.time.time', return_value=3.):
            self.assertFalse(owner.advance())
        self.assertEqual(5, runtime.serial)
        self.assertTrue(owner.cancel_candidate(revision))
        self.assertEqual(old_ids, set(runtime.models))
        self.assertTrue(all(not runtime.hidden(model) for model in old_ids))
        self.assertTrue(owner.advance())
        self.assertEqual(5, runtime.serial)


if __name__ == '__main__':
    unittest.main()
