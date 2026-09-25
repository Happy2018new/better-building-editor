"""Regenerate staff models/icons and legacy HUD button atlases."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import math
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'resource_pack/textures/items'


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    from generate_astral_staffs import generate as generate_staffs
    generate_staffs()

    ui = ROOT / 'resource_pack/textures/modern_projection'
    ui.mkdir(parents=True, exist_ok=True)
    width, height, frames = 160, 48, 24
    for state, brightness in (('normal',1.),('hover',1.28),('pressed',.82)):
        atlas = Image.new('RGBA', (width*frames, height))
        for frame in range(frames):
            button = Image.new('RGBA', (536, 144))
            d = ImageDraw.Draw(button)
            fill = '#111836F2' if state != 'pressed' else '#0A1128F7'
            d.rounded_rectangle((6,9,530,137),radius=26,fill='#070C1B66')
            d.rounded_rectangle((3,3,532,133),radius=24,fill=fill,
                                outline='#5867B8',width=3)
            # The static border keeps the native hit target readable. Light
            # tracks and stars animate inside it via JsonUI's flip_book UV.
            d.arc((7,6,532,130),195,344,fill='#8B7CDA',width=3)
            d.arc((13,15,526,117),28,146,fill='#4A8BC3',width=2)
            rng = random.Random(90210)
            for index in range(48):
                x=rng.randint(19,514)
                y=rng.randint(18,116)
                amount=(index*7+frame)%24
                if amount > 15:
                    continue
                size=2 if index%11 else 4
                alpha=int((70+amount*7)*min(1.5,brightness))
                tint=(178,190,255, min(235,alpha)) if index%3 else (130,218,255,min(235,alpha))
                d.ellipse((x-size,y-size,x+size,y+size),fill=tint)
            phase=frame/float(frames)
            for offset in (0.,.38):
                x=28+int(((phase+offset)%1.)*480)
                y=38+int(14*math.sin((phase+offset)*math.pi*2))
                for length in (72,48,25):
                    d.line((x-length,y+length*.18,x,y),fill=(111,102,217,65+length//2),width=2)
                d.line((x-16,y+3,x+8,y-2),fill=(156,204,255,145),width=3)
                d.line((x-6,y,x+6,y),fill=(233,239,255,210),width=2)
            mask = Image.new('L',button.size)
            ImageDraw.Draw(mask).rounded_rectangle((4,4,532,132),radius=23,fill=255)
            button.putalpha(ImageChops.darker(button.getchannel('A'),mask))
            atlas.paste(button.resize((width,height),Image.Resampling.LANCZOS),(frame*width,0))
        atlas.save(ui / ('tool_button_' + state + '.png'))


if __name__ == '__main__':
    generate()
