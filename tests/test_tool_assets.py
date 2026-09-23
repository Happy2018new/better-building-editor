"""Catch missing registrations, localization and uncraftable tool recipes."""
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ('survey_wand', 'terminal')


class ToolAssetTests(unittest.TestCase):
    def test_items_recipes_and_textures_are_connected(self):
        atlas = json.loads((ROOT / 'resource_pack/textures/item_texture.json').read_text(encoding='utf8'))
        lang = (ROOT / 'resource_pack/texts/zh_CN.lang').read_text(encoding='utf8')
        for name in ITEMS:
            identity = 'modern_projection:' + name
            behavior = json.loads((ROOT / ('behavior_pack/netease_items_beh/' + name + '.json')).read_text(encoding='utf8'))
            resource = json.loads((ROOT / ('resource_pack/netease_items_res/' + name + '.json')).read_text(encoding='utf8'))
            recipe = json.loads((ROOT / ('behavior_pack/recipes/' + name + '.json')).read_text(encoding='utf8'))['minecraft:recipe_shaped']
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
