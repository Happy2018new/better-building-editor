"""Reject version mixtures before any game or resource tests are started."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('version_bundle_check', ROOT / 'tools/check_version_bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class VersionBundleTests(unittest.TestCase):
    def actor_snapshot(self):
        manifest=json.loads((ROOT/'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        version=manifest['game_version'].removeprefix('NEMC ')
        data=json.loads((ROOT/('tools/data/native_actor_materials_nemc_'+version+'.json')).read_text(encoding='utf8'))
        return manifest,data

    def test_stale_native_actor_shader_cannot_pass_version_bundle(self):
        manifest,data=self.actor_snapshot()
        data['adapted']['resource_pack/shaders/glsl/modern_projection_sign_text.fragment']='0'*64
        with self.assertRaisesRegex(ValueError,'repeat shader and visual checks'):
            bundle.check_actor_materials(data,manifest)

    def test_altered_native_source_snapshot_cannot_pass(self):
        manifest,data=self.actor_snapshot()
        data['sources']['shaders/glsl/text.fragment']['text']+='\n// stale source\n'
        with self.assertRaisesRegex(ValueError,'Native source snapshot changed'):
            bundle.check_actor_materials(data,manifest)

    def test_current_sources_and_runtime_observations_match(self):
        manifest, files = bundle.check_provenance()
        self.assertGreater(len(files), 15)
        self.assertGreater(manifest['record_count'], 0)

    def test_rejects_new_palette_with_old_observations(self):
        manifest = {'game_version': 'NEMC next', 'source_sha256': 'a' * 64}
        for version, fingerprint in (('NEMC old', 'a' * 64), ('NEMC next', 'b' * 64), ('NEMC next', None)):
            with self.subTest(version=version, fingerprint=fingerprint), self.assertRaises(ValueError):
                bundle.provenance_matches('fixture', version, fingerprint, manifest)

    def test_reads_literal_metadata_without_running_module_code(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'observations.py'
            path.write_text("SOURCE_VERSION = 'NEMC test'\nPALETTE_SHA256 = 'abc'\nraise RuntimeError('must not execute')\n", encoding='ascii')
            self.assertEqual(bundle.module_constants(path), {'SOURCE_VERSION': 'NEMC test', 'PALETTE_SHA256': 'abc'})

    def test_optional_suite_uses_the_current_manifest_source(self):
        manifest = {'game_version': 'NEMC next', 'source_file': 'docs/reference/block_palettes/nemc_next.json'}
        commands = bundle.commands(manifest, tests=True)
        self.assertIn(manifest['source_file'], commands[0])
        self.assertIn('tools/data/native_block_metadata_nemc_next.json', commands[1])
        self.assertEqual(commands[-1][3:], ['-m', 'unittest', 'discover', '-s', 'tests', '-q'])


if __name__ == '__main__':
    unittest.main()
