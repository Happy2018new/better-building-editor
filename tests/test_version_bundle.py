"""Reject version mixtures before any game or resource tests are started."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import shutil
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('version_bundle_check', ROOT / 'tools/check_version_bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class VersionBundleTests(unittest.TestCase):
    def rail_fixture(self, root):
        manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
        module = Path('behavior_pack/modern_projection/projection/rail_neighbor_data.py')
        values = bundle.module_constants(ROOT / module)
        for name in (module,) + tuple(Path('tools/data') / row[0] for row in values['EVIDENCE']):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        return manifest, values

    def write_rail_table(self, root, values):
        path = root / 'behavior_pack/modern_projection/projection/rail_neighbor_data.py'
        path.write_text(''.join('%s = %r\n' % item for item in values.items()), encoding='ascii')

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

    def test_adapted_text_checkout_newlines_do_not_change_fingerprints(self):
        manifest, data = self.actor_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for newline in (b'\n', b'\r\n'):
                for name in data['adapted']:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    raw = (ROOT / name).read_bytes().replace(b'\r\n', b'\n')
                    path.write_bytes(raw.replace(b'\n', newline))
                bundle.check_actor_materials(data, manifest, root=root)
            path.write_bytes(path.read_bytes() + b'\r\n// changed content\r\n')
            with self.assertRaisesRegex(ValueError, 'repeat shader and visual checks'):
                bundle.check_actor_materials(data, manifest, root=root)

    def test_native_source_bytes_are_still_checked_without_newline_normalization(self):
        manifest, data = self.actor_snapshot()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in data['sources'].items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value['text'].encode('utf8'))
                import hashlib
                value['native_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            bundle.check_actor_materials(data, manifest, game_data=root)
            path = root / 'shaders/glsl/text.fragment'
            path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
            with self.assertRaisesRegex(ValueError, 'Installed native source changed'):
                bundle.check_actor_materials(data, manifest, game_data=root)

    def test_unknown_adapted_text_hash_contract_is_rejected(self):
        manifest, data = self.actor_snapshot()
        data['adapted_hash_format'] = 'sha256-unknown'
        with self.assertRaises(ValueError):
            bundle.check_actor_materials(data, manifest)

    def test_current_sources_and_runtime_observations_match(self):
        with patch.object(bundle, 'check_rail_provenance', wraps=bundle.check_rail_provenance) as rails:
            manifest, files = bundle.check_provenance()
        rails.assert_called_once()
        self.assertIn('rail_neighbor_data', bundle.MODULES)
        self.assertIn(str(Path('behavior_pack/modern_projection/projection/rail_neighbor_data.py')), files)
        table = bundle.module_constants(ROOT / 'behavior_pack/modern_projection/projection/rail_neighbor_data.py')
        for filename, unused in table['EVIDENCE']:
            self.assertIn(str(Path('tools/data') / filename), files)
        self.assertGreater(len(files), 15)
        self.assertGreater(manifest['record_count'], 0)

    def test_rail_provenance_reads_ast_and_preserves_original_differences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, values = self.rail_fixture(root)
            module = root / 'behavior_pack/modern_projection/projection/rail_neighbor_data.py'
            with module.open('a', encoding='ascii') as output:
                output.write("\nraise RuntimeError('must not initialize game modules')\n")
            before = {filename: (root / 'tools/data' / filename).read_bytes()
                      for filename, unused in values['EVIDENCE']}
            self.assertEqual(2, len(bundle.check_rail_provenance(manifest, root=root)))
            for filename, payload in before.items():
                self.assertFalse(json.loads(payload)['comparison']['all_matched'])
                self.assertEqual(payload, (root / 'tools/data' / filename).read_bytes())

    def test_rail_provenance_rejects_changed_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, values = self.rail_fixture(root)
            for filename, unused in values['EVIDENCE']:
                with self.subTest(filename=filename):
                    path = root / 'tools/data' / filename
                    original = path.read_bytes()
                    path.write_bytes(original + b'\n')
                    with self.assertRaisesRegex(ValueError, 'original evidence bytes changed'):
                        bundle.check_rail_provenance(manifest, root=root)
                    path.write_bytes(original)

    def test_rail_provenance_rejects_stale_or_unbound_source_table(self):
        for change in ('schema', 'version', 'palette', 'hash', 'missing', 'foreign', 'duplicate'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, values = self.rail_fixture(root)
                if change == 'schema':
                    values['SCHEMA_VERSION'] = 2
                elif change == 'version':
                    values['SOURCE_VERSION'] = 'NEMC old'
                elif change == 'palette':
                    values['PALETTE_SHA256'] = '0' * 64
                elif change == 'hash':
                    values['EVIDENCE'] = ((values['EVIDENCE'][0][0], '0' * 64), values['EVIDENCE'][1])
                elif change == 'missing':
                    values['EVIDENCE'] = values['EVIDENCE'][:1]
                elif change == 'foreign':
                    values['EVIDENCE'] = (('../foreign.json', values['EVIDENCE'][0][1]), values['EVIDENCE'][1])
                else:
                    values['EVIDENCE'] = (values['EVIDENCE'][0], values['EVIDENCE'][0])
                self.write_rail_table(root, values)
                with self.assertRaises(ValueError):
                    bundle.check_rail_provenance(manifest, root=root)

    def test_rail_provenance_checks_report_contract_even_if_table_hash_is_regenerated(self):
        for change in ('schema', 'version', 'palette', 'start_palette', 'runtime', 'completed',
                       'restored', 'cleanup', 'native_error', 'native_done', 'coverage',
                       'capture_metadata', 'action_metadata'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, values = self.rail_fixture(root)
                filename = values['EVIDENCE'][0][0]
                path = root / 'tools/data' / filename
                data = json.loads(path.read_bytes())
                if change == 'schema':
                    data['schema'] = 2
                elif change == 'version':
                    data['game_version'] = 'NEMC old'
                elif change == 'palette':
                    data['palette_sha256'] = '0' * 64
                elif change == 'start_palette':
                    data['start']['palette_sha256'] = '0' * 64
                elif change == 'runtime':
                    data['start']['runtime'] = 'unobserved'
                elif change in ('completed', 'restored'):
                    data[change] = False
                elif change == 'cleanup':
                    data['cleanup']['restored'] = False
                elif change == 'native_error':
                    data['native']['error'] = 'native callback failed'
                elif change == 'native_done':
                    data['native']['done'] = False
                elif change == 'capture_metadata':
                    data['native'] = None
                elif change == 'action_metadata':
                    data['plans'][0]['actions'] = []
                else:
                    data['native']['rows'].pop()
                payload = json.dumps(data, ensure_ascii=True).encode('ascii')
                path.write_bytes(payload)
                values['EVIDENCE'] = ((filename, hashlib.sha256(payload).hexdigest()), values['EVIDENCE'][1])
                self.write_rail_table(root, values)
                with self.assertRaises(ValueError):
                    bundle.check_rail_provenance(manifest, root=root)

    def test_provenance_only_replays_native_item_source_instead_of_registry_labels(self):
        source_path = 'tools/data/native_item_contents_nemc_3.9.0.401155.json'
        source = json.loads((ROOT / source_path).read_bytes())
        import generate_native_item_contents as items
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'tools/data', root / 'tools/data')
            shutil.copytree(ROOT / 'docs/reference/block_palettes', root / 'docs/reference/block_palettes')
            shutil.copytree(ROOT / 'behavior_pack/modern_projection/projection',
                            root / 'behavior_pack/modern_projection/projection')
            shutil.copytree(ROOT / 'resource_pack/shaders', root / 'resource_pack/shaders')
            shutil.copytree(ROOT / 'resource_pack/materials', root / 'resource_pack/materials')
            shutil.copytree(ROOT / 'resource_pack/models', root / 'resource_pack/models')
            shutil.copytree(ROOT / 'resource_pack/textures/models/modern_projection/liquid',
                            root / 'resource_pack/textures/models/modern_projection/liquid')
            shutil.copyfile(ROOT / 'tools/generate_liquid_skeleton_resources.py',
                            root / 'tools/generate_liquid_skeleton_resources.py')
            with patch.object(items, 'validate', wraps=items.validate) as validate:
                bundle.check_provenance(root=root)
            self.assertTrue(validate.called)
            path = root / source['source_report_file']
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'original report bytes changed'):
                bundle.check_provenance(root=root)

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
        self.assertIn(['tools/generate_liquid_materials.py', '--check'], [row[3:] for row in commands])
        self.assertIn(['tools/generate_bed_proxies.py', '--check'], [row[3:] for row in commands])
        self.assertIn(['tools/generate_flat_item_proxies.py', '--check'], [row[3:] for row in commands])
        self.assertEqual(commands[-1][3:], ['-m', 'unittest', 'discover', '-s', 'tests', '-q'])


if __name__ == '__main__':
    unittest.main()
