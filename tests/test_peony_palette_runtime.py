"""Runtime regressions for independent peony halves; Python 2.7/3 compatible."""
from __future__ import unicode_literals
from copy import deepcopy
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not isinstance(ROOT, type('')):
    ROOT = ROOT.decode(sys.getfilesystemencoding() or 'mbcs')
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection import block_registry as registry, geometry_palette as geometry
from projection.cell import AIR, actor_data, make_cell
from projection.model import Document
from projection.visible_actor import compose_actor

BOTTOM, TOP = (2, 1, 2), (2, 2, 2)
PROXIES = {('minecraft:peony', 0): 'modern_projection:ordinary_peony_bottom',
           ('minecraft:peony', 1): 'modern_projection:ordinary_peony_top'}


def without_peony(data):
    result = deepcopy(data)
    for key in ('common', 'extra', 'states', 'extraStates'):
        result[key] = dict((value, positions) for value, positions in result[key].items()
                           if value[0] != 'minecraft:peony' and value[0] not in PROXIES.values())
    return result


class PeonyPaletteRuntimeTests(unittest.TestCase):
    def document(self):
        nbt = {'Items': {'__type__': 9, '__value__': [
            {'Name': {'__type__': 8, '__value__': 'minecraft:diamond'}}]}}
        actor = compose_actor({'facingDirection': 2}, nbt)
        return Document((5, 4, 5), {
            (2, 0, 2): ('minecraft:dirt', 0),
            BOTTOM: registry.from_states('minecraft:peony', {'upper_block_bit': False}),
            TOP: registry.from_states('minecraft:peony', {'upper_block_bit': True}),
            (0, 1, 0): make_cell(('minecraft:barrel', 2), AIR, actor),
            (4, 1, 4): ('minecraft:stone', 0)}, name='Peony half boundaries', biome='pale_garden')

    def test_only_two_typed_native_states_select_distinct_hidden_models(self):
        self.assertEqual((0, 1), registry.aux_values('minecraft:peony'))
        for aux, upper in ((0, False), (1, True)):
            self.assertEqual(('minecraft:peony', aux),
                             registry.from_states('minecraft:peony', {'upper_block_bit': upper}))
            self.assertEqual({'upper_block_bit': upper}, registry.states(('minecraft:peony', aux)))
            self.assertEqual(PROXIES[('minecraft:peony', aux)],
                             geometry.PLANT_PROXIES[('minecraft:peony', aux)])
            self.assertIn(PROXIES[('minecraft:peony', aux)], geometry.INTERNAL_RENDER_BLOCKS)
        for integer_bit in (0, 1):
            self.assertIsNone(registry.from_states('minecraft:peony', {'upper_block_bit': integer_bit}))

    def test_both_and_clipped_half_palettes_preserve_native_document_nbt_and_unrelated_output(self):
        document = self.document()
        original = deepcopy(document.to_data())
        actor = deepcopy(actor_data(document.get((0, 1, 0))))
        for selected in (None, BOTTOM, TOP):
            source = document.palette_data(None if selected is None else lambda pos: pos == selected)
            saved = deepcopy(source)
            previous = dict(geometry.PLANT_PROXIES)
            try:
                for material in PROXIES:
                    geometry.PLANT_PROXIES.pop(material)
                baseline = geometry.prepare_palette(source)
            finally:
                geometry.PLANT_PROXIES.clear()
                geometry.PLANT_PROXIES.update(previous)
            result = geometry.prepare_palette(source)
            self.assertEqual(without_peony(baseline), without_peony(result))
            self.assertEqual(saved, source)
            self.assertEqual(original, document.to_data())
            # The reader contract is JSON-decoded wire data, including Py2
            # numeric NBT payload strings becoming Unicode on JSON decode.
            wire = json.loads(json.dumps(document.to_data()))
            self.assertEqual(original, Document.from_data(wire).to_data())
            self.assertEqual(actor, actor_data(document.get((0, 1, 0))))
            for position, aux in ((BOTTOM, 0), (TOP, 1)):
                expected = [position[1] * 25 + position[0] * 5 + position[2]]
                proxy = (PROXIES[('minecraft:peony', aux)], 0)
                if selected is None or selected == position:
                    self.assertEqual(expected, result['common'][proxy])
                else:
                    self.assertNotIn(proxy, result['common'])
            self.assertNotIn(('minecraft:peony', 0), result['common'])
            self.assertNotIn(('minecraft:peony', 1), result['common'])

    def test_isolated_half_does_not_create_the_other_half_or_change_controls(self):
        for position, aux in ((BOTTOM, 0), (TOP, 1)):
            document = Document((5, 4, 5), {position: ('minecraft:peony', aux)})
            saved = deepcopy(document.to_data())
            result = geometry.prepare_palette(document.palette_data())
            self.assertEqual({(PROXIES[('minecraft:peony', aux)], 0):
                              [position[1] * 25 + position[0] * 5 + position[2]]}, result['common'])
            self.assertEqual(saved, document.to_data())
        for control in (AIR, ('minecraft:stone', 0)):
            document = Document((1, 1, 1), {(0, 0, 0): control})
            source = document.palette_data()
            result = geometry.prepare_palette(source)
            self.assertEqual(source['common'], result['common'])
            self.assertEqual(source['extra'], result['extra'])


if __name__ == '__main__':
    unittest.main()
