"""Inspect grouped scene settings, retained tabs and workspace footer spacing."""
import base64
import json
import sys
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from verify_biome_controls import native_click
from native_input_mode import state, set_touch


def install():
    game('from modern_projection.pyreact import navigator\nif navigator.contains("modern_projection_workspace"): navigator.pop()\n_result=True')
    time.sleep(.4)
    game('from modern_projection.projection.catalog import SEGMENT_ICONS\nSEGMENT_ICONS.update({u"场景":"eye",u"外观":"sliders",u"图层管理":"layers"})\n_result=True')
    for name in ('panels', 'ui'):
        source=base64.b64encode((ui.ROOT/('behavior_pack/modern_projection/projection/'+name+'.py')).read_bytes()).decode('ascii')
        game('import base64\nfrom modern_projection.projection import '+name+' as module\n'
             'exec(compile(base64.b64decode('+repr(source)+'),'+repr(name+'.py')+',"exec"),module.__dict__)\n_result=True')
    game('''import sys
from modern_projection.pyreact import navigator
from modern_projection.projection.ui import Workspace
sys.modules[s.bridge.system.__class__.__module__].Workspace=Workspace
navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
    time.sleep(3)


def tab(name):
    segment=next(n for n in ui.nodes('Segments',ui.nodes('Layers')[0])
                 if any(pair[1]==name for pair in n['props']['items']))
    return next(n for n in ui.nodes('Button',segment) if name in ui.labels(n))


def press(node, native=False):
    if native:
        # The shared helper accepts an Action containing a Button.
        native_click({'type':'Action','props':{},'children':[node]})
    else:
        ui.call('click',node['id']);time.sleep(.4)


def check_gap():
    tree=ui.tree()
    owner=ui.nodes('Inspector',tree) or ui.nodes('Viewport',tree)
    pane=ui.nodes('Panel',owner[0])[0]['layout']
    parents=next(parents for node,parents in ui._walk(tree) if node.get('type')=='TaskStatus')
    status=next(node['layout'] for node in reversed(parents) if node.get('type')=='Image')
    scale=game('from modern_projection.projection.widgets import Theme\n_result=Theme.scale')
    gap=status['y']-pane['y']-pane['height']
    ui.check('footer has a ten-unit gutter below rounded panels',abs(gap-10*scale)<.2)
    return gap/scale


def main():
    if '--install' in sys.argv:install()
    original=state()['simulated']
    saved=game('_result=[s.page,s.inspector,s.focus_view,s.editor.document.biome]')
    try:
        game('s.set("page","workspace")\ns.set("inspector","layers")\n_result=True')
        time.sleep(2)
        # Sections are prepared by the existing idle queue, without a new
        # native tree on each tab switch.
        deadline=time.time()+20
        while len(ui.nodes('Range',ui.nodes('Layers')[0]))<2 and time.time()<deadline:time.sleep(.3)
        settings=ui.nodes('BiomeTintSettings')[0]
        choose=ui.nodes('Action',settings)[0]
        ui.call('click',ui.nodes('Button',choose)[0]['id']);time.sleep(.7)
        settings=ui.nodes('BiomeTintSettings')[0]
        icons=[n['props']['glyph'] for n in ui.nodes('Action',settings) if n['props'].get('compact')]
        ui.check('all ten biome choices have distinct semantic icons',len(icons)==len(set(icons))==10)
        snapshot('scene66_biomes')
        ui.call('click',ui.nodes('Button',ui.nodes('Action',settings)[0])[0]['id']);time.sleep(.4)
        snapshot('scene66_appearance')
        ids=[n['id'] for n in ui.nodes('Slider',ui.nodes('Layers')[0])]
        for native in (False,) if '--background' in sys.argv else (True,):
            for touch in (original,) if not native else (False,True):
                if native:set_touch(touch)
                press(tab('图层管理'),native)
                time.sleep(.5)
                layers=ui.nodes('Layers')[0]
                ui.check('layer management separates visibility and locks from appearance',
                         not ui.nodes('Range',layers) and not ui.nodes('BiomeTintSettings',layers))
                snapshot('scene66_layers_'+('touch' if touch else 'pc'))
                press(tab('外观'),native)
                ui.check('appearance restores brightness and spectrum controls',len(ui.nodes('Range',ui.nodes('Layers')[0]))==2)
        if '--background' in sys.argv:
            ui.check('switching sections retains slider native controls',ids==[n['id'] for n in ui.nodes('Slider',ui.nodes('Layers')[0])])
        for focus in (False,True):
            game('s.set("focus_view",'+repr(focus)+')\n_result=True');time.sleep(.6)
            check_gap()
            if not focus:
                ui.check('execute caption uses middle dot',any(n['props'].get('label','').startswith('执行 · ') for n in ui.nodes('Action')))
            snapshot('scene66_focus' if focus else 'scene66_workspace')
        (ui.OUT/'scene66_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        game('s.page,s.inspector,s.focus_view='+repr(tuple(saved[:3]))+'\ns.set_biome('+repr(saved[3])+')\ns.emit()\n_result=True')
        if '--background' not in sys.argv:set_touch(original)


if __name__=='__main__':main()
