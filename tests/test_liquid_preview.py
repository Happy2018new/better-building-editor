"""Editor water plans retain snapshots across edits, failures and filtering."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.liquid_preview import LiquidPreview
from projection.liquid_render_plan import LiquidSurface
from projection.model import Document


MODELS = {('still_water_grey', None): 'registered_water_model'}


class LiquidPreviewTests(unittest.TestCase):
    def setUp(self):
        self.sources, self.events = [], []
        self.hidden = set()
        self.session = SimpleNamespace(
            editor=SimpleNamespace(document=Document((8, 3, 8)), revision=0, layer=1),
            preview_hidden=lambda: tuple(sorted(self.hidden)), solo_layer=False,
            emit=self.events.append)
        test = self
        class Provider(object):
            def surface(self, document, pos, layer, value):
                test.sources.append(document)
                return LiquidSurface(pos, layer, (.5,) * 4, 63, 'still_water_grey')
        self.preview = LiquidPreview(self.session, lambda document: Provider(), MODELS, 32)

    def finish(self):
        for unused in range(100):
            if self.preview.advance():
                return
        self.fail('Liquid plan never completed')

    def edit(self, pos, cell):
        self.session.editor.document.set_cell(pos, cell)
        self.session.editor.revision += 1

    def test_cooperative_replacement_uses_snapshot_and_cancels_stale_edit(self):
        water = material('water')
        self.edit((1, 1, 1), water)
        self.finish()
        previous = dict(self.preview.groups)
        self.edit((5, 1, 1), water)
        self.preview.BUILD_SECONDS = 0.
        self.assertFalse(self.preview.advance())
        self.assertEqual(previous, self.preview.groups)
        old_snapshot = self.preview.document
        self.edit((5, 1, 1), AIR)
        self.edit((5, 1, 5), water)
        self.assertEqual(water, old_snapshot.get((5, 1, 1)))
        self.finish()
        self.assertEqual({(0, 0, 0), (4, 0, 4)}, {group.origin for group in self.preview.groups.values()})

    def test_failure_preserves_previous_plan_and_latches_until_retry(self):
        self.edit((1, 1, 1), material('water'))
        self.finish()
        previous = dict(self.preview.groups)
        self.preview.models = {}
        self.edit((5, 1, 1), material('water'))
        self.assertFalse(self.preview.advance())
        self.assertIsInstance(self.preview.error, ValueError)
        self.assertEqual(previous, self.preview.groups)
        requests = len(self.sources)
        for unused in range(5):
            self.assertFalse(self.preview.advance())
        self.assertEqual(requests, len(self.sources))
        self.preview.models = MODELS
        self.preview.retry()
        self.finish()
        self.assertIsNone(self.preview.error)
        self.assertEqual(2, len(self.preview.groups))

    def test_strict_background_water_and_hidden_layers_preserve_complete_context(self):
        self.edit((1, 1, 1), make_cell(material('oak_fence'), material('water')))
        self.edit((1, 2, 1), material('water'))
        self.hidden.add(2)
        self.finish()
        self.assertEqual(1, len(self.preview.groups))
        self.assertEqual(material('water'), self.sources[-1].get((1, 2, 1)))
        self.assertEqual(1, (int(next(iter(self.preview.groups.values())).uniforms[0][0]) >> 6) & 1)
        self.hidden.clear()
        self.session.solo_layer = True
        self.finish()
        self.assertEqual(1, len(self.preview.groups))

    def test_biome_changes_update_payload_without_replacing_slot_keys(self):
        self.edit((1, 1, 1), material('water'))
        self.finish()
        keys, old = self.preview.keys, tuple(self.preview.groups.values())
        event_count = len(self.events)
        self.session.editor.document.biome = 'swampland'
        self.finish()
        self.assertEqual(keys, self.preview.keys)
        self.assertNotEqual(old, tuple(self.preview.groups.values()))
        self.assertEqual(event_count, len(self.events))

    def test_clear_and_unmount_release_plan_and_stop_rescanning(self):
        self.edit((1, 1, 1), material('water'))
        self.finish()
        self.edit((1, 1, 1), AIR)
        self.finish()
        self.assertEqual({}, self.preview.groups)
        self.preview.close()
        requests = len(self.sources)
        self.edit((1, 1, 1), material('water'))
        self.assertFalse(self.preview.advance())
        self.assertEqual(requests, len(self.sources))
