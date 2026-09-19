"""Live 16-cube navigation, far-coordinate edits, mesh reuse and progress."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import category
from verify_large_editor import snapshot
import capture_screen as capture
import numpy as np
from PIL import Image
from verify_interaction import pointer


def assert_live_scene(label):
    """Check displayed pixels too: IPC can work while a sleeping display is stale."""
    box = pointer()['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    images = []
    for i, angle in enumerate(((35,25,1), (70,50,1))):
        diagnostic({'camera':angle,'pan':[0,0]}); time.sleep(.7)
        name = label + '_angle%d' % i
        snapshot(name)
        image = Image.open(ui.OUT/(name+'.png')).convert('RGB')
        scale = image.width/root['width']
        crop = (int((box['x']+.15*box['width'])*scale), int((box['y']+.1*box['height'])*scale),
                int((box['x']+.85*box['width'])*scale), int((box['y']+.8*box['height'])*scale))
        images.append(np.array(image.crop(crop).resize((400,250))).astype('int16'))
    ui.check(label+' contains actual model pixels', all((im.max(2)<220).sum()>700 for im in images))
    ui.check(label+' pixels update with rotation', (np.abs(images[0]-images[1]).max(2)>25).sum()>1000)
    diagnostic({'camera':[35,25,1],'pan':[0,0]})


def axis_button(axis, glyph):
    root = ui.nodes('ChunkNavigation')[0]
    for node, ancestors in ui._walk(root):
        if node.get('type') == 'Label' and node['props'].get('content', '').startswith(axis+' '):
            for parent in reversed(ancestors):
                actions = ui.nodes('Action', parent)
                if len(actions) == 2:
                    action = next(n for n in actions if n['props'].get('glyph') == glyph)
                    return ui.nodes('Button', action)[0]['id']
    raise AssertionError((axis,glyph))


def verify_flat():
    ui.new_region((64,1,64)); wait_preview()
    ui.check('wide flat draft defaults to local editing', diagnostic()['sceneSize']==[16,1,16] and
             '整栋总览' in ui.labels())
    ui.click('整栋总览'); wait_preview(); ui.click('浏览'); ui.click('俯视')
    click_point((63.5,0,63.5))
    ui.check('flat overview reaches the real far corner',diagnostic()['focused']==[63,0,63])
    ui.click('定位选中'); wait_preview()
    ui.check('locating a flat draft enters the correct chunk',diagnostic()['origin']==[48,0,48] and
             diagnostic()['sceneSize']==[16,1,16])


def main():
    capture.user32.SetProcessDPIAware()
    verify_flat()
    ui.new_region((64,128,64)); wait_preview()
    state = diagnostic()
    ui.check('maximum draft defaults to one full-sized 16-cube',state['size']==[64,128,64] and
             state['sceneSize']==[16,16,16] and state['previewSlots']==1 and state['pose'][2]==1)
    ui.check('chunk counters reflect the new document',all(s in ui.labels() for s in ('X 1/4','Y 1/8','Z 1/4')))
    ui.click('浏览');category('brush');ui.click('填充方块')
    start=time.perf_counter();ui.click('执行 · 填充方块');wait_preview()
    fill_seconds=time.perf_counter()-start
    state=diagnostic()
    ui.check('whole-document fill updates all 524288 blocks',state['blocks']==524288)
    ui.check('local view submits only a 4096-cell palette',state['nativeCells']==4096 and state['previewSlots']==1)
    assert_live_scene('chunk_initial')
    for axis in 'XYZ':
        ui.call('click',axis_button(axis,'plus'));wait_preview()
    ui.check('three adjacent-chunk buttons move in exact 16-cell steps',diagnostic()['origin']==[16,16,16])
    for axis in 'XYZ':
        ui.call('click',axis_button(axis,'minus'));wait_preview()
    ui.check('reverse navigation returns to the original chunk',diagnostic()['origin']==[0,0,0])
    diagnostic({'chunk':[63,127,63],'camera':[0,90,1]});wait_preview();time.sleep(.8)
    ui.check('last chunk retains its exact far coordinates',diagnostic()['origin']==[48,112,48])
    ui.click('选中本块')
    ui.check('select current chunk explicitly limits the formal selection',diagnostic()['selection']==4096)
    ui.click('选取');click_point((56.5,128,56.5))
    ui.check('native view picks far roof voxel at 100 percent',diagnostic()['focused']==[56,127,56])
    ui.click('擦除');ui.click('单格');click_point((56.5,128,56.5));wait_preview()
    erased=diagnostic()
    ui.check('far voxel erasure changes only one block',erased['blocks']==524287)
    start=time.perf_counter();ui.click('历史');ui.click('撤销');wait_preview();undo_seconds=time.perf_counter()-start
    restored=diagnostic()
    ui.check('single edit undo restores data without new native geometry',restored['blocks']==524288 and
             restored['previewBuilds']==erased['previewBuilds'])
    ui.click('参数');ui.click('浏览');diagnostic({'camera':[35,25,1],'pan':[0,0]});time.sleep(.7)
    snapshot('chunk_editor_far_100percent')
    assert_live_scene('chunk_far')
    ui.click('整栋总览')
    # Inspect while generation runs, not only after it finishes.
    state=diagnostic()
    ui.check('overview generation reports bounded chunk progress',state['pending'] and
             0<=state['previewProgress'][0]<state['previewProgress'][1]<=128)
    progress=ui.nodes('PreviewProgress')[0]
    ui.check('model-generation progress bar is shown',ui.nodes('Panel',progress)[0]['style'].get('visible') is True)
    snapshot('chunk_editor_progress')
    start=time.perf_counter();wait_preview();overview_seconds=time.perf_counter()-start
    ui.check('overview uses 128 independent local palettes',diagnostic()['previewSlots']==128 and diagnostic()['nativeCells']==524288)
    ui.click('分块编辑');wait_preview()
    ui.check('returning to editing restores low magnification',diagnostic()['previewSlots']==1 and diagnostic()['pose'][2]==1)
    assert_live_scene('chunk_after_overview')
    before=diagnostic()['previewBuilds']
    ui.click('整栋总览'); start=time.perf_counter(); wait_preview(); revisit_seconds=time.perf_counter()-start
    ui.check('revisiting overview reuses existing native meshes',diagnostic()['previewBuilds']==before)
    ui.click('分块编辑');wait_preview()
    (ui.OUT/'chunk_editor_checks.json').write_text(json.dumps({'checks':ui.checks,'fillSeconds':fill_seconds,
        'undoSeconds':undo_seconds,'overviewWaitSeconds':overview_seconds,'overviewRevisitSeconds':revisit_seconds},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
