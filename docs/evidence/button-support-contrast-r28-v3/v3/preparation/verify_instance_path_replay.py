"""Real Diagnostic methods on explicit offline mounted/native interface doubles.

Runs the actual constructor, freeze, guard, prepare, submit/state and restore.
No method/guard is replaced; no Minecraft API, session, RPC or grant is used.
"""
from __future__ import print_function
import argparse
import copy
import hashlib
import json
import os
import sys
import time
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, help='Fresh independent JSON result path')
OUT = os.path.abspath(parser.parse_args().output)
assert os.path.isdir(os.path.dirname(OUT)) and not os.path.exists(OUT)
try:
    text_type = unicode
except NameError:
    text_type = str


class Bag(object):
    def __init__(self, **values):
        self.__dict__.update(values)


def load(path):
    scope = {'__name__': 'OFFLINE_DIAGNOSTIC_CLASS', '__file__': path}
    with open(path, 'rb') as source:
        eval(compile(source.read(), path, 'exec'), scope)
    return scope


def wire(value):
    if type(value) is dict:
        return ('dict', tuple(sorted((wire(k), wire(v)) for k, v in value.items())))
    if type(value) in (list, tuple):
        return (type(value).__name__, tuple(wire(v) for v in value))
    if isinstance(value, bytes):
        return ('bytes', value.decode('ascii'))
    if isinstance(value, text_type):
        return ('unicode', value)
    return (type(value).__name__, repr(value))


def callback(canvas, clipping, clip_geometry, camera, unit, width, height):
    def tick(unused):
        return canvas, clipping, clip_geometry, camera, unit, width, height
    return tick


class Doll(object):
    def __init__(self):
        self.draws = []
    def RenderBlockGeometryModel(self, params):
        self.draws.append(copy.deepcopy(params))
        return True


class Control(object):
    def __init__(self, visible=True, native=None):
        self.visible, self.native = visible, native
    def GetVisible(self): return self.visible
    def SetVisible(self, value, unused): self.visible = value
    def GetPosition(self): return (0., 0.)
    def GetGlobalPosition(self): return (10., 10.)
    def GetSize(self): return (200., 200.)
    def asNeteasePaperDoll(self): return self.native


class Preview(Bag):
    def ready(self, name): return name == self.names[0]


class Document(Bag):
    def to_data(self): return {'OFFLINE_SIMULATION_ONLY': True, 'blocks': sorted(self.blocks)}


class Palette(object):
    def __init__(self, owner): self.owner = owner
    def DeserializeBlockPalette(self, value):
        self.owner.deserializations.append(copy.deepcopy(value))
        self.value = copy.deepcopy(value)
        return True
    def SerializeBlockPalette(self):
        value = copy.deepcopy(self.value)
        if self.owner.failure == 'serialize': value[b'void'] = True
        return value


class Factory(object):
    def __init__(self, failure=None):
        self.failure, self.deserializations, self.combines = failure, [], []
    def CreateBlock(self, unused): return self
    def GetBlankBlockPalette(self): return Palette(self)
    def CreateBlockGeometry(self, unused): return self
    def CombineBlockPaletteToGeometry(self, palette, name, mode):
        assert mode == 0
        self.combines.append((copy.deepcopy(palette.value), name, mode))
        return b'OFFLINE_WRONG_NAME' if self.failure == 'combine' else name
    def CreateGame(self, unused): return self
    def GetScreenSize(self): return (1280, 720)
    def GetScreenViewInfo(self): return (1280, 720, 1., 1.)


for name in ('modern_projection', 'modern_projection.projection', 'modern_projection.projection.widgets'):
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
sys.modules['modern_projection.projection.widgets'].Theme = Bag(scale=1.)


