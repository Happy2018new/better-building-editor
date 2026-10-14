import copy
import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, actor_data, foreground, make_cell
from projection.debug_blueprints import build, material
from projection.debug_spawner_blueprints import POSITIONS
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.model import Document
from projection.render_context import ContextBatchBuilder, ContextPaletteBuilder
from projection.render_layout import OVERLAY_BASE
from projection.spawner_marker import append_markers, candidate_profile, production_profile
from projection.spawner_marker_data import MARKERS
from projection import spawner_marker_qualification as qualification
from projection.session import Session
from test_tiles import Bridge


class SpawnerMarkerTests(unittest.TestCase):
    def test_disabled_default_and_wrong_engine_keep_native_route(self):
        self.assertIsNone(production_profile('3.9.0.401155'))
        with patch.object(qualification, 'PRODUCT_QUALIFIED', False):
            self.assertIsNone(production_profile('3.10.0.420447'))
        doc = build('test.entities.spawners')
        original = copy.deepcopy(doc.to_data())
        result = prepare_palette(doc.palette_data())
        self.assertFalse(any(value[0] in MARKERS.values() for value in result['common']))
        self.assertEqual(original, doc.to_data())

    def test_marker_and_shell_keep_complete_source_data_and_separate_band(self):
        doc = build('test.entities.spawners')
        original = copy.deepcopy(doc.to_data())
        source = doc.palette_data()
        before = copy.deepcopy(source)
        prepared = prepare_palette(source, spawner_profile=candidate_profile())
        indices = [(position[1] * doc.size[0] + position[0]) * doc.size[2] + position[2]
                   for position in POSITIONS]
        expected = {'empty': (indices[0], indices[3]),
                    'present': (indices[1], indices[2], indices[4], indices[5]),
                    'unknown': (indices[6], indices[7])}
        plane = doc.size[0] * doc.size[2]
        for state, positions in expected.items():
            self.assertEqual(sorted(index + OVERLAY_BASE * plane for index in positions),
                             prepared['common'][(MARKERS[state], 0)])
        self.assertEqual(before, source)
        self.assertEqual(original, doc.to_data())
        self.assertEqual((doc.size[2], doc.size[0], OVERLAY_BASE + doc.size[1]), prepared['volume'])
        self.assertEqual(8, sum(len(value) for key, value in prepared['common'].items()
                                if key[0] in ('minecraft:mob_spawner', 'minecraft:trial_spawner')))

    def test_view_local_band_uses_supplied_height_and_validates_source_bounds(self):
        doc = build('test.entities.spawners')
        result = prepare_palette(doc.palette_data(), overlay_base=7, spawner_profile=candidate_profile())
        self.assertEqual((16, 32, 13), result['volume'])
        for index in (-1, 1, True, .5):
            with self.assertRaises(ValueError):
                append_markers({material('mob_spawner'): [index]}, {}, (1, 1, 1), 2, candidate_profile())
        for volume, base in ((None, 2), ((1, 1, 1), 1), ((1, 1, 129), 256)):
            with self.assertRaises(ValueError):
                append_markers({material('mob_spawner'): [0]}, {}, volume, base, candidate_profile())

    def test_no_marker_does_not_expand_or_mutate_unrelated_palettes(self):
        common = {material('stone'): [0]}
        before = copy.deepcopy(common)
        self.assertIsNone(append_markers(common, {}, (1, 1, 1), 2, candidate_profile()))
        self.assertEqual(before, common)

    def test_badges_are_render_only_and_never_appear_in_picker(self):
        self.assertTrue(set(MARKERS.values()) <= INTERNAL_RENDER_BLOCKS)
        doc = build('test.entities.spawners')
        serialized = repr(doc.to_data())
        self.assertFalse(any(name in serialized for name in MARKERS.values()))

    def test_missing_target_keeps_only_target_marker_and_native_neighbor_context(self):
        original = build('test.entities.spawners')
        first, second = POSITIONS[:2]
        doc = Document((8, 4, 8))
        doc.blocks[(2, 1, 2)] = original.get(first)
        doc.blocks[(3, 1, 2)] = original.get(second)
        target = Document(doc.size, {(2, 1, 2): doc.get((2, 1, 2))})
        source = copy.deepcopy(doc.to_data())
        for builder_type in (ContextPaletteBuilder, ContextBatchBuilder):
            builder = builder_type(doc, target.palette_data(), spawner_profile=candidate_profile())
            for unused in builder.prepare():
                pass
            palettes = ([row[2] for row in builder.data['_context_batches']]
                        if '_context_batches' in builder.data else [builder.data])
            counts = dict((name, sum(len(palette['common'].get((name, 0), ())) for palette in palettes))
                          for name in MARKERS.values())
            self.assertEqual(1, counts[MARKERS['empty']])
            self.assertEqual(0, counts[MARKERS['present']])
            self.assertEqual(0, counts[MARKERS['unknown']])
        self.assertEqual(source, doc.to_data())

    def test_partial_bad_payload_does_not_prevent_another_valid_cell(self):
        doc = Document((2, 1, 1), {(0, 0, 0): material('mob_spawner'),
                                  (1, 0, 0): material('stone')})
        result = prepare_palette(doc.palette_data(), spawner_profile=candidate_profile())
        self.assertEqual([0], result['common'][material('mob_spawner')])
        self.assertEqual([1], result['common'][material('stone')])
        self.assertEqual([OVERLAY_BASE * 2], result['common'][(MARKERS['unknown'], 0)])

    def test_declared_qualified_without_complete_evidence_fails_closed(self):
        with patch.object(qualification, 'PRODUCT_QUALIFIED', True), patch.object(qualification, 'GATES', {}):
            with self.assertRaises(ValueError):
                production_profile('3.10.0.420447')

    def test_editor_cache_tracks_badge_ownership_and_reuses_matching_state_only(self):
        bridge = Bridge()
        session = Session(bridge)
        session._loaded(Document((2, 1, 1), {(0, 0, 0): material('mob_spawner')}))
        bridge.settle(session)
        before = copy.deepcopy(session.editor.document.to_data())
        builds = len(bridge.builds)
        original = session.tiles.parts[(0, 0, 0)]['name']
        session.spawner_profile = candidate_profile()
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(builds + 1, len(bridge.builds))
        self.assertNotEqual(original, session.tiles.parts[(0, 0, 0)]['name'])
        session.spawner_profile = candidate_profile()
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(builds + 1, len(bridge.builds))
        session.spawner_profile = None
        session.refresh_preview();bridge.settle(session)
        self.assertEqual(original, session.tiles.parts[(0, 0, 0)]['name'])
        self.assertEqual(builds + 1, len(bridge.builds))
        self.assertEqual(before, session.editor.document.to_data())

    def test_missing_projection_rebuild_preserves_snapshotted_badge_owner(self):
        from test_occupancy_review import Runtime
        from modern_projection.projection.occupancy import ProjectionOccupancy
        from modern_projection.projection.large_preview import SurfacePalette
        document = Document((2, 1, 1), {(0, 0, 0): material('mob_spawner')})
        runtime = Runtime()
        profile = candidate_profile()
        session = SimpleNamespace(editor=SimpleNamespace(document=document,layer=None),
                                  preview_hidden=lambda: (),solo_layer=False,
                                  opacity=1.,projection_missing=True,spawner_profile=profile)
        bridge = SimpleNamespace(session=session,factory=runtime,system=runtime,
                                 level='level',projection_serial=1,alive=True,entity=None,
                                 projection_occupancy=None,projection_mesh=None,models={},model_layouts={})
        tracker = ProjectionOccupancy(bridge,(100,64,100))
        session.spawner_profile = None
        self.assertIs(profile,tracker.spawner_profile)
        tracker.initial_visible((0,0,0))
        tracker.snapshot = tracker.state[:]
        tracker.output = SurfacePalette(document.size)
        for unused in tracker.prepare():
            pass
        rows = tracker.prepared['_context_batches']
        self.assertEqual(1,sum(len(data['common'].get((MARKERS['unknown'],0),()))
                               for origin,context,data in rows))


if __name__ == '__main__':
    unittest.main()
