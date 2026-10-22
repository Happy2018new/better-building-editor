"""Host-only strict creation ledger; never edits a runtime signature or nonce.

The complete wire payloads are retained. SHA256 seals their exported bytes,
not SDK memory. A new attempt to define a name invalidates every old reference
to that name, including when that attempt fails.
"""
import ast
import base64
import hashlib
import json
import math
import zlib


class Rejected(AssertionError):
    pass


def need(condition, message):
    if not condition:
        raise Rejected(message)


def normalized(value):
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=True))


def signature_tree_key(tree):
    """Compare one typed Py2 signature with its explicitly lossy JSON shadow.

    Only this boundary maps Py2 tuple to JSON array and UTF8 bytes/text to JSON
    text. The original wire remains immutable and separately hashed. A raw list
    or dict is not a Session.preview_signature container. Scalar tags retain
    bool/int/float identity; UTF8 is strict and no Unicode normalization occurs.
    """
    need(type(tree) is tuple and tree and type(tree[0]) is str, 'signature typed tree shape')
    tag = tree[0]
    if tag == 'null':
        need(len(tree) == 1, 'signature null shape')
        return ('null',)
    need(len(tree) == 2, 'signature typed scalar/container shape')
    value = tree[1]
    if tag == 'bool':
        need(type(value) is bool, 'signature bool type')
        return ('bool', value)
    if tag == 'int':
        need(type(value) is str, 'signature int encoding')
        number = int(value)
        need(str(number) == value, 'signature int canonical encoding')
        return ('int', value)
    if tag == 'float':
        need(type(value) is str, 'signature float encoding')
        number = float.fromhex(value)
        need(math.isfinite(number) and number.hex() == value, 'signature float canonical encoding')
        return ('float', value)
    if tag in ('bytes', 'text'):
        need(type(value) is str, 'signature text encoding type')
        if tag == 'bytes':
            raw = base64.b64decode(value.encode('ascii'), validate=True)
            need(base64.b64encode(raw).decode('ascii') == value, 'signature bytes canonical base64')
            value = raw.decode('utf8', errors='strict')
        value.encode('utf8', errors='strict')
        return ('text', value)
    if tag == 'tuple':
        need(type(value) is tuple, 'signature tuple payload type')
        return ('array', tuple(signature_tree_key(item) for item in value))
    raise Rejected('signature source container/tag not permitted: ' + tag)


def signature_json_key(value):
    """Type-aware key for the transported signature, never Python == scalars."""
    if value is None: return ('null',)
    if type(value) is bool: return ('bool', value)
    if type(value) is int: return ('int', str(value))
    if type(value) is float:
        need(math.isfinite(value), 'signature JSON nonfinite float')
        return ('float', value.hex())
    if type(value) is str:
        value.encode('utf8', errors='strict')
        return ('text', value)
    if type(value) is list:
        return ('array', tuple(signature_json_key(item) for item in value))
    raise Rejected('signature JSON container/scalar type not permitted')


def signature_key(value):
    need(type(value) is list and len(value) == 12, 'Session signature JSON shape')
    need(all(type(value[index]) is int for index in (0, 1, 4, 6)), 'Session signature integer fields')
    need(type(value[2]) is list and all(type(y) is int for y in value[2]), 'Session signature layer fields')
    need(all(type(value[index]) is bool for index in (3, 5)), 'Session signature boolean fields')
    return signature_json_key(value)


def signature_wire_key(value):
    need(value['codec'] in ('cell.freeze-repr-utf8-base64', 'cell.freeze-repr-utf8-zlib-base64'),
         'typed signature wire required')
    tree = ast.literal_eval(wire_bytes(value).decode('utf8'))
    need(type(tree) is tuple and len(tree) == 2 and tree[0] == 'tuple'
         and type(tree[1]) is tuple and len(tree[1]) == 12, 'Session signature typed tuple shape')
    return signature_tree_key(tree)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        ensure_ascii=True, separators=(',', ':')).encode('ascii')).hexdigest()


