"""Verify palette buttons in PC/F11 modes and capture previews for visual review.

Run via run_live_check.py in a managed test world. Restores the selected biome,
page and input mode; does not write world blocks or save the draft.
"""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from verify_biome_controls import native_click, action
from native_input_mode import set_touch, state, open_workspace
from verify_biome_tint import wait_preview


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd']), 'Managed game window unavailable'
    open_workspace()
    original = state()['simulated']
    saved = game('_result=[s.page,s.editor.document.biome]')
    try:
        for touch in (False, True):
            set_touch(touch)
            game('s.set("page","projection")\n_result=True')
            wait_preview()
            node = ui.nodes('BiomeTintSettings')[0]
            if len(ui.nodes('Action',node)) == 1:
                ui.call('click',ui.nodes('Button',ui.nodes('Action',node)[0])[0]['id'])
                time.sleep(.4)
            node = ui.nodes('BiomeTintSettings')[0]
            choices = [n for n in ui.nodes('Action',node) if n['props'].get('compact')]
            ui.check('thirteen palette choices '+str(touch),len(choices)==13)
            scroll = ui.nodes('VisibleScroll',ui.nodes('ProjectionSettings')[0])[0]
            for name,label in (('pale_garden','苍白花园'),('cherry_grove','樱花树林'),
                               ('mesa','恶地'),('roofed_forest','黑森林')):
                choice = action(label,ui.nodes('BiomeTintSettings')[0])
                button = ui.nodes('Button',choice)[0]['layout']
                viewport = scroll['layout']
                # Centre the target within its scroll viewport at any UI scale.
                position = button['y']-viewport['y']-(viewport['height']-button['height'])*.5
                ui.call('scroll',scroll['id'],max(0.,position))
                time.sleep(.5)
                native_click(action(label,ui.nodes('BiomeTintSettings')[0]))
                ui.check(name+' native click '+str(touch),
                         game('_result=s.editor.document.biome')==name)
                wait_preview()
                snapshot('palette_'+('touch' if touch else 'pc')+'_'+name)
        (ui.OUT/'palette_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        try:
            game('s.set("page",'+repr(saved[0])+')\ns.set_biome('+repr(saved[1])+')\n_result=True')
        finally:
            # A failed F11 switch may have closed the workspace before raising.
            open_workspace()
            time.sleep(.5)
            set_touch(original)


if __name__ == '__main__':
    main()
