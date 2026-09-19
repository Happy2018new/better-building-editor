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
    ui.check('largest volume uses exact native dimensions',state['sceneSize']==[256,384,256] and state['sceneScale']==1)
    ui.check('only two persistent native renderers are used',len(ui.nodes('PaperDoll'))==2)
    snapshot('exact_solid_verified')
    diagnostic({'fixture':'landmarks'});wait_preview()
    ui.click('俯视'); time.sleep(.6)
    click_point((255.5,384.,255.5))
    ui.check('overview picking reaches the far high column',diagnostic()['focused']==[255,383,255])
    click_point((128.5,1.,48.5))
    ui.check('thin full-width structure retains internal coordinates',diagnostic()['focused']==[128,0,48])
    before=diagnostic()['blocks'];ui.click('擦除');click_point((128.5,1.,48.5));wait_preview()
    ui.check('overview erases exactly one real voxel',diagnostic()['blocks']==before-1)
    ui.click('历史');ui.click('撤销');wait_preview();ui.click('参数');ui.click('浏览')
    ui.check('overview undo restores the exact voxel',diagnostic()['blocks']==before)
    snapshot('exact_landmarks_verified')
    ui.click('精细');wait_preview()
    center=next(n for n in ui.nodes('Coordinates') if n['props'].get('label')=='精细视图中心  X, Y, Z')
    ui.call('set_input',ui.nodes('Input',center)[0]['id'],'255, 383, 255');wait_preview()
    state=diagnostic()
    ui.check('precise crop remains located at actual far coordinates',state['origin']==[224,352,224] and state['sceneSize']==[32,32,32])
    click_point((255.5,384.,255.5))
    ui.check('precise picking and overview picking agree',diagnostic()['focused']==[255,383,255])
    snapshot('exact_detail_verified')
    ui.click('总览');wait_preview()
    diagnostic({'fixture':'demo'});wait_preview()
    (ui.OUT/'exact_render_checks.json').write_text(json.dumps({'solidBuildSeconds':elapsed,'checks':ui.checks},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
