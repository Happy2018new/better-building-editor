"""Bind a current original strict raw/certificate to the diagnostic input."""
import hashlib
import json
from pathlib import Path

from client_diagnostic import partition_full


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bind_snapshot(snapshot, observer_config, decode, wire_hash, digest):
    path = Path(snapshot['record_path'])
    assert sha(path) == snapshot['record_sha256']
    original = json.loads(path.read_bytes())
    assert original['lineage'] == snapshot['lineage']
    assert original['raw_status'] == snapshot['raw_status']
    certificate_path = path.with_suffix('.certificate.json')
    signed = json.loads(certificate_path.read_bytes())
    assert signed['record_sha256'] == snapshot['record_sha256']
    assert Path(signed['record_path']).resolve() == path.resolve()
    assert signed['certificate'] == snapshot['certificate']
    assert signed['observation'] == snapshot['observation']
    raw, certificate = original['lineage'], signed['certificate']
    assert certificate['qualified'] is True and certificate['pixels_qualified'] is False
    assert raw['config'] == observer_config
    assert certificate['config_sha256'] == digest(observer_config)
    assert raw['fixture'] == 'test.transforms.acceptance.t02'
    assert raw['nonce'] > 0
    candidates = [part for part in raw['parts'] if all(
        part['origin'][i] <= (3, 3, 27)[i] < part['origin'][i] + part['size'][i] for i in range(3))]
    assert len(candidates) == 1
    part = candidates[0]
    assert part['origin'] == [0, 0, 16] and part['size'] == [16, 10, 16]
    assert part['signature_current'] is True and part['pending'] is False
    rows = [row for row in certificate['parts'] if row['key'] == part['key']]
    assert len(rows) == 1
    certified = rows[0]
    assert certified['model'] == part['name']
    assert certified['signature_current'] is True
    assert certified['ui_classification'] == 'visible_current_native_front'
    assert certified['model_visibility_qualified'] is True and certified['pixels_qualified'] is False
    records = [record for record in raw['records'] if record['serial'] == certified['creation_serial']]
    assert len(records) == 1
    record = records[0]
    assert type(record['serial']) is int and record['serial'] > 0
    assert record['config'] == observer_config
    assert record['name'] == record['result'] == part['name']
    assert record['fixture'] == raw['fixture']
    assert record['nonce'] == raw['nonce'] == certified['creation_nonce'] == certified['current_nonce']
    assert record['editor_id'] == raw['editor_id'] and record['document_id'] == raw['document_id']
    assert record['mode'] == 0 and record['deserialize_accepted'] is True
    assert digest(record) == certified['creation_record_sha256']
    assert wire_hash(record['native_serialized']) == certified['actual_native_serialization_sha256']
    assert wire_hash(record['deserialize_input']) == certified['original_actual_deserialize_sha256']
    assert wire_hash(part['current_native_input']) == certified['current_prepared_native_sha256']
    assert wire_hash(record['native_serialized']) == wire_hash(part['current_native_input'])
    assert record['frame']['key'] == part['key'] and record['frame']['origin'] == part['origin']
    native = decode(record['native_serialized'])
    partition_full(native)
    link = {'owner': observer_config['owner'], 'observer_config': observer_config,
        'raw_path': str(path.resolve()), 'raw_sha256': snapshot['record_sha256'],
        'certificate_path': str(certificate_path.resolve()), 'certificate_sha256': sha(certificate_path),
        'fixture': raw['fixture'], 'nonce': raw['nonce'], 'editor_id': raw['editor_id'],
        'document_id': raw['document_id'], 'owner_key': part['key'], 'origin': part['origin'],
        'native_name': part['name'], 'creation_serial': record['serial'],
        'creation_record_sha256': certified['creation_record_sha256'],
        'actual_native_serialization_sha256': certified['actual_native_serialization_sha256'],
        'native_serialized': record['native_serialized'], 'deserialize_input': record['deserialize_input'],
        'signature': record['signature'], 'pixels_qualified': False}
    return link, native
