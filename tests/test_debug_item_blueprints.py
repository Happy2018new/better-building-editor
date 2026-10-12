"""Enchantment fixtures preserve opaque item NBT across real document flows."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, actor_data, foreground
from projection.debug_appearance_blueprints import observations
from projection.debug_blueprints import build, entries
from projection.debug_item_blueprints import IDENTITY, PAIRS, VISUAL_CASE
from projection.entity_overlays import frame_item
from projection.model import Document, Editor
from projection.nbt_spatial import root_payload, scalar
from projection.sharing_codec import decode_steps, encode_steps
from projection.static_frame_item import frame_item_proxy
from projection.visible_actor import entity_nbt


class ItemBlueprintTests(unittest.TestCase):
    def item(self, document, position):
        cell = document.get(position)
        return frame_item(foreground(cell), actor_data(cell))

    def test_public_blueprint_has_plain_enchanted_and_empty_controls_without_source_mutation(self):
        before = copy.deepcopy(observations())
        document = build(IDENTITY)
        self.assertIn(IDENTITY, [row[0] for row in entries('entities')])
        for pair in PAIRS:
            plain, enchanted = (self.item(document, pair[mode]) for mode in ('plain', 'enchanted'))
            self.assertFalse(plain['isEnchanted'])
            self.assertTrue(enchanted['isEnchanted'])
            self.assertEqual(plain['newItemName'], enchanted['newItemName'])
            self.assertEqual(plain['newAuxValue'], enchanted['newAuxValue'])
            ench = enchanted['userData']['ench']
            self.assertEqual(9, ench['__type__'])
            self.assertEqual(9, scalar(ench['__value__'][0], 'id'))
            self.assertEqual(3, scalar(ench['__value__'][0], 'lvl'))
            self.assertIsNone(self.item(document, pair['empty']))
        self.assertEqual(before, observations())
        self.assertEqual(document.blocks, build(IDENTITY).blocks)

    def test_config_and_compressed_share_keep_complete_enchantment_tags(self):
        document = build(IDENTITY)
        config = Document.from_data(json.loads(json.dumps(document.to_data())))
        shared = list(decode_steps(list(encode_steps(document))[-1]['text']))[-1]['document']
        for restored in (config, shared):
            self.assertEqual(document.blocks, restored.blocks)
            for pair in PAIRS:
                self.assertEqual(self.item(document, pair['enchanted']),
                                 self.item(restored, pair['enchanted']))

    def test_copy_cut_paste_and_undo_keep_enchantment_tags_without_nested_position_rewrites(self):
        document = build(IDENTITY)
        target = (21, 5, 15)
        for pair in PAIRS:
            source = pair['enchanted']
            original = document.get(source)
            for tool in ('copy', 'cut'):
                with self.subTest(frame=pair['id'], tool=tool):
                    editor = Editor(Document(document.size, {source: original}))
                    editor.select_box(source, source)
                    editor.run(tool)
                    editor.start = target
                    editor.run('paste')
                    self.assertEqual(self.item(document, source), self.item(editor.document, target))
                    root = root_payload(entity_nbt(actor_data(editor.document.get(target))))
                    self.assertEqual(target, tuple(scalar(root, axis) for axis in ('x', 'y', 'z')))
                    self.assertTrue(editor.undo())
                    self.assertEqual(AIR, editor.document.get(target))
                    self.assertTrue(editor.redo())
                    self.assertEqual(self.item(document, source), self.item(editor.document, target))

    def test_static_ordinary_item_channel_does_not_flatten_enchanted_content(self):
        document = build(IDENTITY)
        for pair in PAIRS:
            cell = document.get(pair['enchanted'])
            before = actor_data(cell)
            self.assertIsNone(frame_item_proxy(foreground(cell), before))
            self.assertTrue(frame_item(foreground(cell), before)['isEnchanted'])
            self.assertEqual(before, actor_data(cell))

    def test_fixture_data_does_not_claim_native_glint_or_shelf_slot_acceptance(self):
        self.assertEqual(('editor', 'full', 'missing'), VISUAL_CASE['modes'])
        self.assertGreaterEqual(VISUAL_CASE['minimum_temporal_frames'], 3)
        for field in ('native_enchanted_payload_verified', 'item_content_accepted',
                      'enchantment_glint_accepted'):
            self.assertFalse(VISUAL_CASE[field])
        self.assertIn('shelf_item_slots', VISUAL_CASE['unverified_families'])


if __name__ == '__main__':
    unittest.main()
