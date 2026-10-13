"""Centered snapshot plants cover known snow states without changing cells."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from generate_centered_plant_profiles import EXISTING, PROFILE, STYLE, validate_profile, outputs
from projection import block_registry as registry, centered_plant_data
from projection.block_traits_data import SNOW_COVERABLE_BLOCKS
from projection.cell import make_cell, foreground, background
from projection.geometry_palette import PLANT_PROXIES, PLANT_MAX_Y, prepare_palette
from projection.model import Document, Editor
from projection.render_layout import overlay_index


class CenteredPlantProfilesTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(PROFILE.read_bytes())

    def test_all_known_snow_plants_have_centered_rendering_and_alpha_extents(self):
        materials = {(name, registry.DEFAULT_AUX[name]) for name in SNOW_COVERABLE_BLOCKS}
        self.assertEqual(29, len(materials))
        self.assertFalse(materials-set(PLANT_PROXIES))
        self.assertEqual('fixed_centered_snapshot', centered_plant_data.STYLE)
        for name, profile in self.profile['plants'].items():
            self.assertEqual(profile['mesh']['height']*(1.-profile['alpha_bounds'][1]/16.),
                             PLANT_MAX_Y[('minecraft:'+name, 0)])

    def test_all_generated_meshes_stay_in_cell_and_have_original_texture(self):
        files = outputs(self.profile)
        atlas = files[ROOT/'resource_pack/textures/terrain_texture.json']['texture_data']
        for name, plant in self.profile['plants'].items():
            if name in EXISTING:
                continue
            self.assertEqual(plant['texture_path'].rsplit('.', 1)[0], atlas['modern_projection_centered_'+name]['textures'])
            model = files[ROOT/'resource_pack/models/netease_block'/('centered_'+name+'.json')]['netease:block_geometry']
            for bone in model['bones']:
                self.assertEqual([-8, 8, 8], bone['pivot'])
                cube, = bone['cubes']
                self.assertEqual(16, cube['size'][1])
                angle = math.radians(bone['rotation'][1])
                for edge in (0, cube['size'][0]):
                    distance = cube['origin'][0]+edge-bone['pivot'][0]
                    x = (bone['pivot'][0]+math.cos(angle)*distance)/-16.
                    z = (bone['pivot'][2]-math.sin(angle)*distance)/16.
                    for coordinate in (x, z):
                        self.assertGreaterEqual(coordinate, .1-1e-7)
                        self.assertLessEqual(coordinate, .9+1e-7)

    def test_original_grass_meshes_are_fingerprinted_without_generated_replacements(self):
        files = outputs(self.profile)
        for name in EXISTING:
            plant = self.profile['plants'][name]
            model_path = ROOT/plant['mesh']['path']
            model_text = model_path.read_text(encoding='utf8')
            model = json.loads(model_text)['netease:block_geometry']
            self.assertNotIn(model_path, files)
            self.assertNotIn(ROOT/'resource_pack/models/netease_block'/('centered_'+name+'.json'), files)
            self.assertEqual('modern_projection:preview_'+name, model['description']['identifier'])
            self.assertEqual(hashlib.sha256(model_text.encode('utf8')).hexdigest(), plant['mesh']['sha256_utf8_lf'])
            self.assertEqual({.8}, {cube['size'][1]/16. for bone in model['bones'] for cube in bone['cubes']})
            self.assertLessEqual(PLANT_MAX_Y[('minecraft:'+name, 0)], .8)

    def test_profile_rejects_changed_retained_mesh_source(self):
        for name in EXISTING:
            for field, value in (('height', 1.), ('sha256_utf8_lf', '0'*64), ('path', 'other.json')):
                changed = deepcopy(self.profile)
                changed['plants'][name]['mesh'][field] = value
                with self.subTest(plant=name, field=field), self.assertRaisesRegex(ValueError, 'mesh source changed'):
                    validate_profile(changed)

    def test_profile_rejects_version_mapping_style_and_alpha_drift(self):
        for kind in ('version', 'registry', 'style', 'coverage', 'mapping', 'alpha'):
            changed = deepcopy(self.profile)
            if kind == 'version': changed['game_version'] = 'NEMC future'
            elif kind == 'registry': changed['palette_sha256'] = '0'*64
            elif kind == 'style': changed['style']['xz_translation'] = [1, 0]
            elif kind == 'coverage': changed['plants'].pop('poppy')
            elif kind == 'mapping': changed['plants']['poppy']['texture_path'] = 'textures/blocks/other.png'
            else: changed['plants']['poppy']['alpha_bounds'] = [0, 16, 16, 16]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_profile(changed)

    def test_snow_alpha_boundary_and_layers_survive_all_heights_and_origins(self):
        for name in self.profile['plants']:
            material = ('minecraft:'+name, 0)
            proxy = (PLANT_PROXIES[material], 0)
            top = PLANT_MAX_Y[material]
            for height in range(8):
                snow = registry.from_states('minecraft:snow_layer', {'height': height, 'covered_bit': True})
                for front, back in ((snow, material), (material, snow)):
                    doc = Document((3, 3, 3), {(1, 1, 1): make_cell(front, back)})
                    source, original = doc.palette_data(), deepcopy(doc.to_data())
                    for origin in ((0, 0, 0), (31, -48, -6), (-31, 99, 6)):
                        rendered = prepare_palette(source, render_origin=origin)
                        expected = [overlay_index(13, source['volume'])] if (height+1)/8. < top else []
                        self.assertEqual(expected, rendered['common'].get(proxy, []))
                        self.assertEqual(original, doc.to_data())

    def test_strict_layers_and_automatic_snow_erase_preserve_all_plant_data(self):
        pos = (1, 1, 1)
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        for name in SNOW_COVERABLE_BLOCKS:
            material = (name, registry.DEFAULT_AUX[name])
            for layer, expected in ((0, make_cell(('minecraft:air', 0), material)), (1, snow), (2, material)):
                editor = Editor(Document((3, 3, 3), {pos: make_cell(snow, material)}))
                editor.edit_layer = layer
                before = deepcopy(editor.document.blocks)
                self.assertEqual(1, editor.paint_at(pos, erase=True, respect_selection=False))
                self.assertEqual(expected, editor.document.get(pos))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)

    def test_stale_centered_table_is_rejected_on_render(self):
        doc = Document((1, 1, 1), {(0, 0, 0): ('minecraft:poppy', 0)})
        for field, value in (('SCHEMA_VERSION', 3), ('STYLE_VERSION', 2), ('SOURCE_VERSION', 'future'),
                             ('PALETTE_SHA256', '0'*64), ('STYLE', 'random')):
            with self.subTest(field=field), patch.object(centered_plant_data, field, value):
                with self.assertRaisesRegex(ValueError, 'Centered plant profiles need regeneration'):
                    prepare_palette(doc.palette_data())


if __name__ == '__main__':
    unittest.main()
