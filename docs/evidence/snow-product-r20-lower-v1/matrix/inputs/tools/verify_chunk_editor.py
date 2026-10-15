"""Whole-building editing with internal tiles, local orbit and complete reset."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer, gesture
from verify_large_editor import snapshot
from projection.camera import OrbitCamera


def main():
    ui.click('工作台'); ui.click('完整'); ui.click('浏览')
    start=time.perf_counter()
    diagnostic({'fixture':'solid'})
    pending=diagnostic()
    ui.check('whole-scene generation exposes real progress',pending['pending'] and pending['previewProgress'][1]==128)
    state,unused=wait_preview(); load_seconds=time.perf_counter()-start
    ui.check('all 524288 cells are covered by 128 native palettes',state['sceneSize']==[64,128,64] and state['previewSlots']==128 and state['nativeCells']==524288)
    ui.check('no user-facing chunk mode or navigation remains',not ui.nodes('ChunkNavigation') and not any(s in ui.labels() for s in ('整栋总览','分块编辑','选中本块','触控放置','确认放置')))
    snapshot('whole_scene_default')
    builds=state['previewBuilds']
    ui.click('选取'); ui.click('俯视'); time.sleep(.5)
    click_point((56.5,128,56.5))
    ui.check('whole view picks exact far voxel',diagnostic()['focused']==[56,127,56])
    ui.click('定位选中'); time.sleep(1.1)
    state=diagnostic()
    ui.check('locating does not crop or rebuild the building',state['sceneSize']==[64,128,64] and state['previewBuilds']==builds and state['cameraPivot']==[56.5,127.5,56.5])
    ui.click('擦除'); ui.click('单格'); click_point((56.5,128,56.5));wait_preview()
    erased=diagnostic()
    ui.check('one edit rebuilds only the touched tile',erased['blocks']==524287 and erased['previewBuilds']==builds+1)
    start=time.perf_counter();ui.click('历史');ui.click('撤销');wait_preview();undo_seconds=time.perf_counter()-start
    ui.check('undo reuses cached geometry',diagnostic()['blocks']==524288 and diagnostic()['previewBuilds']==erased['previewBuilds'])
    ui.click('参数');ui.click('浏览')
    target=pointer();box=target['layout'];x,y=box['width']/2,box['height']/2
    gesture('down',x,y,target); anchored=diagnostic();anchor=anchored['cameraPivot']
    for i in range(1,13):gesture('move',x+i*2,y+i*.35,target)
    gesture('up',x+24,y+4.2,target);time.sleep(1.5)
    rotated=diagnostic()
    camera=OrbitCamera(*rotated['pose']);camera.pivot=rotated['cameraPivot'];camera.pan=rotated['pan']
    unit=min(box['width'],box['height'])*.72*rotated['pose'][2]/max(rotated['sceneSize'])
    projected=camera.project(anchor,rotated['sceneSize'],box['width'],box['height'],unit)
    ui.check('near orbit keeps the touched surface fixed instead of swinging around the building',max(abs(a-b) for a,b in zip(projected,(x,y)))<.1 and abs(rotated['pose'][0]-anchored['pose'][0])>1)
    ui.check('orbit never rebuilds native geometry',rotated['previewBuilds']==erased['previewBuilds'])
    snapshot('whole_scene_close_orbit')
    for text in ('前移','下移','右移','左转'):ui.click(text)
    ui.click('复位');time.sleep(.6)
    reset=diagnostic()
    ui.check('reset clears pivot, pan, zoom and both angles',reset['cameraPivot'] is None and reset['pan']==[0.,0.] and reset['pose']==[35.,25.,1.])
    ui.click('建筑库');ui.click('工作台');time.sleep(.6)
    ui.check('reset survives page remount and pending input',diagnostic()['pose']==[35.,25.,1.] and diagnostic()['cameraPivot'] is None)
    ui.new_region((64,1,64));wait_preview()
    ui.click('浏览');ui.click('俯视');click_point((63.5,0,63.5))
    ui.check('flat drafts expose every real cell without switching view modes',diagnostic()['sceneSize']==[64,1,64] and diagnostic()['focused']==[63,0,63])
    (ui.OUT/'whole_scene_checks.json').write_text(json.dumps({'checks':ui.checks,'initialLoadSeconds':load_seconds,'singleUndoSeconds':undo_seconds},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
