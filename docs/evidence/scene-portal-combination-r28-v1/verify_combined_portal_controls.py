"""Actual Py2/Py3 offline compilation and candidate callback controls.

The actual pure cell/profile modules execute. Only portal_view is extracted
from Scene; full Scene/client modules never import. Group-view and GUI values
are explicit fake boundaries. These controls are not native/cold evidence.
"""
from __future__ import print_function
import argparse
import ast
import collections
import gzip
import hashlib
import json
import os
import sys
import textwrap
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if sys.version_info[0] < 3:
    HERE = HERE.decode(sys.getfilesystemencoding() or 'mbcs')
PREFIX = 'behavior_pack/modern_projection/projection/'
sys.dont_write_bytecode = True


def raw(relative):
    with open(os.path.join(HERE, relative.replace('/', os.sep)), 'rb') as source:
        return source.read()


def read(relative):
    return json.loads(raw(relative))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_function(source, name):
    text = source.decode('utf8')
    matches = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(matches) == 1, name
    start = matches[0].lineno - 1
    lines = text.splitlines(True)
    indentation = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and len(line) - len(line.lstrip()) <= indentation:
            break
        end += 1
    return textwrap.dedent(''.join(lines[start:end]))


def load_profile(variant):
    package_name = 'offline_portal_' + variant
    package = types.ModuleType(package_name)
    package.__path__ = []
    sys.modules[package_name] = package
    for name, relative in [('cell', 'support/cell.py'), ('portal_profile', variant + '/' + PREFIX + 'portal_profile.py')]:
        module_name = package_name + '.' + name
        module = types.ModuleType(module_name)
        module.__package__ = package_name
        module.__file__ = os.path.join(HERE, relative)
        sys.modules[module_name] = module
        eval(compile(raw(relative), module.__file__, 'exec'), module.__dict__)
    return sys.modules[package_name + '.portal_profile']


View = collections.namedtuple('View', 'position size distance clipped retained')


def callback(source, profile, gui, view):
    calls = []
    camera = object()
    session = types.ModuleType('explicit_fake_session')
    session.scene_origin = (3, 5, 7)
    session.scene_size = (11, 13, 17)
    theme = types.ModuleType('explicit_fake_theme')
    theme.native_gui_scale = gui

    def group_view(*arguments):
        calls.append(arguments)
        assert arguments == ((19, 23, 29), camera, session.scene_origin, session.scene_size, (640., 360.), 16.)
        return view

    namespace = {'group_view': group_view, 'camera': camera, 'session': session,
                 'native_width': 640., 'native_height': 360., 'cell_unit': 16.,
                 'portal_profile': profile, 'Theme': theme}
    eval(compile(source, '<actual-candidate-portal-view>', 'exec'), namespace)
    return namespace['portal_view'], theme, calls


