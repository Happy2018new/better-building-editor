"""Deployment provenance rejects drift even when runtime gates remain true."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_render_qualifications import PREFIX, source_digest, verify_bundle


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


if __name__ == '__main__':
    unittest.main()
