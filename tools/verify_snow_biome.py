"""Capture an existing projection in a normally generated, managed test world.

Run via run_live_check.py after locating minecraft:ice_plains and creating a
projection nearby. For example: verify_snow_biome.py --name snow_after --colors
--require-biome minecraft:ice_plains. --biome-pos X Y Z overrides the sample
position; it does not teleport the player or load distant chunks.

The optional --camera-offset X Y Z frames the projection's centre from a normal
player-following camera, then returns to that camera. It never moves the player
or writes world blocks. Captures are visual evidence, not pixel assertions.
"""
import argparse
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from native_input_mode import open_workspace
import capture_screen as capture


COLORS = ('plains', 'desert', 'jungle', 'pale_garden', 'cherry_grove',
          'mesa', 'roofed_forest', 'ice_plains')


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='snow_biome', help='Capture filename prefix')
    parser.add_argument('--colors', action='store_true', help='Capture representative tints')
    parser.add_argument('--biome-pos', nargs=3, type=int, metavar=('X', 'Y', 'Z'),
                        help='Loaded position to sample; defaults to the player position')
    parser.add_argument('--require-biome', help='Require this biome at the sample and projection centre')
    parser.add_argument('--camera-offset', nargs=3, type=float, metavar=('X', 'Y', 'Z'),
                        help='Optional camera offset from the projection centre')
    args = parser.parse_args()
    if not args.name or any(char in args.name for char in '/\\:') or args.name in ('.', '..'):
        parser.error('--name must be a filename prefix, without directories')
    if args.camera_offset is not None and not any(args.camera_offset):
        parser.error('--camera-offset must be nonzero')
    return args


def wait_projection():
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        value = game('''b=s.bridge
w=b.projection_work
_result={'active':s.projection_active,'preparing':bool(b.preparing_entity),
         'ready':w is None or w.ready,'error':w.error if w else None,
         'entity':b.entity,'bounds':b.projection_outline.bounds}
''')
        assert not value['error'], value
        if value['active'] and value['ready'] and not value['preparing']:
            assert value['entity'] and value['bounds'], 'Create a nonempty projection first: %r' % value
            return value
        time.sleep(.25)
    raise AssertionError('Projection did not become ready: %r' % value)


def frame_projection(offset):
    # Keep the player in the same loaded area, so this must be a nearby projection.
    game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
origin,size=b.projection_outline.bounds
center=tuple(origin[i]+size[i]*.5 for i in range(3))
offset=''' + repr(tuple(offset)) + '''
pos=tuple(center[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(-v for v in offset))
cam.DepartCamera()
cam.SetCameraPos(pos)
cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True
''')
    time.sleep(.5)


def restore(saved, camera_changed):
    try:
        game('s.set_biome(' + repr(saved['biome']) + ')\ns.set("page",' + repr(saved['page']) + ')\n_result=True')
    finally:
        try:
            if camera_changed:
                game('''cam=s.bridge.factory.CreateCamera(s.bridge.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.SetCameraRotation(''' + repr(tuple(saved['rotation'])) + ''')
cam.LockModCameraPitch(''' + repr(saved['pitch']) + ''')
cam.LockModCameraYaw(''' + repr(saved['yaw']) + ''')
_result=True
''')
        finally:
            if saved['workspace']:
                open_workspace()


def main():
    args = arguments()
    sample = game('''b=s.bridge
pos=''' + repr(tuple(args.biome_pos) if args.biome_pos else None) + '''
if pos is None: pos=b.player_origin()
_result={'position':pos,'biome':b.factory.CreateBiome(b.level).GetBiomeName(pos)}
''')
    assert sample['biome'], 'No biome available at the sample position: %r' % sample
    if args.require_biome:
        ui.check('sample is in ' + args.require_biome,
                 sample['biome'].split(':')[-1] == args.require_biome.split(':')[-1])
    projection = wait_projection()
    projection_biome = game('''import math
b=s.bridge
origin,size=b.projection_outline.bounds
pos=tuple(int(math.floor(origin[i]+size[i]*.5)) for i in range(3))
_result={'position':pos,'biome':b.factory.CreateBiome(b.level).GetBiomeName(pos)}
''')
    if args.require_biome:
        ui.check('projection centre is in ' + args.require_biome,
                 bool(projection_biome['biome']) and
                 projection_biome['biome'].split(':')[-1] == args.require_biome.split(':')[-1])
    saved = game('''from modern_projection.pyreact import navigator
cam=s.bridge.factory.CreateCamera(s.bridge.level)
_result={'page':s.page,'biome':s.editor.document.biome,
         'workspace':navigator.contains('modern_projection_workspace'),
         'rotation':cam.GetCameraRotation(),
         'pitch':cam.IsModCameraLockPitch(),'yaw':cam.IsModCameraLockYaw()}
''')
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd']), 'Managed game window unavailable'
    captures = []
    try:
        if saved['workspace']:
            game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
            time.sleep(.5)
        if args.camera_offset is not None:
            frame_projection(args.camera_offset)
        for biome in COLORS if args.colors else (saved['biome'],):
            game('s.set_biome(' + repr(biome) + ')\n_result=True')
            wait_projection()
            # Tint updates reach native rendering on subsequent frames.
            time.sleep(.5)
            name = args.name + ('_' + biome if args.colors else '')
            snapshot(name)
            captures.append(name + '.jpg')
    finally:
        restore(saved, args.camera_offset is not None)
    report = {'sample': sample, 'projection_biome': projection_biome,
              'projection': projection, 'captures': captures}
    (ui.OUT / (args.name + '.json')).write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
