"""Deployment provenance rejects drift even when runtime gates remain true."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_render_qualifications import (PREFIX, RESOURCE_CONTRACTS, json_digest,
                                          source_digest, verify_bundle)


class QualificationProvenanceTests(unittest.TestCase):
    def fixture(self):
        source = PREFIX + 'spawner_marker.py'
        manifest = {'engine_version': '3.10.0.420447', 'gates': {'default_path': True},
                    'implementation_sha256': {source: hashlib.sha256(b'original').hexdigest()}}
        raw = json.dumps(manifest).encode('ascii')
        gate = 'PRODUCT_QUALIFIED = True\nQUALIFICATION_SHA256 = %r\n' % hashlib.sha256(raw).hexdigest()
        return {PREFIX+'gate.py': gate.encode('ascii'),
                'docs/evidence/example/qualification.json': raw, source: b'original'}

    def test_valid_manifest_and_changed_source_are_distinguished(self):
        files = self.fixture()
        self.assertTrue(verify_bundle('test', 'gate.py', 'example', files.__getitem__)['verified'])
        files[PREFIX+'spawner_marker.py'] = b'changed without requalification'
        result = verify_bundle('test', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['verified'])
        self.assertEqual(1, len(result['errors']))

    def test_changed_receipt_is_rejected_even_if_sources_match(self):
        files = self.fixture()
        path = 'docs/evidence/example/qualification.json'
        files[path] += b'\n'
        self.assertFalse(verify_bundle('test', 'gate.py', 'example', files.__getitem__)['verified'])

    def test_disabled_gate_does_not_require_unavailable_pixels(self):
        files = {PREFIX+'gate.py': b'PRODUCT_QUALIFIED = False\n'}
        result = verify_bundle('test', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['enabled'])
        self.assertFalse(result['verified'])
        self.assertEqual([], result['errors'])

    def test_only_circular_portal_metadata_is_normalized(self):
        content = b"PRODUCT_QUALIFIED = True\nQUALIFICATION_SHA256 = 'abc'\nSTYLE = 'stars'\n"
        canonical = b"PRODUCT_QUALIFIED = False\nQUALIFICATION_SHA256 = 'Pending'\nSTYLE = 'stars'\n"
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), source_digest(PREFIX+'portal_profile.py', content))
        self.assertNotEqual(source_digest(PREFIX+'portal_profile.py', content),
                            source_digest(PREFIX+'portal_profile.py', content.replace(b'stars', b'changed')))
        self.assertEqual(hashlib.sha256(content).hexdigest(), source_digest(PREFIX+'other.py', content))

    def resource_fixture(self, bundle='cauldron'):
        files = self.fixture()
        shader = 'resource_pack/shaders/glsl/qualified.fragment'
        files[shader] = b'qualified shader'
        contract = {
            'engine_version': '3.10.0.420447',
            'materials': {'qualified:base': {'fragmentShader': 'shaders/glsl/qualified.fragment'}},
            'models': {'qualified': {'material': 'qualified', 'mesh': 'qualified.json'}},
            'output_sha256': {
                shader: hashlib.sha256(files[shader]).hexdigest(),
                'resource_pack/materials/entity.material': 'historical whole-file fingerprint',
                'resource_pack/models/netease_models.json': 'historical whole-file fingerprint'},
        }
        encoded = json.dumps(contract).encode('ascii')
        files[RESOURCE_CONTRACTS[bundle]] = encoded
        files['resource_pack/materials/entity.material'] = json.dumps(
            {'materials': dict(contract['materials'], unrelated={'old': True})}).encode('ascii')
        files['resource_pack/models/netease_models.json'] = json.dumps(
            dict(contract['models'], unrelated={'old': True})).encode('ascii')
        self.resource_manifest(files, hashlib.sha256(encoded).hexdigest())
        return files

    def resource_manifest(self, files, contract_hash):
        path = 'docs/evidence/example/qualification.json'
        manifest = json.loads(files[path])
        manifest['resource_contract_sha256'] = contract_hash
        files[path] = json.dumps(manifest).encode('ascii')
        files[PREFIX+'gate.py'] = ('PRODUCT_QUALIFIED = True\nQUALIFICATION_SHA256 = %r\n' %
                                  hashlib.sha256(files[path]).hexdigest()).encode('ascii')

    def test_owned_registry_entries_survive_unrelated_additions_and_json_formatting(self):
        for bundle in RESOURCE_CONTRACTS:
            with self.subTest(bundle=bundle):
                files = self.resource_fixture(bundle)
                for relative in ('resource_pack/materials/entity.material',
                                 'resource_pack/models/netease_models.json'):
                    registry = json.loads(files[relative])
                    entries = registry.get('materials', registry)
                    entries['another_family'] = {'new': ['resource']}
                    files[relative] = json.dumps(registry, indent=4, sort_keys=True).encode('ascii')
                self.assertTrue(verify_bundle(bundle, 'gate.py', 'example', files.__getitem__)['verified'])

    def test_owned_registry_changes_and_removals_are_rejected(self):
        for bundle in RESOURCE_CONTRACTS:
            for relative, nested, key in (
                    ('resource_pack/materials/entity.material', 'materials', 'qualified:base'),
                    ('resource_pack/models/netease_models.json', None, 'qualified')):
                for remove in (False, True):
                    with self.subTest(bundle=bundle, registry=relative, remove=remove):
                        files = self.resource_fixture(bundle)
                        registry = json.loads(files[relative])
                        entries = registry[nested] if nested else registry
                        if remove:
                            del entries[key]
                        else:
                            entries[key]['foreign_shader_or_model'] = True
                        files[relative] = json.dumps(registry).encode('ascii')
                        result = verify_bundle(bundle, 'gate.py', 'example', files.__getitem__)
                        self.assertFalse(result['verified'])
                        self.assertIn('Qualified registration changed: '+relative+':'+key, result['errors'])

    def test_resource_bytes_and_frozen_contract_drift_are_rejected(self):
        files = self.resource_fixture()
        files['resource_pack/shaders/glsl/qualified.fragment'] += b' changed'
        result = verify_bundle('cauldron', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['verified'])
        self.assertIn('Qualified resource changed: resource_pack/shaders/glsl/qualified.fragment', result['errors'])
        files = self.resource_fixture()
        files[RESOURCE_CONTRACTS['cauldron']] += b'\n'
        result = verify_bundle('cauldron', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['verified'])
        self.assertIn('Qualification resource contract differs: '+RESOURCE_CONTRACTS['cauldron'], result['errors'])

    def spawner_fixture(self):
        files = self.fixture()
        assets = {'resource_pack/models/netease_block/marker.json': {'geometry': [1, 2, 3]},
                  'behavior_pack/netease_blocks/marker.json': {'render_layer': 'alpha'}}
        contract_hash = json_digest(dict((name, json_digest(value)) for name, value in assets.items()))
        files.update(dict((name, json.dumps(value).encode('ascii')) for name, value in assets.items()))
        files[PREFIX+'spawner_marker_data.py'] = (
            'MARKERS = {"present": "test:marker"}\nRESOURCE_CONTRACT_SHA256 = %r\n' %
            contract_hash).encode('ascii')
        files['resource_pack/blocks.json'] = json.dumps(
            {'test:marker': {'netease_model': 'test:marker', 'sound': 'stone'}}).encode('ascii')
        self.resource_manifest(files, contract_hash)
        return files

    def test_spawner_asset_and_block_registration_contracts_are_checked(self):
        files = self.spawner_fixture()
        self.assertTrue(verify_bundle('spawner', 'gate.py', 'example', files.__getitem__)['verified'])
        files['resource_pack/models/netease_block/marker.json'] = b'{"geometry": [4, 5, 6]}'
        result = verify_bundle('spawner', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['verified'])
        self.assertIn('Qualified spawner assets differ from their frozen contract', result['errors'])
        files = self.spawner_fixture()
        files['resource_pack/blocks.json'] = b'{"test:marker": {"netease_model": "wrong", "sound": "stone"}}'
        result = verify_bundle('spawner', 'gate.py', 'example', files.__getitem__)
        self.assertFalse(result['verified'])
        self.assertIn('Qualified registration changed: resource_pack/blocks.json:test:marker', result['errors'])

    def test_spawner_unrelated_blocks_and_asset_json_formatting_do_not_invalidate_qualification(self):
        files = self.spawner_fixture()
        blocks = json.loads(files['resource_pack/blocks.json'])
        blocks['unrelated'] = {'netease_model': 'unrelated'}
        files['resource_pack/blocks.json'] = json.dumps(blocks, indent=4).encode('ascii')
        for relative in ('resource_pack/models/netease_block/marker.json',
                         'behavior_pack/netease_blocks/marker.json'):
            files[relative] = json.dumps(json.loads(files[relative]), indent=4).encode('ascii')
        self.assertTrue(verify_bundle('spawner', 'gate.py', 'example', files.__getitem__)['verified'])


if __name__ == '__main__':
    unittest.main()
