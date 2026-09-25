"""Reproducible native staff models, floating crystals and inventory artwork."""
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / 'resource_pack'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    compact = path.name.endswith('.geo.json')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=None if compact else 2,
                               separators=(',', ':') if compact else None) + '\n', encoding='utf8')


def cube(origin, size, color=0, rotation=None):
    value = {'origin': origin, 'size': size,
             'uv': {face: {'uv': [color * 8, 0], 'uv_size': [8, 8]}
                    for face in ('north', 'south', 'east', 'west', 'up', 'down')}}
    if rotation:
        value.update(pivot=[origin[i] + size[i] / 2 for i in range(3)], rotation=rotation)
    return value


def staff(kind):
    terminal = kind == 'terminal'
    name = 'modern_projection_' + kind
    body = [cube([-.65, -15, -.65], [1.3, 27, 1.3], 0),
            cube([-.30, -13, -.72], [.60, 23, .16], 2),
            cube([-.82, -16, -.82], [1.64, 2, 1.64], 1),
            cube([-.92, -3.6, -.92], [1.84, .7, 1.84], 1),
            cube([-.92, 3, -.92], [1.84, .7, 1.84], 1),
            cube([-1.1, 10, -1.1], [2.2, 2, 2.2], 1)]
    for y in range(-3, 3):
        body.append(cube([-.72, y, -.72], [1.44, .35, 1.44], 3))
    # Open crescent / astrolabe cradles, with negative space around the core.
    for side in (-1, 1):
        for i in range(6):
            angle = (-65 + i * 24) * math.pi / 180
            x = side * (2.2 + math.cos(angle) * 2.6)
            y = 15 + math.sin(angle) * 4.2
            body.append(cube([x-.38, y-.8, -.38], [.76, 1.8, .76], 1,
                             [0, 0, side * (65-i*24)]))
    if terminal:
        for i in range(8):
            a = i * math.pi / 4
            body.append(cube([math.cos(a)*3.8-.28, 16+math.sin(a)*3.8-.65, -.3],
                             [.56, 1.3, .6], 2, [0, 0, 90-i*45]))
    bones = [{'name': 'staff', 'binding': "q.item_slot_to_bone_name('main_hand')",
              'pivot': [0, 0, 0], 'cubes': body}]
    animate = {'staff': {'position': ['c.is_first_person ? 0.0 : 0.0',
                                     'c.is_first_person ? 18.0 : 22.0',
                                     'c.is_first_person ? 2.4 : 0.0'],
                          'rotation': ['c.is_first_person ? 27.0 : -8.0',
                                       'c.is_first_person ? -39.0 : 0.0',
                                       'c.is_first_person ? -159.0 : 0.0'],
                          'scale': 'c.is_first_person ? 0.62 : 0.85'}}
    for i in range(7):
        bone = 'gem%d' % i
        # Two half prisms taper into a faceted bipyramid in the gem shader.
        bones.append({'name': bone, 'parent': 'staff', 'pivot': [0, 0, 0],
                      'cubes': [cube([-1, -2, -1], [2, 2, 2], 2),
                                cube([-1, 0, -1], [2, 2, 2], 2)]})
        if i == 0:
            animation = {'position': [0, '16.0 + math.sin(q.life_time * 48.0) * 0.24', 0],
                         'rotation': [0, 'q.life_time * 15.0', 0],
                         'scale': [1.6, 1.8, 1.6]}
        elif i == 6:
            animation = {'position': [0, -17, 0], 'rotation': [0, 'q.life_time * -12.0', 0],
                         'scale': [.7, .7, .7]}
        else:
            angle = 'q.life_time * %s + %s' % (22 if terminal else -18, i*72)
            animation = {'position': ['math.cos(%s) * 4.7' % angle,
                                     '17.0 + math.sin(q.life_time * 34.0 + %d.0) * 1.0' % (i*72),
                                     'math.sin(%s) * 3.2' % angle],
                         'rotation': [12, angle, -12 if i % 2 else 12],
                         'scale': [.48, .66, .48]}
        animate[bone] = animation
    write(RP / ('models/entity/' + name + '.geo.json'), {
        'format_version': '1.16.0', 'minecraft:geometry': [{
            'description': {'identifier': 'geometry.' + name, 'texture_width': 32,
                            'texture_height': 8, 'visible_bounds_width': 5,
                            'visible_bounds_height': 5, 'visible_bounds_offset': [0, 1, 0]},
            'bones': bones}]})
    write(RP / ('animations/' + name + '.animation.json'), {
        'format_version': '1.10.0', 'animations': {
            'animation.' + name + '.holding': {'loop': True, 'bones': animate}}})
    write(RP / ('attachables/' + name + '.json'), {
        'format_version': '1.10.0', 'minecraft:attachable': {'description': {
            'identifier': 'modern_projection:' + kind,
            'materials': {'default': 'entity_alphatest',
                          'gem': 'modern_projection_staff_gem' + ('_violet' if terminal else '')},
            'textures': {'default': 'textures/items/modern_projection_staff_palette'},
            'geometry': {'default': 'geometry.' + name},
            'animations': {'holding': 'animation.' + name + '.holding'},
            'scripts': {'animate': ['holding']},
            'render_controllers': ['controller.render.modern_projection.staff']}}})


