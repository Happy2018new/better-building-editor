# -*- coding: utf-8 -*-
"""Execute original/candidate Scene owner prefixes and compare exact effects/traces."""
from __future__ import print_function, unicode_literals
import ast
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if sys.version_info[0] < 3:
    HERE = HERE.decode(sys.getfilesystemencoding() or 'mbcs')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PRODUCT = os.path.join(ROOT, 'behavior_pack', 'modern_projection', 'projection', 'scene.py')
FAMILIES = ('liquid', 'item', 'cauldron', 'portal', 'book')
OWNERS = ('own_liquid', 'own_items', 'own_cauldrons', 'own_portals', 'own_books')
PREVIEWS = ('liquid', 'items', 'cauldrons', 'portals', 'books')


SOURCE_PATHS = {'scene.original.py': 'baseline/behavior_pack/modern_projection/projection/scene.py',
                'scene.candidate.py': 'combined/behavior_pack/modern_projection/projection/scene.py',
                'scene_owner.py': 'combined/behavior_pack/modern_projection/projection/scene_owner.py',
                'scene.portal-only.py': 'inputs/scene.portal-only.py'}

def raw(name):
    with open(os.path.join(HERE, SOURCE_PATHS.get(name, name)), 'rb') as source:
        return source.read()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def parsed(name):
    data = raw(name)
    return ast.parse(data if sys.version_info[0] < 3 else data.decode('utf8'), filename=name)


def scene_node(tree):
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'Scene')


original_ast = parsed('scene.original.py')
candidate_ast = parsed('scene.candidate.py')
restored = copy.deepcopy(candidate_ast)
old_owners = dict((node.name, node) for node in scene_node(original_ast).body
                  if isinstance(node, ast.FunctionDef) and node.name in OWNERS)
for node in scene_node(restored).body:
    if isinstance(node, ast.FunctionDef) and node.name in OWNERS:
        node.body = copy.deepcopy(old_owners[node.name].body)
restored.body = [node for node in restored.body if not (
    isinstance(node, ast.ImportFrom) and node.module == 'scene_owner' and node.level == 1)]
def unique_function(tree, name):
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(nodes) == 1
    return nodes[0]
portal_only = parsed('scene.portal-only.py')
assert ast.dump(unique_function(candidate_ast, 'portal_view')) == ast.dump(unique_function(portal_only, 'portal_view'))
unique_function(restored, 'portal_view').body = copy.deepcopy(unique_function(original_ast, 'portal_view').body)
assert ast.dump(restored) == ast.dump(original_ast), 'Combined Scene escaped five owner bodies/import and sealed portal hook'
for name in ('scene.original.py', 'scene.candidate.py', 'scene_owner.py'):
    compile(raw(name), name, 'exec')
helper_scope = {}
eval(compile(raw('scene_owner.py'), 'scene_owner.py', 'exec'), helper_scope)
assert not [node for node in ast.walk(parsed('scene_owner.py')) if isinstance(node, ast.Import)]


def prefix_code(tree, label):
    fn = copy.deepcopy(scene_node(tree))
    fn.decorator_list = []
    stop = next(index for index, node in enumerate(fn.body) if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'models_signature' for target in node.targets))
    fn.body = fn.body[:stop] + ast.parse('return locals()').body
    future = ast.parse('from __future__ import unicode_literals').body[0]
    module = ast.Module(body=[future, fn])
    if 'type_ignores' in ast.Module._fields:
        module.type_ignores = []
    ast.fix_missing_locations(module)
    return compile(module, label + ':actual-Scene-prefix', 'exec')


PREFIXES = (prefix_code(original_ast, 'original'), prefix_code(candidate_ast, 'candidate'))


class Value(object):
    def __init__(self, label):
        self.label = label


class InjectedClose(Exception):
    pass


