"""Private host sink and client payloads for separate bounded water receipts.

No transport, game import, process action or source mutation occurs on import.
The original palette phase JSON is never passed to or modified by this module.
"""
import base64
import hashlib
import json


INSTALL = '''import types,base64
from modern_projection.projection.liquid_product_render import ProductWorldLiquidRenderer
assert not hasattr(sys,'_books_wire_water')
module=types.ModuleType('books_wire_private_water_observer')
eval(compile(base64.b64decode(%r),'<wire-private-water-observer>','exec'),module.__dict__)
state={'module':module,'observer':None}
sys._books_wire_water=state
observer=module.WaterSetterObserver(b,ProductWorldLiquidRenderer,lambda:sys._books_wire_hook['phase_key'])
state['observer']=observer
_result=json.dumps(observer.install())
'''

READ_CALLS = '''state=sys._books_wire_water
_result=json.dumps(state['observer'].read_calls(%r,64))
'''

SNAPSHOT = '''state=sys._books_wire_water
snapshot=state['observer'].snapshot(%r)
snapshot['profile_id']=id(s.liquid_profile)
snapshot['profile_same_object']=s.liquid_profile is sys._books_wire_independent['profiles']['liquid_profile']
snapshot['projection_work_id']=id(b.projection_work)
snapshot['origin']=s.origin
snapshot['opacity']=s.opacity
_result=json.dumps(snapshot)
'''

RETIRE = '''if hasattr(sys,'_books_wire_water'):
 state=sys._books_wire_water
 try:
  observer=state['observer']
  receipt=observer.retire(%r) if observer is not None else {'restored':True,'never_installed':True}
 finally:
  del sys._books_wire_water
 receipt['marker_removed']=not hasattr(sys,'_books_wire_water')
 _result=json.dumps(receipt)
else:
 _result=json.dumps({'restored':True,'skipped_missing_marker':True,'marker_removed':True})
'''


class WaterReceiptSink:
    def __init__(self, folder, source):
        self.folder, self.source = folder, source
        self.after = 0
        self.packets, self.snapshots = [], []
        self.install_attempted = False
        self.folder.mkdir(parents=True, exist_ok=False)

    def _write(self, name, value):
        raw = (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('ascii')
        path = self.folder / name
        with path.open('xb') as stream:
            stream.write(raw)
        return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def install(self, check):
        assert not self.install_attempted
        self.install_attempted = True  # A lost acknowledgement must still enter retirement.
        source = base64.b64encode(self.source.read_bytes()).decode('ascii')
        result = check.run(INSTALL % source)
        assert result['installed'] and result['calls'] == result['renderers'] == 0
        self._write('installation.json', result)
        return result

    def flush(self, check):
        # 4,096 source calls / 64 per RPC plus a final empty packet.
        for unused in range(65):
            packet = check.run(READ_CALLS % self.after)
            assert packet['schema'] == 'wire-r27-water-native-calls-v1'
            assert type(packet['after']) is int and packet['after'] == self.after
            through, total = packet['through'], packet['total']
            assert type(through) is int and type(total) is int
            assert self.after <= through <= total <= 4096
            calls = packet['calls']
            assert through == self.after + len(calls) and len(calls) <= 64
            assert [call['sequence'] for call in calls] == list(range(self.after + 1, through + 1))
            assert all(call['native_called'] is True for call in calls)
            assert all(call['completed'] is True or 'exception' in call for call in calls)
            if not calls:
                assert through == total
                return self.after
            saved = self._write('calls-%04d.json' % (len(self.packets) + 1), packet)
            saved.update(after=self.after, through=through, total_at_read=total)
            self.packets.append(saved)
            self.after = through
        raise AssertionError('Water call export exceeded bounded packet budget')

    def snapshot(self, check, label):
        before = self.flush(check)
        value = check.run(SNAPSHOT % label)
        assert value['label'] == label and value['profile_same_object'] is True
        assert before <= value['call_count'] <= 4096
        value['exported_before_snapshot'] = before
        value['exported_after_snapshot'] = self.flush(check)
        assert value['call_count'] <= value['exported_after_snapshot']
        saved = self._write('snapshot-%03d.json' % (len(self.snapshots) + 1), value)
        saved['label'] = label
        self.snapshots.append(saved)
        return saved

    def retire(self, check):
        errors = []
        try:
            self.flush(check)
        except Exception as error:
            errors.append({'step': 'flush', 'error': '%s: %s' % (type(error).__name__, error)})
        # Always attempt actual component/class restoration even if export failed.
        receipt = None
        try:
            receipt = check.run(RETIRE % self.after)
            self._write('retirement.json', receipt)
            assert receipt['marker_removed'] is True and receipt['restored'] is True
            assert receipt.get('skipped_missing_marker') is not True
            assert receipt.get('never_installed') is not True
            assert receipt['complete'] is True and receipt['all_call_receipts_exported'] is True
            assert receipt['record_count'] == self.after and not receipt['alive']['dict']
            assert not receipt['budget_exceeded'] and not receipt['errors']
        except Exception as error:
            errors.append({'step': 'retire', 'error': '%s: %s' % (type(error).__name__, error)})
        summary = {'schema': 'wire-r27-water-native-receipt-export-v1',
                   'passed': not errors, 'errors': errors, 'exported_count': self.after,
                   'packets': self.packets, 'snapshots': self.snapshots, 'retirement': receipt,
                   'independent_native_readback': False,
                   'ledger_basis': 'Actual forwarded native setter success acknowledgements',
                   'original_palette_phase_JSON_changed': False}
        self._write('export-summary.json', summary)
        return summary
