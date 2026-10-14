"""Regression gates for the NEMC 3.10 native frame/content boundary.

The 3.10 clean projection evidence returns empty native actor render records
for filled and enchanted frames.  That is structural evidence that the item
payload is not supplied by ``CombineBlockPaletteToGeometry``; it is not
evidence that the frame block itself should be removed.  The frame body must
stay in the native common palette while the optional item companion owns only
the displayed item.  Shelf contents are not yet observed, so their actor data
must remain opaque and must never be routed through the frame-item adapter.
"""
from __future__ import unicode_literals

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.entity_overlays import frame_item
from projection.entity_render import native_actor
from projection.geometry_palette import prepare_palette
from projection.item_sprite_profile import production_profile
from projection.model import Document
from projection.render_context import prepare_context_batches
from projection.visible_actor import compose_actor, entity_nbt, render_actor


def tag(kind, value):
    return {'__type__': kind, '__value__': value}


def frame_payload(identifier='ItemFrame', item='minecraft:diamond_sword'):
    return compose_actor({}, {
        'id': tag(8, identifier),
        'Item': tag(10, {
            'Name': tag(8, item),
            'Damage': tag(2, 0),
            'Count': tag(1, 1),
        }),
        'ItemRotation': tag(5, 45.),
    })


class NativeFrameBoundaryTests(unittest.TestCase):
    def test_native_actor_empty_render_record_does_not_drop_frame_body_or_nbt(self):
        value = material('frame', {'facing_direction': 2,
                                   'item_frame_map_bit': False,
                                   'item_frame_photo_bit': False})
        actor = frame_payload()
        source = {'volume': (1, 1, 1), 'common': {value: [0]},
                  'extra': {}, 'actor': {'minecraft:frame': {0: actor}}}
        saved = copy.deepcopy(source)

        result = prepare_palette(source)

        # 3.10 native Combine receives an empty renderer record for this
        # source, but it still receives the frame's native block identity.
        self.assertEqual([0], result['common'][value])
        self.assertEqual({}, result['actor']['minecraft:frame'][0])
        self.assertEqual({}, native_actor(value, actor))
        self.assertEqual(saved, source)
        self.assertEqual(actor, source['actor']['minecraft:frame'][0])
        self.assertEqual(actor, compose_actor(result['actor']['minecraft:frame'][0],
                                              entity_nbt(actor)))

    def test_editor_context_keeps_frame_body_and_target_actor_separate(self):
        value = material('glow_frame', {'facing_direction': 2,
                                        'item_frame_map_bit': False,
                                        'item_frame_photo_bit': False})
        actor = frame_payload('GlowItemFrame')
        document = Document((2, 1, 1), {
            (0, 0, 0): make_cell(value, nbt=actor),
            (1, 0, 0): make_cell(value, nbt=frame_payload('GlowItemFrame', 'minecraft:apple')),
        })
        saved = copy.deepcopy(document.to_data())
        targets = document.palette_data(lambda pos: pos == (0, 0, 0))

        prepared = prepare_context_batches(document, targets)

        self.assertEqual(saved, document.to_data())
        self.assertEqual(1, len(prepared['_context_batches']))
        _origin, is_context, palette = prepared['_context_batches'][0]
        # Context batches intentionally keep the target's complete neighbor
        # frame so native depth/occlusion remains correct.
        self.assertTrue(is_context)
        self.assertIn(value, palette['common'])
        body_indices = palette['common'][value]
        self.assertEqual(2, len(body_indices))
        self.assertEqual(set(body_indices), set(palette['actor']['minecraft:glow_frame']))
        self.assertTrue(all(payload == {} for payload in palette['actor']['minecraft:glow_frame'].values()))

    def test_production_item_owner_is_gated_until_pixel_acceptance(self):
        # The 3.10 native record has no displayed-item fields.  Enabling the
        # item companion before editor/world pixels pass would create an
        # unverified second owner; production must remain disabled.
        self.assertIsNone(production_profile())

    def test_shelf_actor_is_opaque_and_never_treated_as_frame_content(self):
        value = material('oak_shelf')
        payload = compose_actor({'powered_shelf_type': 2}, {
            'id': tag(8, 'Shelf'),
            'future_slot_schema': tag(10, {'slot0': tag(8, 'minecraft:diamond_sword')}),
        })
        source = {'volume': (1, 1, 1), 'common': {value: [0]},
                  'extra': {}, 'actor': {'minecraft:oak_shelf': {0: payload}}}
        saved = copy.deepcopy(source)

        result = prepare_palette(source)

        self.assertEqual([0], result['common'][value])
        self.assertEqual({'powered_shelf_type': 2},
                         result['actor']['minecraft:oak_shelf'][0])
        self.assertEqual(saved, source)
        self.assertEqual(payload, compose_actor(render_actor(payload), entity_nbt(payload)))
        self.assertIsNone(frame_item(value, payload))


if __name__ == '__main__':
    unittest.main()
