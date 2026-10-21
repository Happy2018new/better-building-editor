"""Execute exact observer source in real Py2; fake native API, no game claims."""
import json
import os
import sys
import types

source_path, output_path = sys.argv[1:3]
assert sys.version_info[0] == 2
module = types.ModuleType('private_water_observer_under_control')
with open(source_path, 'rb') as stream:
    source = stream.read()
eval(compile(source, '<exact-private-water-observer>', 'exec'), module.__dict__)
controls = []


def passed(name, **details):
    details.update(name=name, passed=True)
    controls.append(details)


class Native(object):
    def __init__(self):
        self.calls = []
        self.next_handle = 0
        self.uniform_result = True
        self.uniform_error = None
        self.passthrough_value = object()

    def CreateFreeModel(self, resource, dimension):
        self.calls.append(('CreateFreeModel', resource, dimension))
        self.next_handle += 1
        return 'native-handle-' + str(self.next_handle)

    def SetExtraUniformValue(self, *args, **kwargs):
        self.calls.append(('SetExtraUniformValue', args, kwargs))
        if self.uniform_error is not None:
            raise self.uniform_error
        return self.uniform_result

    def RemoveFreeModel(self, handle):
        self.calls.append(('RemoveFreeModel', handle))
        return True

    def SetFreeModelPos(self, *args, **kwargs):
        self.calls.append(('SetFreeModelPos', args, kwargs))
        return True

    def UntouchedMethod(self, value):
        self.calls.append(('UntouchedMethod', value))
        return self.passthrough_value


class Base(object):
    def __init__(self, bridge, component):
        self.bridge, self.model = bridge, component
        self.active, self.staging, self.retired = {}, {}, {}
        self.closed = self.ready = False


class Product(Base):
    pass


bridge, other_bridge = object(), object()
original_init = Base.__dict__['__init__']
assert '__init__' not in Product.__dict__
phase = ['base']
observer = module.WaterSetterObserver(bridge, Product, lambda: phase[0])
install = observer.install()
native = Native()
renderer = Product(bridge, native)
other_native = Native()
other = Product(other_bridge, other_native)
assert other.model is other_native
assert renderer.model is not native and renderer.model._original is native
handle = renderer.model.CreateFreeModel('actual-resource-name', 0)
assert handle == 'native-handle-1'
args_value = (1., 2., 3., 4.)
sentinel = object()
native.uniform_result = sentinel
assert renderer.model.SetExtraUniformValue(handle, 1, args_value, marker='native-kwarg') is sentinel
assert native.calls[-1][1][2] is args_value and native.calls[-1][2] == {'marker': 'native-kwarg'}
assert observer.applied[(1, handle, 1)]['value'] == module._pack(args_value)
passed('original_native_args_kwargs_and_return_object_identity_preserved')

native.uniform_result = False
assert renderer.model.SetExtraUniformValue(handle, 2, (0.,) * 4) is False
assert (1, handle, 2) not in observer.applied
assert observer.calls[-1]['result'] is False and observer.calls[-1]['completed']
passed('real_forwarded_false_result_recorded_and_not_in_successful_uniform_ledger')

error = RuntimeError('original-native-setter-failure')
native.uniform_error = error
try:
    renderer.model.SetExtraUniformValue(handle, 3, (1.,) * 4)
except RuntimeError as actual:
    assert actual is error
else:
    raise AssertionError('Original native exception swallowed')
assert observer.calls[-1]['exception']['message'] == str(error)
assert observer.calls[-1]['native_called'] and not observer.calls[-1]['completed']
assert (1, handle, 3) not in observer.applied
native.uniform_error = None
passed('native_exception_object_reraised_unchanged_with_complete_failed_receipt')

before = len(observer.calls)
assert renderer.model.UntouchedMethod('unchanged') is native.passthrough_value
assert len(observer.calls) == before
passed('unobserved_component_methods_and_unrelated_bridge_are_untouched')

class Group(object):
    model_name = 'actual-resource-name'
    origin = (0, 0, 0)
    uniforms = ((1.,) * 4,) * 4

renderer.active['fixture-group'] = {'group': Group(), 'model_id': handle,
    'visible': True, 'anchor': (0., 0., 0.)}
renderer.ready = True
snapshot = observer.snapshot('before-shown')
assert snapshot['renderers'][0]['active'][0]['model_id'] == handle
assert snapshot['renderers'][0]['active'][0]['uniforms'] == module._pack(Group.uniforms)
assert snapshot['renderers'][0]['component_id'] == id(native)
assert len(snapshot['applied_native_success_ledger']['dict']) == 1
assert renderer.model.RemoveFreeModel(handle) is True
assert not observer.alive and len(observer.created) == 1
renderer.active.clear()
renderer.closed = True
after = 0
exported = []
while after < len(observer.calls):
    packet = observer.read_calls(after, 2)
    assert packet['schema'] == 'wire-r27-water-native-calls-v1'
    assert packet['after'] == after and packet['total'] == len(observer.calls)
    assert packet['through'] == after + len(packet['calls'])
    exported.extend(packet['calls'])
    after = packet['through']
