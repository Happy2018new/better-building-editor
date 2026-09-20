"""Render full-size asymmetric features and verify real far-corner picking."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_large_editor import snapshot


def main():
    ui.click('工作台'); ui.click('浏览')
    start=time.perf_counter()
    diagnostic({'fixture':'solid'})
    state,unused=wait_preview()
    elapsed=time.perf_counter()-start
    time.sleep(1)
    ui.check('largest overview uses exact native dimensions',state['sceneSize']==[64,128,64] and state['sceneScale']==1)
    ui.check('overview uses bounded local native palettes',state['previewSlots']==128 and state['nativeCells']==524288)
    snapshot('exact_solid_verified')
    diagnostic({'fixture':'landmarks'});wait_preview()
    ui.click('俯视'); time.sleep(.6)
    click_point((63.5,128.,63.5))
    ui.check('overview picking reaches the far high column',diagnostic()['focused']==[63,127,63])
    click_point((32.5,1.,48.5))
    ui.check('thin full-width structure retains internal coordinates',diagnostic()['focused']==[32,0,48])
    before=diagnostic()['blocks'];ui.click('擦除');click_point((32.5,1.,48.5));wait_preview()
    ui.check('overview erases exactly one real voxel',diagnostic()['blocks']==before-1)
    ui.click('历史');ui.click('撤销');wait_preview();ui.click('参数');ui.click('浏览')
    ui.check('overview undo restores the exact voxel',diagnostic()['blocks']==before)
    snapshot('exact_landmarks_verified')
    diagnostic({'focus':[63,127,63]});ui.click('定位选中');time.sleep(1)
    state=diagnostic()
    ui.check('locating keeps the whole building and exact far pivot',state['origin']==[0,0,0] and state['sceneSize']==[64,128,64] and state['cameraPivot']==[63.5,127.5,63.5])
    click_point((63.5,128.,63.5))
    ui.check('chunk picking and overview picking agree',diagnostic()['focused']==[63,127,63])
    snapshot('exact_detail_verified')
    diagnostic({'fixture':'demo'});wait_preview()
    (ui.OUT/'exact_render_checks.json').write_text(json.dumps({'solidBuildSeconds':elapsed,'checks':ui.checks},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
