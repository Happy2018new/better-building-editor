"""Correlate actual forwarded calls and active groups with frozen resource bytes."""
import hashlib
import json
from pathlib import Path


def unpack(value):
    if isinstance(value, dict):
        assert len(value) == 1, 'Opaque native argument cannot establish exact mapping'
        if 'tuple' in value:
            return tuple(unpack(child) for child in value['tuple'])
        if 'list' in value:
            return [unpack(child) for child in value['list']]
        if 'dict' in value:
            return dict((unpack(key), unpack(child)) for key, child in value['dict'])
        raise AssertionError('Unknown packed native argument')
    return value


def verify_mapping(project, folder, fixture):
    resources = project / 'resource_pack'
    models_path = resources / 'models/netease_models.json'
    materials_path = resources / 'materials/entity.material'
    models = json.loads(models_path.read_bytes())
    materials = json.loads(materials_path.read_bytes())['materials']
    expected = json.loads((Path(__file__).parent / 'shader-change-manifest-v1.json').read_bytes())
    shader_rows = {row['path']: row for row in expected['shaders']}
    packets = [json.loads(path.read_bytes()) for path in sorted(folder.glob('calls-*.json'))]
    calls = [row for packet in packets for row in packet['calls']]
    assert [row['sequence'] for row in calls] == list(range(1, len(calls) + 1))
    mappings = {}

    def source(path):
        raw = path.read_bytes()
        return {'path': path.relative_to(project).as_posix(), 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest()}

    for call in calls:
        if call['method'] != 'CreateFreeModel' or not call['completed'] or not call['result']:
            continue
        resource = unpack(call['args'])[0]
        model = models[resource]
        candidates = [(name, value) for name, value in materials.items()
                      if name.split(':')[0] == model['material']]
        assert len(candidates) == 1
        material_name, material = candidates[0]
        fragment = resources / material['fragmentShader']
        fragment_relative = fragment.relative_to(project).as_posix()
        assert fragment_relative in shader_rows, 'Actual water resource uses an unreviewed shader'
        fragment_receipt = source(fragment)
        assert fragment_receipt['sha256'] == shader_rows[fragment_relative]['fixed_sha256']
        mappings[resource] = {'resource_name': resource, 'actual_CreateFreeModel_sequences':
            [item['sequence'] for item in calls if item['method'] == 'CreateFreeModel'
             and item['completed'] and item['result'] and unpack(item['args'])[0] == resource],
            'model_entry': model, 'material_entry_name': material_name, 'material_entry': material,
            'models_source': source(models_path), 'materials_source': source(materials_path),
            'fragment_source': fragment_receipt, 'vertex_source': source(resources / material['vertexShader']),
            'mesh_source': source(resources / 'models' / model['mesh']),
            'skeleton_source': source(resources / 'models' / model['skeleton']),
            'texture_sources': [source(resources / 'textures/models' / (texture + '.png'))
                                for texture in model['texture'].values()]}

    group_count = 0
    snapshot_rows = []
    for path in sorted(folder.glob('snapshot-*.json')):
        snapshot = json.loads(path.read_bytes())
        alive, ledger = {}, {}
        for call in calls[:snapshot['call_count']]:
            if not call['completed'] or not call['result']:
                continue
            args, rid = unpack(call['args']), call['renderer_id']
            if call['method'] == 'CreateFreeModel':
                alive[(rid, unpack(call['result']))] = args[0]
            elif call['method'] == 'RemoveFreeModel':
                alive.pop((rid, args[0]), None)
            elif call['method'] == 'SetExtraUniformValue':
                ledger[(rid, args[0], args[1])] = {'sequence': call['sequence'], 'value': args[2]}
        assert unpack(snapshot['alive']) == alive
        assert unpack(snapshot['applied_native_success_ledger']) == ledger
        checked = 0
        for renderer in snapshot['renderers']:
            rid = renderer['renderer_id']
            for kind in ('active', 'staging', 'retired'):
                for group in renderer[kind]:
                    handle = unpack(group['model_id'])
                    assert alive[(rid, handle)] == group['resource_name']
                    assert group['resource_name'] in mappings
                    uniforms = unpack(group['uniforms'])
                    for index, value in enumerate(uniforms[:3], 1):
                        assert ledger[(rid, handle, index)]['value'] == value
                    visible = group['visible']
                    assert type(visible) is bool
                    visibility = uniforms[3] if visible else uniforms[3][:3] + (0.,)
                    assert ledger[(rid, handle, 4)]['value'] == visibility
                    checked += 1
        group_count += checked
        snapshot_rows.append({'path': path.name, 'label': snapshot['label'],
                              'native_call_count': snapshot['call_count'], 'checked_groups': checked})
    if fixture == 'negative-wet-wire':
        assert mappings and group_count > 0, 'Wet control did not observe actual water groups'
    return {'schema': 'wire-r27-actual-water-call-frozen-resource-mapping-v1', 'passed': True,
            'fixture': fixture, 'native_call_count': len(calls), 'resource_mappings': list(mappings.values()),
            'checked_group_snapshots': group_count, 'snapshot_rows': snapshot_rows,
            'independent_native_readback': False, 'shader_clock_readback': False,
            'shader_clock_basis': 'Exact frozen fragment bytes resolved from actual FreeModel resource names',
            'uniform_basis': 'Actual successful native setter acknowledgements, correlated to active group intentions'}