class Resource(Value):
    def __init__(self, harness, label):
        Value.__init__(self, label)
        self.harness = harness
        self.failure = None
        self.after_close = None
        self.closes = 0

    def close(self):
        self.closes += 1
        self.harness.events.append(['close', self.label])
        if self.failure is not None:
            raise self.failure
        if self.after_close is not None:
            self.after_close()

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__


class Session(object):
    def __init__(self, harness):
        object.__setattr__(self, '_harness', harness)

    def __getattribute__(self, key):
        if any(key.endswith(suffix) for suffix in ('_preview', '_controls', '_error')):
            object.__getattribute__(self, '_harness').events.append(['read', key])
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        if any(key.endswith(suffix) for suffix in ('_preview', '_controls', '_error')):
            harness = object.__getattribute__(self, '_harness')
            harness.events.append(['set', key, harness.value(value)])
        object.__setattr__(self, key, value)


class Harness(object):
    def __init__(self, present, water_custom=True, budget=True, none_controls=None):
        self.events = []
        self.effects = []
        self.references = {}
        self.ref_serial = 0
        self.model_serial = 0
        self.last_family = None
        self.none_controls = none_controls
        self.session = Session(self)
        bridge = Value('bridge')
        factory = Value('factory')
        factory.CreateModel = self.create_model
        bridge.factory = factory
        bridge.attach_frame_pump = self.attach_frame_pump
        self.session.bridge = bridge
        for family in FAMILIES:
            for suffix, value in (('_preview', 'unowned-preview'), ('_controls', 'unowned-controls'), ('_error', 'old-error')):
                object.__setattr__(self.session, family + suffix, value)
            profile = None
            if family in present:
                profile = Value(family + '-profile')
                if family == 'liquid':
                    profile.provider_factory = Value('water-provider')
                    profile.models = Value('water-models')
                    profile.max_groups = 13
                    if water_custom:
                        profile.preview_factory = self.preview_factory('liquid', 'CustomLiquidPreview')
                    if budget:
                        profile.ui_request_starts_per_frame = 3
            setattr(self.session, family + '_profile', profile)

    def value(self, value):
        if value is self.session:
            return 'Session'
        if id(value) in self.references:
            return self.references[id(value)]
        if isinstance(value, Value):
            return value.label
        if isinstance(value, (list, tuple)):
            return [self.value(item) for item in value]
        if callable(value):
            return getattr(value, '__name__', 'callable')
        if isinstance(value, dict):
            return dict((key, self.value(item)) for key, item in value.items())
        return value

    def state(self):
        fields = object.__getattribute__(self.session, '__dict__')
        return dict((key, self.value(value)) for key, value in fields.items()
                    if any(key.endswith(suffix) for suffix in ('_preview', '_controls', '_error')))

    def create_model(self, value):
        assert value is None
        self.model_serial += 1
        result = Value('native-model-%d' % self.model_serial)
        self.events.append(['CreateModel', None, result.label])
        return result

    def attach_frame_pump(self):
        raise AssertionError('Frame pump must only be registered, not executed by this offline control')

    def use_theme(self):
        self.events.append(['hook', 'use_theme'])

    def use_state(self, initial):
        self.events.append(['hook', 'use_state', initial])
        return initial, lambda value: None

    def use_ref(self, initial):
        self.ref_serial += 1
        self.references[id(initial)] = 'registry-%d' % self.ref_serial
        self.events.append(['hook', 'use_ref', self.value(initial)])
        ref = Value('ref-%d' % self.ref_serial)
        ref.current = initial
        return ref

    def use_memo(self, factory, dependencies):
        self.events.append(['hook', 'use_memo', self.value(dependencies)])
        return factory()

    def use_effect(self, effect, dependencies):
        self.events.append(['hook', 'use_effect', effect.__name__, self.value(dependencies)])
        self.effects.append((effect.__name__, effect))

    def preview_factory(self, family, constructor):
        def build(*args, **kwargs):
            self.last_family = family
            self.events.append(['construct', constructor, self.value(args), self.value(kwargs)])
            return Resource(self, family + '-preview')
        return build

    def controls_factory(self, constructor):
        def build(*args, **kwargs):
            family = self.last_family
            self.events.append(['construct', constructor, self.value(args), self.value(kwargs)])
            return None if family == self.none_controls else Resource(self, family + '-controls')
        return build

    def render(self, code):
        scope = {'use_theme': self.use_theme, 'use_state': self.use_state, 'use_ref': self.use_ref,
                 'use_memo': self.use_memo, 'use_effect': self.use_effect,
                 'own_preview': helper_scope['own_preview'],
                 'LiquidControls': self.controls_factory('LiquidControls'),
                 'ItemControls': self.controls_factory('ItemControls')}
        for family, constructor in (('liquid', 'LiquidPreview'), ('item', 'ItemPreview'),
                                    ('cauldron', 'CauldronPreview'), ('portal', 'PortalPreview'), ('book', 'BookPreview')):
            scope[constructor] = self.preview_factory(family, constructor)
        eval(code, scope)
        local = scope['Scene'](session=self.session)
        assert [name for name, effect in self.effects] == ['subscribe', 'attach_frame_pump'] + list(OWNERS)
        return local