def icons():
    palette = Image.new('RGBA', (32, 8))
    d = ImageDraw.Draw(palette)
    for i, color in enumerate(('#16263D', '#D4AC67', '#9EDAF4', '#44445F')):
        d.rectangle((i*8, 0, i*8+7, 7), fill=color)
        d.line((i*8, 0, i*8+7, 0), fill='#E9E5D5')
    palette.save(RP / 'textures/items/modern_projection_staff_palette.png')
    for kind in ('terminal', 'survey_wand'):
        im = Image.new('RGBA', (128, 128))
        d = ImageDraw.Draw(im)
        gold, rim = '#C89F5F', '#F6E7BF'
        d.line((19, 115, 83, 41), fill='#111C32', width=12)
        d.line((20, 114, 83, 42), fill=gold, width=7)
        d.line((20, 113, 81, 43), fill='#394262', width=4)
        d.line((24, 112, 86, 43), fill='#86B9D0', width=1)
        for k in range(4):
            x, y = 38+k*4, 92-k*5
            d.line((x-3, y-3, x+4, y+3), fill=gold, width=3)
        d.arc((60, 4, 118, 64), 5, 284, fill=gold, width=5)
        d.arc((65, 9, 113, 59), 2, 280, fill=rim, width=1)
        gems = [(87, 31, 14), (63, 27, 5), (112, 22, 5), (97, 66, 5), (106, 48, 4)]
        rng = random.Random(772)
        for x, y, size in gems:
            diamond = [(x, y-size*1.4), (x+size*.66, y), (x, y+size*1.4), (x-size*.66, y)]
            d.polygon(diamond, fill='#11213A', outline='#9DE9F8')
            d.polygon([(x,y-size*1.4), (x+size*.66,y), (x,y+size*1.4), (x+size*.1,y)],
                      fill='#51498B' if kind == 'terminal' else '#276C8E')
            for unused in range(int(size*1.6)):
                px, py = rng.uniform(-.45,.45)*size, rng.uniform(-.9,.9)*size
                if abs(px)/(size*.66)+abs(py)/(size*1.4)<.85:
                    d.ellipse((x+px,y+py,x+px+1.5,y+py+1.5),fill='#E3FBFF')
            d.line((x,y-size*1.4,x-size*.66,y),fill='#EDF9FF',width=1)
        for x, y in [(51,15),(120,65),(76,69)]:
            d.line((x-3,y,x+3,y),fill='#A5E6FF',width=1)
            d.line((x,y-3,x,y+3),fill='#D3F7FF',width=1)
        im.resize((32,32), Image.Resampling.LANCZOS).save(
            RP / ('textures/items/modern_projection_' + kind + '.png'))


def aura():
    # 16 real faceted ice shards, 288 ribbon sections, 48 runes, 64 stars,
    # 96 rising motes, 24 orbiting petals. Two materials; one bounded actor.
    ranges = [('crystals',0,128), ('glow',128,648)]
    bones = [{'name':'root','pivot':[0,0,0]}]
    for name, lo, hi in ranges:
        bones.append({'name':name,'parent':'root','pivot':[0,0,0], 'cubes':[
            {'origin':[(i%64)*4-.5,(i//64)*4-.5,0],'size':[1,1,0],
             'uv':{'north':{'uv':[0,0],'uv_size':[2,2]}}} for i in range(lo,hi)]})
    write(RP / 'models/entity/modern_projection_staff_aura.geo.json', {
        'format_version':'1.12.0', 'minecraft:geometry':[{'description':{
            'identifier':'geometry.modern_projection.staff_aura','texture_width':2,'texture_height':2,
            'visible_bounds_width':8,'visible_bounds_height':7,'visible_bounds_offset':[0,1,0]},'bones':bones}]})
    write(RP / 'entity/modern_projection_staff_aura.entity.json', {
        'format_version':'1.10.0','minecraft:client_entity':{'description':{
            'identifier':'modern_projection:staff_aura',
            'materials':{'default':'modern_projection_staff_aura','glow':'modern_projection_staff_aura_glow'},
            'textures':{'default':'textures/modern_projection/transparent'},
            'geometry':{'default':'geometry.modern_projection.staff_aura'},
            'render_controllers':['controller.render.modern_projection.survey_particles']}}})
    behavior=json.loads((ROOT/'behavior_pack/entities/modern_projection_outline.json').read_text())
    behavior['minecraft:entity']['description']['identifier']='modern_projection:staff_aura'
    write(ROOT/'behavior_pack/entities/modern_projection_staff_aura.json',behavior)


def generate():
    for kind in ('terminal','survey_wand'):
        staff(kind)
    icons()
    aura()
    write(RP / 'render_controllers/modern_projection_staff.json', {
        'format_version':'1.8.0','render_controllers':{
            'controller.render.modern_projection.staff':{
                'geometry':'Geometry.default',
                'materials':[{'*':'Material.default'}] +
                            [{'gem%d' % i:'Material.gem'} for i in range(7)],
                'textures':['Texture.default']}}})


if __name__ == '__main__':
    generate()
