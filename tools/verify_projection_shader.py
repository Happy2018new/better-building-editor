"""Sample real frames during batched double-buffered updates in one actor."""
import json
import time
import numpy as np
from PIL import Image, ImageGrab, ImageDraw
import verify_projection_occupancy as qa
import capture_screen as capture
from verify_projection_outline import game, server


def capture_frames(window, seconds):
    # PrintWindow captures this PID-bound window even if a console/tool steals
    # foreground focus. Desktop cropping can silently capture the wrong screen.
    frames, stamps = [], []
    started = time.perf_counter()
    while time.perf_counter()-started < seconds:
        frame = ImageGrab.grab(window=window['hwnd']).resize((850, 480))
        frames.append(frame.crop((100, 175, 750, 290)))
        stamps.append(time.perf_counter()-started)
        time.sleep(.012)
    return frames, stamps


def start_burst(origin, cells, rounds):
    return server('''from modern_projection.server_system import WorldAdapter
adapter=WorldAdapter(p)
timer=f.CreateGame(api.GetLevelId())
origin='''+repr(tuple(origin))+'''
stats={"changes":0,"done":False,"cancel":False}
api._occupancy_qa_burst=stats
def install(adapter,timer,origin,stats):
    def step(index):
        if stats["cancel"]:
            stats["done"]=True
            return
        x=index%'''+str(cells)+'''
        name="minecraft:glass" if index//'''+str(cells)+'''%2==0 else "minecraft:air"
        assert adapter.write((origin[0]+x,origin[1],origin[2]),(name,0))
        stats["changes"]+=1
        if index+1<'''+str(cells*rounds)+''': timer.AddTimer(.07,step,index+1)
        else: stats["done"]=True
    timer.AddTimer(.5,step,0)
install(adapter,timer,origin,stats)
_result=True''')


