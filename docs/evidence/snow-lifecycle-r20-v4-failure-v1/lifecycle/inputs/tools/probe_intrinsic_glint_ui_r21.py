"""Compare native ItemRenderer glint flags on one removable diagnostic page.

Paired false/true controls first establish whether the API preserves inherent
item glint at all. No glint classification is inferred from animation alone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from capture_native_window import capture
from probe_intrinsic_glint_r21 import CASES, ROOT, VERSION, validate_private_session

sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from _session import load_session

PREPARE = '''import json, math, sys
import mod.client.extraClientApi as intrinsic_ui_api
assert intrinsic_ui_api.GetEngineVersion() == '3.10.0.420447'
assert not hasattr(sys, '_intrinsic_glint_ui_r21')
intrinsic_ui_node = intrinsic_ui_api.GetTopUINode()
assert intrinsic_ui_node is not None
intrinsic_ui_game = intrinsic_ui_api.GetEngineCompFactory().CreateGame(intrinsic_ui_api.GetLevelId())
intrinsic_ui_screen = intrinsic_ui_game.GetScreenSize()
intrinsic_ui_physical = intrinsic_ui_game.GetScreenViewInfo()
intrinsic_ui_columns = LAYOUT.get('columns', 8)
intrinsic_ui_top = LAYOUT.get('top', 8.)
intrinsic_ui_row_count = int(math.ceil(len(CASES) * 2. / intrinsic_ui_columns))
intrinsic_ui_cell_width = min(56., (intrinsic_ui_screen[0] - 16.) / intrinsic_ui_columns)
intrinsic_ui_cell_height = min(50., (intrinsic_ui_screen[1] - intrinsic_ui_top - 8.) / intrinsic_ui_row_count)
intrinsic_ui_icon = min(40., intrinsic_ui_cell_width - 6., intrinsic_ui_cell_height - 8.)
assert intrinsic_ui_icon >= 18., (intrinsic_ui_screen, intrinsic_ui_icon)
intrinsic_ui_saved = {'node': intrinsic_ui_node, 'controls': [], 'items': [],
                      'top_ui': intrinsic_ui_api.GetTopUI(), 'screen': intrinsic_ui_screen,
                      'physical_screen': intrinsic_ui_physical, 'rows': [],
                      'control_count': LAYOUT.get('control_count')}
sys._intrinsic_glint_ui_r21 = intrinsic_ui_saved
intrinsic_ui_background = intrinsic_ui_node.CreateChildControl(
    'PyreactBase.image', 'intrinsic_glint_r21_background', None, True)
assert intrinsic_ui_background is not None
intrinsic_ui_saved['controls'].append(intrinsic_ui_background)
intrinsic_ui_background.SetPosition((0., 0.))
intrinsic_ui_background.SetSize(tuple(intrinsic_ui_screen))
intrinsic_ui_background.SetLayer(LAYOUT.get('layer', 1000))
intrinsic_ui_background.asImage().SetSprite('textures/ui/white')
intrinsic_ui_background.asImage().SetSpriteColor((.08, .08, .08))
intrinsic_ui_background.SetVisible(True)
for intrinsic_ui_index, (intrinsic_ui_name, intrinsic_ui_aux, intrinsic_ui_enchanted) in enumerate(CASES):
 for intrinsic_ui_flag in (False, True):
  intrinsic_ui_slot = intrinsic_ui_index * 2 + int(intrinsic_ui_flag)
  intrinsic_ui_x = 8. + intrinsic_ui_slot % intrinsic_ui_columns * intrinsic_ui_cell_width
  intrinsic_ui_y = intrinsic_ui_top + intrinsic_ui_slot // intrinsic_ui_columns * intrinsic_ui_cell_height
  intrinsic_ui_control = intrinsic_ui_node.CreateChildControl(
      'PyreactBase.item', 'intrinsic_glint_r21_item_' + str(intrinsic_ui_slot), None, True)
  assert intrinsic_ui_control is not None
  intrinsic_ui_saved['controls'].append(intrinsic_ui_control)
  intrinsic_ui_saved['items'].append(intrinsic_ui_control)
  intrinsic_ui_control.SetPosition((intrinsic_ui_x, intrinsic_ui_y))
  intrinsic_ui_control.SetSize((intrinsic_ui_icon, intrinsic_ui_icon))
  intrinsic_ui_control.SetVisible(True)
  intrinsic_ui_layer = LAYOUT.get('item_layers', [LAYOUT.get('layer', 1000) + 2] * len(CASES))[intrinsic_ui_index]
  intrinsic_ui_control.SetLayer(intrinsic_ui_layer)
  intrinsic_ui_data = {'ench': [{'id': {'__type__': 2, '__value__': 9},
                              'lvl': {'__type__': 2, '__value__': 1}}]} if intrinsic_ui_enchanted else None
  intrinsic_ui_returned = intrinsic_ui_control.asItemRenderer().SetUiItem(
      intrinsic_ui_name, intrinsic_ui_aux, intrinsic_ui_flag, intrinsic_ui_data)
  intrinsic_ui_saved['rows'].append({'index': intrinsic_ui_index, 'slot': intrinsic_ui_slot,
      'name': intrinsic_ui_name, 'aux': intrinsic_ui_aux, 'is_enchanted_argument': intrinsic_ui_flag,
      'real_ench_user_data': intrinsic_ui_enchanted, 'set_returned': intrinsic_ui_returned,
      'layer': intrinsic_ui_layer,
      'bounds': (intrinsic_ui_x, intrinsic_ui_y, intrinsic_ui_icon, intrinsic_ui_icon),
      'ui_readback': intrinsic_ui_control.asItemRenderer().GetUiItem()})
_result = json.dumps(dict((key, value) for key, value in intrinsic_ui_saved.items()
                         if key not in ('node', 'controls', 'items')))
'''

STATE = '''import json, sys
saved = sys._intrinsic_glint_ui_r21
_result = json.dumps({'top_ui': intrinsic_ui_api.GetTopUI(),
 'screen': intrinsic_ui_game.GetScreenSize(), 'physical_screen': intrinsic_ui_game.GetScreenViewInfo(),
 'items': [{'position': control.GetPosition(), 'size': control.GetSize(),
            'item': control.asItemRenderer().GetUiItem()} for control in saved['items']]})
'''

RESTORE = '''import json, sys
saved = getattr(sys, '_intrinsic_glint_ui_r21', None)
if saved is None:
 _result = json.dumps({'restored': True, 'owned_controls': 0})
else:
 intrinsic_ui_removed = []
 for control in reversed(saved['controls']):
  control.SetVisible(False)
  intrinsic_ui_removed.append(saved['node'].RemoveChildControl(control))
 intrinsic_ui_restored = all(intrinsic_ui_removed)
 if intrinsic_ui_restored:
  del sys._intrinsic_glint_ui_r21
 _result = json.dumps({'restored': intrinsic_ui_restored, 'remove_returns': intrinsic_ui_removed,
                       'owned_controls': len(intrinsic_ui_removed)})
'''


def run(session, owner, output, wgc, cases=CASES, layout=None):
    manifest = load_session(session, owner, live=True)
    validate_private_session(manifest)
    output.mkdir(parents=True, exist_ok=False)
    os.environ.update(MCDEV_SESSION_FILE=str(session), MCDEV_OWNER=owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'engine_version': VERSION, 'owner': owner,
              'session_id': manifest['id'], 'completed': False, 'captures': [],
              'cleanup_errors': [], 'visual_qualification': False,
              'classification': 'unresolved_until_controls_and_pixels_are_reviewed',
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path = output / 'report.json'

    def save():
        path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    def decode(reply):
        if reply.get('isError'):
            raise RuntimeError(reply)
        value = return_value(reply)
        return json.loads(value) if isinstance(value, str) else value

    code = 'CASES = ' + repr(cases) + '\nLAYOUT = ' + repr(layout or {}) + '\n' + PREPARE
    report['submitted_prepare_code'] = code
    report['submitted_prepare_sha256'] = hashlib.sha256(code.encode('ascii')).hexdigest()
    save()
    with Client(timeout=30) as client:
        def execute(code):
            return decode(client.call('execute_code', {'code': code, 'is_client': True,
                                                       'direct_return': True}))

        try:
            report['prepared'] = execute(code)
            save()
            time.sleep(.5)
            for phase in range(3):
                if phase:
                    time.sleep(.45)
                before = execute(STATE)
                receipt = capture(session, owner, output / ('native-ui-phase-' + str(phase) + '.png'), wgc)
                after = execute(STATE)
                if before != after:
                    raise RuntimeError('Native UI controls or screen metrics changed during capture')
                report['captures'].append({'phase': phase, 'state': before,
                                           'state_after': after, 'receipt': receipt})
                save()
            report['completed'] = True
        finally:
            try:
                report['restoration'] = execute(RESTORE)
                if report['restoration'].get('restored') is not True:
                    report['cleanup_errors'].append('Native controls did not all remove')
            except (RuntimeError, OSError, ValueError) as error:
                report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
            save()
    print(json.dumps({'output': str(path), 'completed': report['completed'],
                      'cleanup_errors': report['cleanup_errors']}))
    if report['cleanup_errors']:
        raise RuntimeError('Native diagnostic page restoration failed')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    args = parser.parse_args()
    run(args.session, args.owner, args.output, args.wgc)
