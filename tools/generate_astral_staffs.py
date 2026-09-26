"""Reproducible native staff models, floating crystals and inventory artwork."""
import json
import math
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
    body = [cube([-.65, -9, -.65], [1.3, 24, 1.3], 0),
            cube([-.30, -8, -.72], [.60, 23, .16], 2),
            cube([-.82, -10, -.82], [1.64, 2, 1.64], 1),
            cube([-.92, -6.7, -.92], [1.84, .7, 1.84], 1),
            cube([-.92, 4, -.92], [1.84, .7, 1.84], 1),
            cube([-1.1, 13, -1.1], [2.2, 2, 2.2], 1)]
    grip = [cube([-.73, y, -.73], [1.46, 1.9, 1.46], 4)
            for y in range(-6, 6, 2)]
    for y in (-6, -2, 2, 4):
        body.append(cube([-.82, y, -.82], [1.64, .35, 1.64], 5))
    # Open crescent / astrolabe cradles, with negative space around the core.
    for side in (-1, 1):
        for i in range(6):
            angle = (-65 + i * 24) * math.pi / 180
            x = side * (2.2 + math.cos(angle) * 2.6)
            y = 18 + math.sin(angle) * 4.2
            body.append(cube([x-.38, y-.8, -.38], [.76, 1.8, .76], 1,
                             [0, 0, side * (65-i*24)]))
    motes = []
    for strand in range(2):
        for i in range(24):
            progress = (i + strand * .5) / 24.
            angle = progress * math.pi * 4.5 + strand * math.pi
            radius = 1.65 + .12 * math.sin(i * 2.7)
            size = .26 if i % 4 else .42
            motes.append(cube([math.cos(angle) * radius-size/2,
                               -8 + progress * 24-size/2,
                               math.sin(angle) * radius-size/2], [size, size, size], 5))
    bones = [{'name': 'staff', 'binding': "q.item_slot_to_bone_name('main_hand')",
              'pivot': [0, 0, 0], 'cubes': body},
             {'name': 'grip', 'parent': 'staff', 'pivot': [0, 0, 0], 'cubes': grip},
             {'name': 'motes', 'parent': 'staff', 'pivot': [0, 0, 0], 'cubes': motes}]
    # The native item binding uses Y=24 as its hand origin. The authored
    # grip/rotation pivot is Y=0, so move that pivot to the hand after rotating
    # and scaling. A lower offset makes the player hold the staff by its head.
    animate = {'staff': {'position': [0,
                                     'c.is_first_person ? 18.0 : 24.0',
                                     'c.is_first_person ? 2.4 : 0.0'],
                          'rotation': ['c.is_first_person ? 27.0 : 75.0',
                                       'c.is_first_person ? -39.0 : 0.0',
                                       'c.is_first_person ? -159.0 : 0.0'],
                          'scale': 'c.is_first_person ? 0.62 : 0.85'},
               'motes': {'rotation': [0, 'q.life_time * 18.0', 0]}}
    for i in range(7):
        bone = 'gem%d' % i
        # Two half prisms taper into a faceted bipyramid in the gem shader.
        bones.append({'name': bone, 'parent': 'staff', 'pivot': [0, 0, 0],
                      'cubes': [cube([-1, -2, -1], [2, 2, 2], 2),
                                cube([-1, 0, -1], [2, 2, 2], 2)]})
        if i == 0:
            animation = {'position': [0, '19.0 + math.sin(q.life_time * 48.0) * 0.24', 0],
                         'rotation': [0, 'q.life_time * 15.0', 0],
                         'scale': [1.6, 1.8, 1.6]}
        elif i == 6:
            animation = {'position': [0, -10, 0], 'rotation': [0, 'q.life_time * -12.0', 0],
                         'scale': [.7, .7, .7]}
        else:
            angle = 'q.life_time * %s + %s' % (22 if terminal else -18, i*72)
            animation = {'position': ['math.cos(%s) * 4.7' % angle,
                                     '20.0 + math.sin(q.life_time * 34.0 + %d.0) * 1.0' % (i*72),
                                     'math.sin(%s) * 3.2' % angle],
                         'rotation': [12, angle, -12 if i % 2 else 12],
                         'scale': [.48, .66, .48]}
        animate[bone] = animation
    write(RP / ('models/entity/' + name + '.geo.json'), {
        'format_version': '1.16.0', 'minecraft:geometry': [{
            'description': {'identifier': 'geometry.' + name, 'texture_width': 48,
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
                          'gem': 'modern_projection_staff_gem' + ('_violet' if terminal else ''),
                          'grip': 'modern_projection_staff_grip' + ('_violet' if terminal else ''),
                          'motes': 'modern_projection_staff_motes'},
            'textures': {'default': 'textures/items/modern_projection_staff_palette'},
            'geometry': {'default': 'geometry.' + name},
            'animations': {'holding': 'animation.' + name + '.holding'},
            'scripts': {'animate': ['holding']},
            'render_controllers': ['controller.render.modern_projection.staff']}}})


