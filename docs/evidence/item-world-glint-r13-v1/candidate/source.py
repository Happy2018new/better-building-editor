"""Separate native world capability experiment; it does not exercise projection."""
import argparse
import ast
from pathlib import Path

import prepare_item_glint_r13 as ui

ui.configure('glint','x90')
ROOT,MODEL,ATTRIBUTE,SERVER_ATTRIBUTE=ui.ROOT,ui.MODEL,ui.ATTRIBUTE,ui.SERVER_ATTRIBUTE
UI,ITEM_SCALE,ROTATIONS=ui.UI,ui.ITEM_SCALE,ui.ROTATIONS
digest,resources,archived_files=ui.digest,ui.resources,ui.archived_files
POSITIVE_STATES,POSITIVE_NAME,POSITIVE_TARGET=ui.POSITIVE_STATES,ui.POSITIVE_NAME,ui.POSITIVE_TARGET
PHASE,POSE='world_glint','x90'
TEMPORAL_LABEL='world_enchanted_later'
EXACT_PLAN_SHA256=None
MAPPING={'ui_body':'world_body','ui_plain_x90':'world_plain',
         'ui_enchanted':'world_enchanted','ui_enchanted_later':'world_enchanted_later','ui_body_restored':'world_body_restored'}
STATES=tuple(MAPPING.get(state,state) for state in ui.STATES)


def state_parameters(label):
    return ui.state_parameters(next((name for name,value in MAPPING.items() if value==label),label))


def snippets(nonce):
    programs=ui.snippets(nonce)
    for before,after in MAPPING.items():
        code=programs.pop(before+'_client.py')
        # Longest labels first avoid replacing a temporal state by its prefix.
        for name,value in sorted(MAPPING.items(),key=lambda pair:-len(pair[0])):
            code=code.replace(repr(name),repr(value))
        programs[after+'_client.py']=code
    for name,code in programs.items():ast.parse(code,filename=name)
    return programs


def contract():
    value=ui.contract()
    value.update(candidate='same_actor_native_world_glint_capability',phase=PHASE,states=list(STATES),
                 source_sha256=digest(Path(__file__).read_bytes()),ui_generator_sha256=digest(Path(ui.__file__).read_bytes()),
                 native_world_only=True,projection_tested=False,projection_frame_content_accepted=False,
                 world_fixed_roi=[0,111,1994,1105],world_ordinary_minimum_stable_pixels=80,
                 world_body_minimum_magenta_pixels=80,world_restored_maximum_pixels=2,
                 world_glint_minimum_changed_pixels=80,world_glint_minimum_temporal_pixels=40)
    return value


def prepare(output):return ui.server.client_route.prepare(output,snippets,contract,__file__)
def verify(bundle):return ui.server.client_route.verify(bundle,snippets,contract,__file__)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify'))
    parser.add_argument('path')
    args=parser.parse_args()
    result=prepare(args.path) if args.command=='prepare' else verify(args.path)
    print(digest((Path(args.path)/'plan.json').read_bytes()))
