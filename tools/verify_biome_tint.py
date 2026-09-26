"""Biome pixels, native catalogue contamination, and retained geometry checks.

Run in an isolated managed instance. Changes only an unsaved draft and client
ghosts, restoring the draft and camera; never writes world blocks or preferences.
"""
import json
import time
from PIL import Image, ImageChops, ImageStat
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot


def wait_preview():
    deadline = time.time()+100
    while time.time() < deadline:
        value = game('_result={"pending":s.preview_pending,"mounting":getattr(s.tiles,"mounting",False),'
                     '"edit":s.edit_job is not None,"error":s.preview_error}')
        assert not value['error'], value
        if not value['pending'] and not value['mounting'] and not value['edit']:
            time.sleep(.5)
            return
        time.sleep(.25)
    raise AssertionError(value)


def screenshot(name):
    time.sleep(.5)
    snapshot('biome65_'+name)
    return Image.open(ui.OUT/('biome65_'+name+'.jpg')).convert('RGB')


def main():
    game('''api._biome_saved=(s.editor,s.origin,s.page,s.inspector)
api._biome_native_geometry=s.bridge.geometry
api._biome_builds=0
def wrap_biome_geometry(original,target):
    def wrapped(*args,**kwargs):
        target._biome_builds+=1
        return original(*args,**kwargs)
    return wrapped
s.bridge.geometry=wrap_biome_geometry(s.bridge.geometry,api)
s.set('page','projection')
_result=True''')
    try:
        time.sleep(1.)
        node = ui.nodes('BiomeTintSettings')[0]
        ui.call('click', ui.nodes('Button', ui.nodes('Action', node)[0])[0]['id'])
        time.sleep(.5)
        ui.call('scroll', ui.nodes('VisibleScroll',ui.nodes('ProjectionSettings')[0])[0]['id'], 170)
        screenshot('options')
        names = ('plains', 'desert', 'jungle', 'swampland')
        colors, grass_colors, quartz_colors = {}, {}, {}
        for name in names:
            game('s.set_biome('+repr(name)+')\n_result=True')
            frame = screenshot(name)
            # Left tree is isolated from UI controls and non-tinted quartz.
            colors[name] = ImageStat.Stat(frame.crop((344,277,360,290))).mean
            grass_colors[name] = ImageStat.Stat(frame.crop((380,323,400,332))).mean
            quartz_colors[name] = ImageStat.Stat(frame.crop((373,269,386,280))).mean
        ui.check('biome selection changes rendered foliage pixels',
                 max(abs(a-b) for a,b in zip(colors['desert'],colors['jungle'])) > 8)
        ui.check('grass responds to the selected biome too',
                 max(abs(a-b) for a,b in zip(grass_colors['desert'],grass_colors['jungle'])) > 4)
        ui.check('non-tinted quartz keeps its original color',
                 max(abs(a-b) for a,b in zip(quartz_colors['desert'],quartz_colors['jungle'])) < 2)
        before = game('_result=api._biome_builds')
        game('s.open_materials("material")\n_result=True')
        deadline = time.time()+30
        while game('_result=s.catalogue_loading') and time.time()<deadline:
            time.sleep(.25)
        ui.check('native item catalogue loaded',game('_result=s.catalogue_ready'))
        game('s.set("material_browser",None)\ns.set_biome("plains")\n_result=True')
        frame = screenshot('after_picker')
        color = ImageStat.Stat(frame.crop((344,277,360,290))).mean
        ui.check('catalogue no longer makes foliage red',color[1] > color[0])
        ui.check('tint and catalogue switches never rebuild geometry',game('_result=api._biome_builds')==before==0)

        game('''s.origin=tuple(v+(18 if i==1 else 0) for i,v in enumerate(s.bridge.player_origin()))
s.bridge.project()
_result=True''')
        time.sleep(1.)
        world = game('_result={"entity":s.bridge.entity,"models":len(s.bridge.models),"builds":api._biome_builds}')
        ui.check('world ghost created',bool(world['entity']))
        for name in names:
            game('s.set_biome('+repr(name)+')\n_result=True')
        ui.check('world tint reuses the same actor and geometry',world==game(
            '_result={"entity":s.bridge.entity,"models":len(s.bridge.models),"builds":api._biome_builds}'))
        game('s.bridge.stop_projection()\n_result=True')

        game('''from modern_projection.projection.model import Document
s._loaded(Document((64,128,64)))
s.editor.material=('minecraft:oak_leaves',0)
s.choose_tool('shell')
s.run()
_result=True''')
        wait_preview()
        before = game('_result={"builds":api._biome_builds,"signature":s.preview_signature(),"blocks":len(s.editor.document.blocks)}')
        for name in names:
            game('s.set_biome('+repr(name)+')\n_result=True')
        screenshot('maximum')
        ui.check('maximum size tint keeps all model uploads and block revisions',before==game(
            '_result={"builds":api._biome_builds,"signature":s.preview_signature(),"blocks":len(s.editor.document.blocks)}'))
        (ui.OUT/'biome65_checks.json').write_text(json.dumps({'checks':ui.checks,'colors':colors,'grass':grass_colors,
            'maximum':before},ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(colors),flush=True)
    finally:
        game('''s.bridge.stop_projection()
s.bridge.geometry=api._biome_native_geometry
s.editor,s.origin,s.page,s.inspector=api._biome_saved
s.refresh_preview()
s.emit()
_result=True''')


if __name__ == '__main__':
    main()