def wire_bytes(value):
    need(isinstance(value, dict) and set(value) == {'codec', 'base64', 'bytes'}, 'wire shape')
    need(value['codec'] in ('cell.freeze-repr-utf8-base64', 'cell.freeze-repr-utf8-zlib-base64',
                           'python2-repr-utf8-base64'), 'wire codec')
    transported = base64.b64decode(value['base64'].encode('ascii'), validate=True)
    need(base64.b64encode(transported).decode('ascii') == value['base64'], 'noncanonical base64')
    raw = zlib.decompress(transported) if value['codec'].endswith('-zlib-base64') else transported
    need(len(raw) == value['bytes'], 'wire length')
    raw.decode('utf8')
    return raw


def wire_hash(value):
    return hashlib.sha256(wire_bytes(value)).hexdigest()


def thaw(tree):
    tag = tree[0]
    if tag == 'null': return None
    if tag == 'bool': return tree[1]
    if tag == 'int': return int(tree[1])
    if tag == 'float': return float.fromhex(tree[1])
    if tag == 'bytes': return base64.b64decode(tree[1])
    if tag == 'text': return tree[1]
    if tag in ('list', 'tuple'):
        rows = [thaw(item) for item in tree[1]]
        return rows if tag == 'list' else tuple(rows)
    if tag == 'dict': return {thaw(key): thaw(item) for key, item in tree[1]}
    raise Rejected('invalid complete typed tree tag')


def decode(value):
    need(value['codec'] in ('cell.freeze-repr-utf8-base64', 'cell.freeze-repr-utf8-zlib-base64'), 'typed wire required')
    return thaw(ast.literal_eval(wire_bytes(value).decode('utf8')))


def same_wire(left, right, label):
    need(wire_bytes(left) == wire_bytes(right) and left['codec'] == right['codec'], label)


def recursive_wire_hashes(value, path='$'):
    rows = {}
    if isinstance(value, dict):
        if set(value) == {'codec', 'base64', 'bytes'}:
            rows[path] = {'sha256': wire_hash(value), 'bytes': value['bytes'], 'codec': value['codec']}
        else:
            for key, item in value.items():
                rows.update(recursive_wire_hashes(item, path + '.' + key))
    elif isinstance(value, (tuple, list)):
        for i, item in enumerate(value):
            rows.update(recursive_wire_hashes(item, path + '[%d]' % i))
    return rows


