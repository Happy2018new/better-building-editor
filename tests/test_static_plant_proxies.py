"""Native-source plant candidates preserve strict layers and source contracts."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_static_plant_proxies import (SOURCE, validate, outputs, SPECIAL, CANDIDATES,
                                          source_path, digest, acceptance_metadata,
                                          ACCEPTANCE_MANIFESTS)


class StaticPlantProxyTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(SOURCE.read_text(encoding='utf8'))

    def test_native_texture_identity_and_special_material_boundaries(self):
        validate(self.source)
        files = outputs(self.source)
        atlas = files[ROOT/'resource_pack/textures/terrain_texture.json']['texture_data']
        for name in CANDIDATES:
            record = self.source['plants'][name]
            self.assertNotIn(name, SPECIAL)
            self.assertEqual(record['texture_path'].rsplit('.', 1)[0],
                             atlas['modern_projection_static_'+name]['textures'])
            model = files[ROOT/'resource_pack/models/netease_block'/('preview_'+name+'.json')]
            expected = deepcopy(self.source['template']['netease:block_geometry']['bones'])
            for bone in expected:
                bone['pivot'][1] = 8
                for cube in bone['cubes']:
                    cube['size'][1] = 16
            self.assertEqual(expected, model['netease:block_geometry']['bones'])

    def test_unmeasured_plants_are_not_registered_and_height_uses_native_alpha(self):
        files = outputs(self.source)
        blocks = files[ROOT/'resource_pack/blocks.json']
        atlas = files[ROOT/'resource_pack/textures/terrain_texture.json']['texture_data']
        data = {}
        exec(files[ROOT/'behavior_pack/modern_projection/projection/plant_proxy_data.py'], data)
        from projection import block_registry as registry
        self.assertEqual(1, data['SCHEMA_VERSION'])
        self.assertEqual(registry.source_version(), data['SOURCE_VERSION'])
        self.assertEqual(registry.fingerprint(), data['PALETTE_SHA256'])
        self.assertEqual(set(('minecraft:'+name, 0) for name in CANDIDATES),
                         set(data['STATIC_PLANT_PROXIES']))
        for name, record in self.source['plants'].items():
            material = ('minecraft:'+name, 0)
            proxy = 'modern_projection:preview_'+name
            key = 'modern_projection_static_'+name
            if name in CANDIDATES:
                expected = 1. - record['alpha_bounds'][1]/float(record['texture_size'][1])
                self.assertEqual(expected, data['STATIC_PLANT_MAX_Y'][material])
            else:
                self.assertNotIn(material, data['STATIC_PLANT_MAX_Y'])
                self.assertNotIn(proxy, blocks)
                self.assertNotIn(key, atlas)
                self.assertNotIn(ROOT/'behavior_pack/netease_blocks'/('preview_'+name+'.json'), files)

    def test_missing_native_source_or_changed_mapping_is_rejected(self):
        for kind in ('missing_plant', 'missing_hash', 'texture_path', 'schema', 'version', 'palette', 'geometry_evidence',
                     'alpha_bounds'):
            with self.subTest(kind=kind):
                modified = deepcopy(self.source)
                if kind == 'missing_plant':
                    del modified['plants']['poppy']
                elif kind == 'missing_hash':
                    del modified['sha256']['texture_poppy']
                elif kind == 'texture_path':
                    modified['plants']['poppy']['texture_path'] = 'textures/blocks/flower_allium.tga'
                elif kind == 'version':
                    modified['game_version'] = 'Different native version'
                elif kind == 'schema':
                    modified['schema'] = 2
                elif kind == 'palette':
                    modified['palette_sha256'] = '0'*64
                elif kind == 'alpha_bounds':
                    modified['plants']['brown_mushroom']['alpha_bounds'] = [4, 16, 12, 16]
                else:
                    modified['geometry_evidence']['brown_mushroom']['texture_alpha_top_row'] = 7
                with self.assertRaises(ValueError):
                    validate(modified)

    def test_source_snapshot_follows_the_registry_version(self):
        self.assertEqual(ROOT/'tools/data/static_plant_sources_nemc_4.0.0.123.json',
                         source_path({'game_version': 'NEMC 4.0.0.123'}))
        for version in ('NEMC ', 'Other 4.0.0.123'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                source_path({'game_version': version})

    def test_generated_acceptance_retains_only_original_cells_and_measured_views(self):
        data = {}
        files = outputs(self.source)
        exec(files[ROOT/'behavior_pack/modern_projection/projection/plant_proxy_data.py'], data)
        self.assertEqual(digest(SOURCE), data['SOURCE_MANIFEST_SHA256'])
        self.assertEqual(1, data['ACCEPTANCE_SCHEMA_VERSION'])
        scopes = data['STATIC_PLANT_ACCEPTANCE']
        self.assertEqual(set(data['STATIC_PLANT_PROXIES']), set(scopes))
        for material, scope in scopes.items():
            self.assertEqual((-47, 117, -70), scope['native_target'])
            expected_views = ('public',) if 'mushroom' in material[0] else ('public', 'right')
            self.assertEqual(set(expected_views), set(scope['views']))
            self.assertEqual(tuple(range(8)), scope['snow_heights'])
            self.assertEqual(('full', 'missing'), scope['world_modes'])
            self.assertEqual('1.21.120.0', scope['runtime_minecraft_version'])
            self.assertTrue(scope['dry_native_controls'])
            self.assertTrue(scope['independent_editor_controls'])
            self.assertFalse(scope['other_positions_or_runtime_versions_accepted'])
            self.assertFalse(scope['native_mesh_authority'])
            self.assertFalse(scope['random_offset_contract_recovered'])
            self.assertEqual(digest(ROOT/scope['acceptance_manifest']),
                             scope['acceptance_manifest_sha256'])

    def test_changed_acceptance_manifest_is_rejected_before_generation(self):
        changed = tuple((relative, '0'*64) for relative, expected in ACCEPTANCE_MANIFESTS)
        with patch('generate_static_plant_proxies.ACCEPTANCE_MANIFESTS', changed):
            with self.assertRaisesRegex(ValueError, 'acceptance evidence changed'):
                acceptance_metadata(self.source)

    def test_fungus_all_height_acceptance_preserves_disjoint_original_evidence(self):
        evidence = self.source['geometry_evidence']['fungus_all_heights_r8']
        path = ROOT/evidence['acceptance_manifest']
        self.assertEqual(evidence['acceptance_manifest_sha256'], digest(path))
        acceptance = json.loads(path.read_bytes())
        partitions = acceptance['evidence_partitions']
        old = partitions['r7_boundary']
        new = partitions['r8_remaining']
        self.assertEqual(digest(ROOT/'docs/snow-fungus-boundary-acceptance-r7.json'),
                         old['acceptance_manifest']['sha256'])
        for plant in acceptance['accepted_scope']['plants']:
            boundary = set(old['snow_heights'][plant])
            remaining = set(new['snow_heights'][plant])
            self.assertFalse(boundary & remaining)
            self.assertEqual(set(range(8)), boundary | remaining)
        self.assertEqual(18, len(new['ordinary_other_application_switch_observations']))
        self.assertTrue(new['foreground_changes_are_diagnostics'])
        self.assertFalse(acceptance['geometry']['native_mesh_authority'])
        self.assertFalse(acceptance['geometry']['random_offset_contract_recovered'])
        self.assertFalse(acceptance['accepted_scope']['other_positions_or_runtime_versions_accepted'])
        for relative, expected in acceptance['production_render_asset_sha256'].items():
            self.assertEqual(expected, digest(ROOT/relative))

    def test_native_alpha_metadata_matches_the_fingerprinted_texture(self):
        source = deepcopy(self.source)
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory)
            for relative in source['paths'].values():
                (native/relative).parent.mkdir(parents=True, exist_ok=True)
            for key in ('blocks', 'terrain'):
                (native/source['paths'][key]).write_text('{}', encoding='utf8')
            for record in source['plants'].values():
                image = Image.new('RGBA', tuple(record['texture_size']))
                left, top, right, bottom = record['alpha_bounds']
                ImageDraw.Draw(image).rectangle((left, top, right-1, bottom-1),
                                                fill=(180, 90, 40, 255))
                image.save(native/record['texture_path'])
            source['sha256'] = {key: digest(native/path) for key, path in source['paths'].items()}
            validate(source, native)
            modified = deepcopy(source)
            modified['plants']['brown_mushroom']['alpha_bounds'][1] -= 1
            with self.assertRaisesRegex(ValueError, 'alpha metadata changed: brown_mushroom'):
                validate(modified, native)
            path = native/source['plants']['brown_mushroom']['texture_path']
            Image.new('RGBA', (32, 16), (180, 90, 40, 255)).save(path)
            source['sha256']['texture_brown_mushroom'] = digest(path)
            with self.assertRaisesRegex(ValueError, 'alpha metadata changed: brown_mushroom'):
                validate(source, native)

    def test_render_adapter_keeps_source_document_layers_and_actor(self):
        from projection.geometry_palette import prepare_palette
        from projection.cell import make_cell
        from projection.model import Document
        for name in sorted(CANDIDATES):
            material = ('minecraft:'+name, 0)
            document = Document((1, 1, 1), {(0, 0, 0): make_cell(
                material, ('minecraft:water', 0), {'opaque': {'plant': name}})})
            original = deepcopy(document.to_data())
            rendered = prepare_palette(document.palette_data())
            self.assertEqual(original, document.to_data())
            self.assertEqual([0], rendered['common'][('modern_projection:preview_'+name, 0)])
            self.assertEqual([0], rendered['extra'][('minecraft:water', 0)])

    def assert_stale_runtime_table_rejected(self, metadata, fields, snow, message):
        from projection import block_registry as registry
        from projection.cell import make_cell
        from projection.geometry_palette import prepare_palette
        from projection.model import Document
        from projection.render_context import prepare_context_batches, prepare_context_palette
        plant = ('minecraft:brown_mushroom', 0)
        value = (make_cell(registry.from_states('minecraft:snow_layer',
                    {'height': 0, 'covered_bit': True}), plant) if snow else plant)
        document = Document((1, 1, 1), {(0, 0, 0): value})
        before = deepcopy(document.to_data())
        source = document.palette_data()
        original = deepcopy(source)
        routes = (('palette', lambda: prepare_palette(source)),
                  ('context', lambda: prepare_context_palette(source, source)),
                  ('batches', lambda: prepare_context_batches(document, source)))
        for field, changed in fields:
            with patch.object(metadata, field, changed):
                for route, prepare in routes:
                    with self.subTest(table=metadata.__name__, field=field, route=route):
                        with self.assertRaisesRegex(ValueError, message):
                            prepare()
                        self.assertEqual(original, source)
                        self.assertEqual(before, document.to_data())

    def test_generated_plant_provenance_is_checked_by_full_and_missing_render_routes(self):
        from projection import plant_proxy_data
        self.assert_stale_runtime_table_rejected(plant_proxy_data,
            (('SCHEMA_VERSION', 2), ('SCHEMA_VERSION', None),
             ('SOURCE_VERSION', 'NEMC old'), ('PALETTE_SHA256', '0'*64)),
            False, 'Native plant proxies need regeneration')

    def test_generated_snow_traits_are_checked_before_using_plant_eligibility(self):
        from projection import block_traits_data
        self.assert_stale_runtime_table_rejected(block_traits_data,
            (('SCHEMA_VERSION', 2), ('SCHEMA_VERSION', None),
             ('SOURCE_VERSION', 'NEMC old'), ('SOURCE_SHA256', '0'*64)),
            True, 'Native snow capabilities need regeneration')

    def test_buried_static_plant_overlays_keep_logical_layers_at_and_above_alpha_top(self):
        from projection import block_registry as registry
        from projection.geometry_palette import prepare_palette
        from projection.cell import make_cell
        from projection.model import Document
        from projection.render_layout import overlay_index
        burial_height = {'brown_mushroom': 3, 'red_mushroom': 3,
                         'crimson_fungus': 5, 'warped_fungus': 4}
        self.assertEqual(set(burial_height), set(CANDIDATES))
        for name in sorted(CANDIDATES):
            with self.subTest(plant=name):
                material = ('minecraft:'+name, 0)
                proxy = ('modern_projection:preview_'+name, 0)
                document = Document((8, 1, 1), {
                    (height, 0, 0): make_cell(registry.from_states('minecraft:snow_layer',
                        {'height': height, 'covered_bit': True}), material,
                        {'opaque': {'height': height}})
                    for height in range(8)})
                saved_document = deepcopy(document.to_data())
                source = document.palette_data()
                source['extraStates'] = {material: registry.states(material)}
                saved = deepcopy(source)
                rendered = prepare_palette(source)
                self.assertEqual([overlay_index(height, source['volume']) for height in range(burial_height[name])],
                                 rendered['common'][proxy])
                self.assertEqual(source['extra'], rendered['extra'])
                self.assertEqual(source['extraStates'], rendered['extraStates'])
                self.assertEqual(saved_document, document.to_data())
                self.assertEqual(saved, source)
                for height in range(burial_height[name], 8):
                    buried = Document((1, 1, 1), {(0, 0, 0): make_cell(
                        registry.from_states('minecraft:snow_layer',
                            {'height': height, 'covered_bit': True}), material)})
                    original = deepcopy(buried.palette_data())
                    result = prepare_palette(original)
                    self.assertNotIn(proxy, result['common'])
                    self.assertEqual(original['volume'], result['volume'])
                    self.assertEqual(original['extra'], result['extra'])
                    self.assertEqual(original, buried.palette_data())


if __name__ == '__main__':
    unittest.main()
