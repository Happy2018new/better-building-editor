"""Private strict adapter for a newly frozen owner; no MC startup at import.

Use make_check(entry_module, blue_module) around the owner's EntryCheck. The
original STATUS text and signature flags remain untouched in every capture.
Only the private adapter substitutes its separately certified controls result.
"""
import base64
import hashlib
import json
from pathlib import Path
import time

from lineage_host import Ledger, need, decode
from source_partition_proof import FrozenSource

HERE = Path(__file__).resolve().parent


def structural_ready(state, metadata=None, editor_id=None, document_id=None):
    """The original non-cache gates, without editing its raw signature report."""
    if state.get('preview_error'):
        raise AssertionError('Editor preview failed: %r' % state)
    liquid = state.get('liquid', {})
    if liquid.get('enabled'):
        if liquid.get('error'):
            raise AssertionError('Editor liquid preview failed: %r' % state)
        if not liquid.get('owned') or not liquid.get('plan_ready') or liquid.get('controls_pending', True):
            return False
    metadata = state['expected_metadata'] if metadata is None else metadata
    editor_id = state['expected_editor_id'] if editor_id is None else editor_id
    document_id = state['expected_document_id'] if document_id is None else document_id
    if not (state.get('metadata') == metadata and state.get('editor_id') == editor_id and
            state.get('document_id') == document_id and state.get('current_source') and
            state['page'] == 'workspace' and not state['preview_pending'] and
            not state['running'] and not state['dirty'] and not state['mounting'] and
            not state['edit_active'] and not state['io_active'] and
            state['model_revision_current'] and
            all(not row['pending'] and row['cache_current'] for row in state['parts'])):
        return False
    if not metadata['blocks']:
        return not state['model_name'] and not any(row['name'] for row in state['parts'])
    return (bool(state['model_name'] and state['parts']) and state['renderer_active'] and
            state['renderer_age'] < .5 and
            all(row.get('result') and not row.get('error') for row in state['native_calls']))


