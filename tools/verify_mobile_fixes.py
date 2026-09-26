"""Visual safe-area and biome fixture in an isolated MCDK world."""
import time

from PIL import Image, ImageChops, ImageStat

import verify_ui as ui
from verify_world_tools import game, snapshot


def frame(name):
    time.sleep(.5)
    path = snapshot(name)
    return Image.open(path).convert('RGB'), path


def wait_preview():
    deadline = time.time() + 45
    while time.time() < deadline:
        status = game('_result=(s.preview_pending, s.preview_error, s.tiles.mounting)')
        assert not status[1], status
        if not status[0] and not status[2]:
            time.sleep(.4)
            return
        time.sleep(.2)
    raise AssertionError('Preview did not settle')


def main():
    game('''from modern_projection.pyreact import host
api._mobile_fix_saved=(s.editor,s.page,s.inspector,s.material_browser,
    s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan)
api._mobile_safe_saved=(host.get_safe_area_size(),host.get_safe_area_insets())
probe=host._SAFE_AREA_PROBE[0]
probe._next_measure=host.time.time()+45.
host._publish_safe_area((1.,1.),host.SafeAreaInsets(13.,24.,27.,48.))
owner.open_workspace()
_result=True''')
    try:
        before, _ = frame('mobile_fix_safe_before')
        game('s.set("material_browser","material")\n_result=True')
        after, path = frame('mobile_fix_safe_modal')
        border = ImageChops.difference(before, after).crop((0, 0, 12, before.height))
        ui.check('unsafe margin darkens with modal', max(ImageStat.Stat(border).mean) > 5)
        print('safe area: ' + path, flush=True)
        game('''from modern_projection.pyreact import host
s.set('material_browser',None)
size,insets=api._mobile_safe_saved
host._publish_safe_area(size,insets)
host._SAFE_AREA_PROBE[0]._next_measure=0.
from modern_projection.projection.model import Document
blocks=dict(((x,0,z),('minecraft:grass',0)) for x in range(8) for z in range(8))
s._loaded(Document((8,1,8),blocks,biome='plains'))
s.set('page','projection')
s.zoom=3.
s.emit('view')
_result=True''')
        wait_preview()
        labels = [node['props'] for node in ui.nodes('Label')
                  if node['props'].get('content', '').endswith('\u500d')]
        ui.check('scale unit uses retained glyphs', bool(labels) and
                 all(props.get('rasterText') for props in labels))
        grass = {}
        for biome in ('plains', 'jungle'):
            game('s.set_biome(%r)\n_result=True' % biome)
            image, path = frame('mobile_fix_grass_' + biome)
            grass[biome] = image
            print('%s: %s %s' % (biome, path, image.size), flush=True)
        top = (500, 205)
        side = (510, 345)
        dirt = (220, 323)
        plain_side = grass['plains'].getpixel(side)
        jungle_side = grass['jungle'].getpixel(side)
        ui.check('grass side follows building biome',
                 jungle_side[1] > plain_side[1] + 8 and
                 jungle_side[0] < plain_side[0] - 15)
        jungle_top = grass['jungle'].getpixel(top)
        ui.check('grass top and side use the same hue',
                 abs(float(jungle_top[1]) / jungle_top[0] -
                     float(jungle_side[1]) / jungle_side[0]) < .2)
        ui.check('grass side dirt stays unchanged',
                 grass['plains'].getpixel(dirt) == grass['jungle'].getpixel(dirt))
        game('''from modern_projection.projection.model import Document
blocks=dict(((x,0,z),('minecraft:green_wool',0)) for x in range(8) for z in range(8))
s._loaded(Document((8,1,8),blocks,biome='plains'))
s.set('page','projection')
s.zoom=3.
s.emit('view')
_result=True''')
        wait_preview()
        wool = {}
        for biome in ('plains', 'jungle'):
            game('s.set_biome(%r)\n_result=True' % biome)
            wool[biome], unused = frame('mobile_fix_wool_' + biome)
        difference = ImageChops.difference(wool['plains'], wool['jungle'])
        ui.check('green wool is not biome tinted',
                 max(ImageStat.Stat(difference.crop((280, 200, 500, 300))).mean) < 2)
    finally:
        game('''from modern_projection.pyreact import host,navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
size,insets=api._mobile_safe_saved
host._publish_safe_area(size,insets)
host._SAFE_AREA_PROBE[0]._next_measure=0.
s.editor,s.page,s.inspector,s.material_browser,s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan=api._mobile_fix_saved
s.refresh_preview()
s.emit()
_result=True''')


if __name__ == '__main__':
    main()