assert exported == observer.calls
assert [call['sequence'] for call in exported] == list(range(1, len(exported) + 1))
empty = observer.read_calls(after)
assert empty['calls'] == [] and empty['through'] == after
for invalid in ((-1, 64), (after + 1, 64), (True, 64), (0, True), (0, 65), (0, 0), (0., 64)):
    try:
        observer.read_calls(*invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid incremental native receipt range accepted')
passed('incremental_call_receipts_are_complete_ordered_bounded_and_invalid_ranges_rejected')
closed = observer.snapshot('after-removal')
assert closed['renderers'] == [] and closed['closed_empty_renderer_count'] == 1
passed('closed_empty_renderers_are_counted_without_repeating_old_group_history')
retired = observer.retire(after)
assert retired['restored'] and not retired['alive']['dict']
assert retired['complete'] and retired['all_call_receipts_exported']
assert renderer.model is native and '__init__' not in Product.__dict__
assert getattr(Product.__init__, 'im_func', Product.__init__) is original_init
assert install['had_own_init'] is False
passed('complete_groups_successful_native_ledger_creation_removal_census_and_original_class_component_restored')

native2 = Native()
limited = module.WaterSetterObserver(bridge, Product, lambda: 'budget', max_calls=1)
limited.install()
limited_renderer = Product(bridge, native2)
limited_renderer.model.CreateFreeModel('resource', 0)
native_before = len(native2.calls)
try:
    limited_renderer.model.SetExtraUniformValue('native-handle-1', 1, (0.,) * 4)
except RuntimeError:
    pass
else:
    raise AssertionError('Observer silently dropped over-budget call')
assert len(native2.calls) == native_before and limited.exceeded
receipt = limited.retire(len(limited.calls))
assert receipt['restored'] and receipt['budget_exceeded'] and receipt['alive']['dict']
assert not receipt['complete'] and receipt['all_call_receipts_exported']
assert limited_renderer.model is native2 and '__init__' not in Product.__dict__
passed('call_budget_rejects_before_native_and_restores_but_keeps_live_handle_census_explicit')

foreign_observer = module.WaterSetterObserver(bridge, Product, lambda: 'foreign')
foreign_observer.install()
component_a, component_b = Native(), Native()
renderer_a, renderer_b = Product(bridge, component_a), Product(bridge, component_b)
renderer_a.model = object()
receipt = foreign_observer.retire(len(foreign_observer.calls))
assert not receipt['restored'] and receipt['errors']
assert not receipt['all_components_restored_same_objects'] and receipt['class_init_restored_same_function']
assert renderer_b.model is component_b and '__init__' not in Product.__dict__
renderer_a.model = component_a
passed('foreign_component_change_fails_explicitly_while_other_components_and_class_still_restore')

missed = module.WaterSetterObserver(bridge, Product, lambda: 'missing-export')
missed.install()
missed_native = Native()
missed_renderer = Product(bridge, missed_native)
missed_handle = missed_renderer.model.CreateFreeModel('resource', 0)
missed_renderer.model.RemoveFreeModel(missed_handle)
receipt = missed.retire(1)
assert receipt['restored'] and not receipt['complete'] and receipt['errors']
assert not receipt['all_call_receipts_exported'] and receipt['record_count'] == 2
assert missed_renderer.model is missed_native and '__init__' not in Product.__dict__
passed('missing_export_census_fails_without_preventing_exact_restoration')

init_calls = []
class OwnProduct(Base):
    def __init__(self, bridge, component, marker=None):
        init_calls.append((bridge, component, marker))
        Base.__init__(self, bridge, component)

own_init = OwnProduct.__dict__['__init__']
own = module.WaterSetterObserver(bridge, OwnProduct, lambda: 'own-init')
own.install()
own_native, own_marker = Native(), object()
own_renderer = OwnProduct(bridge, own_native, marker=own_marker)
assert init_calls == [(bridge, own_native, own_marker)]
receipt = own.retire(0)
assert receipt['complete'] and receipt['restored']
assert OwnProduct.__dict__['__init__'] is own_init and own_renderer.model is own_native
passed('original_own_init_called_once_with_argument_identity_and_own_attribute_restored')

init_error = RuntimeError('original-init-failure')
class FailingProduct(Base):
    def __init__(self, bridge, component):
        raise init_error

failing_init = FailingProduct.__dict__['__init__']
failing = module.WaterSetterObserver(bridge, FailingProduct, lambda: 'failed-init')
failing.install()
try:
    FailingProduct(bridge, Native())
except RuntimeError as actual:
    assert actual is init_error
else:
    raise AssertionError('Original constructor exception swallowed')
assert failing.renderers == [] and failing.calls == []
receipt = failing.retire(0)
assert receipt['complete'] and FailingProduct.__dict__['__init__'] is failing_init
passed('original_constructor_exception_identity_preserved_and_class_restored')

foreign_init = module.WaterSetterObserver(bridge, Product, lambda: 'foreign-init')
foreign_init.install()
def outsider_init(self, *args, **kwargs):
    return Base.__init__(self, *args, **kwargs)
Product.__init__ = outsider_init
receipt = foreign_init.retire(0)
assert not receipt['restored'] and not receipt['class_init_restored_same_function']
assert Product.__dict__['__init__'] is outsider_init
del Product.__init__
passed('foreign_init_mutation_is_rejected_without_overwriting_unknown_function')

stale = module.WaterSetterObserver(bridge, Product, lambda: 'stale-init')
Product.__init__ = outsider_init
try:
    stale.install()
except RuntimeError:
    pass
else:
    raise AssertionError('Changed class init overwritten during installation')
assert Product.__dict__['__init__'] is outsider_init and not stale.installed
del Product.__init__
passed('preinstallation_init_change_rejects_before_class_mutation')

result = {'schema': 'wire-r27-water-setter-observer-real-Py2-controls-v1',
    'passed': True, 'python_version': sys.version, 'control_count': len(controls),
    'controls': controls, 'game_native_API_executed': False, 'actual_game_capability_proven': False,
    'runtime_calls': 0, 'MC_started': False, 'production_changed': False,
    'candidate_promoted': False, 'manual_closures': 0}
with open(output_path, 'wb') as stream:
    stream.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'controls': len(controls), 'game_native_API_executed': False}))
