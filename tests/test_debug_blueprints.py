"""Editable native fixtures preserve layers, groups and complete actor data."""
import ast
from functools import partial
import json
import sys
from types import SimpleNamespace
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_groups import group_partner, actor_pair_position
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import BLUEPRINTS, CATEGORIES, VISUAL_CASES, build, entries, material, open_blueprint
from projection.render_layout import OVERLAY_BASE
from projection.debug_entity_blueprints import ENTITY_CASES, REFERENCE_EXCLUSIONS, coverage
from projection.debug_entity_defaults import evidence, nbt as native_nbt
from projection.geometry_palette import prepare_palette
from projection.model import Document, Editor
from projection.nbt_spatial import root_payload, scalar
from projection.session import Session
from projection.sharing_codec import decode_steps, encode_steps
from projection.visible_actor import entity_nbt, render_actor


class BlueprintReachabilityTests(unittest.TestCase):
    def test_every_registered_fixture_has_a_card_on_the_actual_public_page(self):
        from projection.debug_ordinary_blueprints import CASES, SECTIONS, search_text

        path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprint_ui.py'
        module = ast.parse(path.read_text(encoding='utf8'), filename=str(path))
        # Execute the real page functions with inert hosts and controlled hook state.
        # This exercises their routing, filtering and pagination without a game UI.
        functions = [node for node in module.body if isinstance(node, ast.FunctionDef)]
        state, cards = [], set()

        def panel(*args, **kwargs):
            if kwargs.get('key'):
                cards.add(kwargs['key'])
            return kwargs

        def use_state(default):
            return next(state[0]), lambda value: None

        def inert(*args, **kwargs):
            return kwargs

        scope = dict(Component=lambda function: function, partial=partial,
                     Panel=panel, use_state=use_state, use_effect=inert,
                     use_theme=inert, use_material_names=inert,
                     Theme=SimpleNamespace(muted='muted'), S=inert, row=inert,
                     text=inert, Action=inert, Segments=inert, Scroll=inert,
                     Input=inert, line=inert, MaterialIcon=inert, PreparedColumn=inert,
                     CATEGORIES=CATEGORIES, entries=entries, material=material,
                     open_blueprint=open_blueprint, SECTIONS=SECTIONS,
                     CASES=CASES, search_text=search_text,
                     material_name=lambda value: value[0])
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), scope)
        session = SimpleNamespace(busy=False, edit_job=None, io_job=None,
                                  confirm=inert, page='testing')
        reachable = set()
        for category, unused_title in CATEGORIES:
            sections = SECTIONS if category == 'manual' else ((None, None),)
            for section, unused_section_title in sections:
                for page in range(len(BLUEPRINTS) + 1):
                    cards.clear()
                    state[:] = [iter((category, section, '', page))]
                    scope['TestBlueprints'](session=session)
                    new = cards - reachable
                    reachable.update(cards)
                    if category != 'manual' or not new:
                        break
        self.assertEqual({row[0] for row in BLUEPRINTS}, reachable)


class DebugBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = dict((row[0], build(row[0])) for row in BLUEPRINTS)

    def test_all_fixtures_have_legal_native_layers_and_prepare_without_mutation(self):
        self.assertEqual(len(BLUEPRINTS), len(self.documents))
        self.assertEqual(7, len(CATEGORIES))
        self.assertEqual(set(self.documents), {row[0] for category, unused in CATEGORIES
                                              for row in entries(category)})
        for identity, doc in self.documents.items():
            before = doc.blocks.copy()
            for pos, value in doc.blocks.items():
                self.assertTrue(doc.contains(pos), (identity, pos))
                for part in (foreground(value), background(value)):
                    self.assertEqual(part, registry.canonical(part))
            prepared = prepare_palette(doc.palette_data())
            source_identity = identity.replace('test.ordinary.context.', '')
            height = doc.size[1] + (OVERLAY_BASE if source_identity == 'test.layers.snow' else 0)
            self.assertEqual((doc.size[2], doc.size[0], height), prepared['volume'])
            self.assertEqual(before, doc.blocks)

    def test_independent_opens_and_config_sharing_round_trip(self):
        for identity, doc in self.documents.items():
            reopened = build(identity)
            self.assertIsNot(doc, reopened)
            self.assertIsNot(doc.blocks, reopened.blocks)
            self.assertEqual(doc.blocks, reopened.blocks)
            restored = Document.from_data(json.loads(json.dumps(doc.to_data())))
            self.assertEqual(doc.blocks, restored.blocks, identity)
            text = list(encode_steps(doc))[-1]['text']
            self.assertTrue(text.startswith('MP4:'))
            shared = list(decode_steps(text))[-1]['document']
            self.assertEqual(doc.blocks, shared.blocks, identity)

    def test_water_comparison_has_dry_wet_and_background_only_fence(self):
        doc = self.documents['test.layers.water']
        fence, water = material('oak_fence'), material('water')
        self.assertEqual(fence, doc.get((3, 1, 3)))
        self.assertEqual(fence, foreground(doc.get((3, 1, 6))))
        self.assertEqual(water, background(doc.get((3, 1, 6))))
        self.assertEqual(AIR, foreground(doc.get((3, 1, 9))))
        self.assertEqual(water, background(doc.get((3, 1, 9))))

    def test_neighbor_visual_metadata_resolves_source_and_cross_chunk_cells(self):
        case = VISUAL_CASES['neighbor_context']
        doc = self.documents[case['fixture']]
        self.assertEqual(6, len(case['cells']))
        self.assertEqual(set(case['cells']), set(case['cross_chunk_cells']))
        for family, (keep, occupied) in case['cells'].items():
            with self.subTest(family=family):
                front = foreground(doc.get(keep))
                self.assertNotEqual(AIR, front)
                self.assertEqual(front[0], foreground(doc.get(occupied))[0])
                target, partner = case['cross_chunk_cells'][family]
                delta = tuple(target[i] - keep[i] for i in range(3))
                self.assertEqual(partner, tuple(occupied[i] + delta[i] for i in range(3)))
                self.assertNotEqual(tuple(v >> 4 for v in target), tuple(v >> 4 for v in partner))
                for position in (target, partner):
                    self.assertTrue(doc.contains(position))

    def test_snow_native_order_uses_measured_coverable_plants(self):
        doc = self.documents['test.layers.snow']
        for x, name in ((3, 'short_grass'), (8, 'fern'), (13, 'dandelion'), (18, 'poppy')):
            covered = doc.get((x, 1, 9))
            self.assertEqual('minecraft:snow_layer', foreground(covered)[0])
            self.assertTrue(registry.states(foreground(covered))['covered_bit'])
            self.assertEqual(material(name), background(covered))
            relationship = group_partner(background(covered))
            if relationship is not None:
                offset, expected = relationship
                self.assertEqual(expected, foreground(doc.get((x, 1 + offset[1], 9))))

    def test_snow_visual_metadata_resolves_actual_blueprint_cells(self):
        case = VISUAL_CASES['snow_plant_visibility']
        doc = self.documents[case['fixture']]
        self.assertEqual('test.layers.snow', case['fixture'])
        self.assertEqual(29, len(case['cells']))
        for row in case['cells']:
            plant = material(row['plant'])
            self.assertEqual(plant, doc.get(row['standalone']))
            self.assertEqual(tuple(range(8)), tuple(height for height, unused in row['covered']))
            for height, pos in row['covered']:
                cell = doc.get(pos)
                self.assertEqual(plant, background(cell))
                self.assertEqual(height, registry.states(foreground(cell))['height'])
                self.assertTrue(registry.states(foreground(cell))['covered_bit'])

    def test_existing_wet_and_snowy_fixtures_follow_automatic_erase_order(self):
        for identity, pos, remainder in (
                ('test.layers.water', (3, 1, 6), material('water')),
                ('test.layers.snow', (13, 1, 9), material('dandelion'))):
            source = self.documents[identity]
            editor = Editor(Document(source.size, source.blocks.copy()))
            editor.edit_layer = 2
            before = editor.document.blocks.copy()
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(remainder, editor.document.get(pos))
            editor.undo()
            self.assertEqual(before, editor.document.blocks)
            editor.redo()
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(AIR, editor.document.get(pos))

    def test_every_group_part_has_reciprocal_in_either_native_layer(self):
        for identity in ('test.layers.snow', 'test.groups.parts', 'test.registry.vanilla'):
            doc = self.documents[identity]
            for pos, cell in doc.blocks.items():
                for part in (foreground(cell), background(cell)):
                    relationship = group_partner(part)
                    if relationship is None:
                        continue
                    offset, expected = relationship
                    partner = tuple(pos[index] + offset[index] for index in range(3))
                    actual = doc.get(partner)
                    self.assertIn(expected, (foreground(actual), background(actual)), (identity, pos))

    def test_connections_have_closed_rail_loop_and_complementary_chest_halves(self):
        doc = self.documents['test.connections.context']
        corners = {(3, 1, 3): 6, (11, 1, 3): 7, (11, 1, 11): 8, (3, 1, 11): 9}
        for pos, shape in corners.items():
            self.assertEqual(shape, registry.states(foreground(doc.get(pos)))['rail_direction'])
        for z in (5, 10):
            first, second = (26, 1, z), (27, 1, z)
            if doc.get(first) == AIR:
                continue
            self.assertEqual(second, actor_pair_position(doc.get(first), first))
            self.assertEqual(first, actor_pair_position(doc.get(second), second))
            for field in ('pairlead', 'renderlead'):
                values = [scalar(root_payload(entity_nbt(actor_data(doc.get(pos)))), field)
                          for pos in (first, second)]
                self.assertEqual({0, 1}, set(values))
            for pos in (first, second):
                self.assertTrue(render_actor(actor_data(doc.get(pos))))

    def test_six_whole_document_transforms_are_reversible(self):
        inverses = {'rotate_y90': 'rotate_y270', 'rotate_y180': 'rotate_y180',
                    'rotate_y270': 'rotate_y90', 'mirror_x': 'mirror_x',
                    'mirror_y': 'mirror_y', 'mirror_z': 'mirror_z'}
        for identity in ('test.connections.context', 'test.transforms.directions'):
            source = self.documents[identity]
            for operation, inverse in inverses.items():
                editor = Editor(Document(source.size, source.blocks.copy()))
                editor._transform(operation)
                editor._transform(inverse)
                self.assertEqual(source.blocks, editor.document.blocks, (identity, operation))

    def test_vanilla_gallery_contains_every_catalogue_native_block_type(self):
        expected = {value[0] for value in registry.catalogue_values()
                    if value[0].startswith('minecraft:') and value != AIR}
        actual = {foreground(value)[0] for value in self.documents['test.registry.vanilla'].blocks.values()}
        self.assertFalse(expected - actual)

    def test_entity_reference_coverage_is_explicit(self):
        reference = json.loads((ROOT / 'docs/reference/block_entities/nemc_3.9_reference.json').read_text())
        expected = {row['name'] for row in reference['entities']}
        self.assertEqual(expected, {row[1] for row in ENTITY_CASES} | {row[0] for row in REFERENCE_EXCLUSIONS})
        report = coverage()
        self.assertEqual(57, len(report['present']) + len(report['unavailable']))
        self.assertEqual([], report['native_unobserved'])
        self.assertEqual(155, report['native_evidence']['native_block_count'])
        for doc in self.documents.values():
            for pos, value in doc.blocks.items():
                nbt = root_payload(entity_nbt(actor_data(value)))
                if nbt is not None:
                    self.assertEqual(pos, tuple(scalar(nbt, axis) for axis in ('x', 'y', 'z')))

    def test_entities_use_all_observed_native_identities_and_preserve_complete_defaults(self):
        actual = set()
        for category in ('classic', 'mechanisms', 'recent'):
            doc = self.documents['test.entities.' + category]
            for unused_pos, value in doc.blocks.items():
                root = root_payload(entity_nbt(actor_data(value)))
                if root is not None:
                    actual.add(scalar(root, 'id'))
        self.assertEqual({row[1] for row in ENTITY_CASES}, actual)
        chest = native_nbt('minecraft:chest', (2, 3, 4))
        self.assertIn('Items', root_payload(chest))
        root_payload(chest)['Items'].append({'custom': 'independent copy'})
        self.assertEqual([], root_payload(native_nbt('minecraft:chest', (2, 3, 4)))['Items'])
        for category in ('classic', 'recent'):
            doc = self.documents['test.entities.' + category]
            for unused_pos, value in doc.blocks.items():
                data = actor_data(value)
                root = root_payload(entity_nbt(data))
                if root is not None and scalar(root, 'id') in ('Sign', 'HangingSign'):
                    self.assertEqual(render_actor(data)['signRealText'], scalar(root['FrontText'], 'Text'))
                    self.assertEqual(render_actor(data)['signColor'], scalar(root['FrontText'], 'SignTextColor'))

    def test_native_default_snapshot_matches_generated_provenance_and_observed_aux(self):
        import hashlib
        from projection import entity_defaults_data as defaults
        from projection.debug_entity_defaults import material as native_material
        source = ROOT / 'tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json'
        raw = source.read_bytes()
        snapshot = json.loads(raw)
        canonical = json.dumps(snapshot, ensure_ascii=True, sort_keys=True,
                               separators=(',', ':')).encode('ascii')
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), evidence()['source_sha256'])
        self.assertEqual('canonical-json-v1', evidence()['source_hash_format'])
        self.assertEqual(set(snapshot['block_entities']), set(defaults.DEFAULTS))
        for name, row in snapshot['block_entities'].items():
            self.assertEqual((name, row['aux']), native_material(name))
            origin = tuple(scalar(root_payload(row['nbt']), axis) for axis in ('x', 'y', 'z'))
            self.assertEqual(row['nbt'], native_nbt(name, origin))


