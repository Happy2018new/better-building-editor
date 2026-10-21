"""Private bounded forwarding observer, compatible with game Python 2.

This module imports no game API. A reviewed payload supplies the exact owned
bridge, renderer class and phase-key callback. No product file is modified.
"""

try:
    _TEXT = (str, unicode)
    _INTEGER = (int, long)
except NameError:
    _TEXT = (str,)
    _INTEGER = (int,)

_METHODS = frozenset(('CreateFreeModel', 'SetExtraUniformValue', 'RemoveFreeModel',
    'SetFreeModelPos', 'SetFreeModelScale', 'SetFreeModelRot', 'SetFreeModelBoundingBox'))


def _function(value):
    return getattr(value, 'im_func', value)


def _pack(value):
    if value is None or isinstance(value, (bool, float) + _TEXT + _INTEGER):
        return value
    if isinstance(value, tuple):
        return {'tuple': [_pack(child) for child in value]}
    if isinstance(value, list):
        return {'list': [_pack(child) for child in value]}
    if isinstance(value, dict):
        return {'dict': [[_pack(key), _pack(value[key])] for key in sorted(value, key=repr)]}
    return {'opaque_type': type(value).__name__, 'opaque_id': id(value), 'repr': repr(value)}


class _ModelProxy(object):
    def __init__(self, owner, renderer_id, original):
        self._owner = owner
        self._renderer_id = renderer_id
        self._original = original

    def __getattr__(self, name):
        native = getattr(self._original, name)
        if name not in _METHODS:
            return native
        owner, renderer_id = self._owner, self._renderer_id

        def forwarded(*args, **kwargs):
            if len(owner.calls) >= owner.max_calls:
                owner.exceeded = True
                raise RuntimeError('Private water native-call receipt budget exceeded')
            receipt = {'sequence': len(owner.calls) + 1, 'phase_key': owner.phase_key(),
                'renderer_id': renderer_id, 'component_id': id(self._original),
                'method': name, 'args': _pack(args), 'kwargs': _pack(kwargs),
                'native_called': False, 'completed': False}
            owner.calls.append(receipt)
            try:
                receipt['native_called'] = True
                result = native(*args, **kwargs)
            except BaseException as error:
                receipt['exception'] = {'type': type(error).__name__, 'message': str(error)}
                raise
            receipt['result'] = _pack(result)
            receipt['completed'] = True
            if result:
                if name == 'CreateFreeModel':
                    owner.alive[(renderer_id, result)] = args[0]
                    owner.created[(renderer_id, result, receipt['sequence'])] = args[0]
                elif name == 'SetExtraUniformValue':
                    owner.applied[(renderer_id, args[0], args[1])] = {
                        'sequence': receipt['sequence'], 'value': _pack(args[2])}
                elif name == 'RemoveFreeModel':
                    owner.alive.pop((renderer_id, args[0]), None)
            return result

        return forwarded


