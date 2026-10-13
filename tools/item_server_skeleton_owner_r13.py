"""Supervise one server-owned opaque body/plain sword UI comparison."""
from pathlib import Path
import sys

from isolated_diagnostic_module import load
import execute_item_server_skeleton_r13 as runtime
import prepare_item_server_skeleton_r13 as candidate

route=load('item_skeleton_owner_r13')

shared=route.shared
shared.runtime=runtime
shared.PREFIX='item-server-skeleton-r13-v1'
shared.ENTRYPOINT=Path(__file__).resolve()
shared.READINESS=shared.READINESS.replace(route.candidate.ATTRIBUTE,candidate.ATTRIBUTE)
previous_contract=shared.owner_contract


def owner_contract():
    value=previous_contract()
    value.update(server_owned_diagnostic_actor_count=1,is_client_entity_for_items=False,
                 exact_actor_replication_before_set_model=True,server_actor_is_npc=True,
                 player_or_inventory_or_existing_entities_mutated=False,
                 server_destroy_after_item_remove_and_ui_unmount=True)
    return value


shared.owner_contract=owner_contract


if __name__=='__main__':
    route.configure()
    candidate.EXACT_PLAN_SHA256=shared.PLAN_HASH
    if len(sys.argv)>1 and sys.argv[1]=='score':
        del sys.argv[1]
        runtime.main()
    else:
        raise SystemExit(shared.main())