def make_check(entry, blue, client_prefix=''):
    class StrictCheck(entry.EntryCheck):
        def install_lineage(self, config, observer_path=HERE / 'observer_client.py', source_manifest_path=None):
            source = observer_path.read_bytes()
            need(hashlib.sha256(source).hexdigest() == config['observer_sha256'], 'observer file binding')
            need(config['owner'] == self.binding['owner'], 'observer owner differs from live binding')
            need(config['session_id'] == self.binding['id'], 'observer session differs from live binding')
            need(config['game_identity'] == self.binding['game_identity'], 'observer game identity differs')
            need(config['mcdk_identity'] == self.binding['mcdk_identity'], 'observer MCDK identity differs')
            need(source_manifest_path is not None, 'v5 requires explicit verified frozen source manifest path')
            frozen_source = FrozenSource(source_manifest_path, config['source_manifest_sha256'], decode, need)
            self.lineage_config = config
            self.lineage_ledger = Ledger(config, frozen_source)
            self.lineage_sequence = 0
            self.lineage_directory = self.directory / 'lineage'
            self.lineage_directory.mkdir(exist_ok=False)
            self.lineage_active = False
            encoded = base64.b64encode(source).decode('ascii')
            # globals() is the client request's actual namespace. Closures retain
            # its s/b references; saved callables survive later request namespaces.
            self.run('import base64\n'
                'eval(compile(base64.b64decode(%r),"<r27-strict-observer>","exec"),globals())\n'
                'install(json.loads(%r))\n_result=True' % (encoded, json.dumps(config)))
            self.lineage_active = True

        def restore_lineage(self):
            if self.lineage_active:
                self.run('sys._strict_cache_r27["restore"]()\n'
                         'assert not hasattr(sys,"_strict_cache_r27")\n_result=True')
                self.lineage_active = False

        def run(self, code):
            if code == entry.CONTROLS and getattr(self, 'lineage_active', False):
                row = self.lineage_snapshot('public controls')
                return {'editor_id': row['lineage']['editor_id'],
                        'document_id': row['lineage']['document_id'],
                        'models': row['lineage']['controls'],
                        'strict_certificate': row['certificate'], 'raw_status': row['raw_status']}
            return super().run(client_prefix + code)

        def lineage_snapshot(self, label, metadata=None, editor_id=None, document_id=None):
            # Capture STATUS and collector in one client turn so revision, cache,
            # actual Deserialize records and actual UI refer to one observation.
            gate = ('_legacy_status=json.loads(_result)\n'
                    '_lineage=sys._strict_cache_r27["collect"]()\n'
                    '_result=json.dumps({"raw_status":_legacy_status,"lineage":_lineage})')
            value = self.run(blue.STATUS + '\n' + gate)
            self.lineage_sequence += 1
            path = self.lineage_directory / ('%04d.json' % self.lineage_sequence)
            path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf8')
            value['record_path'] = str(path)
            value['record_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            value['observation'] = self.lineage_ledger.observe(value['lineage'], label)
            value['certificate'] = self.lineage_ledger.certify(value['lineage'])
            need(structural_ready(value['raw_status'], metadata, editor_id, document_id),
                 'structural state changed during certified snapshot')
            certificate_path = path.with_suffix('.certificate.json')
            certificate_path.write_text(json.dumps({key: value[key] for key in
                ('record_path', 'record_sha256', 'observation', 'certificate')}, indent=2) + '\n', encoding='utf8')
            return value

        def editor_preview(self, label, metadata=None, editor_id=None, document_id=None):
            gate = lambda state: structural_ready(state, metadata, editor_id, document_id)
            self.wait(label + ' structural', gate, lambda: self.run(blue.STATUS))
            first = self.lineage_snapshot(label, metadata, editor_id, document_id)
            time.sleep(.15)
            self.wait(label + ' stable structural', gate, lambda: self.run(blue.STATUS))
            final = self.lineage_snapshot(label, metadata, editor_id, document_id)
            # Preserve the original fields expected by existing public-card and
            # typed-data hosts; old all_parts_current / all_parts_ready stay raw.
            result = dict(final['raw_status'])
            result['strict_lineage'] = final['certificate']
            result['strict_lineage_raw_path'] = final['record_path']
            result['strict_lineage_raw_sha256'] = final['record_sha256']
            result['strict_lineage_first_certificate'] = first['certificate']
            return result

    return StrictCheck


def native_material(snapshot, point):
    """Decode complete actual original SDK Serialize result, never logical input."""
    rows = []
    records = {record['serial']: record for record in snapshot['lineage']['records']}
    certificates = {tuple(row['key']): row for row in snapshot['certificate']['parts']}
    for part in snapshot['lineage']['parts']:
        local = tuple(point[i] - part['origin'][i] for i in range(3))
        if not all(0 <= local[i] < part['size'][i] for i in range(3)):
            continue
        if not part['name']:
            rows.append({'part': part['key'], 'name': None, 'material': None, 'local': local})
            continue
        certificate = certificates[tuple(part['key'])]
        record = records[certificate['creation_serial']]
        palette = decode(record['native_serialized'])
        def get(name):
            return palette.get(name, palette.get(name.encode('ascii')))
        sz, sx, sy = get('volume')
        index = local[1] * sx * sz + local[0] * sz + local[2]
        matches = [material for material, indices in get('common').items() if index in indices]
        need(len(matches) <= 1, 'duplicate actual native common material index')
        material = matches[0] if matches else None
        if material is not None:
            material = [item.decode('utf8') if isinstance(item, bytes) else item for item in material]
        rows.append({'part': part['key'], 'name': part['name'], 'local': local,
            'native_volume': [sz, sx, sy], 'native_index': index, 'material': material,
            'creation_serial': certificate['creation_serial'],
            'native_serialization_sha256': certificate['actual_native_serialization_sha256']})
    need(len(rows) == 1, 'native coordinate must belong to exactly one region owner')
    return rows[0]
