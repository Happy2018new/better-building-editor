"""Build the complete existing Noto Sans SC cmap into shared UI atlas pages."""
import argparse
import json
import math
from pathlib import Path
import runpy
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
PAGE=2048


def build(path):
    cmap=TTFont(str(path)).getBestCmap()
    font=ImageFont.truetype(str(path),64)
    font.set_variation_by_name('Medium')
    mapping=ROOT/'behavior_pack/HelloScript/projection/font_atlas.py'
    existing=runpy.run_path(str(mapping))['GLYPHS'] if mapping.exists() else {}
    chars=[chr(code) for code in cmap if code>=32 and not 0x7f<=code<0xa0]
    # Preserve page order on regeneration, independently of phrase inventory.
    chars.sort(key=lambda char:tuple(existing[char][:3][i] for i in (0,2,1)) if char in existing else (100000,0,ord(char)))
    dest=ROOT/'resource_pack/textures/modern_projection/type'
    rows={};page=0;x=y=2
    image=Image.new('RGBA',(PAGE,PAGE),(255,255,255,0))
    draw=ImageDraw.Draw(image)
    def save():
        image.save(dest/('atlas_%03d.png'%page),optimize=True)
    for char in chars:
        advance=font.getlength(char);width=max(1,math.ceil(advance)+4)
        if x+width+2>PAGE:x,y=2,y+92
        if y+88+2>PAGE:
            save();page+=1;x=y=2
            image=Image.new('RGBA',(PAGE,PAGE),(255,255,255,0));draw=ImageDraw.Draw(image)
        draw.text((x+1,y+69),char,font=font,fill='white',anchor='ls')
        rows[char]=[page,x,y,width,advance]
        x+=width+4
    save()
    output=ROOT/'behavior_pack/HelloScript/projection/font_atlas.py'
    output.write_text('# -*- coding: utf-8 -*-\n# Generated complete Noto Sans SC cmap (OFL), 64 px Medium.\nimport json\nGLYPHS = json.loads(r\'\'\''+json.dumps(rows,ensure_ascii=True,separators=(',',':'))+'\'\'\')\n',encoding='utf8')
    print('Generated %d glyphs in %d shared atlas pages'%(len(rows),page+1),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--font',required=True)
    build(Path(parser.parse_args().font))