def unmounted_empty_owner(snapshot, key, part, partition_proof):
    """No fabricated UI: certify only an empty owner deliberately not requested."""
    need('actual_render_keys' in snapshot and 'actual_scene_census' in snapshot,
         'missing actual PreviewTile control without explicit empty-owner census')
    render_keys = [tuple(value) for value in snapshot['actual_render_keys']]
    census = snapshot['actual_scene_census']
    need(len(set(render_keys)) == len(render_keys), 'duplicate actual render key')
    need(normalized(census['model_requested_keys']) == normalized(snapshot['actual_render_keys']),
         'actual Scene requested keys differ from actual render keys')
    need(all(type(census[field]) is int and census[field] > 0
             for field in ('scene_fiber_id', 'models_fiber_id')),
         'actual Scene census lacks real fiber identities')
    for field in ('fiber_tile_keys', 'registry_keys'):
        keys = [tuple(value) for value in census[field]]
        need(len(set(keys)) == len(keys), 'duplicate actual Scene census key')
        need(key not in keys, 'unmounted empty owner remains in actual Scene or registry')
    fiber_keys = set(map(tuple, census['fiber_tile_keys']))
    need(all(tuple(row['key']) in fiber_keys for row in snapshot['controls']),
         'actual control lacks a matching Scene fiber')
    need(key not in render_keys, 'unmounted empty owner was requested by actual render keys')
    need(part['name'] is None and part['cache_model'] is None,
         'missing actual PreviewTile control belongs to a model')
    need(part['pending'] is False and type(part['count']) is int and part['count'] == 0
         and type(part['current_count']) is int and part['current_count'] == 0,
         'unmounted empty owner has count or pending work')
    need(partition_proof['actual_planner_reconstructed'] and
         partition_proof['actual_source_state_reconstructed'] and
         partition_proof['actual_build_preview_reconstructed'],
         'unmounted owner lacks exact frozen source reconstruction')
    need(partition_proof['halo_count'] == 0 or partition_proof['full_cache_snapshot_reconstructed'],
         'unmounted context owner full cached source differs from current reconstruction')
    need(partition_proof['owned_count'] == 0 and partition_proof['logical_count'] == 0,
         'unmounted owner has actual owned source cells')
    for field in ('current_source_cells', 'source_snapshot_cells'):
        cells = decode(part[field])
        need(type(cells) is tuple and len(cells) == partition_proof['halo_count'],
             'unmounted owner context/source census differs')
    body = decode(part['current_source_body'])
    need(type(body) is dict and type(body['cells']) is tuple and
         len(body['cells']) == partition_proof['halo_count'],
         'unmounted owner complete context/source body census differs')
    need(body['region'] == decode(part['current_region']) and
         body['size'] == decode(part['current_source_context'])[0],
         'unmounted empty owner source region or document size differs')
    data = decode(part['current_part_data'])
    need(type(data) is tuple and len(data) == 12
         and all(type(value) is dict and not value for value in data[:3]),
         'unmounted owner has foreground background or actor part data')
    need(data[3] == tuple(part['size']) and data[4] == tuple(part['origin']),
         'unmounted empty owner part data region differs')
    logical = decode(part['logical_palette'])
    need(type(logical) is dict and set(logical) ==
         {'common', 'extra', 'actor', 'void', 'volume', 'eliminateAir'},
         'unmounted empty owner logical palette schema differs')
    volume = tuple(part['size'][i] for i in (2, 0, 1))
    need(type(logical['volume']) is tuple and all(type(value) is int and value > 0 for value in logical['volume'])
         and logical['volume'] == volume and logical['void'] is False and logical['eliminateAir'] is True
         and all(type(logical[field]) is dict and not logical[field] for field in ('common', 'extra', 'actor')),
         'unmounted empty owner logical palette is not completely empty')
    need(part['current_native_input'] is not None, 'unmounted empty owner lacks complete prepared native input')
    prepared = decode(part['current_native_input'])
    need(type(prepared) is dict and set(prepared) ==
         {b'common', b'extra', b'actor', b'void', b'volume', b'eliminateAir', b'states', b'extraStates'},
         'unmounted empty owner prepared native schema differs')
    need(type(prepared[b'volume']) is tuple and all(type(value) is int and value > 0 for value in prepared[b'volume'])
         and prepared[b'volume'] == volume and prepared[b'void'] is False and prepared[b'eliminateAir'] is True
         and all(type(prepared[field]) is dict and not prepared[field]
                 for field in (b'common', b'extra', b'actor', b'states', b'extraStates')),
         'unmounted empty owner prepared native input is not completely empty')
    for record in snapshot['records']:
        frame = record.get('frame')
        same_source = all(record[field] == snapshot[field]
                          for field in ('nonce', 'editor_id', 'document_id'))
        need(not (same_source and frame is not None and tuple(frame['key']) == key),
             'unmounted empty owner has an actual native creation attempt')
    return {'actual_render_key_absent': True, 'actual_fiber_and_registry_absent': True,
            'owned_source_empty': True,
            'relevant_source_empty': partition_proof['source_count'] == 0,
            'relevant_source_context_only': partition_proof['halo_count'] > 0,
            'partition_reconstruction': partition_proof,
            'complete_logical_palette_empty': True,
            'complete_prepared_native_empty': True, 'same_source_native_creation_absent': True,
            'complete_prepared_native_sha256': wire_hash(part['current_native_input']),
            'complete_relevant_source_sha256': wire_hash(part['current_source_cells']),
            'actual_native_front_observed': False, 'model_visibility_qualified': False,
            'pixels_qualified': False}


