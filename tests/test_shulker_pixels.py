"""Native/proxy image comparisons reject label swaps and missing texture proof."""
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from shulker_pixels import central_object, native_proxy_comparison, pair_comparison


def patterned(facing):
    frame = Image.new('RGB', (200, 200), (110, 170, 210))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((50, 50, 149, 149), fill=(115, 42, 150))
    draw.rectangle((56 + facing * 8, 60, 60 + facing * 8, 133), fill=(180, 65, 205))
    draw.rectangle((63, 72 + facing * 7, 138, 75 + facing * 7), fill=(85, 25, 110))
    draw.rectangle((72 + facing * 5, 124 - facing * 4, 86 + facing * 5, 138 - facing * 4),
                   fill=(165, 52, 190))
    return frame


class ShulkerPixelTests(unittest.TestCase):
    def test_brightness_changes_and_unrelated_background_do_not_change_texture_match(self):
        native = [patterned(facing) for facing in range(6)]
        proxy = [ImageEnhance.Brightness(frame).enhance(1.25) for frame in native]
        evidence = native_proxy_comparison(native, proxy)
        self.assertTrue(evidence['passed'], evidence)
        self.assertTrue(all(row['texture_cosine'] > .9 for row in evidence['same_face']))

    def test_swapped_face_labels_fail_even_when_all_models_exist(self):
        native = [patterned(facing) for facing in range(6)]
        proxy = [frame.copy() for frame in native]
        proxy[2], proxy[5] = proxy[5], proxy[2]
        evidence = native_proxy_comparison(native, proxy)
        self.assertFalse(evidence['passed'])
        self.assertEqual([5], evidence['same_face'][2]['best_proxy_faces'])
        self.assertEqual([2], evidence['same_face'][5]['best_proxy_faces'])

    def test_uniform_boxes_do_not_supply_texture_direction_evidence(self):
        blank = Image.new('RGB', (200, 200), 'black')
        ImageDraw.Draw(blank).rectangle((50, 50, 149, 149), fill=(115, 42, 150))
        evidence = native_proxy_comparison([blank] * 6, [blank] * 6)
        self.assertFalse(evidence['passed'])
        self.assertTrue(all(row['texture_cosine'] is None for row in evidence['same_face']))

    def test_empty_or_displaced_models_fail_and_unrelated_purple_objects_are_ignored(self):
        with self.assertRaises(AssertionError):
            central_object(Image.new('RGB', (200, 200), 'black'))
        displaced = Image.new('RGB', (200, 200), 'black')
        ImageDraw.Draw(displaced).rectangle((2, 2, 30, 30), fill=(120, 40, 180))
        with self.assertRaises(AssertionError):
            central_object(displaced)
        frame = patterned(1)
        ImageDraw.Draw(frame).rectangle((2, 2, 30, 30), fill=(120, 40, 180))
        unused_image, unused_mask, evidence = central_object(frame)
        self.assertEqual(1, evidence['nearby_components_ignored'])
        self.assertEqual((49, 49, 151, 151), evidence['bbox'])

    def test_proxy_scale_error_is_retained_instead_of_hidden_by_image_normalization(self):
        frame = patterned(3)
        proxy = Image.new('RGB', frame.size, 'black')
        crop = frame.crop((50, 50, 150, 150)).resize((150, 150))
        proxy.paste(crop, (25, 25))
        evidence = pair_comparison(frame, proxy)
        self.assertGreater(evidence['scale_relative_error'], .4)


if __name__ == '__main__':
    unittest.main()
