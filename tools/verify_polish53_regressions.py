"""Run the final input/depth/preview regressions and restore the original draft."""
import json
import sys
import time
import verify_ui as ui
from verify_font_share_polish import game
from native_input_mode import set_touch,state
import verify_native_touch
import verify_editor_depth
import verify_preview_recovery


def main():
    original=state()['simulated']
    if '--restore-fixture' in sys.argv:
        payload=(ui.OUT/'stage51_current_document.json').read_text(encoding='utf8')
        game('import json\nfrom modern_projection.projection.model import Document\ns._loaded(Document.from_data(json.loads('+repr(payload)+')))\ns.emit()\n_result=True')
        for unused in range(150):
            if not game('_result=s.preview_pending or s.tiles.mounting'):break
            time.sleep(.1)
    game('''api._polish_saved=(s.editor,s.name,s.page,s.direct_mode,s.section,s.solo_layer,s.focused,s.box_anchor)
_result=True''')
    try:
        if '--runtime-only' not in sys.argv:
            verify_native_touch.main()
            set_touch(False)
            verify_editor_depth.main()
            verify_preview_recovery.main()
        value=game('''from modern_projection.projection.typography import supported,characters,GLYPHS
from modern_projection.projection.widgets import Theme
g=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
gui=max(1.,round(float(g.GetScreenViewInfo()[0])/g.GetScreenSize()[0]))
_result={'font_integer':abs(Theme.input_font_scale*gui-round(Theme.input_font_scale*gui))<.0001,
         'narrow_unicode':supported(next(c for c in GLYPHS if len(c)>1 or ord(c)>65535)),
         'glyphs':len(GLYPHS)}''')
        ui.check('original input font keeps integral physical scale',value['font_integer'])
        ui.check('embedded Python loads complete font map',value['glyphs']==30890)
        ui.check('supplementary CJK works on narrow Python 2',value['narrow_unicode'])
        import base64
        files=list((ui.ROOT/'behavior_pack/modern_projection/projection').glob('*.py'))
        for path in files:
            encoded=base64.b64encode(path.read_bytes()).decode('ascii')
            game('import base64\ncompile(base64.b64decode('+repr(encoded)+'),'+repr(path.name)+',"exec")\n_result=True')
        ui.check('embedded Python 2 compiles all %d projection sources'%len(files),True)
    finally:
        game('''s.editor,s.name,s.page,s.direct_mode,s.section,s.solo_layer,s.focused,s.box_anchor=api._polish_saved
s.reset_camera(False)
s.refresh_preview()
s.emit()
del api._polish_saved
_result=True''')
        set_touch(original)
        for unused in range(150):
            if not game('_result=s.preview_pending or s.tiles.mounting'):break
            time.sleep(.1)
        report='stage53_runtime_checks.json' if '--runtime-only' in sys.argv else 'stage53_native_regressions.json'
        (ui.OUT/report).write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