class Ledger:
    def __init__(self, config, frozen_source):
        self.config = normalized(config)
        self.poll = 0
        self.records = []
        self.seals = []
        self.latest = {}
        self.stage = None
        self.source_fixtures = {}
        need(frozen_source is not None and frozen_source.sha == config['source_manifest_sha256'],
             'v5 requires an independently bound frozen source')
        self.frozen_source = frozen_source

    def observe(self, snapshot, stage):
        """Seal records as first seen, before checking whether UI has settled."""
        need(normalized(snapshot['config']) == self.config, 'snapshot source/host/owner binding')
        signature_key(snapshot['signature_values'])
        source_identity = tuple(snapshot[field] for field in ('nonce', 'editor_id', 'document_id'))
        need(self.source_fixtures.get(source_identity, snapshot['fixture']) == snapshot['fixture'],
             'fixture changed for already observed source identity')
        records = snapshot['records']
        need(len(records) >= len(self.records), 'creation ledger truncated')
        for i, old in enumerate(self.seals):
            need(digest(records[i]) == old['record_sha256'], 'sealed creation record changed')
        additions = []
        for i, record in enumerate(records[len(self.records):], len(self.records)):
            need(record['serial'] == i + 1, 'creation sequence gap or duplicate')
            need(normalized(record['config']) == self.config, 'creation source/host/owner binding')
            need(record['mode'] == 0, 'unqualified native mode')
            if all(record[field] == snapshot[field] for field in ('nonce', 'editor_id', 'document_id')):
                need(record['fixture'] == snapshot['fixture'], 'new native record fixture differs from its current source')
            need(record['deserialize_accepted'] is True, 'native Deserialize was not accepted')
            need(record['deserialize_input'] is not None, 'no original Deserialize input')
            need(record['native_serialized'] is not None, 'no original Serialize result')
            need(record['legacy_records_after'] == record['legacy_records_before'] + 1,
                 'original probe was not delegated exactly once')
            need(signature_wire_key(record['signature']) == signature_key(record['signature_values']),
                 'creation signature serialization disagrees')
            current_at_first_observation = all(record[key] == snapshot[key]
                for key in ('nonce', 'fixture', 'editor_id', 'document_id')) and (
                signature_key(record['signature_values']) == signature_key(snapshot['signature_values']))
            seal = {'serial': record['serial'], 'record_sha256': digest(record),
                'first_poll': self.poll + 1, 'first_stage': stage,
                'current_at_first_observation': current_at_first_observation,
                'wire_hashes': recursive_wire_hashes(record)}
            additions.append((record, seal))
        self.poll += 1
        self.stage = stage
        self.source_fixtures[source_identity] = snapshot['fixture']
        for record, seal in additions:
            self.records.append(normalized(record))
            self.seals.append(seal)
            # The attempt itself invalidates the previous requested name.
            self.latest[record['name']] = record['serial']
            if record.get('result'):
                self.latest[record['result']] = record['serial']
        return {'poll': self.poll, 'stage': stage, 'records': len(self.records),
                'new_records': len(additions), 'seals': [seal for unused, seal in additions]}

    def certify(self, snapshot):
        need(normalized(snapshot['config']) == self.config, 'certificate binding')
        source_identity = tuple(snapshot[field] for field in ('nonce', 'editor_id', 'document_id'))
        need(self.source_fixtures.get(source_identity) == snapshot['fixture'], 'certificate fixture source identity not observed')
        need(len(snapshot['records']) == len(self.records), 'observe all records before certification')
        need(all(digest(record) == seal['record_sha256'] for record, seal in
            zip(snapshot['records'], self.seals)), 'certificate snapshot changed a sealed creation')
        partition = self.frozen_source(snapshot)
        signature = normalized(snapshot['signature_values'])
        current_signature_key = signature_key(signature)
        owners = {tuple(key) for key in snapshot['owner_keys']}
        document_regions = decode(snapshot['document_regions'])
        need(owners == {tuple(value[0]) for value in document_regions.values()}, 'document region owner census')
        need(len(owners) == len(snapshot['owner_keys']), 'duplicate owner key')
        parts = {tuple(row['key']): row for row in snapshot['parts']}
        controls = {tuple(row['key']): row for row in snapshot['controls']}
        need(len(parts) == len(snapshot['parts']) and set(parts) == owners, 'active owner census')
        need(len(controls) == len(snapshot['controls']), 'duplicate native UI owner')
        rows = []
        for key in sorted(owners):
            part, control = parts[key], controls.get(key)
            empty_unmounted_evidence = None
            if control is None:
                empty_unmounted_evidence = unmounted_empty_owner(snapshot, key, part, partition[key])
                ui_classification = ('source_proven_empty_owner_with_verified_context_unmounted'
                    if partition[key]['halo_count'] else 'source_proven_empty_owner_unmounted')
                visibility_qualified = False
            else:
                need(control['owner'] and control['name'] == part['name'], 'actual UI owner model differs')
                need(type(control['front']) is int and control['front'] in (0, 1), 'invalid actual front index')
                need(all(len(control[field]) == 2 for field in ('names', 'visible', 'surface_visible', 'tracked_visible', 'poses')),
                     'incomplete actual two-surface control census')
                front = control['front']
                need(control['front_name'] == control['names'][front], 'reported front index/name disagree')
                need(control['ready'] == (control['pending'] is None and control['front_name'] == part['name']),
                     'reported PreviewBuffer ready disagrees')
                need(not control['suspended'] and not part['pending'], 'actual owner suspended or pending')
                need(all(type(value) is bool for value in control['surface_visible'] + control['visible']),
                     'actual native controls missing')
                if control['depth_hidden']:
                    need(not any(control['surface_visible']) and not any(control['tracked_visible']),
                         'depth-hidden owner retains visible surface')
                    ui_classification = 'source_proven_offscreen_or_depth_hidden'
                    visibility_qualified = False
                elif part['name']:
                    need(control['ready'] and control['pending'] is None, 'actual model not ready')
                    need(control['front_name'] == part['name'], 'actual PreviewBuffer front differs')
                    need(control['surface_visible'][front] and control['visible'][front] and
                         control['tracked_visible'][front], 'actual front surface is hidden')
                    need(not control['surface_visible'][1 - front] and not control['tracked_visible'][1 - front],
                         'actual previous surface remains visible')
                    need(control['poses'][front] is not None, 'visible front lacks native pose submission')
                    ui_classification = 'visible_current_native_front'
                    visibility_qualified = True
                else:
                    need(control['ready'] and not any(control['surface_visible']) and
                         not any(control['tracked_visible']), 'empty owner retains actual surface')
                    ui_classification = 'verified_empty_native_front'
                    visibility_qualified = False
            need(part['cache_model'] == part['name'], 'cache model differs')
            need(part['source_snapshot_complete'] in part['cache_sources_complete'], 'original source absent from cache bank')
            need(normalized(part['origin']) == normalized(part['current_origin']), 'current native region origin differs')
            need(normalized(part['size']) == normalized(part['current_size']), 'current native region size differs')
            need(part['count'] == part['current_count'], 'current visible cell count differs')
            for field in ('part_data', 'cache_data'):
                same_wire(part[field], part['current_part_data'], 'cached/current complete part data differs')
            same_wire(part['source_context'], part['current_source_context'], 'cached/current source context differs')
            same_wire(part['source_region'], part['current_region'], 'cached/current source region differs')
            same_wire(part['source_snapshot_cells'], part['current_source_cells'], 'original/current relevant source cells differ')
            old_signature = normalized(part['signature_values'])
            old_signature_key = signature_key(old_signature)
            need(signature_json_key(old_signature[:1] + old_signature[2:]) ==
                 signature_json_key(signature[:1] + signature[2:])
                and 0 <= old_signature[1] <= signature[1], 'part signature differs beyond allowed older revision')
            need(type(part['signature_current']) is bool and part['signature_current'] ==
                 (old_signature_key == current_signature_key), 'raw signature flag disagrees')
            if not part['name']:
                logical = decode(part['logical_palette'])
                need(part['count'] == 0 and not logical['common'] and not logical['extra'] and not logical['actor'],
                     'empty owner contains native geometry')
                rows.append({'key': list(key), 'classification': 'verified_empty_owner',
                    'signature_current': part['signature_current'], 'ui_classification': ui_classification,
                    'model_visibility_qualified': visibility_qualified, 'pixels_qualified': False,
                    'unmounted_empty_evidence': empty_unmounted_evidence})
                continue
            candidates = [record for record in self.records if record.get('result') == part['name']]
            need(candidates, 'model has no observed original creation')
            record = candidates[-1]
            seal = self.seals[record['serial'] - 1]
            need(self.latest.get(record['name']) == record['serial'] and
                 self.latest.get(part['name']) == record['serial'], 'same-name redefinition invalidated creation')
            need(not record.get('error') and record.get('result'), 'native creation failed')
            frame = record['frame']
            need(frame is not None, 'native creation lacks original tiled creation input')
            need(frame['requested_name'] == record['name'], 'original requested name differs')
            need(normalized(frame['key']) == list(key), 'original creation owner differs')
            need(normalized(frame['origin']) == normalized(part['origin']) and
                 normalized(frame['size']) == normalized(part['size']), 'original creation region differs')
            same_wire(frame['part_data'], part['current_part_data'], 'original creation/current cache data differs')
            same_wire(frame['source_body'], part['current_source_body'], 'original creation/current source differs')
            same_wire(frame['source_cells'], part['current_source_cells'], 'original creation/current source cells differ')
            same_wire(frame['source_snapshot_cells'], part['current_source_cells'], 'original snapshot/current source cells differ')
            same_wire(frame['source_context'], part['current_source_context'], 'original creation source context differs')
            same_wire(frame['source_region'], part['current_region'], 'original creation source region differs')
            same_wire(frame['logical_palette'], part['logical_palette'], 'original creation/current logical palette differs')
            same_wire(frame['expected_native_input'], record['deserialize_input'], 'actual Deserialize differs from prepared creation input')
            same_wire(record['deserialize_input'], part['current_native_input'], 'original actual Deserialize/current prepared palette differs')
            fresh = seal['first_stage'] == self.stage and part['signature_current'] and all(record[name] == snapshot[name]
                for name in ('nonce', 'fixture', 'editor_id', 'document_id')) and (
                signature_key(record['signature_values']) == current_signature_key)
            if fresh:
                category = 'fresh_current_source_submission'
            else:
                need(seal['first_poll'] < self.poll and seal['current_at_first_observation'],
                     'retained creation was not sealed while its original source was current')
                category = 'retained_geometry_full_lineage'
            rows.append({'key': list(key), 'model': part['name'], 'classification': category,
                'signature_current': part['signature_current'], 'part_signature': old_signature,
                'ui_classification': ui_classification, 'model_visibility_qualified': visibility_qualified,
                'pixels_qualified': False,
                'current_signature': signature, 'creation_serial': record['serial'],
                'creation_nonce': record['nonce'], 'current_nonce': snapshot['nonce'],
                'creation_record_sha256': seal['record_sha256'],
                'creation_first_poll': seal['first_poll'], 'creation_first_stage': seal['first_stage'],
                'actual_native_serialization_sha256': wire_hash(record['native_serialized']),
                'original_actual_deserialize_sha256': wire_hash(record['deserialize_input']),
                'original_full_source_snapshot_sha256': wire_hash(frame['source_snapshot_complete']),
                'current_full_source_snapshot_sha256': wire_hash(part['source_snapshot_complete']),
                'current_relevant_source_sha256': wire_hash(part['current_source_cells']),
                'current_prepared_native_sha256': wire_hash(part['current_native_input'])})
        slots = {tuple(key) for key in snapshot['slot_keys']}
        empty = {tuple(row['key']): row for row in snapshot['empty_slots']}
        need(len(slots) == len(snapshot['slot_keys']) and owners <= slots, 'owner/slot census mismatch')
        need(slots == set(document_regions), 'document region slot census')
        need(len(empty) == len(snapshot['empty_slots']), 'duplicate nonowner slot')
        need(set(empty) == slots - owners, 'nonowner empty slot census')
        for key, row in empty.items():
            need(row['name'] is None and row['count'] == 0 and not row['pending'] and
                 row['palette_counts'] == [0, 0, 0] and row['cache_current'], 'nonowner retained visible geometry')
            if key in controls:
                need(not controls[key]['owner'] and controls[key]['name'] is None and
                     controls[key]['front_name'] is None and controls[key]['pending'] is None,
                     'actual nonowner UI retains a model')
        need(set(controls) <= slots, 'actual UI has unaccounted slots')
        return {'qualified': True, 'poll': self.poll, 'parts': rows,
            'qualified_scope': 'complete source/native/cache lineage; actual visible fronts individually marked',
            'pixels_qualified': False,
            'creation_records': len(self.records), 'config_sha256': digest(self.config),
            'strict_original_signature_flags': [row['signature_current'] for row in rows],
            'verified_nonowner_empty_slots': len(empty),
            'native_serialization_note': 'SHA256 of complete typed serialization exported from API result; not SDK memory.'}
