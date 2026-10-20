"""Water owns custom draws while complete mixed-fluid sources retain native lava."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import liquid_product_deployment as deployment
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.geometry_palette import prepare_palette
from projection.liquid_product_preview import ProductLiquidPreview
from projection.liquid_product_plan import iter_groups
from projection.model import Document
from tests.test_liquid_product_owner_contracts import finish, records, world_groups
from tests.test_liquid_render import Runtime


FOCUS = (2, 2, 2)


def liquid(name, depth=0):
    return material(name, {'liquid_depth': depth})


def source(lava_name='lava', depth=0, background=False):
    lava = liquid(lava_name, depth)
    barrier = make_cell(AIR, lava) if background else lava
    return Document((7, 4, 7), {FOCUS: liquid('water'), (2, 2, 1): barrier,
        (2, 1, 1): liquid('flowing_water', 7), (6, 0, 6): lava})


def only_focus(groups):
    return [row for row in records(groups) if row[0] == FOCUS]


class MixedLiquidFamiliesTests(unittest.TestCase):
    def owners(self, document):
        profile = deployment.candidate_profile()
        session = SimpleNamespace(editor=SimpleNamespace(document=document, revision=0, layer=2),
            preview_hidden=lambda: (), solo_layer=False, emit=lambda unused: None, opacity=1.)
        preview = profile.preview_factory(session, profile.provider_factory, profile.models, profile.max_groups)
        self.assertIsInstance(preview, ProductLiquidPreview)
        runtime = Runtime()
        runtime.session = session
        world = profile.projection_factory(runtime, document, (10, 64, 20), profile, 0)
        self.addCleanup(preview.close)
        self.addCleanup(world.close)
        world.renderer.SETTLE_SECONDS = 0.
        world.request()
        finish(preview)
        finish(world)
        world.publish()
        return preview, world

    def test_mixed_aliases_depths_and_layers_keep_native_lava_and_plan_only_water(self):
        profile = deployment.candidate_profile()
        for name in ('lava', 'flowing_lava'):
            for depth in (0, 3, 8, 15):
                for back in (False, True):
                    with self.subTest(name=name, depth=depth, background=back):
                        document = source(name, depth, back)
                        targets = document.palette_data()
                        before = copy.deepcopy((document.to_data(), targets))
                        native = prepare_palette(targets, liquid_profile=profile)
                        lava = liquid(name, depth)
                        self.assertIn(lava, native['common'])
                        self.assertFalse(any('water' in value[0]
                            for layer in ('common', 'extra') for value in native[layer]))
                        for selected in (None, targets):
                            provider = profile.provider_factory(document)
                            self.assertEqual(profile.supported_names, provider.supported_names)
                            groups = list(iter_groups(document, provider, selected))
                            self.assertTrue(groups)
                            self.assertTrue(all('water' in group.texture_key for group in groups))
                            self.assertEqual({FOCUS, (2, 1, 1)},
                                {shape.position for group in groups for shape in group.surfaces})
                        self.assertEqual(before, (document.to_data(), targets))

    def test_water_planner_ignores_pure_lava_sources_and_lava_only_targets(self):
        profile = deployment.candidate_profile()
        for name in ('lava', 'flowing_lava'):
            lava = liquid(name, 3)
            document = Document((3, 2, 3), {(1, 1, 1): lava})
            for selected in (None, document.palette_data()):
                self.assertEqual([], list(iter_groups(document, profile.provider_factory(document), selected)))
            mixed = source(name)
            targets = mixed.palette_data(lambda pos: pos == (6, 0, 6))
            self.assertEqual([], list(iter_groups(mixed, profile.provider_factory(mixed), targets)))
            with self.assertRaisesRegex(ValueError, 'no validated shape profile'):
                profile.provider_factory(document).surface(document, (1, 1, 1), 0, lava)

    def test_actual_editor_and_world_full_missing_restore_keep_complete_lava_barriers(self):
        for name in ('lava', 'flowing_lava'):
            for back in (False, True):
                with self.subTest(name=name, background=back):
                    document = source(name, 3, back)
                    before = copy.deepcopy(document.to_data())
                    preview, world = self.owners(document)
                    baseline = only_focus(world_groups(world))
                    self.assertTrue(baseline)
                    self.assertEqual(baseline, only_focus(preview.groups.values()))
                    self.assertEqual([0], [row[3] for row in baseline if row[1] & 1])
                    complete = records(world_groups(world))
                    sx, unused_sy, sz = document.size
                    occupied = bytearray(document.volume)
                    for x, y, z in ((2, 2, 1), (2, 1, 1), (6, 0, 6)):
                        occupied[(y * sx + x) * sz + z] = 2
                    for targets, mask in ((document.palette_data(lambda pos: pos == FOCUS), None),
                                          (None, occupied)):
                        world.request(targets, occupied=mask)
                        finish(world)
                        self.assertEqual(baseline, records(world_groups(world)))
                        self.assertEqual(document.blocks, world.document.blocks)
                    world.request()
                    finish(world)
                    self.assertEqual(complete, records(world_groups(world)))
                    self.assertEqual(before, document.to_data())

    def test_opposing_lava_barrier_still_changes_water_flow_when_not_drawn(self):
        profile = deployment.candidate_profile()
        document = source()
        target = document.palette_data(lambda pos: pos == FOCUS)
        groups = list(iter_groups(document, profile.provider_factory(document), target))
        blocked = [shape.flow_uv for group in groups for shape in group.surfaces if shape.faces & 1]
        document.blocks[(2, 2, 1)] = AIR
        groups = list(iter_groups(document, profile.provider_factory(document), target))
        open_drop = [shape.flow_uv for group in groups for shape in group.surfaces if shape.faces & 1]
        self.assertEqual([None], blocked)
        self.assertEqual([(profile.top_templates['flowing_water_grey'], 128)], open_drop)


if __name__ == '__main__':
    unittest.main()
