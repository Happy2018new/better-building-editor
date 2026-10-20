"""Protect native flipbooks and the centered plant's frozen silhouette."""
import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import generate_firefly_bush_animation as animation


class FireflyAnimationTests(unittest.TestCase):
    def test_native_declarations_keep_duplicate_variants_and_local_precedence(self):
        unused, native = animation.source_data()
        local = [{'atlas_tile': 'magma', 'ticks_per_frame': 9},
                 {'atlas_tile': 'another_local_sprite', 'ticks_per_frame': 2}]
        original = copy.deepcopy((native, local))
        merged = animation.merged_entries(native, local)
        self.assertEqual(80, len(native))
        self.assertEqual(native, merged[:80])
        self.assertEqual(local, merged[80:82])
        self.assertEqual(animation.DECLARATION, merged[82])
        names = [row['atlas_tile'] for row in native]
        self.assertLess(len(set(names)), len(names))
        self.assertEqual(original, (native, local))
        merged[0]['atlas_tile'] = 'mutation'
        self.assertEqual(original, (native, local))

    def test_regeneration_does_not_duplicate_baseline_or_own_declaration(self):
        unused, native = animation.source_data()
        first = animation.merged_entries(native, [{'atlas_tile': 'local'}])
        second = animation.merged_entries(native, first)
        self.assertEqual(first, second)
        self.assertEqual(82, len(second))

    def test_conflicting_and_duplicate_own_declarations_are_rejected(self):
        unused, native = animation.source_data()
        bad = dict(animation.DECLARATION, ticks_per_frame=99)
        for local in ([bad], [animation.DECLARATION] * 2,
                      [animation.DECLARATION, bad], {'atlas_tile': 'local'}, [None]):
            with self.subTest(local=local), self.assertRaises(ValueError):
                animation.merged_entries(native, local)

    def test_source_bytes_and_geometry_alpha_provenance_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            shutil.copytree(animation.SOURCE, source)
            path = source / 'body.png'
            path.write_bytes(path.read_bytes() + b'tampered')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                animation.source_data(source)
        manifest, unused = animation.source_data()
        profile = animation.load_json(ROOT / manifest['fixed_centered_geometry_source'])
        profile['plants']['firefly_bush']['texture_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'silhouettes'):
            animation.centered_texture(profile)

    def test_ten_distinct_frames_keep_the_exact_carried_alpha(self):
        raw = animation.composited_strip()
        self.assertEqual('02724cb3a6218e044a58726fa5e953d6a407b86d91c0c13997694bfe8cb20bf0',
                         hashlib.sha256(raw).hexdigest())
        with Image.open(BytesIO(raw)) as strip, Image.open(animation.SOURCE / 'carried.png') as carried:
            self.assertEqual((16, 160), strip.size)
            alpha = carried.convert('RGBA').getchannel('A').tobytes()
            frames = []
            for index in range(10):
                frame = strip.convert('RGBA').crop((0, index * 16, 16, (index + 1) * 16))
                self.assertEqual(alpha, frame.getchannel('A').tobytes())
                frames.append(frame.tobytes())
            self.assertEqual(10, len(set(frames)))

    def test_generation_preserves_other_atlas_entries_and_local_flipbooks(self):
        manifest, native = animation.source_data()
        atlas = animation.load_json(ROOT / animation.ATLAS)
        before = copy.deepcopy(atlas)
        local = [{'atlas_tile': 'magma', 'ticks_per_frame': 11}]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in (animation.ATLAS, manifest['fixed_centered_geometry_source']):
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)
            (root / animation.FLIPBOOK).write_text(json.dumps(local), encoding='utf8')
            first = animation.outputs(root)
            self.assertEqual({animation.ATLAS, animation.FLIPBOOK, animation.STRIP}, set(first))
            generated = json.loads(first[animation.ATLAS])
            before['texture_data'][animation.KEY] = {'textures': animation.TEXTURE}
            self.assertEqual(before, generated)
            self.assertEqual(native + local + [animation.DECLARATION], json.loads(first[animation.FLIPBOOK]))
            for relative, raw in first.items():
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
            self.assertEqual(first, animation.outputs(root))

    def test_strict_json_rejects_ambiguous_or_invalid_source(self):
        for text in ('{"a":1,"a":2}', '[NaN]', '[Infinity]', '[1,]', '//comment\n[]'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'input.json'
                path.write_text(text, encoding='utf8')
                with self.assertRaises(ValueError):
                    animation.load_json(path)


if __name__ == '__main__':
    unittest.main()