class DebugBlueprintSessionTests(unittest.TestCase):
    def test_load_resets_editor_navigation_preserves_library_and_layer(self):
        session = Session(object())
        session.refresh_preview = lambda: None
        session.editor.edit_layer = 1
        session.library = [{'id': 7, 'data': {'name': 'saved'}}]
        saved = session.library
        session.focused, session.box_anchor = (4, 5, 6), (1, 2, 3)
        session.paste_pinned, session.progress = True, {'old': True}
        session.page = 'testing'
        open_blueprint(session, 'test.layers.water')
        self.assertEqual('workspace', session.page)
        self.assertEqual(1, session.editor.edit_layer)
        self.assertIs(saved, session.library)
        self.assertIsNone(session.focused)
        self.assertIsNone(session.box_anchor)
        self.assertIsNone(session.progress)
        self.assertFalse(session.paste_pinned)
        self.assertEqual([], session.editor.undo_stack)
        self.assertEqual([], session.editor.redo_stack)

    def test_failed_key_and_busy_jobs_leave_draft_intact(self):
        session = Session(object())
        original = session.editor
        for field in ('busy', 'io_job', 'edit_job'):
            previous = getattr(session, field)
            setattr(session, field, True)
            with self.assertRaises(ValueError):
                open_blueprint(session, 'test.layers.water')
            self.assertIs(original, session.editor)
            setattr(session, field, previous)
        with self.assertRaises(ValueError):
            open_blueprint(session, 'test.missing')
        self.assertIs(original, session.editor)

    def test_top_navigation_exposes_independent_public_test_page(self):
        source = (ROOT / 'behavior_pack/modern_projection/projection/ui.py').read_text(encoding='utf8')
        self.assertIn("('testing', '测试蓝图')", source)
        self.assertIn("RetainedPane(key='testing'", source)
        self.assertIn('children=TestBlueprints(', source)


if __name__ == '__main__':
    unittest.main()