def main(args):
    assert not os.path.exists(args.output)
    provenance = read('provenance.json')
    compiled = []
    for variant in ('baseline', 'combined'):
        for name in ('portal_profile.py', 'scene.py'):
            relative = variant + '/' + PREFIX + name
            data = raw(relative)
            expected = next(row for row in provenance['files'] if row['path'] == PREFIX + name)
            assert sha(data) == expected['base_sha256' if variant == 'baseline' else 'candidate_sha256']
            compile(data, relative, 'exec')
            compiled.append({'path': relative, 'sha256': sha(data)})
    compile(raw('support/cell.py'), 'support/cell.py', 'exec')
    assert sha(raw('support/cell.py')) == provenance['cell_sha256']
    assert sha(raw('combined.patch')) == provenance['patch_sha256']

    baseline = load_profile('baseline')
    candidate = load_profile('combined')
    base_profile = baseline.PortalProfile()
    profile = candidate.PortalProfile()
    assert base_profile.__dict__ == profile.__dict__
    assert not hasattr(base_profile, 'ui_offset_for_gui')
    assert 'ui_offset' not in profile.__dict__ and 'ui_offset_for_gui' not in profile.__dict__
    base_scene = source_function(raw('baseline/' + PREFIX + 'scene.py'), 'portal_view')
    changed_scene = source_function(raw('combined/' + PREFIX + 'scene.py'), 'portal_view')
    book_scene = source_function(raw('baseline/' + PREFIX + 'scene.py'), 'book_view')
    assert ast.dump(ast.parse(changed_scene)) == ast.dump(ast.parse(book_scene.replace('book_view', 'portal_view').replace('book_profile', 'portal_profile')))

    # Check the full real profile AST differs only by the new GUI-aware method.
    base_tree = ast.parse(raw('baseline/' + PREFIX + 'portal_profile.py'))
    changed_tree = ast.parse(raw('combined/' + PREFIX + 'portal_profile.py'))
    klass = next(node for node in changed_tree.body if isinstance(node, ast.ClassDef) and node.name == 'PortalProfile')
    added = [node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == 'ui_offset_for_gui']
    assert len(added) == 1
    klass.body.remove(added[0])
    assert ast.dump(base_tree) == ast.dump(changed_tree)

    view = View((11., 23.), (368., 162.), -7., False, 'unchanged view fields')
    formula_rows = []
    for gui in (1, 2, 3, 4, 5, 2., 3., 4.):
        inherited = base_profile.ui_offset(view.size)
        actual = profile.ui_offset_for_gui(view.size, gui)
        assert profile.ui_offset(view.size) == inherited
        assert actual == (0., min(view.size) / float(gui))
        fn, theme, calls = callback(changed_scene, profile, gui, view)
        changed = fn((19, 23, 29))
        assert changed.position == (view.position[0] + actual[0], view.position[1] + actual[1])
        assert changed._replace(position=view.position) == view and len(calls) == 1
        old_fn, unused, old_calls = callback(base_scene, base_profile, gui, view)
        original = old_fn((19, 23, 29))
        expected_delta = min(view.size) * (1. / gui - 1. / 4.)
        assert abs((changed.position[1] - original.position[1]) - expected_delta) < 1e-12
        if gui == 4:
            assert changed == original
        formula_rows.append({'gui': gui, 'legacy_offset': inherited, 'candidate_offset': actual,
                             'expected_y_delta': expected_delta, 'Scene_called': True, 'GUI4_equal': gui == 4})

    rejected = []
    for label, gui in [('true', True), ('false', False), ('zero', 0), ('negative', -1),
                       ('fraction', 2.5), ('inf', float('inf')), ('negative_inf', -float('inf')),
                       ('nan', float('nan')), ('text', '2'), ('none', None), ('list', []), ('dict', {})]:
        try:
            profile.ui_offset_for_gui(view.size, gui)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError('Invalid GUI accepted: ' + label)

    class Legacy(object):
        def __init__(self):
            self.calls = []

        def ui_offset(self, size):
            self.calls.append(size)
            return (13., 17.)

    class ExplicitNone(Legacy):
        ui_offset_for_gui = None

    class Hook(Legacy):
        def __init__(self):
            Legacy.__init__(self)
            self.hook_calls = []

        def ui_offset_for_gui(self, size, gui):
            self.hook_calls.append((size, gui))
            return (29., 31.)

    dispatch_rows = []
    for gui in (2, 3, 4):
        for kind in (Legacy, ExplicitNone, Hook):
            control = kind()
            fn, theme, calls = callback(changed_scene, control, gui, view)
            result = fn((19, 23, 29))
            expected = (40., 54.) if kind is Hook else (24., 40.)
            assert result.position == expected and result._replace(position=view.position) == view
            if kind is Hook:
                assert control.hook_calls == [(view.size, gui)] and not control.calls
            else:
                assert control.calls == [view.size]
            dispatch_rows.append({'gui': gui, 'profile': kind.__name__, 'position': result.position,
                                  'legacy_calls': len(control.calls),
                                  'hook_calls': len(getattr(control, 'hook_calls', []))})

    # One mounted callback must read each newly supplied GUI, rather than cache.
    hook = Hook()
    fn, theme, calls = callback(changed_scene, hook, 2, view)
    for gui in (2, 3, 4, 2):
        theme.native_gui_scale = gui
        fn((19, 23, 29))
    assert hook.hook_calls == [(view.size, gui) for gui in (2, 3, 4, 2)] and not hook.calls

    # These are historical V4 sizes/formulas, not a native run of the candidate.
    report_path = os.path.join(HERE, '..', '..', '..', 'docs', 'evidence', 'portal-gui-anchor-r28-v4', 'raw', 'report.json.gz')
    with gzip.open(report_path, 'rb') as source:
        report_raw = source.read()
    assert sha(report_raw) == '51c566cf095528f24c1a2878db9cac26fa48ac9262f31a9e6e40ccd6081d1513'
    report = json.loads(report_raw)
    historical_formula_rows = []
    for family in report['families']:
        for gui in (2, 3, 4):
            stages = {stage['stage']: stage['after'] for stage in family['stages'] if stage['gui'] == gui}
            for a in stages['a']['portal_geometry']:
                b = next(geo for geo in stages['b']['portal_geometry'] if geo['key'] == a['key'])
                size = tuple(a['size'])
                offset = profile.ui_offset_for_gui(size, gui)
                assert tuple(b['offset']) == offset
                underlying = tuple(a['geometry'][0][i] - a['offset'][i] for i in range(2))
                sample = View(underlying, size, a['distance'], a['clipped'], a['key'])
                fn, unused, calls = callback(changed_scene, profile, gui, sample)
                output = fn((19, 23, 29))
                residual = max(abs(output.position[i] - b['geometry'][0][i]) for i in range(2))
                assert residual < 1e-10
                historical_formula_rows.append({'family': family['family'], 'gui': gui, 'key': a['key'],
                                                'formula_matches_recorded_B_offset': True,
                                                'Scene_cache_formula_residual': residual,
                                                'candidate_native_tested': False})
    assert len(historical_formula_rows) == 21

    result = {
        'passed': True, 'executed_source': 'combined private source, not sealed portal-only candidate',
        'composition_base': 'b70ce7bf13ad6a4472f2b089ac812c162b174861', 'python': list(sys.version_info[:3]), 'interpreter': sys.executable,
        'interpreter_sha256': sha(open(sys.executable, 'rb').read()),
        'actual_files_compiled': compiled, 'pure_cell_compiled_and_executed': True,
        'actual_baseline_candidate_profiles_executed': True, 'profile_metadata_AST_unchanged': True,
        'actual_portal_view_extracted_and_called': True, 'actual_Scene_module_imported': False,
        'Scene_hook_matches_existing_book_AST': True,
        'formula_rows': formula_rows, 'invalid_GUI_rejected': rejected, 'dispatch_rows': dispatch_rows,
        'same_callback_GUI_changes_forwarded': [2, 3, 4, 2],
        'historical_V4_formula_rows': historical_formula_rows,
        'fake_boundaries': ['group_view return data', 'camera/session closure objects', 'Theme.native_gui_scale'],
        'native_slot_or_GPU_called': False, 'MC_started': False, 'MC_connected': False,
        'production_modified': False, 'qualification_awarded': False, 'candidate_cold_tested': False,
        'manual_issues_closed': 0,
    }
    with open(args.output, 'w') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'passed': True, 'python': result['python'], 'compiled_actual_files': len(compiled),
                      'formula_rows': len(formula_rows), 'dispatch_rows': len(dispatch_rows),
                      'historical_V4_formula_rows': len(historical_formula_rows),
                      'invalid_GUI_rejected': len(rejected), 'MC_started': False, 'candidate_cold_tested': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    main(parser.parse_args())