def fixture(scope, failure=None):
    button, support = scope['BUTTON'], scope['SUPPORT']
    source = {b'volume': (16, 16, 10), b'common': {button: [827], support: [1083]},
        b'states': {button: {b'button_pressed_bit': False, b'facing_direction': 0}, support: {}},
        b'extra': {}, b'extraStates': {}, b'actor': {}, b'eliminateAir': True, b'void': False}
    factory, native = Factory(failure), (Doll(), Doll())
    dolls = tuple(Bag(current=Control(native=value)) for value in native)
    surfaces = tuple(Bag(current=Control(visible=value)) for value in (True, False))
    name, key, origin = b'OFFLINE_original_production_model', (0, 0, 0, 1, 1), (0, 0, 16)
    pose = (4.31325, -170., 35.)
    preview = Preview(front=0, names=(name, b'OFFLINE_original_back'), poses=(pose, pose),
        pending=False, started=0., frames=0, initialized=True, retry_at=0., restore=False,
        visible=True, scene_signature=('OFFLINE',), geometry=name, tint_color=(1., 1., 1., 1.),
        depth_hidden=False, suspended=False, tint=Bag(current=Control()))
    document = Document(blocks={(3, 3, 27): button, (3, 4, 27): support})
    editor = Bag(document=document)
    part = {'origin': origin, 'name': name, 'pending': False}
    session = Bag(editor=editor, solo_layer=False, camera_depth=0., camera_depth_pose=0.,
        camera_pose=(35., -80., 12.), camera_pivot=(0., 0., 0.), camera_pan=(0., 0.),
        scene_origin=(0., 0.), scene_size=(32, 10, 32), scene_scale=10.,
        tiles=Bag(region_owners={key}, parts={key: part}))
    entry = (dolls, surfaces, preview)
    registry = {key: entry}
    tile = Bag(kind='PreviewTile', props={'identity': key, 'registry': registry}, child_fibers=[], _mounted=True)
    camera = Bag(pan=session.camera_pan, pivot=session.camera_pivot, _projection_value=(1., 0., 0., 1.), _basis_value=(1., 0., 0.))
    camera.render_angles = lambda: (35., -80.)
    camera._projection_key = (camera.render_angles(), camera.pan, camera.pivot, session.scene_size, 1280., 720., pose[0])
    old_callback = callback(Bag(current=Control()), Bag(current=Control()), Bag(current=(0., 0., 200., 200.)),
        camera, lambda: pose[0], 1280, 720)
    hook = {'type': 'animation_frame', 'callback': old_callback, 'active': True}
    hook['_registration_id'] = id(hook)
    scene = Bag(kind='Scene', props={'session': session}, child_fibers=[tile], hooks=[hook], _mounted=True)
    host = Bag(_root_fiber=Bag(kind='Root', props={}, child_fibers=[scene]), _animation_frames={id(hook): hook})
    navigator, bridge = Bag(top=Bag(_host=host)), Bag(level='OFFLINE_NO_LEVEL')
    config = {'owner': 'OFFLINE_NO_OWNER_GRANT', 'scope': 'SIMULATED_SOURCE_LINK_NOT_NATIVE_CERTIFICATE'}
    serialized = wire(source)
    link = {'raw_sha256': 'a' * 64, 'certificate_sha256': 'b' * 64,
        'actual_native_serialization_sha256': 'c' * 64, 'creation_serial': 1,
        'observer_config': config, 'owner': config['owner'], 'fixture': 'test.transforms.acceptance.t02',
        'nonce': 'OFFLINE_NONCE', 'native_name': name, 'native_serialized': serialized,
        'deserialize_input': serialized, 'editor_id': id(editor), 'document_id': id(document),
        'owner_key': list(key), 'origin': list(origin), 'signature': 'OFFLINE_SIGNATURE'}
    record = {'serial': 1, 'config': config, 'nonce': link['nonce'], 'fixture': link['fixture'],
        'name': name, 'result': name, 'mode': 0, 'deserialize_accepted': True,
        'native_serialized': serialized, 'deserialize_input': serialized,
        'editor_id': id(editor), 'document_id': id(document), 'frame': {'key': key, 'origin': origin},
        'signature': link['signature']}
    strict = {'config': config, 'records': [record], 'factory': factory}
    sys._strict_cache_r27 = strict
    sys._blueprint_qa_nonce, sys._blueprint_qa_identity = link['nonce'], link['fixture']
    diagnostic = scope['NativePairDiagnostic'](session, navigator, bridge, 'd' * 32,
        link, source, lambda fiber: fiber.kind, wire, strict)
    return Bag(diagnostic=diagnostic, factory=factory, strict=strict, hook=hook,
        original_callback=old_callback, surfaces=surfaces, native=native, source=source)


def restore(value):
    result = value.diagnostic.restore()
    assert result['restored'] and not result['errors']
    assert value.hook['callback'] is value.original_callback
    assert tuple(ref.current.GetVisible() for ref in value.surfaces) == (True, False)
    assert not value.diagnostic.frozen
    return result