def analyze(frames, stamps, label, empty):
    frames[0].save(qa.ui.OUT/('projection_shader_'+label+'_baseline.png'))
    baseline = np.asarray(frames[0]).astype(int)
    # Select the actual projection by its difference from a deliberately
    # shader-hidden reference. This works against sky as well as terrain.
    empty = np.asarray(empty).astype(int)
    delta = baseline-empty
    contrast = np.sum(delta*delta, axis=2)
    neutral = contrast > 20*20
    neutral &= (neutral.sum(axis=1) > baseline.shape[1]*.15)[:,None]
    yy, xx = np.where(neutral)
    assert len(xx) > 1000, 'Projection not visible in baseline: %d pixels' % len(xx)
    lo, hi = np.percentile(xx, (3, 22))
    top, bottom = np.percentile(yy, (20, 80))
    stable = neutral & (np.indices(neutral.shape)[1] > lo) & (np.indices(neutral.shape)[1] < hi)
    stable &= (np.indices(neutral.shape)[0] > top) & (np.indices(neutral.shape)[0] < bottom)
    assert stable.sum() > 150, 'Insufficient unaffected projection pixels'
    coverage = []
    for frame in frames:
        rgb = np.asarray(frame).astype(int)
        # Project onto the measured ghost-vs-empty color difference. A hidden
        # pixel is near 0, a rendered ghost near 1; no absolute RGB tolerance
        # that could accidentally accept the empty sky as a ghost.
        strength = np.sum((rgb-empty)[stable]*delta[stable],axis=1)/contrast[stable]
        coverage.append(float((strength > .5).mean()))
    output = qa.ui.OUT / ('projection_shader_'+label)
    frames[0].save(str(output)+'.gif', save_all=True, append_images=frames[1:],
                   duration=max(20, int(1000*stamps[-1]/len(frames))), loop=0)
    picks = sorted(set([0,len(frames)//4,len(frames)//2,3*len(frames)//4,len(frames)-1]+
                       sorted(range(len(frames)), key=coverage.__getitem__)[:6]))
    sheet = Image.new('RGB',(650,140*len(picks)), 'white')
    for row, index in enumerate(picks):
        sheet.paste(frames[index],(0,row*140+25))
        ImageDraw.Draw(sheet).text((5,row*140+5),'%.3fs stable %.1f%%'%(stamps[index],coverage[index]*100),fill='black')
    sheet.save(str(output)+'.png')
    result = dict(frames=len(frames), duration=stamps[-1], min_coverage=min(coverage),
                  below_95=sum(v<.95 for v in coverage), coverage=coverage, times=stamps,
                  stable_pixels=int(stable.sum()), artifact=str(output)+'.png')
    output.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    assert result['below_95']==0, result
    return result


def main():
    origin, installed = None, False
    results = {}
    try:
        origin = qa.setup_fixture()

        server('''from modern_projection.server_system import WorldAdapter
a=WorldAdapter(p)
origin='''+repr(tuple(origin))+'''
extra=[((origin[0]+x,origin[1],origin[2]),a.read((origin[0]+x,origin[1],origin[2]))) for x in range(16)]
assert all(value==("minecraft:air",0) for pos,value in extra)
api._occupancy_qa_saved+=extra
_result=True''')
        qa.install_probe(origin)
        installed = True
        qa.wait_points((x,0,0) for x in range(8))
        game('''b=s.bridge
b.stop_projection()
from modern_projection.projection.model import Document,Editor
s.editor=Editor(Document((16,1,1),dict(((x,0,0),("minecraft:quartz_block",0)) for x in range(16))))
b.project()
_result=True''')
        qa.wait_points((x,0,0) for x in range(16))
        capture.user32.SetProcessDPIAware()
        window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
        assert window
        qa.capture_fixture(origin,'shader_full',16,camera_height=.5)
        game('b=s.bridge\nu=b.projection_occupancy.shader\nv=u.uniforms[4]\nassert u.render.SetEntityExtraUniforms(4,v[:2]+(-1.,v[3]))\n_result=True')
        time.sleep(.25)
        empty = ImageGrab.grab(window=window['hwnd']).resize((850,480)).crop((100,175,750,290))
        empty.save(qa.ui.OUT/'projection_shader_empty.png')
        game('u=s.bridge.projection_occupancy.shader\nassert u.render.SetEntityExtraUniforms(4,u.uniforms[4])\n_result=True')
        time.sleep(.25)
        for label, cells, rounds in (('batch8',8,8),('batch12',12,6)):
            before = qa.snapshot()
            start_burst(origin,cells,rounds)
            frames, stamps = capture_frames(window,cells*rounds*.075+2.)
            after = qa.wait_points((x,0,0) for x in range(16))
            results[label] = analyze(frames,stamps,label,empty)
            results[label]['before'] = before
            results[label]['after'] = after
            assert before['actor']==after['actor'] and after['actors']==1
            assert 0 < after['metrics']['builds']-before['metrics']['builds'] < cells*rounds/2
            print(label, results[label]['frames'], results[label]['min_coverage'],
                  'rebases',after['metrics']['builds']-before['metrics']['builds'],flush=True)
    finally:
        if origin is not None:
            server('''from modern_projection.server_system import WorldAdapter
if hasattr(api,"_occupancy_qa_burst"): api._occupancy_qa_burst["cancel"]=True
a=WorldAdapter(p)
for pos,value in api._occupancy_qa_saved: assert a.write(pos,value)
_result=True''')
        if installed:
            game('''s.bridge.stop_projection()
cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos();cam.UnDepartCamera()
cam.LockModCameraPitch(api._occupancy_qa_camera[0]);cam.LockModCameraYaw(api._occupancy_qa_camera[1])
s.editor,s.origin,s.projection_missing,s.projection_outline,s.solo_layer,s.bridge.geometry,s.bridge.factory=api._occupancy_qa_saved
s.refresh_preview();s.emit()
_result=True''')
        qa.dump(qa.ui.OUT/'projection_shader_checks.json',results)


if __name__ == '__main__':
    main()
