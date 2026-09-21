"""Responsive sharing surfaces without clipboard or persistent library writes."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_large_editor import snapshot


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd'])
    resize=str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py')
    game('api._share_layout=(s.library,s.page)\ns.library=[{"id":90001,"data":{"name":"Layout fixture","size":[64,128,64],"blockCount":20649}}]\ns.set("page","library")\ns.emit()\n_result=True')
    try:
        for preset in ('4:3','16:9'):
            subprocess.run([sys.executable,resize,'--preset',preset],check=True,capture_output=True)
            time.sleep(.8)
            lib=ui.nodes('Library')[0]
            clip=ui.nodes('ScrollView',lib)[0]['layout']
            for name in ('载入','重命名','分享','删除'):
                action=next(n for n in ui.nodes('Action',lib) if n['props'].get('label')==name)
                box=ui.nodes('Button',action)[0]['layout']
                ui.check(preset+' card '+name+' stays in list',box['x']>=clip['x']-1 and box['x']+box['width']<=clip['x']+clip['width']+1)
            snapshot('stage52_library_'+preset.replace(':','_'))
            game('s.sharing.open_export()\n_result=True')
            for unused in range(100):
                if not game('_result=s.sharing.busy'):break
                time.sleep(.1)
            dialog=ui.nodes('SharingDialog')[0]
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            for action in ui.nodes('Action',dialog):
                box=ui.nodes('Button',action)[0]['layout']
                assert box['x']>=0 and box['y']>=0 and box['x']+box['width']<=root['width']+1 and box['y']+box['height']<=root['height']+1,box
            ui.check(preset+' complete and segmented copy controls fit',True)
            snapshot('stage52_dialog_'+preset.replace(':','_'))
            game('s.sharing.close()\n_result=True');time.sleep(.4)
    finally:
        game('s.sharing.close()\ns.library,s.page=api._share_layout\ns.emit()\n_result=True')
        subprocess.run([sys.executable,resize,'--size','%dx%d'%(width,height)],check=True,capture_output=True)
        (ui.OUT/'stage52_sharing_layout.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
