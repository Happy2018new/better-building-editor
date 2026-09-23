"""Deterministic 32px pixel art for the two craftable world tools."""
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw
import math
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'resource_pack/textures/items'


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    dark, blue, cyan, light = '#25394F', '#397DED', '#57D9E2', '#EFFAFF'
    wand = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(wand)
    d.line((7, 26, 20, 13), fill=dark, width=7)
    d.line((7, 25, 20, 12), fill=blue, width=4)
    d.line((8, 24, 19, 13), fill=light, width=1)
    d.polygon([(14, 5), (23, 1), (30, 7), (29, 16), (20, 21), (13, 14)], fill=dark)
    d.polygon([(15, 6), (23, 3), (28, 8), (20, 11)], fill=light)
    d.polygon([(15, 8), (19, 13), (19, 18), (15, 13)], fill=blue)
    d.polygon([(21, 13), (28, 10), (27, 15), (21, 18)], fill=cyan)
    d.rectangle((13, 5, 16, 8), fill=cyan)
    d.rectangle((26, 14, 29, 17), fill=light)
    d.rectangle((4, 26, 8, 29), fill=dark)
    wand.save(OUT / 'modern_projection_survey_wand.png')

    terminal = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(terminal)
    d.polygon([(4, 18), (24, 15), (30, 20), (28, 29), (7, 31), (2, 26)], fill=dark)
    d.polygon([(5, 19), (23, 17), (27, 20), (24, 26), (6, 28), (4, 25)], fill=light)
    d.polygon([(8, 21), (23, 19), (24, 21), (22, 24), (8, 26)], fill=blue)
    d.line((7, 29, 26, 27), fill=blue, width=1)
    d.rectangle((24, 26, 26, 27), fill=cyan)
    d.polygon([(10, 6), (18, 2), (25, 7), (25, 15), (17, 19), (10, 14)], fill=dark)
    d.polygon([(12, 7), (18, 4), (23, 7), (17, 10)], fill=light)
    d.polygon([(12, 9), (16, 12), (16, 16), (12, 13)], fill=blue)
    d.polygon([(18, 12), (23, 9), (23, 14), (18, 17)], fill=cyan)
    d.point((6, 12), fill=cyan)
    d.line((27, 3, 27, 5), fill=cyan)
    d.line((26, 4, 28, 4), fill=cyan)
    terminal.save(OUT / 'modern_projection_terminal.png')

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
