"""Execute exact proposed Scene callback AST with both old and new profiles."""
import ast
from collections import namedtuple
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from candidate_geometry import ui_geometry_for_gui

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROJECT = ROOT / '.runtime/projects/water-r27-merged-flow-editor-v1'
View = namedtuple('View', 'position size distance clipped')


def callback(path, profile, view, gui):
    node = next(node for node in ast.walk(ast.parse(path.read_text(encoding='utf8')))
                if isinstance(node, ast.FunctionDef) and node.name == 'liquid_view')
    module = ast.Module(body=[node], type_ignores=[])
    env = dict(liquid_profile=profile, group_view=lambda *unused: view,
               camera=None, session=SimpleNamespace(scene_origin=(0, 0, 0), scene_size=(10, 8, 10)),
               native_width=340.625, native_height=159.75, cell_unit=52.9092,
               Theme=SimpleNamespace(native_gui_scale=gui))
    exec(compile(module, str(path), 'exec'), env)
    return env['liquid_view']((0, 0, 0))


def main():
    output = WORK / 'callback-controls-v1.json'
    assert not output.exists()
    original = PROJECT / 'behavior_pack/modern_projection/projection/scene.py'
    proposed = WORK / 'proposed_scene.py'
    profiles = [SimpleNamespace(ui_offset=lambda size: (0., min(size) / 4.)),
                SimpleNamespace(ui_offset_for_gui=lambda size, gui: (0., min(size) / gui))]
    legacy = []
    new = []
    for gui in (1., 2., 3., 4.):
        for position, size in (((0., 0.), (366.6114, 413.8420)), ((-77.9592, 0.), (418.5842, 164.7063)),
                               ((-14., -36.), (120., 150.))):
            view = View(position, size, -2., False)
            for index, profile in enumerate(profiles):
                before, after = callback(original, profile, view, gui), callback(proposed, profile, view, gui)
                assert before == after
                legacy.append({'gui': gui, 'profile_index': index, 'equal': True})
            profile = SimpleNamespace(ui_geometry_for_gui=ui_geometry_for_gui)
            measured = callback(proposed, profile, view, gui)
            expected = ui_geometry_for_gui(position, size, gui)
            assert (measured.position, measured.size) == expected and measured.distance == view.distance and measured.clipped == view.clipped
            new.append({'gui': gui, 'equal': True})
    result = {'schema': 1, 'passed': True, 'legacy_profile_comparisons': len(legacy),
              'new_callback_comparisons': len(new), 'legacy_fallback': legacy, 'new_callback': new,
              'proposed_scene_sha256': hashlib.sha256(proposed.read_bytes()).hexdigest(),
              'actual_Scene_function_AST_executed': True, 'SDK_or_MC_called': False}
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key not in ('legacy_fallback', 'new_callback')}, indent=2))


if __name__ == '__main__':
    main()
