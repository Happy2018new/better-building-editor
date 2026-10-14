"""Actual editor submission retains biome, saved actors, and ownership caches."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_bridge
from test_cauldron_render_plan import SuppliedProfile
from test_tiles import Bridge
from projection.bridge import ClientBridge
from projection.cauldron_preview import CauldronPreview
from projection.cell import actor_data, make_cell
from projection.geometry_palette import prepare_palette
from projection.large_preview import SurfacePalette
from projection.model import Document
from projection.session import Session


class Profile(SuppliedProfile):
    identity = ('test', 1)


class CauldronIntegrationTests(unittest.TestCase):
    def document(self):
        return Document((2, 1, 1), {
            (0, 0, 0): make_cell(('minecraft:cauldron', 6),
                                nbt={'unknown': {'retained': 9}}),
        }, biome='swampland')

    def test_editor_surface_palette_uses_current_document_biome_and_strips_private_metadata(self):
        document = self.document()
        surface = SurfacePalette(document.size)
        for position, value in document.blocks.items():
            surface.add(position, value)
        before = deepcopy((document.to_data(), surface.palette_data()))
        submitted, seen_biomes = {}, []
        profile = Profile()
        original_top = profile.top
        def top(material, actor, biome):
            seen_biomes.append(biome)
            return original_top(material, actor, biome)
        profile.top = top
        bridge = ClientBridge.__new__(ClientBridge)
        bridge.session = SimpleNamespace(editor=SimpleNamespace(document=document),
                                          cauldron_profile=profile)
        bridge.models, bridge.model_layouts, bridge.level = {}, {}, 'level'
        palette = SimpleNamespace(DeserializeBlockPalette=lambda data: submitted.update(data) or True)
        bridge.factory = SimpleNamespace(
            CreateBlock=lambda level: SimpleNamespace(GetBlankBlockPalette=lambda: palette),
            CreateBlockGeometry=lambda level: SimpleNamespace(
                CombineBlockPaletteToGeometry=lambda palette, name, mode: name))
        self.assertTrue(bridge.geometry(surface, name='cauldron_editor'))
        self.assertEqual(['swampland'], seen_biomes)
        self.assertEqual({('minecraft:cauldron', 0): [0]}, submitted['common'])
        self.assertEqual(before, (document.to_data(), surface.palette_data()))
        self.assertFalse(any(str(key).startswith('_') for key in submitted))

    def test_cauldron_preview_snapshots_nbt_and_obeys_visibility(self):
        session = Session(Bridge())
        document = self.document()
        session._loaded(document)
        preview = CauldronPreview(session, Profile())
        signature = preview.signature()
        preview._start(signature)
        before = deepcopy(preview.document.to_data())
        document.set_cell((0, 0, 0), ('minecraft:stone', 0))
        self.assertEqual(before, preview.document.to_data())
        self.assertEqual(1, len([group for group in preview.iterator if group is not None]))
        session.editor.hidden_layers = {0}
        preview._start(preview.signature())
        self.assertEqual([], [group for group in preview.iterator if group is not None])

    def test_profile_changes_rebuild_cached_native_shell_and_preserve_saved_nbt(self):
        bridge = Bridge()
        session = Session(bridge)
        session._loaded(self.document())
        bridge.settle(session)
        before = deepcopy(session.editor.document.to_data())
        builds = len(bridge.builds)
        session.cauldron_profile = Profile()
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(builds + 1, len(bridge.builds))
        session.cauldron_profile = Profile()
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(builds + 1, len(bridge.builds))
        session.cauldron_profile = None
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(builds + 1, len(bridge.builds))
        self.assertEqual(before, session.editor.document.to_data())

    def test_plain_water_biome_change_rebuilds_editor_and_world_colors_without_recoloring_potions(self):
        from projection import biomes
        from projection.cauldron_profile import candidate_profile
        from projection.cauldron_render_plan import iter_render_steps
        from projection.debug_cauldron_blueprints import FOCUS, source_document
        profile = candidate_profile()
        session = Session(Bridge())
        session._loaded(source_document('water6'))
        preview = CauldronPreview(session, profile)
        old_signature = preview.signature()
        original_actor = actor_data(session.editor.document.get(FOCUS))
        colors = []
        for biome in ('plains', 'swampland'):
            session.editor.document.biome = biome
            preview._start(preview.signature())
            self.assertEqual(biome, preview.document.biome)
            colors.append(profile.top(('minecraft:cauldron', 6), original_actor, biome).color)
            for world in (False, True):
                groups = [group for group in iter_render_steps(preview.document, profile, world=world)
                          if group is not None]
                self.assertEqual(1, len(groups))
                self.assertEqual(biomes.water_appearance(biome)[0], groups[0].key[1][2])
        self.assertNotEqual(colors[0], colors[1])
        self.assertNotEqual(old_signature, preview.signature())
        self.assertEqual(original_actor, actor_data(session.editor.document.get(FOCUS)))
        for case in ('potion_5_0', 'custom_red'):
            document = source_document(case)
            payload = actor_data(document.get(FOCUS))
            self.assertEqual(profile.top(('minecraft:cauldron', 6), payload, 'plains').color,
                             profile.top(('minecraft:cauldron', 6), payload, 'swampland').color)


if __name__ == '__main__':
    unittest.main()
