"""One bounded background skeleton diagnostic using the reviewed finite owner."""
import argparse
import os
from pathlib import Path
import sys

import client_anchor_depth_owner_r15 as shared
import execute_item_skeleton_candidate_r13 as runtime
import prepare_item_skeleton_candidate_r13 as candidate

shared.runtime=runtime
shared.OWNER='item-skeleton-r13-v1'
shared.PREFIX='item-skeleton-r13-v1'
shared.CANDIDATE=shared.ROOT/'.runtime'/shared.PREFIX/'candidate'
shared.ENTRYPOINT=Path(__file__).resolve()
shared.READINESS=shared.READINESS.replace('_client_anchor_depth_probe',candidate.ATTRIBUTE)
previous_contract=shared.owner_contract
previous_guard=shared.OwnerGuard


def owner_contract():
    value=previous_contract()
    value.pop('cow_gate_before_binding')
    value.pop('cow_roi')
    value.update(opaque_skeleton_gate_before_binding=True,positive_target='owned_skeleton_actor',
                 registered_model=candidate.MODEL,material='entity_for_skeleton',
                 wgc_dispatches=10,same_entity_id_for_render_and_bind=True,
                 deferred_nonnegative_ui_model_id=True,resource_or_shader_or_player_or_world_or_inventory_mutation=False,
                 isolated_resources_installed_before_freeze=True,ordinary_sword_bind_count=1)
    return value


class SkeletonOwnerGuard(previous_guard):
    def loaded_resources(self):
        result=super().loaded_resources()
        extras={}
        for name,raw in candidate.resources().items():
            if name=='registration.json':
                continue
            target=shared.ROOT/'resource_pack'/name
            shared.require(shared.digest(target)==candidate.digest(raw),'Frozen opaque skeleton resource changed: '+name)
            extras[name]=dict(shared.file_identity(target),sha256=shared.digest(target))
        import json
        registration=json.loads((shared.ROOT/'resource_pack/models/netease_models.json').read_bytes())
        shared.require(registration.get(candidate.MODEL)==json.loads(candidate.resources()['registration.json'])[candidate.MODEL],
                       'Opaque model registration changed')
        result['opaque_skeleton_resources']=extras
        return result


shared.owner_contract=owner_contract
shared.OwnerGuard=SkeletonOwnerGuard


def configure():
    # Plan-hash and background-binary settings persist to the supervised child.
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--candidate-hash')
    parser.add_argument('--candidate-bundle')
    parser.add_argument('--guard-dll')
    known,remainder=parser.parse_known_args(sys.argv[1:])
    if known.candidate_hash:
        os.environ['MCDEV_ITEM_R13_CANDIDATE_HASH']=known.candidate_hash
    if known.candidate_bundle:
        os.environ['MCDEV_ITEM_R13_CANDIDATE_BUNDLE']=str(Path(known.candidate_bundle).resolve(strict=True))
    if known.guard_dll:
        os.environ['MCDEV_ITEM_R13_GUARD_DLL']=str(Path(known.guard_dll).resolve(strict=True))
    sys.argv=[sys.argv[0]]+remainder
    shared.PLAN_HASH=os.environ.get('MCDEV_ITEM_R13_CANDIDATE_HASH','')
    if len(shared.PLAN_HASH)!=64 or any(c not in '0123456789abcdef' for c in shared.PLAN_HASH):
        raise ValueError('Supply the exact frozen --candidate-hash')
    candidate.EXACT_PLAN_SHA256=shared.PLAN_HASH
    if 'MCDEV_ITEM_R13_CANDIDATE_BUNDLE' in os.environ:
        shared.CANDIDATE=Path(os.environ['MCDEV_ITEM_R13_CANDIDATE_BUNDLE']).resolve(strict=True)
    if 'MCDEV_ITEM_R13_GUARD_DLL' in os.environ:
        shared.BINARY_PINS.pop(str(shared.DLL))
        shared.DLL=Path(os.environ['MCDEV_ITEM_R13_GUARD_DLL']).resolve(strict=True)
        shared.BINARY_PINS[str(shared.DLL)]=shared.digest(shared.DLL)


if __name__=='__main__':
    configure()
    if len(sys.argv)>1 and sys.argv[1]=='score':
        del sys.argv[1]
        runtime.main()
    else:
        raise SystemExit(shared.main())
