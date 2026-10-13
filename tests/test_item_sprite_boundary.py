"""Exactly one item owner per supported cell; other content keeps its fallback."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from projection import block_registry, static_frame_item_data
from projection.cell import AIR, make_cell
from projection.debug_blueprints import build
from projection.debug_item_blueprints import IDENTITY
from projection.geometry_palette import prepare_palette
from projection.item_sprite_plan import iter_render_steps
from projection.item_sprite_profile import candidate_profile
from projection.item_sprite_projection import projection_plan
from projection.large_preview import SurfacePalette
from projection.model import Document
from projection.occupancy import ProjectionOccupancy
from projection.render_context import (ContextBatchBuilder, prepare_context_palette,
                                        prepare_document_context)
from projection.session import Session
from projection.world_projection import WorldProjection
from test_occupancy_review import Runtime, STONE
from test_static_frame_items import actor, frame
from test_tiles import Bridge


class ItemOwnerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.static = copy.deepcopy(static_frame_item_data.FRAME_ITEMS)
        self.static[('minecraft:diamond_sword', 0)]['accepted'] = True
        self.proxies = frozenset(self.static[('minecraft:diamond_sword', 0)]['proxies'].values())
        self.profile = candidate_profile()

    def overlays(self, data):
        palettes = ([row[2] for row in data['_context_batches']]
                    if '_context_batches' in data else [data])
        return sum(len(indices) for palette in palettes
                   for value, indices in palette['common'].items() if value[0] in self.proxies)

    def sprite_slots(self, groups):
        return sum(int(group.uniforms[3][1]) for group in groups if group is not None)

    def test_all_supported_faces_rotations_and_families_have_one_item_owner(self):
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            for family in ('minecraft:frame', 'minecraft:glow_frame'):
                for facing in range(6):
                    for rotation in range(8):
                        material = block_registry.from_states(family, block_registry.states(frame(facing)))
                        document = Document((1, 1, 1), {(0, 0, 0):
                            make_cell(material, nbt=actor(rotation*45.))})
                        saved = copy.deepcopy(document.to_data())
                        self.assertEqual(1, self.overlays(prepare_palette(document.palette_data())))
                        self.assertEqual(0, self.overlays(prepare_palette(document.palette_data(),
                                                                         item_profile=self.profile)))
                        self.assertEqual(1, self.sprite_slots(iter_render_steps(document, self.profile)))
                        self.assertEqual(saved, document.to_data())

    def test_disabled_or_unsupported_profile_keeps_static_fallback_and_actor_data(self):
        document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=actor())})
        saved = copy.deepcopy(document.to_data())
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            for profile in (None, SimpleNamespace(items={})):
                self.assertEqual(1, self.overlays(prepare_palette(document.palette_data(),
                                                                  item_profile=profile)))
        self.assertEqual(saved, document.to_data())

    def test_background_frame_promoted_for_native_render_is_not_suppressed(self):
        document = Document((1, 1, 1), {(0, 0, 0): make_cell(AIR, frame())})
        source = document.palette_data()
        # Raw SDK palettes can include actors for a promoted secondary material.
        source['actor'] = {'minecraft:frame': {0: actor()}}
        saved = copy.deepcopy(source)
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            self.assertEqual(1, self.overlays(prepare_palette(source,
                                                              item_profile=self.profile)))
            self.assertEqual(0, self.sprite_slots(iter_render_steps(document, self.profile)))
        self.assertEqual(saved, source)

    def test_empty_unknown_custom_and_invalid_pose_never_become_sprite_targets(self):
        empty = actor()
        empty.pop('Item')
        payloads = (empty, actor(item='minecraft:filled_map'),
                    actor(user_data={'custom': {'__type__': 3, '__value__': 1}}), actor(22.5))
        for payload in payloads:
            document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=payload)})
            saved = copy.deepcopy(document.to_data())
            with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
                enabled = prepare_palette(document.palette_data(), item_profile=self.profile)
                disabled = prepare_palette(document.palette_data())
                self.assertEqual(disabled, enabled)
                self.assertEqual(0, self.sprite_slots(iter_render_steps(document, self.profile)))
            self.assertEqual(saved, document.to_data())

    def test_observed_plain_enchanted_and_empty_fixture_uses_exactly_four_sprite_slots(self):
        document = build(IDENTITY)
        saved = copy.deepcopy(document.to_data())
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            self.assertEqual(2, self.overlays(prepare_palette(document.palette_data())))
            self.assertEqual(0, self.overlays(prepare_palette(document.palette_data(),
                                                              item_profile=self.profile)))
            groups = tuple(row for row in iter_render_steps(document, self.profile) if row is not None)
            self.assertEqual(4, self.sprite_slots(groups))
            self.assertEqual(2, sum(int(code)//4096 for row in groups for code in row.uniforms[0]))
        self.assertEqual(saved, document.to_data())

    def test_context_targets_share_the_item_owner_without_leaking_neighbor_contents(self):
        document = Document((2, 2, 1), {(0, 0, 0): make_cell(frame(), nbt=actor()),
                                       (1, 1, 0): make_cell(frame(), nbt=actor(45.))})
        target = document.palette_data(lambda pos: pos == (0, 0, 0))
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            palettes = [prepare_context_palette(document.palette_data(), target, item_profile=self.profile),
                        prepare_document_context(document, target, item_profile=self.profile)]
            builder = ContextBatchBuilder(document, target, item_profile=self.profile)
            for unused in builder.prepare():
                pass
            palettes.append(builder.data)
            self.assertTrue(all(self.overlays(data) == 0 for data in palettes))
            self.assertEqual(1, self.sprite_slots(projection_plan(document, self.profile, target,
                                                                   lambda pos: True, 1.)))
            self.assertEqual(1, self.sprite_slots(iter_render_steps(document, self.profile,
                                                                    lambda pos: pos[1] == 1)))

    def test_missing_rebuild_keeps_frozen_profile_after_session_changes(self):
        document = Document((2, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=actor()),
                                       (1, 0, 0): make_cell(frame(), nbt=actor(45.))})
        runtime, origin = Runtime(), (100, 64, 100)
        runtime.world[origin] = STONE
        session = SimpleNamespace(editor=SimpleNamespace(document=document, layer=None),
            preview_hidden=lambda: (), solo_layer=False, item_profile=self.profile)
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime,
            level='level', projection_serial=1, projection_occupancy=None)
        tracker = ProjectionOccupancy(bridge, origin)
        session.item_profile = None
        self.assertIs(self.profile, tracker.item_profile)

        def prepare():
            tracker.snapshot = tracker.state[:]
            tracker.output = SurfacePalette(tracker.size)
            for unused in tracker.prepare():
                pass
            return tracker.prepared, tracker.output.palette_data()

        def visible(pos):
            return tracker.state[tracker.index(pos)] != 2

        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static):
            self.assertFalse(tracker.initial_visible((0, 0, 0)))
            self.assertTrue(tracker.initial_visible((1, 0, 0)))
            data, targets = prepare()
            self.assertEqual(0, self.overlays(data))
            self.assertEqual(1, self.sprite_slots(projection_plan(document, tracker.item_profile,
                                                                  targets, visible, 1.)))
            runtime.world[origin] = AIR
            tracker.read((0, 0, 0))
            data, targets = prepare()
            self.assertEqual(0, self.overlays(data))
            self.assertEqual(2, self.sprite_slots(projection_plan(document, tracker.item_profile,
                                                                  targets, visible, 1.)))

    def test_full_and_missing_initial_build_share_the_profile_with_the_companion_owner(self):
        document = Document((1, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=actor())})
        runtime = Runtime()
        runtime.CreateGame = lambda level: SimpleNamespace(GetCurrentDimension=lambda: 0)
        session = SimpleNamespace(editor=SimpleNamespace(document=document, layer=None),
            preview_hidden=lambda: (), solo_layer=False, opacity=1., liquid_profile=None)
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime,
            level='level', projection_serial=1, projection_occupancy=None)
        def companion(unused_bridge, unused_doc, unused_origin, profile, *args):
            return SimpleNamespace(profile=profile, prepare=lambda *args: iter(()))
        with patch.object(static_frame_item_data, 'FRAME_ITEMS', self.static), \
                patch('projection.item_sprite_projection.ItemProjection', side_effect=companion):
            for missing in (False, True):
                session.item_profile, session.projection_missing = self.profile, missing
                work = WorldProjection(bridge, (100, 64, 100))
                session.item_profile = None
                for unused in work.prepare():
                    pass
                self.assertIs(self.profile, work.item_profile)
                self.assertIs(self.profile, work.liquid.profile)
                if missing:
                    self.assertIs(self.profile, work.occupancy.item_profile)
                self.assertEqual(0, self.overlays(work.prepared))

    def test_editor_mesh_cache_distinguishes_profile_enable_and_disable(self):
        bridge = Bridge()
        session = Session(bridge)
        session._loaded(Document((1, 1, 1), {(0, 0, 0): make_cell(frame(), nbt=actor())}))
        bridge.settle(session)
        original = session.preview_signature()
        builds = len(bridge.builds)
        session.item_profile = self.profile
        self.assertNotEqual(original, session.preview_signature())
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(builds+1, len(bridge.builds))
        session.item_profile = None
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(builds+1, len(bridge.builds))
        self.assertEqual(original, session.preview_signature())


if __name__ == '__main__':
    unittest.main()