CASES = []


def lifecycle(code, family, mode):
    harness = Harness([value for value in FAMILIES if value != family] if mode == 'None_preview' else FAMILIES,
                      none_controls=family if mode == 'None_controls' else None)
    local = harness.render(code)
    index = FAMILIES.index(family)
    effect = dict(harness.effects)[OWNERS[index]]
    before = harness.state()
    cleanup = effect()
    if mode == 'None_preview':
        assert cleanup is None and harness.state() == before
        return {'events': harness.events, 'state': harness.state(), 'error': None}
    preview = local[PREVIEWS[index]]
    controls = local[family + '_controls' if family != 'liquid' else 'liquid_controls']
    assert preview is not None and not preview  # falsey preview still owns resources
    injected = InjectedClose('exact-original-exception')
    replacement_preview = Resource(harness, 'new-preview')
    replacement_controls = Resource(harness, 'new-controls')
    if mode == 'late_old_cleanup':
        setattr(harness.session, family + '_preview', replacement_preview)
        setattr(harness.session, family + '_controls', replacement_controls)
        setattr(harness.session, family + '_error', 'new-owner-error')
    elif mode == 'same_preview_new_controls':
        setattr(harness.session, family + '_controls', replacement_controls)
    elif mode == 'controls_close_error':
        controls.failure = injected
    elif mode == 'preview_close_error':
        preview.failure = injected
    elif mode == 'missing_current_attribute':
        delattr(harness.session, family + '_preview')
    elif mode == 'close_replaces_owner':
        def replace():
            setattr(harness.session, family + '_preview', replacement_preview)
            setattr(harness.session, family + '_controls', replacement_controls)
            setattr(harness.session, family + '_error', 'new-owner-error')
        controls.after_close = replace
    error = None
    try:
        cleanup()
        if mode == 'repeat_cleanup':
            cleanup()
    except Exception as caught:
        error = {'type': type(caught).__name__, 'injected_identity_preserved': caught is injected}
    final = harness.state()
    if mode == 'controls_close_error':
        assert error == {'type': 'InjectedClose', 'injected_identity_preserved': True}
        assert preview.closes == 0 and controls.closes == 1
    elif mode == 'preview_close_error':
        assert error == {'type': 'InjectedClose', 'injected_identity_preserved': True}
        assert preview.closes == controls.closes == 1
    elif mode == 'None_controls':
        assert error['type'] == 'AttributeError' and preview.closes == 0
    elif mode == 'missing_current_attribute':
        assert (error is None) == (family in ('liquid', 'item'))
        if error is not None:
            assert error['type'] == 'AttributeError'
        assert family + '_preview' not in final and final[family + '_error'] == 'old-error'
        assert preview.closes == controls.closes == 1
    else:
        assert error is None
        if mode in ('late_old_cleanup', 'close_replaces_owner'):
            assert final[family + '_preview'] == 'new-preview'
            assert final[family + '_controls'] == 'new-controls'
            assert final[family + '_error'] == 'new-owner-error'
        else:
            assert final[family + '_preview'] is None and final[family + '_controls'] is None
            assert final[family + '_error'] == ''
        expected = 2 if mode == 'repeat_cleanup' else 1
        assert preview.closes == controls.closes == expected
    # Session state inspection does not invoke/read its tracked native fields.
    return {'events': harness.events, 'state': final, 'error': error}


