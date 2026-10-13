"""Execute one exact reviewed server read in the owned ready item session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import item_skeleton_owner_r13 as route
import execute_item_world_glint_r13 as runtime

shared=route.shared
shared.runtime=runtime
PREFIX='item-scaffold-readonly-r13-v1'
SOURCE_SHA256='844bc9dbc4ff9e09c95967903db502edfb4e9c9f58365e09e5ee7f3ad1b9c011'
SNIPPET_SHA256='c92637ecfa07161e0cc16e2a308f53921aa03d8af0c3bd6e9fac88f6279c0eeb'


def main():
    route.configure()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute'))
    parser.add_argument('bundle')
    parser.add_argument('--session-file')
    args=parser.parse_args()
    if args.command=='prepare':
        plan=shared.prepare(args.bundle)
        print(json.dumps({'sources':len(plan['source_pins']),'owner_plan_sha256':shared.digest(Path(args.bundle)/'plan.json')}))
        return
    plan=shared.verify(args.bundle)
    source=Path('D:/bbe-r13-scaffold/tools/probe_scaffold_air_readback.py')
    assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA256
    sys.path.insert(0,str(source.parent))
    import probe_scaffold_air_readback as probe
    raw=probe.SERVER.encode('ascii')
    assert hashlib.sha256(raw).hexdigest()==SNIPPET_SHA256
    session=Path(args.session_file).resolve(strict=True)
    guard=route.SkeletonOwnerGuard(session,plan)
    output=shared.artifact_directory(session)/(PREFIX+'.json')
    assert not output.exists()
    started=time.monotonic()
    report={'schema':1,'owner':shared.OWNER,'session_file':str(session),'source_sha256':SOURCE_SHA256,'snippet_sha256':SNIPPET_SHA256,
            'started_at':shared.timestamp(),'normal_seconds':30,'outer_seconds':60,'server_read_attempts':0,
            'completed':False,'restored':False,'requests':[],'network_requests':[],'errors':[],'cleanup_errors':[],
            'no_world_or_entity_mutation':True,'no_items_or_inventory':True,'no_ui_or_capture':True}
    preserve=lambda:shared.save(output,report)
    client=None
    try:
        os.environ.update(MCDEV_SESSION_FILE=str(session),MCDEV_OWNER=shared.OWNER)
        client=shared.recorded_client(guard,report,preserve,started+30.,started+60.)
        client.__enter__()
        report['identity']=shared.execute(client,shared.IDENTITY % ('server','Server'),False)
        shared.validate_identity(report['identity'],client)
        report['server_read_attempts']=1
        preserve()
        report['raw']=shared.execute(client,probe.SERVER,False)
        assert report['raw']['mutations']==[] and len(report['raw']['planes'])==2
        assert all(len(plane['cells'])==17 for plane in report['raw']['planes'])
        report['completed']=True
    except Exception as error:report['errors'].append(repr(error))
    finally:
        if client is not None:
            try:client.close()
            except Exception as error:report['cleanup_errors'].append('transport close: '+repr(error))
        try:
            guard.verify_after()
            report['protected_sources_unchanged']=True
        except Exception as error:report['cleanup_errors'].append('source verify: '+repr(error))
        report['restored']=report['completed'] and not report['cleanup_errors']
        report.update(elapsed_seconds=time.monotonic()-started,finished_at=shared.timestamp())
        preserve()
    print(json.dumps({k:report[k] for k in ('completed','restored','errors','cleanup_errors','elapsed_seconds')}))


if __name__=='__main__':main()
