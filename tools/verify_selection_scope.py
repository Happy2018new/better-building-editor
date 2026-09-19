"""Live shared selection, empty-space picking and grid identity regression."""
import sys
import time
import json
import verify_ui as ui
from verify_interaction import pointer, tap, category
from verify_large_editor import snapshot
sys.path.insert(0, str(ui.ROOT / 'behavior_pack/HelloScript'))
from projection.camera import OrbitCamera


def diagnostic(value=None):
    node = next(n for n in ui.nodes('Panel') if n['props'].get('onDebug'))
    return ui.call('debug_component',node['id'],value)['result']


def wait_preview(timeout=120):
    start=time.perf_counter()
    while time.perf_counter()-start<timeout:
        state=diagnostic()
        if not state['pending']:
            assert not state['error'],state
            time.sleep(.4)
            return state,time.perf_counter()-start
        time.sleep(.5)
    raise AssertionError('preview timeout')


def click_point(pos):
    state=diagnostic()
    camera=OrbitCamera(*state['pose'])
    camera.pan=tuple(state.get('pan',(0,0)))
    box=pointer()['layout']; size=state['sceneSize']
    p=tuple(pos[i]-state['origin'][i] for i in range(3))
    tap(*camera.project(p,size,box['width'],box['height'],min(box['width'],box['height'])*.72*state['pose'][2]/max(size)))


def main():
    ui.click('工作台')
    diagnostic({'fixture':'offset_odd','selection':[[2,1,3],[5,3,8]]})
    wait_preview(); ui.click('浏览')
    category('cube'); ui.click('空心长方体')
    ui.click('俯视'); time.sleep(.5)
    ui.click('三维框选'); click_point((10.5,.5,10.5))
    ui.check('first empty-space corner keeps committed selection',diagnostic()['selection']==72)
    ui.click('执行 · 空心长方体')
    ui.check('incomplete box prevents batch execution',diagnostic()['blocks']==72)
    click_point((12.5,.5,13.5))
    ui.check('two empty-space clicks commit exact shared cuboid',diagnostic()['selection']==12)
    ui.check('batch tool remains available while framing','执行 · 空心长方体' in ui.labels())
    identities=[n['id'] for n in ui.nodes('PaperDoll')]+[pointer()['id']]
    before=diagnostic()
    for unused in range(4):ui.click('网格')
    ui.check('grid toggles retain native model and pointer identities',identities==[n['id'] for n in ui.nodes('PaperDoll')]+[pointer()['id']])
    after=diagnostic()
    ui.check('grid does not change selection or block data',all(before[k]==after[k] for k in ('start','end','selection','blocks')))
    ui.click('执行 · 空心长方体'); wait_preview()
    ui.check('shape uses viewport selection',diagnostic()['blocks']==84)
    category('grid'); ui.click('棋盘拼色')
    ui.check('switching tool preserves shared scope',diagnostic()['selection']==12)
    ui.click('坐标设置')
    field=next(n for n in ui.nodes('Coordinates') if n['props'].get('label')=='选区终点  X, Y, Z')
    ui.call('set_input',ui.nodes('Input',field)[0]['id'],'11, 0, 12');time.sleep(.4)
    ui.check('coordinate editing immediately changes actual selection',diagnostic()['selection']==6)
    diagnostic({'fixture':'offset_odd','selection':[[2,1,3],[5,3,8]]});wait_preview()
    ui.click('浏览'); snapshot('scope_outline_verified')
    (ui.OUT/'scope_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
