"""Slab clicks exercise real picking, layer edits, and undo transactions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.camera import pick_target, raycast
from projection.cell import AIR, actor_data, make_cell
from projection.model import Document, Editor
from projection.session import Session
from projection.slab_placement import slab_half, merged_slab, placed_slab

STONE = ('minecraft:stone', 0)
BOTTOM = ('minecraft:oak_slab', 0)
TOP = ('minecraft:oak_slab', 1)
DOUBLE = ('minecraft:oak_double_slab', 0)
WATER = ('minecraft:water', 0)
POS = (2, 2, 2)


class Bridge:
    def later(self, delay, callback):
        pass


class SlabPlacementTests(unittest.TestCase):
    def session(self, blocks=None, layer=2):
        session = Session(Bridge())
        session.editor = Editor(Document((6, 6, 6), blocks or {}))
        session.editor.edit_layer = layer
        session.editor.material = BOTTOM
        session.choose_mode('place')
        return session

    def test_every_dump_slab_family_resolves_halves_and_double_without_aux_arithmetic(self):
        singles = sorted(name for name in registry.BLOCKS if name.endswith('_slab') and
                         'double' not in name.split(':', 1)[1].split('_'))
        self.assertEqual(62, len(singles))
        for name in singles:
            for aux in registry.aux_values(name):
                with self.subTest(name=name, aux=aux):
                    material = (name, aux)
                    self.assertIn(slab_half(material), ('top', 'bottom'))
                    bottom = placed_slab(material, (0, 1, 0))
                    top = placed_slab(material, (0, -1, 0))
                    self.assertEqual('bottom', slab_half(bottom))
                    self.assertEqual('top', slab_half(top))
                    double = merged_slab(bottom, top)
                    self.assertIsNone(slab_half(double))
                    self.assertEqual(double, registry.canonical(double))
                    self.assertEqual(double, merged_slab(top, bottom))

    def test_legacy_aliases_and_mismatched_materials(self):
        self.assertEqual('bottom', slab_half(('minecraft:wooden_slab', 0)))
        self.assertEqual('top', slab_half(('minecraft:wooden_slab', 8)))
        self.assertEqual(DOUBLE, merged_slab(('minecraft:wooden_slab', 8), BOTTOM))
        self.assertIsNone(merged_slab(BOTTOM, ('minecraft:birch_slab', 0)))
        self.assertIsNone(slab_half(('minecraft:double_wooden_slab', 0)))
        self.assertIsNone(slab_half(('custom:oak_slab', 0)))

    def test_placement_chooses_face_and_side_height_and_preserves_palette_material(self):
        cases = [((0, 1, 0), (2.25, 3., 2.25), BOTTOM),
                 ((0, -1, 0), (2.25, 2., 2.25), TOP)]
        for normal in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)):
            cases.extend((normal, (2.25, height, 2.25), result)
                         for height, result in ((2.25, BOTTOM), (2.5, BOTTOM), (2.75, TOP)))
        for mode in (0, 1, 2):
            for normal, point, material in cases:
                with self.subTest(mode=mode, normal=normal, point=point):
                    session = self.session({POS: STONE}, mode)
                    target = POS if mode == 1 else tuple(POS[i] + normal[i] for i in range(3))
                    self.assertEqual((target, None), session.cursor_target(POS, normal, point))
                    self.assertEqual(1, session.point_action(POS, normal, point))
                    self.assertEqual(material, session.editor.document.get_layer(target, mode))
                    self.assertEqual(BOTTOM, session.editor.material)
                    self.assertEqual(1, len(session.editor.undo_stack))
                    session.editor.undo()
                    self.assertEqual({POS: STONE}, dict(session.editor.document.blocks.items()))
                    session.editor.redo()
                    self.assertEqual(material, session.editor.document.get_layer(target, mode))

    def test_grid_cell_respects_explicit_selected_half(self):
        session = self.session()
        session.editor.material = TOP
        self.assertEqual(1, session.point_action(POS))
        self.assertEqual(TOP, session.editor.document.get(POS))

    def test_exposed_half_merge_and_double_break_are_single_transactions(self):
        for mode in (0, 2):
            for original, normal, point in ((BOTTOM, (0, 1, 0), (2.4, 2.5, 2.4)),
                                            (TOP, (0, -1, 0), (2.4, 2.5, 2.4))):
                with self.subTest(mode=mode, original=original):
                    session = self.session({POS: original}, mode)
                    self.assertEqual((POS, None), session.cursor_target(POS, normal, point))
                    self.assertEqual(1, session.point_action(POS, normal, point))
                    self.assertEqual(DOUBLE, session.editor.document.get(POS))
                    session.editor.undo()
                    self.assertEqual(original, session.editor.document.get(POS))
                    session.editor.redo()
                    session.choose_mode('erase')
                    session.erase_scope = 'single'
                    self.assertEqual(1, session.point_action(POS))
                    self.assertEqual(AIR, session.editor.document.get(POS))
                    session.editor.undo()
                    self.assertEqual(DOUBLE, session.editor.document.get(POS))

    def test_opposite_half_in_adjacent_target_merges_but_same_half_is_occupied(self):
        neighbor = (3, 2, 2)
        for material, expected in ((TOP, DOUBLE), (BOTTOM, BOTTOM)):
            session = self.session({POS: STONE, neighbor: material})
            session.point_action(POS, (1, 0, 0), (3., 2.25, 2.5))
            self.assertEqual(1 if material == TOP else 0, len(session.editor.undo_stack))
            self.assertEqual(expected, session.editor.document.get(neighbor))

    def test_strict_layer_merge_keeps_other_layer_and_actor(self):
        actor = {'id': 'Chest', 'Items': [{'Count': 3, 'tag': {'bytes': b'\x00\xff'}}]}
        before = make_cell(STONE, BOTTOM, actor)
        session = self.session({POS: before}, 1)
        self.assertEqual(1, session.point_action(POS, (0, 1, 0), (2.3, 3., 2.3)))
        self.assertEqual(make_cell(STONE, DOUBLE, actor), session.editor.document.get(POS))
        self.assertEqual(actor, actor_data(session.editor.document.get(POS)))
        session.editor.undo()
        self.assertEqual(before, session.editor.document.get(POS))
        session = self.session({POS: make_cell(BOTTOM, WATER)}, 0)
        session.point_action(POS, (0, 1, 0), (2.3, 2.5, 2.3))
        self.assertEqual(make_cell(DOUBLE, WATER), session.editor.document.get(POS))

    def test_auto_merge_expels_water_but_undo_restores_complete_waterlogged_slab(self):
        before = make_cell(BOTTOM, WATER)
        session = self.session({POS: before})
        self.assertEqual(1, session.point_action(POS, (0, 1, 0), (2.3, 2.5, 2.3)))
        self.assertEqual(DOUBLE, session.editor.document.get(POS))
        session.editor.undo()
        self.assertEqual(before, session.editor.document.get(POS))

    def test_locked_and_masked_merge_do_not_modify_or_enter_history(self):
        for condition in ('locked', 'mask'):
            session = self.session({POS: BOTTOM})
            if condition == 'locked':
                session.editor.locked_layers.add(2)
            else:
                session.editor.mask = 'air'
            session.point_action(POS, (0, 1, 0), (2.3, 2.5, 2.3))
            self.assertEqual(BOTTOM, session.editor.document.get(POS))
            self.assertEqual([], session.editor.undo_stack)

    def test_raycast_hits_actual_slab_surface_and_passes_empty_half(self):
        for material, surface, sign in ((BOTTOM, 2.5, 1), (TOP, 2.5, -1)):
            doc = Document((6, 6, 6), {POS: material})
            origin = (2.25, 8. if sign > 0 else -2., 2.25)
            direction = (0., -float(sign), 0.)
            hit = raycast(doc, origin, direction, detailed=True)
            self.assertEqual((POS, (0, sign, 0), (2.25, surface, 2.25)), hit)
        for material, occupied, empty in ((BOTTOM, 2.25, 2.75), (TOP, 2.75, 2.25)):
            doc = Document((6, 6, 6), {POS: material, (4, 2, 2): STONE})
            self.assertEqual(POS, raycast(doc, (-2., occupied, 2.5), (1., 0., 0.))[0])
            self.assertEqual((4, 2, 2), raycast(doc, (-2., empty, 2.5), (1., 0., 0.))[0])
        doc = Document((6, 6, 6), {POS: DOUBLE})
        self.assertEqual(3., raycast(doc, (2.3, 8., 2.3), (0., -1., 0.), detailed=True)[2][1])

    def test_picker_to_real_action_merges_slab_using_retained_surface(self):
        session = self.session({POS: BOTTOM})
        hit = pick_target(session.editor.document, (2.3, 8., 2.3), (0., -1., 0.), detailed=True)
        self.assertEqual((POS, None), session.cursor_target(*hit))
        self.assertEqual(1, session.point_action(*hit))
        self.assertEqual(DOUBLE, session.editor.document.get(POS))

    def test_public_blueprint_is_the_shared_source_for_click_and_render_cases(self):
        from projection.debug_blueprints import BLUEPRINTS, VISUAL_CASES, build
        from projection.debug_slab_blueprints import METADATA, CASES
        from projection.cell import background
        self.assertIn(METADATA, BLUEPRINTS)
        contract = VISUAL_CASES['slab_interactions']
        self.assertEqual(METADATA[0], contract['fixture'])
        self.assertEqual(CASES, contract['cases'])
        document = build(contract['fixture'])
        for case in CASES:
            value = document.get(case['pos'])
            expected = registry.from_states('minecraft:' + case['name'],
                                            {'minecraft:vertical_half': case['half']})
            self.assertEqual(expected, tuple(value))
            self.assertEqual(WATER if case.get('water') else AIR, background(value))
        self.assertEqual('pending', contract['acceptance']['editor'])
        self.assertEqual('pending', contract['acceptance']['full'])
        self.assertEqual('pending', contract['acceptance']['missing'])


if __name__ == '__main__':
    unittest.main()