with open(PRODUCT, 'rb') as source:
    product_before = source.read()
assert product_before == raw('scene.original.py')
construction_cases = [([], True, True), (FAMILIES, True, True), (FAMILIES, False, False)]
construction_cases.extend(([family], True, True) for family in FAMILIES)
for present, custom, budget in construction_cases:
    left, right = Harness(present, custom, budget), Harness(present, custom, budget)
    left.render(PREFIXES[0])
    right.render(PREFIXES[1])
    assert left.events == right.events
    CASES.append({'kind': 'actual-Scene-construction-hooks', 'profiles': list(present),
                  'water_custom_factory': custom, 'water_budget_present': budget,
                  'identical_event_count': len(left.events), 'passed': True})
for family in FAMILIES:
    for mode in ('None_preview', 'normal_cleanup', 'late_old_cleanup', 'same_preview_new_controls',
                 'controls_close_error', 'preview_close_error', 'missing_current_attribute',
                 'repeat_cleanup', 'None_controls', 'close_replaces_owner'):
        left, right = lifecycle(PREFIXES[0], family, mode), lifecycle(PREFIXES[1], family, mode)
        assert left == right, (family, mode, left, right)
        encoded = json.dumps(left, sort_keys=True, separators=(',', ':')).encode('utf8')
        CASES.append({'kind': 'actual-owner-effect-closure', 'family': family, 'mode': mode,
                      'identical_event_count': len(left['events']), 'trace_state_sha256': sha(encoded),
                      'error': left['error'], 'passed': True})
with open(PRODUCT, 'rb') as source:
    assert source.read() == product_before
result = {'scope': 'Exact b70 and combined private source actual Scene prefix (all original owner construction/hooks) and actual five effect closures, with explicit fake hook scheduler/native factories/SDK resource close boundaries',
    'python': list(sys.version_info[:3]), 'completed': True, 'cases': CASES,
    'whole_module_AST_identical_except_five_owner_bodies_helper_import_and_sealed_portal_hook': True,
    'executed_source': 'combined private source, not sealed owner-only candidate',
    'source_path_bindings': SOURCE_PATHS,
    'all_hook_order_dependencies_and_constructor_expressions_unchanged': True,
    'original_controls_close_then_preview_close_then_identity_guard_retained': True,
    'SDK_import_or_Scene_UI_or_real_Pyreact_effect_scheduling_executed': False,
    'product_sha256_before_after': sha(product_before),
    'sources': dict((name, sha(raw(name))) for name in ('scene.original.py', 'scene.candidate.py', 'scene_owner.py')),
    'MC_started': False, 'product_written': False, 'native_runtime_qualified': False,
    'water39_qualification_transferred': False, 'this_round_merge': False}
target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'controls-py%d.json' % sys.version_info[0])
assert not os.path.exists(target)
with open(target, 'w') as output:
    json.dump(result, output, indent=2, sort_keys=True)
    output.write('\n')
print(json.dumps({'completed': True, 'construction_hook_cases': len(construction_cases),
    'actual_owner_closure_cases': len(CASES)-len(construction_cases), 'python': result['python'],
    'product_written': False, 'MC_started': False}))
