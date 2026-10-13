"""Reuse finite UI/capture lifecycle around exact server actor ownership."""
from pathlib import Path
import time

from isolated_diagnostic_module import load
import prepare_item_server_skeleton_r13 as candidate

body_runtime=load('execute_item_skeleton_candidate_r13')

body_runtime.candidate=candidate
body_runtime.shared.candidate=candidate
ROOT=candidate.ROOT
dependencies=body_runtime.dependencies
HELPERS=body_runtime.HELPERS
HELPER_PINS=body_runtime.HELPER_PINS
preflight=body_runtime.preflight
main=body_runtime.main


def execute_probe(bundle,output,check,guard,deadline):
    import client_anchor_depth_owner_r15 as owner
    bundle=Path(bundle).resolve(strict=True)
    candidate.verify(bundle)
    original=check.run
    install=(bundle/'install_client.py').read_text(encoding='ascii')
    destroy=(bundle/'destroy_client.py').read_text(encoding='ascii')
    server_created=False
    server_journal=[]

    def server_run(source):
        guard.guard()
        check.client.frame_dispatch_deadline=deadline if cleanup[0] else deadline-30.
        if time.monotonic()>=check.client.frame_dispatch_deadline:
            raise TimeoutError('Server fixture SDK deadline exhausted')
        return owner.execute(check.client,source,False)

    def read(name):
        return (bundle/name).read_text(encoding='ascii')

    cleanup=[False]
    def dispatch(source):
        nonlocal server_created
        if source==install:
            initial=original(source)
            payload={key:initial[key] for key in ('nonce','player','position')}
            server_created=True  # execution may mutate before a transport error
            created=server_run(read('create_server.py').replace('APPROVED_CLIENT_PAYLOAD',repr(payload)))
            server_journal.append({'operation':'create','result':created})
            if not isinstance(created.get('actor'),str) or not created['actor'] or created['actor'] in ('-1',initial['player']):
                original("saved=sys.%s\nsaved['create']['state']='returned'\n_result=True" % candidate.ATTRIBUTE)
                raise ValueError('Exact server diagnostic actor creation failed: '+repr(created))
            original(read('adopt_client.py').replace('APPROVED_ACTOR_PAYLOAD',repr(created)))
            until=min(time.monotonic()+10.,deadline-30.)
            observations=[]
            while time.monotonic()<until:
                guard.guard()
                row=original(read('replication_client.py'))
                observations.append(row)
                if row['ready']:
                    break
                time.sleep(.1)
            else:raise TimeoutError('Exact server actor did not replicate a root model')
            server_journal.append({'operation':'replicate','observations':observations})
            return original(read('set_model_client.py'))
        if source==destroy:
            cleanup[0]=True
            if server_created:
                destroyed=server_run(read('destroy_server.py'))
                server_journal.append({'operation':'destroy','result':destroyed})
                if not destroyed.get('destroyed'):
                    raise ValueError('Exact server fixture destruction failed: '+repr(destroyed))
            return original(source)
        return original(source)

    check.run=dispatch
    report=None
    try:
        report=body_runtime.shared.execute_probe(bundle,output,check,guard,deadline)
    finally:
        check.run=original
        cleanup[0]=True
        if server_created and not any(row['operation']=='destroy' and row['result'].get('destroyed') for row in server_journal):
            try:
                row=server_run(read('destroy_server.py'))
                server_journal.append({'operation':'finally_destroy','result':row})
                if report is not None and not row.get('destroyed'):
                    report['cleanup_errors'].append('Server fixture finally destruction failed: '+repr(row))
                    report['restored']=False
            except Exception as error:
                if report is not None:
                    report['cleanup_errors'].append('Server fixture cleanup: '+repr(error))
                    report['restored']=False
                else:raise
        if report is not None:
            report['server_fixture_journal']=server_journal
            dependencies()['execute_frame_item_translation'].save_report(Path(output),report)
    return report


if __name__=='__main__':
    main()
