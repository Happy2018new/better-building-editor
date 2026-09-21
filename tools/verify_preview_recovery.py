"""Preview cancellation, hidden pages, failures and exact sparse large models."""
import json
import time
import verify_ui as ui
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import key


def wait():
    for unused in range(180):
        result=game('_result={"pending":s.preview_pending,"error":s.preview_error,"tiles":len(s.tiles.render_keys),"blocks":len(s.editor.document.blocks),"performance":s.performance}')
        if not result['pending']:return result
        time.sleep(.1)
    raise AssertionError(result)


def main():
    game('api._preview_saved=(s.editor,s.page,s.camera_pose,s.camera_pan,s.camera_pivot,s.section,s.solo_layer)\n_result=True')
    try:
        game('from HelloScript.projection.model import Document\ns._loaded(Document((64,128,64)))\ns.emit()\n_result=True')
        result=wait()
        ui.check('maximum empty document needs no native model controls',result['tiles']==0)
        ui.check('central construction message removed','正在构建方块预览…' not in ui.labels())
        game('s.editor.select_box((0,0,0),(63,0,63))\ns.editor.run("fill")\ns.refresh_preview()\ns.set("page","library")\n_result=True')
        result=wait()
        ui.check('hidden workspace finishes full-size floor without renderer ack',result['blocks']==4096 and not result['error'])
        game('s.set("page","workspace")\ns.editor.select_box((0,1,0),(63,31,63))\ns.editor.run("shell")\ns.refresh_preview()\ns.tiles.cancel()\n_result=True')
        result=wait()
        ui.check('cancel clears work without deleting draft',not result['pending'] and bool(result['error']) and result['blocks']>4096)
        time.sleep(.25)
        ui.check('stale scheduled work stays cancelled',game('_result=not s.tiles.running and not s.preview_pending'))
        snapshot('stage51_preview_paused')
        game('s.tiles.retry()\n_result=True');result=wait()
        ui.check('retry recovers exact full-size preview',not result['error'] and result['tiles']>0)
        # Fault injection uses a new document, so no retained cache can bypass it.
        game('''api._preview_geometry=s.bridge.geometry
def broken(*args,**kwargs):raise RuntimeError('preview test failure')
s.bridge.geometry=broken
s._loaded(Document((8,8,8),{(0,0,0):('minecraft:stone',0)}))
s.emit()
_result=True''')
        result=wait()
        ui.check('failed native build exits pending with recoverable error','preview test failure' in result['error'])
        game('s.bridge.geometry=api._preview_geometry\ns.tiles.retry()\n_result=True');result=wait()
        ui.check('failed native build can be retried',not result['error'] and result['blocks']==1)
        game('s.editor,s.page,s.camera_pose,s.camera_pan,s.camera_pivot,s.section,s.solo_layer=api._preview_saved\ns.refresh_preview()\ns.emit()\n_result=True')
        wait();time.sleep(.4)
        snapshot('stage51_current_building')
    finally:
        game('''if hasattr(api,'_preview_geometry'):s.bridge.geometry=api._preview_geometry
s.editor,s.page,s.camera_pose,s.camera_pan,s.camera_pivot,s.section,s.solo_layer=api._preview_saved
s.camera_yaw,s.camera_pitch,s.zoom=s.camera_pose
s.camera_revision+=1
s.refresh_preview()
s.emit()
_result=True''')
        (ui.OUT/'stage51_preview_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
