"""Cube resource provenance, actual item aliases and independent frame admission."""
import copy
from io import BytesIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

from projection import frame_block_item_data as source, item_icon_data
from projection.cell import make_cell
from projection.item_sprite_plan import iter_render_steps, sprite_content, sprite_item
from projection.item_sprite_profile import (candidate_profile, frame_block_candidate_profile,
                                           production_profile)
from projection.frame_block_item_profile import candidate_items, production_items
from projection.item_sprite_projection import projection_plan
from projection.model import Document
from test_static_frame_items import actor, frame, tag
import generate_frame_block_items as generator

ENGINE = generator.VERSION


class FrameBlockResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(generator.CATALOG.read_bytes())

    def test_real_item_aliases_resolve_exact_observed_aux_and_keep_distinct_textures(self):
        profile = frame_block_candidate_profile(ENGINE)
        for name in ('stone', 'grass_block', 'oak_log', 'oak_planks', 'glass'):
            self.assertIsNotNone(profile.items.get(('minecraft:' + name, 0)))
        oak = profile.items.get(('minecraft:oak_log', 0))
        spruce = profile.items.get(('minecraft:log', 1))
        self.assertEqual(oak['ui_model'], profile.items.get(('minecraft:log', 0))['ui_model'])
        self.assertNotEqual(oak['ui_model'], spruce['ui_model'])
        self.assertNotEqual(profile.items.get(('minecraft:stone', 0))['ui_model'],
                            profile.items.get(('minecraft:stone', 1))['ui_model'])
        self.assertIsNone(profile.items.get(('minecraft:stone', 65535)))

    def test_each_item_has_exact_native_texture_and_separate_geometry_scope(self):
        self.assertGreater(len({row['name'] for row in self.catalog['items']}), 300)
        for row in source.ITEMS.values():
            self.assertEqual(('frame',), row['content_families'])
            self.assertIs(row['supports_enchantment'], True)
        for row in self.catalog['items']:
            self.assertTrue(row['observed_item_texture'].startswith('textures/blocks/'))
            self.assertIn(row['resource'], self.catalog['resources'])
            self.assertEqual('block', self.catalog['native_items'][row['name']]['itemType'])
        for name in ('oak_stairs', 'oak_slab', 'chest', 'skeleton_skull', 'water', 'beacon'):
            self.assertNotIn('minecraft:' + name, {row['name'] for row in self.catalog['items']})

    def test_cube_has_six_real_faces_four_slots_and_nonzero_depth(self):
        faces = dict.fromkeys(generator.FACE_VERTICES, [0., 0., 1., 1.])
        mesh = generator.cube_mesh(faces, 'fixture')['mesh'][0]
        self.assertEqual(96, len(mesh['vertices']))
        self.assertEqual(48, len(mesh['indices']))
        for slot in range(4):
            vertices = mesh['vertices'][slot * 24:(slot + 1) * 24]
            self.assertEqual(set(generator.NORMALS.values()), {tuple(row['normal']) for row in vertices})
            values = np.array([row['pos'] for row in vertices])
            np.testing.assert_allclose(values.max(axis=0) - values.min(axis=0), (.5, .5, .5))
            self.assertTrue(np.all(np.floor(values[:, 0] / 2.) == slot))
            for index in range(slot * 12, (slot + 1) * 12):
                a, b, c = (mesh['vertices'][vertex] for vertex in mesh['indices'][index])
                normal = np.cross(np.array(b['pos']) - a['pos'], np.array(c['pos']) - a['pos'])
                self.assertGreater(np.dot(normal, a['normal']), 0.)

    def test_carried_faces_override_world_faces_and_ambiguous_variants_fail_closed(self):
        selection, faces = generator.face_keys({'textures': 'world', 'carried_textures': {
            'up': 'top', 'down': 'bottom', 'side': 'carried'}})
        self.assertEqual('carried_textures', selection)
        self.assertEqual({'top', 'bottom', 'carried'}, set(faces.values()))
        with self.assertRaises(generator.Unsupported):
            generator.texture_entry({'textures': ['first', 'second']})
        with self.assertRaises(generator.Unsupported):
            generator.texture_entry({'textures': {'path': 'texture', 'unknown': True}})
        resource = self.catalog['resources'][next(row['resource'] for row in self.catalog['items']
            if row['name'] == 'minecraft:grass_block' and row['aux'] == 0)]
        self.assertEqual('carried_textures', resource['texture_selection'])
        self.assertEqual('grass_carried_top', resource['faces']['up']['atlas_key'])

    def test_face_atlas_has_padding_and_preserves_each_face_interior(self):
        colors = [(index * 31, 255 - index * 27, index * 19, 255) for index in range(6)]
        faces = {face: Image.new('RGBA', (2, 2), color)
                 for face, color in zip(generator.FACE_VERTICES, colors)}
        bitmap, rectangles = generator.atlas_image(faces)
        image = Image.open(BytesIO(bitmap))
        for face, color in zip(generator.FACE_VERTICES, colors):
            u0, v0, u1, v1 = rectangles[face]
            x0, y0 = round(u0 * image.width), round(v0 * image.height)
            x1, y1 = round(u1 * image.width), round(v1 * image.height)
            self.assertEqual({color}, set(image.crop((x0 - 1, y0 - 1, x1 + 1, y1 + 1)).getdata()))

    def test_terrain_overlay_recipe_is_explicit_and_does_not_turn_dirt_green(self):
        image = Image.new('RGBA', (2, 1))
        # Installed grass_side.tga stores dirt at alpha 0 and gray grass at 255.
        image.putdata(((100, 80, 60, 0), (200, 200, 200, 255)))
        baked, operations = generator.bake_texture(image, {'overlay_color': '#80ff40'})
        self.assertEqual((100, 80, 60, 255), baked.getpixel((0, 0)))
        self.assertEqual((100, 200, 50, 255), baked.getpixel((1, 0)))
        self.assertIn('pending_native_pixels', operations[0])

    def test_native_flipbooks_are_explicitly_frozen_even_when_source_bitmap_is_square(self):
        square_animated = []
        for resource in self.catalog['resources'].values():
            for face in resource['faces'].values():
                if face['native_flipbooks']:
                    self.assertIn('animated_texture_frozen_source_snapshot', face['degradation'])
                    if face['source_size'][0] == face['source_size'][1]:
                        square_animated.append(face['atlas_key'])
        self.assertIn('command_block_front', square_animated)
        for row in self.catalog['items']:
            faces = self.catalog['resources'][row['resource']]['faces'].values()
            if any(face['native_flipbooks'] for face in faces):
                self.assertIn('animated_texture_frozen_source_snapshot', row['degradation'])

    def test_glass_materials_do_not_share_opaque_admission_or_alpha_discard(self):
        profile = frame_block_candidate_profile(ENGINE, ('opaque',))
        self.assertIsNone(profile.items.get(('minecraft:glass', 0)))
        for kind in generator.MATERIALS:
            fragment = (ROOT / ('resource_pack/shaders/glsl/modern_projection_frame_block_' + kind + '.fragment')).read_text()
            self.assertIn('if(texel.a<=0.0)' if kind == 'translucent' else 'if(texel.a<0.5)', fragment)
        registration = json.loads((ROOT / ('tools/data/frame_block_item_registrations_nemc_' + ENGINE + '.json')).read_bytes())
        names = set(registration['materials'])
        self.assertTrue(any('_opaque:' in name for name in names))
        self.assertTrue(any('_cutout:' in name for name in names))
        self.assertTrue(any('_translucent:' in name for name in names))

    def test_measured_candidate_only_replaces_two_owned_cube_poses_and_keeps_production_disabled(self):
        import prepare_frame_block_pose_r21 as candidate
        files, meshes, contract = candidate.resources()
        self.assertEqual({('minecraft:stone', 0), ('minecraft:quartz_block', 0)},
                         {tuple(row['item']) for row in meshes})
        for row in meshes:
            mesh = json.loads(files[row['path']])['mesh'][0]
            vertices = np.array([vertex['pos'] for vertex in mesh['vertices'][:24]])
            np.testing.assert_allclose(vertices.max(axis=0) - vertices.min(axis=0), (.25, .25, .25))
            np.testing.assert_allclose((vertices.max(axis=0) + vertices.min(axis=0)) / 2., (.5, .5, .4375))
        namespace = {}
        exec(files['behavior_pack/modern_projection/projection/frame_block_item_data.py'], namespace)
        self.assertEqual(contract, namespace['RESOURCE_SHA256'])
        self.assertEqual(set(candidate.ITEMS), set(namespace['ITEMS']))
        self.assertIs(namespace['PRODUCTION_QUALIFIED'], False)
        self.assertIs(namespace['POSE']['accepted'], False)
        self.assertIsNone(namespace['QUALIFICATION_SHA256'])
        self.assertNotIn('resource_pack/models/netease_models.json', files)
        self.assertNotIn('resource_pack/materials/entity.material', files)
        self.assertEqual(.5, source.POSE['scale_blocks'])


