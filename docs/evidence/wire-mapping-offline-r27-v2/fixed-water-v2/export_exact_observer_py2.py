"""Real desktop Py2 executes exact frozen observer; native component is fake."""
import hashlib
import json
import os
import sys
import types

assert sys.version_info[0] == 2
source_path, output = sys.argv[1:3]
assert not os.path.exists(output)
os.makedirs(output)
with open(source_path, 'rb') as stream:
    source = stream.read()
module = types.ModuleType('exact_frozen_water_observer_under_Py2_control')
eval(compile(source, '<exact-frozen-water-observer>', 'exec'), module.__dict__)


def write(folder, name, value):
    with open(os.path.join(folder, name), 'wb') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


class Native(object):
    def __init__(self):
        self.uniform_result = True
        self.uniform_error = None

    def CreateFreeModel(self, resource, dimension):
        return 'reused-native-handle'

    def SetExtraUniformValue(self, handle, index, value):
        if self.uniform_error is not None:
            raise self.uniform_error
        return self.uniform_result

    def RemoveFreeModel(self, handle):
        return True


class Base(object):
    def __init__(self, bridge, native):
        self.bridge, self.model = bridge, native
        self.active, self.staging, self.retired = {}, {}, {}
        self.closed = False
        self.ready = True


class Product(Base):
    pass


class Group(object):
    def __init__(self, resource, offset):
        self.model_name = resource
        self.origin = (0, 0, 0)
        self.uniforms = tuple((offset + index, .25, .5, .75) for index in range(4))


bridge = object()
phase = ['first-owned-generation']
observer = module.WaterSetterObserver(bridge, Product, lambda: phase[0])
install = observer.install()
native = Native()
renderer = Product(bridge, native)
wet = os.path.join(output, 'wet')
os.mkdir(wet)
snapshots = []


def snapshot(label):
    value = observer.snapshot(label)
    snapshots.append(value)
    write(wet, 'snapshot-%03d.json' % len(snapshots), value)


first = Group('modern_projection_liquid_product_still_water_grey_world', 1.)
handle = renderer.model.CreateFreeModel(first.model_name, 0)
for index, value in enumerate(first.uniforms, 1):
    assert renderer.model.SetExtraUniformValue(handle, index, value) is True
renderer.active['first-group'] = {'group': first, 'model_id': handle, 'visible': True, 'anchor': (0., 0., 0.)}
snapshot('first-visible')
native.uniform_result = False
assert renderer.model.SetExtraUniformValue(handle, 2, (999.,) * 4) is False
native.uniform_result = True
error = RuntimeError('original-native-control-error')
native.uniform_error = error
try:
    renderer.model.SetExtraUniformValue(handle, 3, (999.,) * 4)
except RuntimeError as actual:
    assert actual is error
else:
    raise AssertionError('Original fake native exception was swallowed')
native.uniform_error = None
snapshot('failed-calls-do-not-overwrite-success-ledger')
assert renderer.model.SetExtraUniformValue(handle, 4, first.uniforms[3][:3] + (0.,)) is True
renderer.active['first-group']['visible'] = False
snapshot('first-hidden')
assert renderer.model.RemoveFreeModel(handle) is True
renderer.active.clear()
phase[0] = 'second-owned-generation-reused-handle'
second = Group('modern_projection_liquid_product_flowing_water_grey_world', 8.)
second_handle = renderer.model.CreateFreeModel(second.model_name, 0)
assert second_handle == handle
for index, value in enumerate(second.uniforms, 1):
    assert renderer.model.SetExtraUniformValue(second_handle, index, value) is True
renderer.active['second-group'] = {'group': second, 'model_id': second_handle, 'visible': True, 'anchor': (4., 0., 0.)}
snapshot('second-generation-same-handle-different-resource')
assert renderer.model.RemoveFreeModel(second_handle) is True
renderer.active.clear()
renderer.closed = True
snapshot('closed-empty-after-second-removal')
after = 0
packet_count = 0
while after < len(observer.calls):
    packet = observer.read_calls(after, 64)
    packet_count += 1
    write(wet, 'calls-%04d.json' % packet_count, packet)
    after = packet['through']
retired = observer.retire(after)
assert retired['complete'] and retired['restored'] and not retired['alive']['dict']
assert retired['creation_count'] == 2 and renderer.model is native
assert '__init__' not in Product.__dict__
write(wet, 'retirement.json', retired)

dry = os.path.join(output, 'dry')
os.mkdir(dry)
empty = module.WaterSetterObserver(bridge, Product, lambda: 'dry-no-water')
empty.install()
write(dry, 'snapshot-001.json', empty.snapshot('empty-dry'))
empty_retired = empty.retire(0)
assert empty_retired['complete'] and empty_retired['record_count'] == 0
write(dry, 'retirement.json', empty_retired)
write(output, 'export.json', {'schema': 'wire-r27-exact-observer-real-Py2-nonempty-export-v2',
    'python_version': sys.version, 'exact_observer_sha256': hashlib.sha256(source).hexdigest(),
    'native_component_is_fake': True, 'MC_started': False, 'game_native_API_executed': False,
    'actual_game_capability_proven': False, 'control_call_count': after,
    'snapshot_count': len(snapshots), 'failed_native_return_count': 1,
    'original_native_exception_identity_preserved': True,
    'handle_reused_after_successful_removal': True, 'creation_history_count': 2,
    'all_exact_components_and_class_attributes_restored': True, 'production_changed': False})
print(json.dumps({'exported': True, 'actual_desktop_Py2': True,
                  'control_calls': after, 'snapshots': len(snapshots), 'game_native_API_executed': False}))
