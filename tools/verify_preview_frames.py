"""Detect blank preview frames during actual repeated mouse placements (requires mss/Pillow)."""
import json
import sys
import time
import threading
import numpy as np
import mss
from PIL import Image, ImageDraw
import verify_ui as ui
import verify_interaction as interaction
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if '还原视图' in ui.labels():
        ui.click('还原视图')
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')
    if '--large' in sys.argv:
        diagnostic({'fixture':'demo_large'})
        wait_preview()
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id'])
    ui.click('俯视'); ui.click('放置')
    wait_preview()
    diagnostic({'camera':[0,90,1], 'pan':[0,0]})
    if '--large' in sys.argv:
        diagnostic({'focus':[8,10,14]});ui.click('定位选中')
    time.sleep(.8)
    before=diagnostic()
    box = interaction.pointer()['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    hwnd = window['hwnd']
    left, top, width, unused = capture._window_rect(hwnd)
    scale = width / root['width']
    region = dict(left=int(left + box['x'] * scale), top=int(top + box['y'] * scale),
                  width=int(box['width'] * scale), height=int(box['height'] * scale))
    size=before['sceneSize']
    cam=interaction.OrbitCamera(*before['pose']);cam.pan=before['pan'];cam.pivot=before['cameraPivot']
    x,y=cam.project((8.5,11.,14.5),size,box['width'],box['height'],
        min(box['width'],box['height'])*.72*before['pose'][2]/max(size))
    capture.user32.SetCursorPos(int(region['left'] + x * scale), int(region['top'] + y * scale))
    time.sleep(.15)
    frames, counts, quartz_counts, times = [], [], [], []
    pressed = False
    start = time.perf_counter()
    epoch = time.time()
    def clicks():
        for at in (.3,.9,1.5,2.1):
            time.sleep(max(0.,start+at-time.perf_counter()))
            capture.user32.mouse_event(2,0,0,0,0)
            time.sleep(.12)
            capture.user32.mouse_event(4,0,0,0,0)
    worker=threading.Thread(target=clicks);worker.start()
    with mss.MSS() as screen:
        try:
            while time.perf_counter() - start < 3.0:
                assert capture.user32.GetForegroundWindow() == hwnd
                t = time.perf_counter() - start
                raw = screen.grab(region)
                frame = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX').resize((320, 200))
                # Model pixels are dark/saturated; the near-white grid is excluded.
                frames.append(frame); times.append(round(t, 4))
                time.sleep(.003)
        finally:
            worker.join(); capture.user32.mouse_event(4, 0, 0, 0, 0)
    arrays=[np.array(frame).astype('int16') for frame in frames]
    reference=arrays[0]
    # Roof-only mask is independent of world brightness; wood revealed by a
    # missing tile differs strongly from the baseline roof color.
    roof=(reference.max(2)-reference.min(2)<55)&(reference.max(2)<220)
    for pixels in arrays:
        counts.append(int((pixels.max(2)<180).sum()))
        quartz_counts.append(int((roof & (np.abs(pixels-reference).max(2)<35)).sum()))
    baseline = max(counts[:max(1, sum(t < .25 for t in times))])
    blank = [i for i, c in enumerate(counts) if c < baseline * .5]
    # Include the lowest coverage frame and its neighbours plus evenly spaced frames.
    low = min(range(len(counts)), key=counts.__getitem__)
    selected = sorted(set([max(0, min(len(frames) - 1, low + d)) for d in range(-3, 4)] +
                          [int(i * (len(frames) - 1) / 8) for i in range(9)]))
    sheet = Image.new('RGB', (320 * 4, 225 * ((len(selected) + 3) // 4)), 'white')
    draw = ImageDraw.Draw(sheet)
    for n, i in enumerate(selected):
        x, y = n % 4 * 320, n // 4 * 225
        sheet.paste(frames[i], (x, y))
        draw.text((x + 5, y + 202), '%.3fs | model pixels %d' % (times[i], counts[i]), fill='black')
    sheet.save(ui.OUT / ('frames_' + label + '.png'))
    result = dict(epoch=epoch, samples=len(frames), seconds=times[-1], baseline=baseline, minimum=min(counts),
                  blank_samples=len(blank), times=times, model_pixels=counts)
    result['minimumRoofCoverage'] = min(quartz_counts)/float(max(quartz_counts[:max(1, sum(t<.25 for t in times))]))
    (ui.OUT / ('frames_' + label + '.json')).write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('times', 'model_pixels')}, indent=2))
    after=diagnostic()
    ui.check('four native placements are accepted', after['blocks']==before['blocks']+4)
    ui.check('model remains visible in every sampled frame', not blank)
    ui.check('individual roof tiles remain visible during replacement', result['minimumRoofCoverage']>.9)


if __name__ == '__main__':
    main()
