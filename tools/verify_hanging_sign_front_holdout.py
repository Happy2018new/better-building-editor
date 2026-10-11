"""Frozen hanging-sign front holdout with camera/style records around every frame."""
import hashlib
import json
import os
import sys
from pathlib import Path

import verify_sign_visuals as signs
from verify_shulker_orientations import matching_camera


CAPTURE_STATE = '''from modern_projection.projection.cell import foreground,actor_data
from modern_projection.projection.entity_render import native_actor
from modern_projection.projection.debug_sign_blueprints import VISUAL_CASE
focus=VISUAL_CASE['focus']
doc=s.editor.document
value=doc.get(focus)
cam=b.factory.CreateCamera(b.level)
row=next(row for row in sys._native_sign_probe_rows if row['name']=='minecraft:oak_hanging_sign')
pos=tuple(row['pos'])
data=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(pos,pos,False).SerializeBlockPalette()
native=dict((key,value) for key,value in data.items() if key not in ('common','extra','states','extraStates'))
for field in ('common','extra','states','extraStates'):
 native[field]=[{'material':material,'value':field_value} for material,field_value in data.get(field,{}).items()]
_result=json.dumps({'camera':{'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()},
 'editor_camera':{'pose':s.camera_pose,'pivot':s.camera_pivot,'pan':s.camera_pan},
 'document':doc.to_data(),'renderer':native_actor(foreground(value),actor_data(value)),
 'native_position':pos,'native_palette':native,
 'projection':{'active':s.projection_active,'mesh':b.projection_mesh},
 'workspace_open':navigator.contains('modern_projection_workspace')})
'''

BaseSignCheck = signs.SignCheck


class ControlledSignCheck(BaseSignCheck):
    def __init__(self, *args, **kwargs):
        kwargs['native_capture_helper'] = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER'])
        BaseSignCheck.__init__(self, *args, **kwargs)

    def capture(self, label, tree=None):
        before = self.run(CAPTURE_STATE)
        try:
            result = BaseSignCheck.capture(self, label, tree)
        except Exception:
            path = self.output.parent / (label + '_failed_capture_control_state.json')
            path.write_text(json.dumps({'before': before}, indent=2) + '\n', encoding='utf-8')
            raise
        assert result['capture']['backend'] == 'Windows.Graphics.Capture', result
        after = self.run(CAPTURE_STATE)
        camera_unchanged = matching_camera(after['camera'], {
            'position': before['camera']['position'],
            'rotation': [before['camera']['rotation'][0], before['camera']['rotation'][1] - 180.]})
        noncamera_unchanged = {key: value for key, value in before.items() if key != 'camera'} == {
            key: value for key, value in after.items() if key != 'camera'}
        result['controlled_state_before'] = before
        result['controlled_state_after'] = after
        result['camera_unchanged'] = camera_unchanged
        result['style_source_and_editor_state_unchanged'] = noncamera_unchanged
        assert camera_unchanged and noncamera_unchanged, (label, before, after)
        return result


def record_file(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    expected = ['--case', 'hanging_front_back', '--view', 'front', '--response',
                'wood_composite', '--native-resolution']
    args = sys.argv[1:]
    if len(args) != 1:
        raise SystemExit('Usage: verify_hanging_sign_front_holdout.py <output-directory>')
    capture_exe = os.environ.get('MCDEV_NATIVE_CAPTURE_EXE')
    if not capture_exe or not Path(capture_exe).is_file():
        raise SystemExit('Set MCDEV_NATIVE_CAPTURE_EXE to the verified WGC executable before setup')
    capture_helper = os.environ.get('MCDEV_NATIVE_CAPTURE_HELPER')
    if not capture_helper or not Path(capture_helper).is_file() or Path(capture_helper).name != 'capture_native_window.py':
        raise SystemExit('Bind MCDEV_NATIVE_CAPTURE_HELPER to the reviewed capture_native_window.py before setup')
    output = Path(args[0])
    if output.exists():
        raise SystemExit('Holdout output must be a new directory')
    production = []
    for directory in ('behavior_pack', 'resource_pack'):
        production.extend(record_file(path) for path in sorted((signs.ROOT / directory).rglob('*'))
                          if path.is_file())
    tool_files = [Path(__file__), signs.ROOT / 'tools/verify_sign_visuals.py',
                 signs.ROOT / 'tools/verify_shulker_orientations.py',
                 signs.ROOT / 'tools/context_test_environment.py',
                 Path(capture_helper), Path(capture_exe)]
    frozen = {'schema': 1, 'scope': 'Hanging front only; frozen files; no chest candidate production resources',
              'tools': [record_file(path) for path in tool_files], 'production': production,
              'response': 'Existing unmodified wood_composite implementation',
              'limits': {'minimum_difference': 20, 'minimum_color_response': 20,
                         'normalized_glyph_iou': .45, 'layout_center': .1, 'layout_size': .2}}
    output.mkdir(parents=True)
    (output / 'frozen_source.json').write_text(json.dumps(frozen, indent=2) + '\n', encoding='utf-8')
    signs.SignCheck = ControlledSignCheck
    sys.argv = [str(signs.ROOT / 'tools/verify_sign_visuals.py'), str(output)] + expected
    try:
        signs.main()
    finally:
        unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                        for row in production + frozen['tools'])
        (output / 'frozen_source_after.json').write_text(
            json.dumps({'production_and_tools_unchanged': unchanged}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
