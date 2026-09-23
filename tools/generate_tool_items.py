"""Deterministic 32px pixel art for the two craftable world tools."""
from pathlib import Path
from PIL import Image, ImageDraw

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
    for state, fill, edge, stripe in (
        ('normal', '#18273CEB', '#658CBACD', '#82D7F9'),
        ('hover', '#253E5FF5', '#94D2FC', '#C8F3FF'),
        ('pressed', '#102039F5', '#86B3F1', '#77C9FA'),
    ):
        button = Image.new('RGBA', (536, 144), (0, 0, 0, 0))
        d = ImageDraw.Draw(button)
        d.rounded_rectangle((5,14,530,141),radius=40,fill='#07122155')
        d.rounded_rectangle((3,3,532,130),radius=36,fill=fill,outline=edge,width=4)
        d.rounded_rectangle((25,8,510,11),radius=2,fill=stripe)
        button = button.resize((268,72),Image.Resampling.LANCZOS)
        button.save(ui / ('tool_button_' + state + '.png'))


if __name__ == '__main__':
    generate()
