"""Private same-volume native draw diagnostic with unchanged base lifecycle.

No launcher. Requires the final owner/config/session and an explicit MC window.
The base main owns global restoration; this function owns diagnostic cleanup.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import uuid

from host_binding import bind_snapshot
from protocol import PAIR_PLAN
from calibration_host import bind_capture

HERE = Path(__file__).resolve().parent
driver = None  # Bound explicitly by run_support_runtime.main after frozen-source verification.
CLIENT = HERE / 'client_diagnostic.py'
OWNER = 'r28-button-support-contrast-v3'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pair_diagnostic(check, report, save):
    from lineage_host import decode, wire_hash, digest
    base, steps = driver.base, driver.steps
    row = {'identity': PAIR_PLAN['identity'], 'plan': PAIR_PLAN,
        'manual_issues_closed': 0, 'pixels_qualified': False, 'completed': False,
        'world_write_performed': False, 'production_certificate_during_diagnostic': False,
        'native_mesh_vertices_readback': False, 'native_tint_uniform_readback': False,
        'stages': [], 'host': {'path': str(Path(__file__).resolve()), 'sha256': sha(__file__)}}
    report['button_separate'] = row
    def persist():
        (check.directory / 'button-separate-report.json').write_text(json.dumps(row, indent=2) + '\n', encoding='utf8')
        save()
    row['card'] = check.load_card(PAIR_PLAN['identity'])
    oracle = base.build(PAIR_PLAN['identity'])
    keep = tuple(tuple(point) for point in PAIR_PLAN['points'])
    remove = sorted(set(oracle.blocks) - set(keep))
    assert len(remove) == 58
    erased = False
    token = uuid.uuid4().hex
    install_attempted = False
    try:
        row['erase'] = check.run('s.editor.selection=set(%r)\ns.editor.sync_selection_bounds()\n'
            'assert s.action(lambda:s.editor.run("erase"))\n'
            'sys._blueprint_qa_expected["metadata"]={"name":s.editor.document.name,"size":s.editor.document.size,"blocks":len(s.editor.document.blocks)}\n'
            '_result=json.dumps({"editor_id":id(s.editor),"document_id":id(s.editor.document),"cells":len(s.editor.document.blocks)})' % (remove,))
        erased = True
        assert row['erase']['cells'] == 2
        check.run('s.layer(3)\ns.display_mode("full")\n_result=True')
        row['pose'] = steps.pose(check, keep[0], 35., -80., 12., 'button_pair_full_baseline')
        fixed = check.run('_result=json.dumps({"editor_id":id(s.editor),"document_id":id(s.editor.document),"document":s.editor.document.to_data()})')
        row['fixed_document'] = fixed
        fixed_semantics = base.document_semantics(fixed['document'])
        snapshot = check.lineage_snapshot('button pair original full baseline')
        link, actual_native = bind_snapshot(snapshot, report['observer_config'], decode, wire_hash, digest)
        row['source_link'] = link
        (check.directory / 'button-pair-source-link.json').write_text(json.dumps(link, indent=2) + '\n', encoding='utf8')
        persist()
        source = base64.b64encode(CLIENT.read_bytes()).decode('ascii')
        # The durable slot precedes __init__. Even constructor failure reaches
        # this function's finally and the unchanged base main's global finally.
        install_attempted = True
        check.run('import base64\nassert not hasattr(sys,"_r27_native_pair")\n'
            '_scope={}\neval(compile(base64.b64decode(%r),"<r27-native-pair-client>","exec"),_scope)\n'
            '_object=_scope["NativePairDiagnostic"].__new__(_scope["NativePairDiagnostic"])\n'
            'sys._r27_native_pair={"token":%r,"object":_object}\n'
            '_saved=sys._strict_cache_r27\n'
            '_collect=_saved["collect"]\n'
            '_globals=getattr(_collect,"func_globals",getattr(_collect,"__globals__",None))\n'
            'from modern_projection.pyreact.debug import _type_name\n'
            '_object.__init__(s,navigator,b,%r,json.loads(%r),%r,_type_name,_globals["wire"],_saved)\n'
            '_object.freeze()\n'
            '_object.prepare_models(_saved["factory"],b.level)\n'
            '_result=json.dumps({"token":%r,"creations":_object.creation_records,"frozen":_object.frozen})'
            % (source, token, token, json.dumps(link, ensure_ascii=True), actual_native, token))
        row['creations'] = check.run('assert sys._r27_native_pair["token"]==%r\n'
            '_result=json.dumps(sys._r27_native_pair["object"].creation_records)' % token)
        assert len(row['creations']) == PAIR_PLAN['model_count']
        persist()
        for expected_label in PAIR_PLAN['stage_labels']:
            label = check.run('assert sys._r27_native_pair["token"]==%r\n'
                '_result=json.dumps(sys._r27_native_pair["object"].submit_next())' % token)
            assert label == expected_label
            stage = {'label': label, 'pixels_qualified': False}
            row['stages'].append(stage)
            deadline = time.monotonic() + PAIR_PLAN['maximum_wait_seconds']
            while True:
                state = check.run('assert sys._r27_native_pair["token"]==%r\n'
                    '_result=json.dumps(sys._r27_native_pair["object"].state())' % token)
                stage['latest_state'] = state
                persist()
                assert state['document_id'] == fixed['document_id'] and state['editor_id'] == fixed['editor_id']
                assert base.document_semantics(state['document']) == fixed_semantics
                assert state['stage']['label'] == expected_label
                assert state['surface_visibility'] == state['stage']['requested_surface_visibility']
                assert state['doll_visibility'] == [True, True]
                if state['settled_gate']:
                    break
                assert time.monotonic() < deadline, 'Native diagnostic frame gate exceeded two seconds'
                time.sleep(.05)
            stage['before_png'] = state
            stage['capture'] = check.capture('button_pair_' + label)
            stage['after_png'] = check.run('assert sys._r27_native_pair["token"]==%r\n'
                '_result=json.dumps(sys._r27_native_pair["object"].state())' % token)
            assert stage['after_png']['calibration'] == state['calibration']
            stage['capture_calibration'] = bind_capture(state['calibration'], stage['capture'], report['observer_config'])
            assert stage['after_png']['stage'] == state['stage']
            assert base.document_semantics(stage['after_png']['document']) == fixed_semantics
            persist()
    except Exception as error:
        row['error'], row['traceback'] = repr(error), traceback.format_exc()
        persist()
        raise
    finally:
        previous_cleaning = check.cleaning
        check.cleaning = True
        cleanup_error = None
        try:
            if install_attempted:
                row['diagnostic_restore'] = check.run('if hasattr(sys,"_r27_native_pair"):\n'
                    ' assert sys._r27_native_pair["token"]==%r\n'
                    ' _object=sys._r27_native_pair["object"]\n'
                    ' _restore=_object.restore()\n'
                    ' _result=json.dumps({"restore":_restore,"creations":getattr(_object,"creation_records",[]),'
                    '"stages":getattr(_object,"stage_records",[])})\n'
                    ' del sys._r27_native_pair\n'
                    'else:_result=json.dumps({"restore":{"restored":True,"object_was_absent":True}})' % token)
                assert row['diagnostic_restore']['restore']['restored'], 'Native diagnostic restore reported failure'
            if erased:
                row['after_diagnostic'] = check.editor_preview('native pair production source restored')
                row['after_diagnostic_capture'] = check.capture('button_pair_original_source_restored')
                after = check.run('_result=json.dumps(s.editor.document.to_data())')
                assert base.document_semantics(after) == fixed_semantics
        except Exception as error:
            row['cleanup_error'], row['cleanup_traceback'] = repr(error), traceback.format_exc()
            cleanup_error = error
        finally:
            try:
                if erased:
                    row['undo_attempted'] = True
                    check.run('assert s.action(s.editor.undo)\n'
                        'sys._blueprint_qa_expected["metadata"]={"name":s.editor.document.name,"size":s.editor.document.size,"blocks":len(s.editor.document.blocks)}\n_result=True')
                    restored = check.run('_result=json.dumps({"document_id":id(s.editor.document),"document":s.editor.document.to_data()})')
                    assert restored['document_id'] == row['erase']['document_id']
                    assert base.document_semantics(restored['document']) == base.document_semantics(oracle.to_data())
                    row['all60_restored'] = check.editor_preview('native pair all60 restored')
            except Exception as error:
                row['undo_error'], row['undo_traceback'] = repr(error), traceback.format_exc()
                cleanup_error = error
            check.cleaning = previous_cleaning
            persist()
        if cleanup_error is not None:
            raise RuntimeError('Native pair local cleanup failed: %r' % cleanup_error)
    row['completed'] = True
    persist()


if __name__ == '__main__':
    raise SystemExit('Use the independently granted run_support_runtime.py --config live-config.json entry.')
