"""Native resource reuse must not hide owner drift or counterfeit default runs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qualify_book_product_r18 import (default_binding, BODY_SOURCES, ENGINE_VERSION, OWNER_SOURCES, RESOURCE_KEYS,
                                      REQUIRED_GATES, body_binding, resource_binding, source_binding)


class BookQualificationTests(unittest.TestCase):
    def test_old_owner_counts_cannot_admit_missing_boundary_pixels(self):
        self.assertIn('body_boundary_pixels', REQUIRED_GATES)
        passed, errors = body_binding(None, {}, {}, Path('unused'))
        self.assertFalse(passed)
        self.assertTrue(errors)

    def test_reusing_native_pixels_requires_all_render_resources_and_owned_entries(self):
        current = dict(contract_present=True, contract_sha256='a'*64, files={'mesh':'b'*64},
                       models={'book':{'material':'book'}}, materials={'book':{'+states':['InvertCulling']}})
        report = {'installed_sources':deepcopy(current)}
        self.assertEqual([], resource_binding({'native':report}, current))
        for key, value in (('files', {'mesh':'c'*64}), ('models', {'book':{'material':'alias'}}),
                           ('materials', {'book':{'+states':['DisableCulling']}})):
            bad = deepcopy(report)
            bad['installed_sources'][key] = value
            self.assertTrue(resource_binding({'native':bad}, current))

    def test_owner_closure_rejects_changed_or_missing_owner_and_body_registration(self):
        current = dict(owner_files=dict.fromkeys(OWNER_SOURCES, 'a'*64),
                       body_files=dict.fromkeys(BODY_SOURCES, 'b'*64))
        for key in ('resource_pack/blocks.json','resource_pack/textures/terrain_texture.json'):
            current[key] = {'body':'render-registration'}
        report = {'installed_sources':deepcopy(current)}
        self.assertEqual([], source_binding(report, current))
        bad = deepcopy(report)
        bad['installed_sources']['owner_files'][OWNER_SOURCES[-1]] = 'c'*64
        self.assertTrue(source_binding(bad, current))
        del bad['installed_sources']['owner_files'][OWNER_SOURCES[0]]
        self.assertTrue(source_binding(bad, current))
        bad = deepcopy(report)
        bad['installed_sources']['resource_pack/blocks.json'] = {'body':'wrong-model'}
        self.assertTrue(source_binding(bad, current))

    def test_default_path_must_bind_its_disposable_admission_without_profile_assignment(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'qualification.json'
            owners = dict.fromkeys(OWNER_SOURCES, 'a'*64)
            resources = dict(contract_present=True, contract_sha256='d'*64,
                             files={'mesh':'b'*64}, models={'book':{}}, materials={'book':{}})
            admission = dict(stage='isolated_default_test', engine_version=ENGINE_VERSION,
                reviewed=True, resource_snapshot=resources,
                implementation_sha256=owners, gates=dict.fromkeys(REQUIRED_GATES, True))
            path.write_text(json.dumps(admission), encoding='ascii')
            report = dict(stage='production_default', production_default_requested=True,
                profile_assignment_performed=False, default_profile=dict(qualified=True,
                    stage='isolated_default_test', qualification_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            measured = {'owner_matrix_passed':True, 'owner_matrix':{'occupancy_included':True}}
            owner = {'installed_sources':dict(resources, owner_files=owners)}
            self.assertTrue(default_binding(report, measured, path, owner))
            report['profile_assignment_performed'] = True
            with self.assertRaisesRegex(ValueError, 'candidate'):
                default_binding(report, measured, path, owner)