cases = []
CURRENT = 'load'
try:
    new_path = os.path.join(HERE, 'client_diagnostic.py')
    old_path = os.path.join(os.path.dirname(HERE), 'button-support-contrast-v2', 'client_diagnostic.py')
    old, new = load(old_path), load(new_path)
    CURRENT = 'exact_failed_v2_constructor_freeze_reproduces_combined_KeyError'
    value = fixture(old)
    try:
        value.diagnostic.freeze()
    except KeyError as error:
        assert error.args == ('combined',)
    else:
        raise AssertionError('Unmodified old instance must reproduce its actual first failure')
    finally:
        restore(value)
    cases.append({'name': CURRENT, 'passed': True, 'actual_constructor_and_guard_called': True, 'expected_error': 'KeyError combined'})

    CURRENT = 'new_real_constructor_freeze_guard_prepare4_submit6_state_restore'
    value = fixture(new)
    diagnostic = value.diagnostic
    try:
        diagnostic.freeze()
        diagnostic.prepare_models(value.factory, 'OFFLINE_NO_LEVEL')
        assert len(diagnostic.creation_records) == len(value.factory.combines) == 4
        assert tuple(row['label'] for row in diagnostic.creation_records) == new['MODEL_LABELS']
        assert diagnostic.native_inputs['combined_stone'] == value.source
        for label, unused in new['STAGES']:
            assert diagnostic.submit_next() == label
            for count in range(6):
                value.hook['callback'](time.time())
            time.sleep(.26)
            state = diagnostic.state()
            assert state['stage']['label'] == label and state['settled_gate']
        assert len(diagnostic.stage_records) == 6
        assert diagnostic.stage_records[0]['drawings'][0]['params'] == diagnostic.stage_records[4]['drawings'][0]['params']
        assert diagnostic.stage_records[1]['drawings'][0]['params'] == diagnostic.stage_records[5]['drawings'][0]['params']
    finally:
        restore(value)
    cases.append({'name': CURRENT, 'passed': True, 'actual_constructor_and_all_real_guards_called': True,
        'native_interfaces_explicit_doubles': True, 'models_prepared': 4, 'stages_submitted': 6,
        'original_stone_source_still_checked_during_white_stages': True, 'callback_and_surface_visibility_restored': True})

    CURRENT = 'guard_source_tamper_rejected_before_any_prepare_call'
    value = fixture(new)
    try:
        value.diagnostic.freeze()
        value.strict['records'][0]['native_serialized'] = ('OFFLINE_TAMPER',)
        try:
            value.diagnostic.prepare_models(value.factory, 'OFFLINE_NO_LEVEL')
        except AssertionError:
            assert not value.factory.deserializations and not value.factory.combines
        else:
            raise AssertionError('Real source guard must reject tampering')
    finally:
        restore(value)
    cases.append({'name': CURRENT, 'passed': True, 'real_validate_source_not_stubbed': True, 'prepare_native_calls': 0})

    for failure in ('serialize', 'combine'):
        CURRENT = 'real_prepare_' + failure + '_mismatch_rejected_and_restored'
        value = fixture(new, failure)
        try:
            value.diagnostic.freeze()
            try:
                value.diagnostic.prepare_models(value.factory, 'OFFLINE_NO_LEVEL')
            except AssertionError:
                assert len(value.factory.deserializations) == 1
                assert len(value.factory.combines) == int(failure == 'combine')
            else:
                raise AssertionError('Actual prepare must reject native interface mismatch')
        finally:
            restore(value)
        cases.append({'name': CURRENT, 'passed': True, 'real_guard_and_prepare_not_stubbed': True,
            'native_interface_mismatch': failure, 'callback_and_surface_visibility_restored': True})

    with open(new_path, 'rb') as source:
        new_sha = hashlib.sha256(source.read()).hexdigest()
    result = {'passed': True, 'python': list(sys.version_info[:3]), 'scope': 'OFFLINE_REAL_DIAGNOSTIC_INSTANCE_METHODS',
        'cases': cases, 'client_sha256': new_sha, 'Diagnostic_methods_or_guards_replaced': False,
        'source_links_and_native_interfaces_are_explicit_simulation': True,
        'MC_started': False, 'RPC_executed': False, 'native_Minecraft_API_called': False,
        'root_grant_assigned': False, 'pixels_qualified': False, 'manual_issues_closed': 0}
    with open(OUT, 'w') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps({'passed': True, 'python': list(sys.version_info[:3]), 'cases': len(cases),
        'real_constructor_freeze_guard_prepare4_submit6_restore': True, 'MC_started': False}))
except BaseException as error:
    result = {'passed': False, 'first_failed_case': CURRENT, 'completed_cases': cases,
        'error': repr(error), 'traceback': traceback.format_exc(), 'MC_started': False, 'RPC_executed': False}
    with open(OUT, 'w') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    raise