class WaterSetterObserver(object):
    def __init__(self, bridge, renderer_type, phase_key, max_calls=4096,
                 max_renderers=32, max_snapshots=128):
        self.bridge, self.renderer_type, self.phase_key = bridge, renderer_type, phase_key
        self.max_calls, self.max_renderers, self.max_snapshots = max_calls, max_renderers, max_snapshots
        self.calls, self.renderers, self.snapshots = [], [], []
        self.alive, self.created, self.applied = {}, {}, {}
        self.exceeded = False
        self.original_init = getattr(renderer_type, '__init__')
        self.had_own_init = '__init__' in renderer_type.__dict__
        self.original_own_init = renderer_type.__dict__.get('__init__')
        self.installed = False
        self.wrapper = None

    def install(self):
        if self.installed:
            raise RuntimeError('Private water observer already installed')
        if (('__init__' in self.renderer_type.__dict__) != self.had_own_init
                or _function(getattr(self.renderer_type, '__init__')) is not _function(self.original_init)):
            raise RuntimeError('Water renderer init changed before observer installation')
        original, owner = self.original_init, self

        def init(instance, *args, **kwargs):
            original(instance, *args, **kwargs)
            if instance.bridge is not owner.bridge:
                return
            if len(owner.renderers) >= owner.max_renderers:
                owner.exceeded = True
                raise RuntimeError('Private water renderer receipt budget exceeded')
            renderer_id = len(owner.renderers) + 1
            native = instance.model
            proxy = _ModelProxy(owner, renderer_id, native)
            owner.renderers.append({'renderer_id': renderer_id, 'instance': instance,
                'native': native, 'proxy': proxy})
            instance.model = proxy

        self.wrapper = init
        setattr(self.renderer_type, '__init__', init)
        self.installed = True
        return {'installed': True, 'class_id': id(self.renderer_type),
            'original_init_function_id': id(_function(self.original_init)),
            'had_own_init': self.had_own_init, 'calls': 0, 'renderers': 0}

    def _groups(self, renderer, name):
        values = getattr(renderer, name)
        result = []
        for key in sorted(values, key=repr):
            record = values[key]
            group = record['group']
            result.append({'key': _pack(key), 'model_id': _pack(record['model_id']),
                'resource_name': group.model_name, 'origin': _pack(group.origin),
                'uniforms': _pack(group.uniforms), 'visible': record.get('visible'),
                'anchor': _pack(record.get('anchor'))})
        return result

    def snapshot(self, label):
        if not self.installed or self.exceeded:
            raise RuntimeError('Private water observer missing or exceeded budget')
        if len(self.snapshots) >= self.max_snapshots:
            self.exceeded = True
            raise RuntimeError('Private water snapshot receipt budget exceeded')
        renderers = []
        closed_empty = 0
        for row in self.renderers:
            instance = row['instance']
            if instance.model is not row['proxy']:
                raise RuntimeError('Observed water model component changed outside observer')
            if instance.closed and not any(getattr(instance, name) for name in ('active', 'staging', 'retired')):
                closed_empty += 1
                continue
            renderers.append({'renderer_id': row['renderer_id'], 'instance_id': id(instance),
                'component_id': id(row['native']), 'model_proxy_same_object': True,
                'closed': instance.closed, 'ready': instance.ready,
                'active': self._groups(instance, 'active'),
                'staging': self._groups(instance, 'staging'),
                'retired': self._groups(instance, 'retired')})
        result = {'label': label, 'phase_key': self.phase_key(), 'call_count': len(self.calls),
            'closed_empty_renderer_count': closed_empty,
            'renderers': renderers, 'creation_count': len(self.created), 'alive': _pack(self.alive),
            'applied_native_success_ledger': _pack(self.applied)}
        self.snapshots.append({'label': label, 'phase_key': result['phase_key'], 'call_count': len(self.calls)})
        return result

    def read_calls(self, after, limit=64):
        if (type(after) not in _INTEGER or not 0 <= after <= len(self.calls)
                or type(limit) not in _INTEGER or not 1 <= limit <= 64):
            raise ValueError('Invalid water native-call receipt range')
        end = min(after + limit, len(self.calls))
        return {'schema': 'wire-r27-water-native-calls-v1', 'after': after, 'through': end,
            'total': len(self.calls), 'calls': self.calls[after:end]}

    def retire(self, exported_count):
        errors = []
        components_restored = True
        class_restored = True
        for row in self.renderers:
            instance = row['instance']
            try:
                if instance.model is row['proxy']:
                    instance.model = row['native']
                if instance.model is not row['native']:
                    raise RuntimeError('Observed renderer model component is not original')
            except BaseException as error:
                components_restored = False
                errors.append({'renderer_id': row['renderer_id'], 'error': str(error)})
        try:
            current = self.renderer_type.__dict__.get('__init__')
            if current is self.wrapper:
                if self.had_own_init:
                    setattr(self.renderer_type, '__init__', self.original_own_init)
                else:
                    delattr(self.renderer_type, '__init__')
            if ('__init__' in self.renderer_type.__dict__) != self.had_own_init:
                raise RuntimeError('Water renderer init class ownership did not restore')
            if _function(getattr(self.renderer_type, '__init__')) is not _function(self.original_init):
                raise RuntimeError('Water renderer init function did not restore')
        except BaseException as error:
            class_restored = False
            errors.append({'class_restore_error': str(error)})
        self.installed = False
        exported = type(exported_count) in _INTEGER and exported_count == len(self.calls)
        if not exported:
            errors.append({'export_census_error': 'Not every actual native call was exported'})
        return {'schema': 'wire-r27-water-setter-observer-retirement-v1',
            'restored': components_restored and class_restored,
            'complete': not errors and not self.exceeded and not self.alive,
            'errors': errors, 'alive': _pack(self.alive),
            'creation_count': len(self.created), 'applied_uniform_count': len(self.applied),
            'exported_count': exported_count, 'all_call_receipts_exported': exported,
            'budget_exceeded': self.exceeded, 'record_count': len(self.calls),
            'renderer_count': len(self.renderers), 'snapshot_count': len(self.snapshots),
            'all_components_restored_same_objects': components_restored,
            'class_init_restored_same_function': class_restored}