def icons():
    palette = Image.new('RGBA', (48, 8))
    d = ImageDraw.Draw(palette)
    for i, color in enumerate(('#16263D', '#D4AC67', '#9EDAF4', '#44445F',
                               '#10203A', '#EBC871')):
        d.rectangle((i*8, 0, i*8+7, 7), fill=color)
        d.line((i*8, 0, i*8+7, 0), fill='#E9E5D5')
    for x, y in ((33, 2), (36, 5), (39, 3), (34, 7)):
        d.point((x, y), fill='#B7DDF3')
    d.line((41, 4, 47, 4), fill='#3B4F6D')
    palette.save(RP / 'textures/items/modern_projection_staff_palette.png')
    for kind in ('terminal', 'survey_wand'):
        im = Image.new('RGBA', (128, 128))
        d = ImageDraw.Draw(im)
        gold, rim = '#C89F5F', '#F6E7BF'
        d.line((20, 114, 82, 43), fill=gold, width=11)
        d.line((20, 114, 82, 43), fill='#142740', width=7)
        d.line((25, 110, 84, 44), fill='#78B7CC', width=2)
        for x, y in ((37, 96), (51, 80), (65, 64)):
            d.line((x-4, y-3, x+5, y+4), fill=gold, width=3)
        d.arc((60, 3, 118, 63), 15, 270, fill=gold, width=6)
        d.arc((64, 7, 114, 59), 15, 270, fill=rim, width=2)
        x, y, size = 87, 31, 17
        diamond = [(x, y-size*1.4), (x+size*.66, y), (x, y+size*1.4), (x-size*.66, y)]
        d.polygon(diamond, fill='#11213A', outline='#9DE9F8')
        d.polygon([(x, y-size*1.4), (x+size*.66, y), (x, y+size*1.4), (x+size*.1, y)],
                  fill='#51498B' if kind == 'terminal' else '#276C8E')
        d.line((x, y-size*1.4, x-size*.66, y), fill='#EDF9FF', width=2)
        for px, py in ((-2, -5), (3, 3), (0, 11)):
            d.ellipse((x+px, y+py, x+px+2, y+py+2), fill='#E3FBFF')
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


def staff_assets():
    for kind in ('terminal','survey_wand'):
        staff(kind)
    icons()
    write(RP / 'render_controllers/modern_projection_staff.json', {
        'format_version':'1.8.0','render_controllers':{
            'controller.render.modern_projection.staff':{
                'geometry':'Geometry.default',
                'materials':[{'*':'Material.default'}, {'grip':'Material.grip'},
                             {'motes':'Material.motes'}] +
                            [{'gem%d' % i:'Material.gem'} for i in range(7)],
                'textures':['Texture.default']}}})


def generate():
    staff_assets()
    aura()


if __name__ == '__main__':
    generate()
