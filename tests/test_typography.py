import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/HelloScript'))
from projection.typography import GLYPHS, glyph, supported, layout, characters


class TypographyTests(unittest.TestCase):
    def test_dynamic_names_and_future_ui_use_complete_existing_font(self):
        for text in ('annnn币','分享当前草稿','导入分享码','缺少第 1–3、8 段','视线已深入 40 格','龘㐀繁體建築'):
            self.assertTrue(supported(text),text)
            self.assertTrue(all(glyph(char) for char in text))
        self.assertGreater(len(GLYPHS),30000)
        self.assertEqual(20976,sum(chr(i) in GLYPHS for i in range(0x4e00,0xa000)))

    def test_atlas_cells_have_padding_and_files(self):
        pages=set()
        for page,x,y,width,advance in GLYPHS.values():
            self.assertGreaterEqual(x,2);self.assertGreaterEqual(y,2)
            self.assertLessEqual(x+width+2,2048);self.assertLessEqual(y+88+2,2048)
            self.assertGreaterEqual(width,advance)
            pages.add(page)
        directory=Path(__file__).resolve().parents[1]/'resource_pack/textures/modern_projection/type'
        self.assertTrue(all((directory/('atlas_%03d.png'%page)).is_file() for page in pages))

    def test_narrow_python_unicode_pairs_keep_supplementary_glyphs(self):
        char=next(c for c in GLYPHS if ord(c)>0xffff)
        code=ord(char)-0x10000
        pair=chr(0xd800+(code>>10))+chr(0xdc00+(code&1023))
        self.assertEqual([char],list(characters(pair)))
        self.assertTrue(supported(pair))
        pieces,widths=layout(pair,12.)
        self.assertEqual(1,len(pieces))
        self.assertEqual(glyph(char),pieces[0][0])

    def test_phrase_sprites_explicitly_reset_previous_atlas_crop(self):
        from projection.typography import ASSETS
        from PIL import Image
        directory=Path(__file__).resolve().parents[1]/'resource_pack/textures/modern_projection/type'
        for phrase in ('未命名建筑','现代化投影'):
            data=glyph(phrase)
            with Image.open(directory/(data[0]+'.png')) as image:
                self.assertEqual(image.size,data[5])
            self.assertEqual((0,0),data[4])

    def test_wrapping_keeps_closing_punctuation_with_preceding_character(self):
        value='请先保存需要保留的作品。'
        font=13.;width=sum(glyph(c)[3] for c in value[:-1])*font+.01
        pieces,widths=layout(value,font,width)
        self.assertEqual(2,len(widths))
        self.assertEqual(2,sum(row==1 for unused,row,x in pieces))
        self.assertTrue(all(w<=width for w in widths))
        lines,widths=layout('新建 64 × 128 × 64 区域将替换当前草稿。\n请先保存需要保留的作品。',font,372)
        self.assertGreaterEqual(len(widths),2)
        self.assertLessEqual(max(widths),372)


if __name__=='__main__':unittest.main()