class FrameBlockAdmission(unittest.TestCase):
    def test_bounded_capture_matrix_preserves_orientation_and_declares_artificial_source(self):
        from frame_block_capture_matrix_r21 import matrix
        from projection.debug_item_blueprints import ORIENTATION_CASES
        before = copy.deepcopy(ORIENTATION_CASES)
        cases = [{'id': name + str(angle), 'orientation': 'frame_f2_r0',
                  'item': ['minecraft:' + name, 0], 'view_angle_degrees': angle,
                  'artificially_enchanted': name == 'quartz_block'}
                 for name in ('stone', 'quartz_block') for angle in (0, -75, 75)]
        manifest = {'schema': 1, 'production_qualified': False, 'cases': cases}
        rows = matrix(ORIENTATION_CASES, manifest)
        self.assertEqual(6, len(rows))
        self.assertEqual(6, len({label for label, source in rows}))
        self.assertEqual(before, ORIENTATION_CASES)
        self.assertTrue(all(source['artificially_enchanted'] for label, source in rows[3:]))
        for invalid in (dict(manifest, production_qualified=True), dict(manifest, cases=cases[:1] * 2)):
            with self.assertRaises(ValueError):
                matrix(ORIENTATION_CASES, invalid)
        for change in ({'view_angle_degrees': float('nan')}, {'orientation': 'frame_f0_r0', 'view_angle_degrees': 75},
                       {'item': ['minecraft:stone', True]}, {'artificially_enchanted': 1}):
            with self.assertRaises(ValueError):
                matrix(ORIENTATION_CASES, dict(manifest, cases=[dict(cases[0], **change)]))

    def test_artificial_enchantment_preserves_native_block_compound_and_does_not_mutate_source(self):
        from projection.debug_frame_block_items import artificial_enchantment_payload
        from projection.nbt_spatial import root_payload, scalar
        native = actor(item='minecraft:quartz_block')
        block = {'name': tag(8, 'minecraft:quartz_block'), 'states': {},
                 'val': tag(2, 0), 'version': tag(3, 18168865)}
        root_payload(native['Item'])['Block'] = copy.deepcopy(block)
        original = copy.deepcopy(native)
        enchanted = artificial_enchantment_payload(native)
        item = root_payload(enchanted['Item'])
        self.assertEqual(block, item['Block'])
        self.assertEqual('minecraft:quartz_block', scalar(item, 'Name'))
        self.assertEqual(0, scalar(item, 'Damage'))
        self.assertEqual(1, scalar(item, 'Count'))
        enchants = root_payload(item['tag'])['ench']
        self.assertEqual([(9, 3)], [(scalar(row, 'id'), scalar(row, 'lvl')) for row in enchants])
        self.assertEqual(original, native)
        self.assertTrue(sprite_content(frame(), enchanted, frame_block_candidate_profile(ENGINE).items)[3])
        for invalid in ({}, actor(), actor(item='minecraft:quartz_block')):
            with self.assertRaises(ValueError):
                artificial_enchantment_payload(invalid)

    def test_runtime_fixture_has_one_observed_plain_aux_and_an_empty_control(self):
        from projection.debug_frame_block_items import document
        from projection.debug_item_blueprints import orientation_document
        from projection.cell import actor_data, foreground
        before = orientation_document('frame_f2_r3').to_data()
        profile = frame_block_candidate_profile(ENGINE)
        doc = document('frame_f2_r3', 'minecraft:stone', 1)
        cell = doc.get((2, 3, 3))
        item = sprite_content(foreground(cell), actor_data(cell), profile.items)
        self.assertIsNotNone(item)
        self.assertEqual(('minecraft:stone', 1), item[0])
        empty = doc.get((5, 3, 3))
        self.assertIsNone(sprite_content(foreground(empty), actor_data(empty), profile.items))
        self.assertEqual(before, orientation_document('frame_f2_r3').to_data())
        self.assertIsNotNone(actor_data(doc.get((5, 3, 3))))
        enchanted = document('frame_f2_r3', 'minecraft:quartz_block', enchanted=True)
        cell = enchanted.get((2, 3, 3))
        self.assertTrue(sprite_content(foreground(cell), actor_data(cell), profile.items)[3])
        with self.assertRaises(ValueError):
            document('frame_f2_r3', 'minecraft:oak_stairs', 0)

    def test_all_48_poses_preserve_nbt_and_frame_only_content_ownership(self):
        profile = frame_block_candidate_profile(ENGINE)
        for facing in range(6):
            for rotation in range(8):
                payload = actor(rotation * 45., 'minecraft:oak_log')
                saved = copy.deepcopy(payload)
                document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(facing), nbt=payload)})
                groups = tuple(row for row in iter_render_steps(document, profile) if row)
                self.assertEqual(1, len(groups))
                self.assertEqual(float(facing * 64 + rotation * 512), groups[0].uniforms[0][0])
                self.assertEqual(saved, payload)
        item = {'newItemName': 'minecraft:stone', 'newAuxValue': 0, 'isEnchanted': False, 'userData': {}}
        for family in ('shelf', 'campfire'):
            self.assertIsNone(sprite_item(item, candidate_profile(ENGINE).items, family))
        for name in ('stone', 'quartz_block'):
            payload = actor(item='minecraft:' + name,
                user_data={'ench': tag(9, [tag(10, {'id': tag(2, 9), 'lvl': tag(2, 3)})])})
            saved = copy.deepcopy(payload)
            self.assertTrue(sprite_content(frame(), payload, profile.items)[3])
            document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=payload)})
            groups = tuple(row for row in iter_render_steps(document, profile) if row)
            self.assertEqual(1, int(groups[0].uniforms[0][0]) // 4096)
            self.assertEqual(saved, payload)
        self.assertIsNone(sprite_content(frame(), actor(item='minecraft:stone',
            user_data={'CustomColor': tag(3, 123)}), profile.items))

    def test_artificially_enchanted_quartz_block_keeps_all_48_pose_codes_and_icon_ownership(self):
        profile = frame_block_candidate_profile(ENGINE)
        for facing in range(6):
            for rotation in range(8):
                payload = actor(rotation * 45., 'minecraft:quartz_block',
                    {'ench': tag(9, [tag(10, {'id': tag(2, 9), 'lvl': tag(2, 3)})])})
                saved = copy.deepcopy(payload)
                document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(facing), nbt=payload)})
                groups = tuple(row for row in iter_render_steps(document, profile) if row)
                self.assertEqual(float(4096 + facing * 64 + rotation * 512), groups[0].uniforms[0][0])
                self.assertEqual(saved, payload)
        combined = candidate_profile(ENGINE)
        quartz = combined.items.get(('minecraft:quartz', 0))
        quartz_block = combined.items.get(('minecraft:quartz_block', 0))
        self.assertIsNotNone(quartz)
        self.assertEqual('frame_block_cube', quartz_block['family'])
        self.assertNotEqual(quartz['ui_model'], quartz_block['ui_model'])

    def test_world_missing_targets_and_cutaway_do_not_leak_neighbor_block_items(self):
        profile = frame_block_candidate_profile(ENGINE)
        document = Document((2, 1, 1), {(x, 0, 0): make_cell(frame(), nbt=actor(item='minecraft:stone'))
                                       for x in range(2)})
        targets = {'volume': (1, 2, 1), 'common': {frame(): (0,)}}
        groups = tuple(row for row in projection_plan(document, profile, targets, lambda pos: True, .5) if row)
        self.assertEqual(1., groups[0].uniforms[3][1])
        self.assertEqual(.5, groups[0].uniforms[3][3])
        self.assertEqual((), tuple(row for row in projection_plan(document, profile, targets, lambda pos: False, .5) if row))

    def test_static_block_and_flat_icon_acceptance_are_independent_and_material_scoped(self):
        self.assertFalse(source.PRODUCTION_QUALIFIED)
        self.assertFalse(item_icon_data.PRODUCTION_QUALIFIED)
        self.assertEqual({}, production_items(ENGINE))
        self.assertIsNone(production_profile(ENGINE))
        accepted_pose = dict(source.POSE, accepted=True)
        with patch.multiple(source, PRODUCTION_QUALIFIED=True, QUALIFICATION_SHA256='a' * 64,
                            QUALIFICATION_RESOURCE_SHA256=source.RESOURCE_SHA256,
                            QUALIFIED_MATERIALS=('opaque',), POSE=accepted_pose):
            profile = production_profile(ENGINE)
            self.assertEqual(('frame',), profile.content_families)
            self.assertIsNotNone(profile.items.get(('minecraft:stone', 0)))
            self.assertIsNone(profile.items.get(('minecraft:glass', 0)))
            self.assertIsNone(profile.items.get(('minecraft:diamond_sword', 0)))
            self.assertFalse(item_icon_data.PRODUCTION_QUALIFIED)
            with patch.object(source, 'QUALIFICATION_RESOURCE_SHA256', 'b' * 64):
                with self.assertRaises(ValueError):
                    production_profile(ENGINE)
            with patch.object(source, 'POSE', dict(accepted_pose, accepted=False)):
                with self.assertRaises(ValueError):
                    production_profile(ENGINE)
            with patch.object(source, 'QUALIFIED_MATERIALS', ('unknown',)):
                with self.assertRaises(ValueError):
                    production_profile(ENGINE)

    def test_candidate_rejects_engine_palette_and_scope_mismatch(self):
        self.assertEqual({}, production_items('3.11.0'))
        with self.assertRaises(ValueError):
            candidate_items('3.11.0')
        with patch.object(source, 'PALETTE_SHA256', 'b' * 64):
            with self.assertRaises(ValueError):
                candidate_items(ENGINE)
        forged = copy.deepcopy(source.ITEMS)
        next(iter(forged.values()))['content_families'] = ('frame', 'shelf')
        with patch.object(source, 'ITEMS', forged):
            with self.assertRaises(ValueError):
                candidate_items(ENGINE)


if __name__ == '__main__':
    unittest.main()
