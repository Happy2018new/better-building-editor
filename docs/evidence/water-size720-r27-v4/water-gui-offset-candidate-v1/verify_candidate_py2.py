"""Execute private candidate AST in Python2 with explicit SDK/UI boundaries."""
import ast
from collections import namedtuple
from functools import partial
import hashlib
import json
import os
import sys
import types

WORK = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(WORK)))
PREFIX = 'behavior_pack/modern_projection/projection/'
BASE = os.path.join(ROOT, '.runtime/projects/water-r27-anchor-diagnostic-v1')
CANDIDATE = os.path.join(WORK, 'candidate')
CONTROLS = []


def read(root, name):
    return open(os.path.join(root, PREFIX + name), 'rb').read()


def definitions(raw, kind, name):
    return [node for node in ast.walk(ast.parse(raw)) if isinstance(node, kind) and node.name == name]


def execute(node, namespace):
    module = ast.Module(body=[node])
    ast.fix_missing_locations(module)
    exec compile(module, '<actual-candidate-ast>', 'exec') in namespace
    return namespace[node.name]


def check(name, condition, detail=None):
    assert condition, (name, detail)
    CONTROLS.append({'name': name, 'passed': True, 'detail': detail})


class Box(object):
    def __init__(self, current=None):
        self.current = current


class FakeGame(object):
    def __init__(self):
        self.logical = (499, 277)
        self.physical = (1995, 1107, 0, 0)
        self.calls = {'GetScreenViewInfo': 0, 'GetScreenSize': 0}

    def GetScreenViewInfo(self):
        self.calls['GetScreenViewInfo'] += 1
        return self.physical

    def GetScreenSize(self):
        self.calls['GetScreenSize'] += 1
        return self.logical


class FakeAPI(object):
    def __init__(self, game):
        self.game = game

    def GetEngineCompFactory(self):
        return self

    def CreateGame(self, level):
        assert level == 'synthetic-level'
        return self.game

    def GetLevelId(self):
        return 'synthetic-level'


