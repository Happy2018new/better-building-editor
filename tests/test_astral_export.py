"""The frozen old VFX must be independently reusable alongside golden VFX."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package_astral_effects import build, SOURCE
from audit_runtime_imports import audit


class AstralExportTests(unittest.TestCase):
    def test_independent_pack_references_resolve_and_namespace_does_not_conflict(self):
        rp = SOURCE / 'resource_pack'
        materials = json.loads((rp/'materials/entity.material').read_text())['materials']
        geometries = {g['description']['identifier'] for p in (rp/'models').rglob('*.json')
                      for g in json.loads(p.read_text())['minecraft:geometry']}
        controllers = json.loads((rp/'render_controllers/astral_survey_anchor.json').read_text())['render_controllers']
        for key, material in materials.items():
            if key == 'version': continue
            parent = key.split(':')[1]
            self.assertTrue(parent == 'entity_static' or any(k.split(':')[0] == parent for k in materials))
            for field in ('vertexShader', 'fragmentShader'):
                if field in material: self.assertTrue((rp/material[field]).is_file())
        for path in (rp/'entity').glob('*.json'):
            desc = json.loads(path.read_text())['minecraft:client_entity']['description']
            self.assertTrue(desc['identifier'].startswith('astral_survey:'))
            self.assertIn(desc['geometry']['default'], geometries)
            self.assertIn(desc['render_controllers'][0], controllers)
            self.assertTrue((rp/(desc['textures']['default']+'.png')).is_file())
            self.assertTrue(any(k.split(':')[0] == desc['materials']['default'] for k in materials))
            bp = json.loads((SOURCE/'behavior_pack/entities'/path.name.replace('.entity','')).read_text())
            self.assertEqual(desc['identifier'], bp['minecraft:entity']['description']['identifier'])
        for path in SOURCE.rglob('*.py'):
            code = path.read_text(encoding='utf8')
            self.assertNotIn('modern_projection', code)
            self.assertNotIn('modern_projection:', code)

    def test_archive_integrity_and_reproducible_output(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp)/'a.zip', Path(temp)/'b.zip'
            build(a);build(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                self.assertIsNone(archive.testzip())
                sums=archive.read('astral_survey_v1/SHA256SUMS.txt').decode().splitlines()
                for line in sums:
                    digest, name = line.split('  ', 1)
                    self.assertEqual(digest,hashlib.sha256(archive.read('astral_survey_v1/'+name)).hexdigest())

    def test_standalone_runtime_passes_same_module_whitelist(self):
        self.assertFalse(audit(SOURCE/'behavior_pack')['violations'])


if __name__ == '__main__': unittest.main()
