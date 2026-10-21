"""Python 2 offline lower bound from acknowledged boundary document and parts.

No runtime imports, fabricated native contents, transport calls, or MC launch.
The failed response itself was NOT captured. This is deliberately a lower bound.
"""
import ast
import hashlib
import json
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def read(path):
    with open(path, 'rb') as stream:
        return stream.read()


def sha(path):
    return hashlib.sha256(read(path)).hexdigest()


def main():
    boundary = os.path.join(HERE, 'flat-boundary-actual-v3')
    expected_path = os.path.join(boundary, 'rpc-0016-result.json')
    source_path = os.path.join(boundary, 'rpc-0019-result.json')
    expected = json.loads(read(expected_path))
    source = json.loads(read(source_path))
    assert source['work_current'] and source['cache_current'] and not source['missing']
    assert source['fixture'] == expected['fixture'] == 'wire-r27.flat-boundary'
    assert source['nonce'] == expected['nonce']
    assert source['editor_id'] == expected['editor_id']
    assert source['document_id'] == expected['document_id']
    assert len(source['parts']) == 7 and all(row[2] for row in source['parts'])
    doc = dict(expected['logical_document'])
    doc.pop('host_sha256')
    assert len(doc['base64']) == 575376 and doc['bytes'] == 431530
    # Named successful geometry never takes the unnamed-fingerprint cache branch.
    # Each of seven actual parts requires CreatePalette, Deserialize, and Combine.
    inferred_minimum_records = len(source['parts']) * 3
    minimum = {'records': [dict(logical_document=doc, work_document=doc)
                           for unused in range(inferred_minimum_records)]}
    phase_json = json.dumps(minimum)

    session_path = os.path.join(os.environ['USERPROFILE'], '.pyreact-debug',
                                'instances', '71370f6649744e06b8eef352ca786898',
                                'session.json')
    session = json.loads(read(session_path))
    deployed_root = os.path.join(session['appdata'], 'MinecraftPE_Netease', 'games',
                                 'com.netease', 'behavior_packs')
    candidates = []
    for parent, dirs, files in os.walk(deployed_root):
        if 'IPCSystem.py' in files:
            candidates.append(os.path.join(parent, 'IPCSystem.py'))
    assert len(candidates) == 1
    deployed = candidates[0]
    assert sha(deployed) == 'aa37dc422b869936d34380c23f81a8fb1b0ca3b8cd12aed781efa929c9c91e8c'
    tree = ast.parse(read(deployed))
    names = ('_SAFE_REPR', '_GET_TYPE_NAME', '_JSON_SAFE_VALUE', '_EXEC_CODE_RESULT')
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in names]
    assert len(nodes) == 4
    namespace = {'_UNICODE_TYPE': unicode, '_LONG_TYPE': long,
                 '_EXEC_CODE_VALUE': lambda unused: phase_json}
    eval(compile(ast.Module(body=nodes), '<exact-deployed-IPC-result-functions>',
                 'exec'), namespace)
    result = namespace['_EXEC_CODE_RESULT']('unused', 'client')
    packet = json.dumps({'id': 'x', 'ok': True, 'result': result}, ensure_ascii=False)
    limit = 16 * 1024 * 1024
    output = {
        'schema': 'wire-r27-boundary-v3-source-derived-frame-lower-bound',
        'python_version': sys.version,
        'actual_phase_records_exported': 0,
        'actual_native_record_count_known': False,
        'actual_complete_response_packet_captured': False,
        'acknowledged_native_parts': len(source['parts']),
        'inferred_minimum_native_records': inferred_minimum_records,
        'minimum_record_inference': '7 acknowledged named successful context parts; audited original geometry requires 3 observer records each; spare path and all other fields omitted',
        'actual_logical_document_bytes': doc['bytes'],
        'actual_logical_document_base64_bytes': len(doc['base64']),
        'record_base64_only_lower_bound_bytes': inferred_minimum_records * 2 * len(doc['base64']),
        'minimum_phase_json_bytes': len(phase_json.encode('ascii')),
        'minimum_result_JSON_plus_repr_packet_bytes': len(packet.encode('utf8')),
        'receiver_frame_limit_bytes': limit,
        'lower_bound_exceeds_receiver_limit': len(packet.encode('utf8')) > limit,
        'game_exit_attribution': 'No native stack or captured complete response; game 0xC0000409 recorded separately and not attributed by this bound.',
        'minimum_snapshot_omissions': ['all native palette payloads', 'all actual identity and provenance fields', 'all shader spare records', 'top-level logical/work document copies', 'buffer parts', 'helper traces', 'actual request id width'],
        'inputs': [{'path': os.path.relpath(path, ROOT).replace('\\', '/'), 'sha256': sha(path)}
                   for path in (expected_path, source_path,
                     os.path.join(boundary, 'rpc-0020.py'),
                     os.path.join(HERE, 'observer_client_v3.py'),
                     os.path.join(ROOT, '.runtime', 'projects', 'wire-r27-small-retirement-v3',
                                  'behavior_pack', 'modern_projection', 'projection', 'bridge.py'))],
        'deployed_IPCSystem_sha256': sha(deployed),
        'runtime_calls': 0,
        'MC_started': False,
        'candidate_promoted': False,
        'GPU_qualified': False,
    }
    output_path = os.path.join(HERE, 'boundary-frame-lower-bound-v3.json')
    with open(output_path, 'wb') as stream:
        stream.write(json.dumps(output, indent=2, ensure_ascii=True))
    print(json.dumps(output))


if __name__ == '__main__':
    main()
