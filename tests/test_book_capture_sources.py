"""Material mutations must invalidate book evidence even with an old contract."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from probe_book_native_r16 import book_sources


class BookCaptureSourceTests(unittest.TestCase):
    def test_actual_materials_are_fingerprinted_without_diagnostic_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {
                'tools/data/book_resource_contract_nemc310_v1.json': {'output_sha256': {}},
                'resource_pack/models/netease_models.json': {},
                'resource_pack/materials/entity.material': {'materials': {}},
            }
            registry = files['resource_pack/models/netease_models.json']
            materials = files['resource_pack/materials/entity.material']['materials']
            for family in ('enchanting_table', 'lectern'):
                for suffix in ('', '_world'):
                    name = 'modern_projection_book_' + family + suffix
                    registry[name] = {'material': name}
                    materials[name + ':entity_for_skeleton_alpha'] = {
                        '+states': ['Blending'], '-states': ['DisableDepthWrite'],
                        'vertexShader': 'shaders/book.vertex',
                        'fragmentShader': 'shaders/book.fragment',
                    }
            for relative, value in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding='ascii')
            for suffix in ('vertex', 'fragment'):
                path = root / ('resource_pack/shaders/book.' + suffix)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('shader fixture', encoding='ascii')
            before = book_sources(root)
            first = next(iter(materials.values()))
            first['+states'].append('DisableCulling')
            (root / 'resource_pack/materials/entity.material').write_text(
                json.dumps({'materials': materials}), encoding='ascii')
            after = book_sources(root)
            self.assertEqual(before['contract_sha256'], after['contract_sha256'])
            self.assertEqual(before['files'], after['files'])
            self.assertNotEqual(before['materials'], after['materials'])


if __name__ == '__main__':
    unittest.main()