def main():
    output = sys.argv[1]
    assert not os.path.exists(output), 'Keep prior controls immutable'
    binding = json.load(open(os.path.join(WORK, 'candidate-v1.json'), 'rb'))
    for relative, row in binding['changed_files'].items():
        raw = open(os.path.join(CANDIDATE, relative), 'rb').read()
        assert hashlib.sha256(raw).hexdigest() == row['candidate_sha256']
        compile(raw, relative, 'exec')
    game = FakeGame()
    api = FakeAPI(game)
    theme = execute(definitions(read(CANDIDATE, 'widgets.py'), ast.ClassDef, 'Theme')[0],
                    {'Color': lambda value: value, 'clientApi': api})
    changes = []
    def listener(value):
        changes.append(value)
    theme.listeners.add(listener)
    for logical, physical, gui in [((499, 277), (1995, 1107, 0, 0), 4.),
                                   ((533, 300), (1600, 900, 0, 0), 3.),
                                   ((641, 360), (1281, 720, 0, 0), 2.)]:
        game.logical, game.physical = logical, physical
        theme.configure(3., True)
        check('Theme GUI refresh before same-font early-return: %s' % gui,
              theme.native_gui_scale == gui and theme.input_font_scale == 5.)
    check('Same-font refresh preserves listener tuple semantics', len(changes) == 1,
          {'notifications': len(changes), 'sdk_calls': dict(game.calls)})
    check('Exactly one existing pair of GUI SDK reads per configure',
          game.calls == {'GetScreenViewInfo': 3, 'GetScreenSize': 3})

    package = types.ModuleType('r27_candidate')
    package.__path__ = []
    sys.modules[package.__name__] = package
    def module(name, **values):
        item = types.ModuleType(package.__name__ + '.' + name)
        item.__dict__.update(values)
        sys.modules[item.__name__] = item
        setattr(package, name, item)
        return item
    module('liquid_product_qualification_data', PRODUCT_QUALIFIED=False)
    module('liquid_render_target_data', TARGET_ENGINE_VERSION='synthetic-engine')
    module('storage', integer_types=(int, long))
    legacy_namespace = {}
    for name in ('ui_pose', 'ui_offset'):
        execute(definitions(read(BASE, 'liquid_deployment.py'), ast.FunctionDef, name)[0], legacy_namespace)
    module('liquid_deployment', **legacy_namespace)
    class Product(object):
        def __init__(self, resources, ui_pose, ui_offset):
            self.resources, self.ui_pose, self.ui_offset = resources, ui_pose, ui_offset
    module('liquid_product_profile', ProductLiquidProfile=Product)
    module('liquid_product_resource_data', PRODUCT_RESOURCES={'models': 'dynamic'}, FROZEN_PRODUCT_MODELS='frozen')
    deployment = module('liquid_product_deployment')
    deployment.__package__ = package.__name__
    exec compile(read(CANDIDATE, 'liquid_product_deployment.py'), '<actual-product-deployment>', 'exec') in deployment.__dict__
    offset = deployment.ui_offset_for_gui
    for size in ((400., 300.), (220., 480.), (171.74, 379.24)):
        for gui in (2, 3., 4L):
            check('Offset exact integer GUI %s size %s' % (gui, size),
                  offset(size, gui) == (0., min(size) / float(gui)))
    rejected = []
    for gui in (None, True, False, '2', 0, -2, 2.5, float('nan'), float('inf'), -float('inf')):
        try:
            offset((400., 300.), gui)
        except ValueError as error:
            rejected.append(type(gui).__name__)
        else:
            raise AssertionError('Invalid GUI accepted: %r' % (gui,))
    check('Unknown/noninteger/nonfinite GUI fails closed without quarter fallback', len(rejected) == 10)
    profile = deployment.candidate_profile()
    frozen = deployment.candidate_profile(frozen=True)
    check('Both explicit Product profiles own new callback; legacy callback preserved',
          profile.ui_offset_for_gui is offset and frozen.ui_offset_for_gui is offset
          and profile.ui_offset is legacy_namespace['ui_offset']
          and profile.resources['models'] == 'dynamic' and frozen.resources['models'] == 'frozen')
    check('Production false gate still refuses selection', deployment.production_profile('synthetic-engine') is None)

    View = namedtuple('View', 'position size')
    source_view = View((12., 24.), (400., 300.))
    calls_before = dict(game.calls)
    env = {'Theme': theme, 'liquid_profile': profile, 'camera': None,
           'session': type('Session', (), {'scene_origin': None, 'scene_size': None})(),
           'native_width': 400, 'native_height': 300, 'cell_unit': 24,
           'group_view': lambda *args: source_view}
    liquid_view = execute(definitions(read(CANDIDATE, 'scene.py'), ast.FunctionDef, 'liquid_view')[0], env)
    for gui in (4., 3., 2.):
        theme.native_gui_scale = gui
        views = [liquid_view((0, 0, 0)) for unused in range(100)]
        check('Actual water Scene branch uses cached GUI %s' % gui,
              all(view.position == (12., 24. + 300. / gui) and view.size == source_view.size for view in views))
    check('Hundreds of water group reads add no FFI calls', game.calls == calls_before)
    legacy = type('Legacy', (), {})()
    legacy.ui_offset = legacy_namespace['ui_offset']
    env['liquid_profile'] = legacy
    check('Actual water Scene branch retains legacy profile callback', liquid_view(None).position == (12., 99.))
    for name in ('item_view', 'cauldron_view', 'portal_view', 'book_view'):
        before = definitions(read(BASE, 'scene.py'), ast.FunctionDef, name)
        after = definitions(read(CANDIDATE, 'scene.py'), ast.FunctionDef, name)
        check('Other profile AST unchanged: ' + name,
              len(before) == len(after) == 1 and ast.dump(before[0]) == ast.dump(after[0]))

    # Execute the unchanged real resize callback and its scheduled settle chain.
    pending, measured_pixels, measured_screen = Box(False), Box((1281, 720)), Box((641, 360))
    queue, resize_events = [], []
    class Bridge(object):
        def later(self, delay, callback):
            queue.append((delay, callback))
    fake_session = type('Session', (), {'bridge': Bridge()})()
    def rendered():
        theme.configure(3., True)
        resize_events.append(('configured', theme.native_gui_scale))
    def set_screen(size):
        resize_events.append(('set_screen', size))
        rendered()
    def refresh():
        resize_events.append(('refresh', None))
        rendered()
    resize_env = {'resize_pending': pending, 'measured_pixels': measured_pixels,
                  'measured_screen': measured_screen, 'get_screen_size': game.GetScreenSize,
                  'clientApi': api, 'session': fake_session, 'partial': partial,
                  'set_screen': set_screen, 'refresh': refresh}
    resized = execute(definitions(read(BASE, 'ui.py'), ast.FunctionDef, 'resized')[0], resize_env)
    game.logical, game.physical = (641, 360), (1923, 1080, 0, 0)
    resized(None)
    resized(None)
    check('Real resize event coalesces pending notifications', len(queue) == 1 and queue[0][0] == .05)
    queue.pop(0)[1]()
    check('Physical-only resize renders and refreshes same-font GUI cache',
          ('refresh', None) in resize_events and theme.native_gui_scale == 3.)
    game.logical, game.physical = (499, 277), (1995, 1107, 0, 0)
    delay, callback = queue.pop(0)
    callback()
    check('Real final .25 settle renders new logical size and refreshes GUI cache',
          delay == .25 and not pending.current and theme.native_gui_scale == 4.
          and ('set_screen', (499, 277)) in resize_events)
    report = {'schema': 1, 'python': sys.version, 'scope': 'Actual Python2 candidate AST/module execution with explicitly fake SDK, constructor and UI render boundaries',
              'MC_started': False, 'controls': CONTROLS, 'passed': True,
              'production_admission_performed': False, 'formal_A_accepted': False,
              'candidate_manifest_sha256': hashlib.sha256(open(os.path.join(WORK, 'candidate-v1.json'), 'rb').read()).hexdigest(),
              'real_resize_sdk_execution': False, 'real_Scene_native_render': False}
    open(output, 'wb').write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'controls': len(CONTROLS), 'output': output}))


if __name__ == '__main__':
    main()
