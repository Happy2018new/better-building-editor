"""Catch missing registrations, localization and uncraftable tool recipes."""
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ('survey_wand', 'terminal')


class ToolAssetTests(unittest.TestCase):
    def test_native_tool_buttons_leave_room_for_two_line_actionbar(self):
        ui=json.loads((ROOT/'resource_pack/ui/ModernProjectionTools.json').read_text(encoding='utf8'))
        controls={name:body for entry in ui['hudContent']['controls'] for name,body in entry.items()}
        tip=controls['tip_panel']
        for name in ('open_button@common.button','clear_button@common.button'):
            button=controls[name]
            self.assertEqual([50,20],button['size'])
            # Bottom-anchored tip grows upward; leave a gap above the button.
            self.assertLessEqual(tip['offset'][1]+6,button['offset'][1]-button['size'][1])
            children={name:body for child in button['controls'] for name,body in child.items()}
            self.assertEqual('center',children['caption']['text_alignment'])
            self.assertEqual([48,10],children['caption']['size'])
            for state in ('default','hover','pressed'):
                self.assertEqual('textures/gui/gui',children[state]['texture'])
                self.assertEqual([0,164],children[state]['uv'])
                self.assertEqual([118,20],children[state]['uv_size'])

    def test_items_recipes_and_textures_are_connected(self):
        atlas = json.loads((ROOT / 'resource_pack/textures/item_texture.json').read_text(encoding='utf8'))
        lang = (ROOT / 'resource_pack/texts/zh_CN.lang').read_text(encoding='utf8')
        for name in ITEMS:
            identity = 'modern_projection:' + name
            behavior = json.loads((ROOT / ('behavior_pack/netease_items_beh/' + name + '.json')).read_text(encoding='utf8'))
            resource = json.loads((ROOT / ('resource_pack/netease_items_res/' + name + '.json')).read_text(encoding='utf8'))
            recipe = json.loads((ROOT / ('behavior_pack/netease_recipes/' + name + '.json')).read_text(encoding='utf8'))['minecraft:recipe_shaped']
            self.assertEqual(identity, behavior['minecraft:item']['description']['identifier'])
            self.assertEqual(identity, resource['minecraft:item']['description']['identifier'])
            self.assertEqual(identity, recipe['result']['item'])
            self.assertIn('crafting_table', recipe['tags'])
            self.assertIn('item.' + identity + '.name=', lang)
            icon = resource['minecraft:item']['components']['minecraft:icon']
            path = ROOT / 'resource_pack' / (atlas['texture_data'][icon]['textures'] + '.png')
            with Image.open(path) as image:
                self.assertEqual((32, 32), image.size)
                self.assertGreater(image.getbbox()[2], 16)


if __name__ == '__main__':
    unittest.main()
