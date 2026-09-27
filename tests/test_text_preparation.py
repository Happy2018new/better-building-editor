"""Cold text resources get render turns before workspace entrance can begin."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class TextPreparationTests(unittest.TestCase):
    def setUp(self):
        ui = types.ModuleType('text_prep_test.pyreact')
        ui.Component = lambda function: function
        for name in ('Panel', 'Style', 'Position', 'use_ref', 'use_effect', 'native'):
            setattr(ui, name, None)
        hooks = types.ModuleType('text_prep_test.pyreact.hooks')
        hooks.use_animation_frame = None
        modules = {'text_prep_test.pyreact': ui, 'text_prep_test.pyreact.hooks': hooks}
        path = Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection/projection/text_preparation.py'
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location('text_prep_test.projection.text_preparation', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.preparation = module.TextPreparation()
        self.submitted = []

    def test_mounting_or_binding_an_image_does_not_mean_it_has_rendered(self):
        p = self.preparation
        p.request('atlas_a')
        p.step()
        self.assertFalse(p.settled())
        p.submit = self.submitted.append
        p.step()
        self.assertEqual(['atlas_a'], self.submitted)
        self.assertFalse(p.settled())
        p.step()
        self.assertFalse(p.settled())
        p.step()
        self.assertTrue(p.settled())

    def test_many_labels_share_one_request_and_only_one_atlas_is_submitted_per_frame(self):
        p = self.preparation
        p.submit = self.submitted.append
        for unused in range(100):
            p.request('atlas_a')
            p.request('atlas_b')
        p.step()
        self.assertEqual(['atlas_a'], self.submitted)
        p.step()
        self.assertEqual(['atlas_a', 'atlas_b'], self.submitted)

    def test_last_editor_stage_waits_for_its_new_textures(self):
        p = self.preparation
        p.submit = self.submitted.append
        p.request('header')
        for unused in range(3):
            p.step()
        self.assertTrue(p.settled())
        p.request('inspector')
        self.assertFalse(p.settled())
        for unused in range(3):
            p.step()
        self.assertTrue(p.settled())

    def test_after_reveal_background_labels_cannot_clone_preload_controls(self):
        p = self.preparation
        p.submit = self.submitted.append
        p.seal()
        p.request('hidden_library')
        p.step()
        self.assertEqual([], self.submitted)
        self.assertEqual([], p.pending)

    def test_close_discards_callbacks_and_pending_resources(self):
        p = self.preparation
        p.submit = self.submitted.append
        p.request('cancelled')
        p.dispose()
        p.step()
        self.assertEqual([], self.submitted)
        self.assertEqual([], p.pending)
        self.assertIsNone(p.submit)

    def test_reopen_reuses_only_pages_from_a_completed_preparation(self):
        p = self.preparation
        p.submit = self.submitted.append
        p.request('header')
        for unused in range(3):
            p.step()
        p.seal()
        reopened = type(p)(p.prepared)
        reopened.submit = self.submitted.append
        reopened.request('header')
        reopened.request('cancelled')
        reopened.dispose()
        self.assertEqual({'header'}, p.prepared)
        self.assertEqual(['header'], self.submitted)

    def test_preload_samples_are_transparent_in_all_font_pages(self):
        from PIL import Image
        directory = Path(__file__).resolve().parents[1] / 'resource_pack/textures/modern_projection/type'
        for path in directory.glob('*.png'):
            with Image.open(path) as image:
                self.assertEqual((0, 0), image.getchannel('A').crop((0, 0, 2, 2)).getextrema(),
                                 path.name)


if __name__ == '__main__':
    unittest.main()
