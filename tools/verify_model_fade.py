"""Pixel regression for opaque preview faces and inherited workspace fades.

Uses an unsaved solid fixture and restores all temporary native overrides.
No geometry rebuilds are needed to fade the model or to hide it for comparison.
"""
import json
import time
import mss
from PIL import Image, ImageChops, ImageStat
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_selection_scope import diagnostic, wait_preview
from verify_global_cursor import screen_point
from verify_interaction import pointer
from native_input_mode import key, set_touch, open_workspace


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    if not game('from modern_projection.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        open_workspace();time.sleep(3.)
    set_touch(False)
    diagnostic.identity=None
    diagnostic({'fixture':'solid','size':[8,8,8],'layer':0,'camera':[35,25,1.]});wait_preview()
    # Use a saturated surface. White quartz nearly matches the white UI;
    # when the backdrop fades to the moving world, that near-zero reference
    # can invert the contrast ratio even though the model itself fades.
    game('s.editor.material=("minecraft:red_wool",0)\ns.editor.run("fill")\ns.refresh_preview()\ns.emit()\n_result=True')
    wait_preview()
    game('s.choose_mode("browse")\ns.set("grid",True)\n_result=True')
    time.sleep(1.)
    left,top,width,height=capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left+30,top+40)
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    box=pointer()['layout'];scale=width/root['width']
    x,y=screen_point((4.5,8.,4.5))
    px,py=int((x+box['x'])*scale),int((y+box['y'])*scale)
    patch=(px-4,py-4,px+5,py+5)
    frames={};measurements={}

    def capture_frame(name):
        time.sleep(.2)
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        with mss.MSS() as screen:
            raw=screen.grab(dict(left=left,top=top,width=width,height=height))
            frame=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
        frames[name]=frame
        frame.save(ui.OUT/('fade_'+name+'.png'))
        return frame.crop(patch)

    def distance(a,b):
        return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3.

    game('''from modern_projection.pyreact.debug import _type_name
def find(f,name):
    if _type_name(f)==name:return f
    for c in f.child_fibers:
        found=find(c,name)
        if found:return found
root=api.GetTopScreen()._root_fiber
api._fade_probe=find(root,'WorkspaceMotion').child_fibers[0].child_fibers[1]
scene=find(root,'Scene').child_fibers[0]
api._fade_models=scene.child_fibers[1]
s._ui_preparation.pause()
_result=True''')
    def alpha(value):
        game('f=api._fade_probe\nc=f.host.GetBaseUIControl(f.native_path)\n'
             'c.SetAlpha(%r)\nc.SetVisible(%r,False)\n_result=True'%(value,value>0))
    def models(shown):
        game('f=api._fade_models\nf.host.GetBaseUIControl(f.native_path).SetVisible(%r,False)\n_result=True'%shown)
    try:
        on=capture_frame('grid_on')
        game('s.set("grid",False)\n_result=True');time.sleep(.4)
        off=capture_frame('grid_off')
        measurements['opaqueGridDelta']=distance(on,off)
        ui.check('opaque roof is unchanged by grid alpha',measurements['opaqueGridDelta']<2.)
        game('s.set("grid",True)\n_result=True');time.sleep(.4)
        for value in (1.,.5,.2,0.):
            alpha(value)
            shown=capture_frame('alpha_%s'%value)
            models(False);hidden=capture_frame('background_%s'%value)
            contrast=distance(shown,hidden)
            measurements[str(value)]=contrast/max(1.,distance(on,hidden))
            if value==1.:
                measurements['opaqueContrast']=contrast
            models(True)
        ui.check('opaque roof has visible contrast',measurements['opaqueContrast']>12.)
        ui.check('preview contribution fades with the workspace',
                 measurements['1.0']>measurements['0.5']>measurements['0.2']>measurements['0.0'])
        ui.check('zero alpha leaves no floating preview',measurements['0.0']<.01)
        alpha(1.);restored=capture_frame('restored')
        ui.check('hiding and reopening restores opaque geometry',distance(on,restored)<2.)
        sheet=Image.new('RGB',(1280,720))
        for i,name in enumerate(('alpha_1.0','alpha_0.5','alpha_0.2','alpha_0.0')):
            sheet.paste(frames[name].resize((640,360)),((i%2)*640,(i//2)*360))
        sheet.save(ui.OUT/'model_fade_pixels.png')
    finally:
        models(True);alpha(1.)
        game('del api._fade_probe\ndel api._fade_models\n_result=True')
        (ui.OUT/'model_fade_checks.json').write_text(json.dumps(dict(checks=ui.checks,measurements=measurements),indent=2),encoding='utf8')


if __name__=='__main__':main()
