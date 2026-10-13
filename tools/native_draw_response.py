"""Require visible native draw changes, independently of compositor receipts."""
import hashlib
import time
from PIL import Image, ImageChops

from verify_debug_blueprints import walk, write_json

INSTALL = '''assert not hasattr(sys,'_snow_product_render_frames')
class SnowProductRenderFrames(object):
 def __init__(self):self.count=0
 def tick(self,unused):self.count+=1
probe=SnowProductRenderFrames()
sys._snow_product_render_frames=probe
owner.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
_result=True
'''

REMOVE = '''if hasattr(sys,'_snow_product_render_frames'):
 probe=sys._snow_product_render_frames
 owner.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',probe,probe.tick)
 del sys._snow_product_render_frames
_result=True
'''


def frame_count(check):
    return check.run('_result=sys._snow_product_render_frames.count')


def await_frames(check, before, deadline):
    while time.monotonic() < deadline:
        after = frame_count(check)
        if after >= before+2:
            return {'before': before, 'after': after, 'source': 'GameRenderTickEvent'}
        time.sleep(.1)
    raise TimeoutError('Actual native GameRenderTickEvent did not advance twice')


def changed_pixels(first, second, crop, threshold=20):
    with Image.open(first['path']) as a, Image.open(second['path']) as b:
        if a.size != b.size:
            raise ValueError('Native response captures changed dimensions')
        delta = ImageChops.difference(a.convert('RGB').crop(crop), b.convert('RGB').crop(crop))
        red, green, blue = delta.split()
        maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        return sum(maximum.histogram()[threshold+1:])


def native_clock(record):
    """Pinned debug build draws its native wall-clock text in this top strip."""
    with Image.open(record['path']) as image:
        width, height = image.size
        crop = (int(width*.3), int(height*.065), int(width*.7), int(height*.095))
        pixels = image.convert('RGB').crop(crop)
        return {'crop': crop, 'sha256': hashlib.sha256(pixels.tobytes()).hexdigest()}


def capture_response(check, label, reference, crop, before, minimum=80, seconds=6.):
    """Poll frames/captures only; never replay the caller's native mutation."""
    deadline = time.monotonic()+seconds
    attempts = []
    reference_clock = native_clock(reference)
    time.sleep(1.2)  # The pictured wall clock advances in whole seconds.
    while time.monotonic() < deadline:
        ticks = await_frames(check, before, deadline)
        capture = check.capture(label)
        clock = native_clock(capture)
        changed = changed_pixels(reference, capture, crop)
        row = {'capture': capture, 'render_frames': ticks, 'clock': clock,
               'changed_pixels': changed, 'native_clock_advanced': clock['sha256'] != reference_clock['sha256']}
        attempts.append(row)
        if changed >= minimum and row['native_clock_advanced']:
            return capture, {'passed': True, 'reference_clock': reference_clock, 'attempts': attempts,
                             'minimum_changed_pixels': minimum, 'channel_threshold': 20}
        time.sleep(.2)
    failure = {'passed': False, 'reason': 'Native draw did not visibly respond before deadline',
               'reference': reference, 'reference_clock': reference_clock, 'crop': crop,
               'attempts': attempts, 'seconds': seconds, 'minimum_changed_pixels': minimum}
    path = check.output.with_name(check.output.stem+'_'+label+'_response_error.json')
    write_json(path, failure)
    raise RuntimeError('Native visible response failed; retained evidence '+str(path))


def ui_preflight(check):
    """Hide the ordinary inspector header, then require its actual return."""
    tree = check.command('dump_tree')['tree']
    header = next(node for node in walk(tree) if node.get('key') == 'header' and node.get('layout'))
    root = next(node['layout'] for node in walk(tree) if node.get('layout'))
    control_record = check.run('''from modern_projection.pyreact.debug import find_fiber_by_id
host=navigator.top._host
fiber=find_fiber_by_id(host._root_fiber,%r)
assert fiber is not None and fiber.native_path
control=host.GetBaseUIControl(fiber.native_path)
assert control is not None and control.GetVisible()
_result=json.dumps({'path':fiber.native_path,'visible':control.GetVisible()})
''' % header['id'])
    native_path = control_record['path']
    baseline = check.capture('native_ui_response_shown')
    width, height = baseline['size']
    sx, sy = width/root['width'], height/root['height']
    box = header['layout']
    crop = (int((box['x']-root.get('x', 0))*sx), int((box['y']-root.get('y', 0))*sy),
            int((box['x']-root.get('x', 0)+box['width'])*sx),
            int((box['y']-root.get('y', 0)+box['height'])*sy))
    saved = check.run('''host=navigator.top._host
control=host.GetBaseUIControl(%r)
assert control is not None
before=control.GetVisible()
assert before
_result=before
''' % native_path)
    try:
        count = frame_count(check)
        check.run('host.GetBaseUIControl(%r).SetVisible(False)\nassert not host.GetBaseUIControl(%r).GetVisible()\n_result=True' % (native_path, native_path))
        hidden, hiding = capture_response(check, 'native_ui_response_hidden', baseline, crop, count)
        count = frame_count(check)
        check.run('host.GetBaseUIControl(%r).SetVisible(True)\nassert host.GetBaseUIControl(%r).GetVisible()\n_result=True' % (native_path, native_path))
        restored, showing = capture_response(check, 'native_ui_response_restored', hidden, crop, count)
        residual = changed_pixels(baseline, restored, crop)
        if residual > 24:
            raise AssertionError('Formal UI header did not return to its original pixels: '+str(residual))
        return {'passed': True, 'control': native_path, 'crop': crop, 'shown': baseline, 'hidden': hidden,
                'restored': restored, 'hiding': hiding, 'showing': showing, 'restoration_changed_pixels': residual}
    finally:
        check.run('host.GetBaseUIControl(%r).SetVisible(%r)\n_result=True' % (native_path, saved))
