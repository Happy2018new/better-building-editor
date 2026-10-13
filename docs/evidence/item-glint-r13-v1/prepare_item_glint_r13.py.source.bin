"""Freeze ordinary orientation first, then a separate same-pose glint comparison."""
import argparse
import ast
import os
from pathlib import Path

import prepare_item_server_skeleton_r13 as server

ROOT, MODEL, ATTRIBUTE = server.ROOT, server.MODEL, server.ATTRIBUTE
SERVER_ATTRIBUTE=server.SERVER_ATTRIBUTE
POSITIVE_STATES=server.POSITIVE_STATES
POSITIVE_NAME,POSITIVE_TARGET='skeleton',server.POSITIVE_TARGET
UI=dict(server.UI,scale=1.4)
digest,archived_files,resources=server.digest,server.archived_files,server.resources
EXACT_PLAN_SHA256=None
PHASE=os.environ.get('MCDEV_ITEM_R13_PHASE','orientation')
POSE=os.environ.get('MCDEV_ITEM_R13_POSE','x90')
ROTATIONS={'x90':(90.,0.,0.),'y90':(0.,90.,0.)}


def configure(phase,pose):
    global PHASE,POSE,STATES
    if phase not in ('orientation','glint') or pose not in ROTATIONS:
        raise ValueError('Only prospectively declared orientation/glint poses are supported')
    PHASE,POSE=phase,pose
    middle=('ui_plain_x90','ui_plain_y90') if phase=='orientation' else ('ui_plain_'+pose,'ui_enchanted','ui_enchanted_later')
    STATES=(POSITIVE_STATES[0],'ui_body')+middle+('ui_body_restored',POSITIVE_STATES[1])


configure(PHASE,POSE)


def state_parameters(label):
    if label in ('ui_plain_x90','ui_plain_y90'):
        return False,ROTATIONS[label.removeprefix('ui_plain_')]
    if label in ('ui_enchanted','ui_enchanted_later'):
        return True,ROTATIONS[POSE]
    return None,None


def snippets(nonce):
    programs=server.snippets(nonce)
    for name in server.STATES:
        programs.pop(name+'_client.py')
    programs['install_client.py']=programs['install_client.py'].replace("'scale': 0.35", "'scale': 1.4")
    programs['open_ui_client.py']=programs['open_ui_client.py'].replace('scale=.35,','scale=1.4,')
    programs['destroy_server.py']=programs['destroy_server.py'].replace(
        "destroyed=saved['actor'] is None or saved.get('destroy_result') is True",
        "kind=api.GetEngineCompFactory().CreateEngineType(saved['actor']).GetEngineTypeStr() if saved['actor'] is not None else None\n saved['server_absence_kind']=kind\n destroyed=saved['actor'] is None or (saved.get('destroy_result') is True and kind is None)")
    original=server.snippets(nonce)['ui_plain_client.py']
    begin=original.index("if label=='ui_plain':")
    end=original.index("native_item=None",begin)
    action="""enchanted,rotation=STATE_PARAMETERS
if enchanted is not None:
 if saved['current'] is not None:
  old=saved['attachments'][-1]
  assert old['state']=='bound' and old['id']==saved['current']
  old['remove_attempted']=True
  old['remove_result']=itemcomp.SetBindBoneForBindItem(saved['actor'],old['id'],'',False)
  assert old['remove_result'] is True
  old['state']='removed'
  saved['current']=None
 item=deepcopy(saved['plain'])
 item['isEnchanted']=enchanted
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','attempted':True,'id':None,'offset':[0.,0.,0.],'rotation':list(rotation),'scale':1.}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToSkeletonModel(saved['actor'],item,'root',False,(0.,0.,0.),rotation,1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert valid and row['item_nonmutation'],row
 saved['current']=identity
elif label=='ui_body_restored':
 assert saved['current'] is not None
 row=saved['attachments'][-1]
 row['remove_attempted']=True
 row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['actor'],row['id'],'',False)
 assert row['remove_result'] is True
 row['state']='removed'
 saved['current']=None
"""
    for label in STATES:
        parameters=state_parameters(label)
        # A later temporal sample retains the exact enchanted binding.
        code=action.replace('STATE_PARAMETERS',repr(parameters))
        if label=='ui_enchanted_later':
            code="assert saved['current'] is not None and saved['attachments'][-1]['item']['isEnchanted'] is True\nrotation=%r\n" % (ROTATIONS[POSE],)
        source=original[:begin]+code+original[end:]
        source=source.replace("label='ui_plain'",'label='+repr(label))
        source=source.replace("'rotation':(0.,0.,0.)", "'rotation':rotation")
        programs[label+'_client.py']=source
    for name,source in programs.items():ast.parse(source,filename=name)
    return programs


def contract():
    value=server.contract()
    value.update(candidate='server_skeleton_'+PHASE,states=list(STATES),phase=PHASE,selected_pose=POSE,
                 ui=dict(UI,scale=1.4),source_sha256=digest(Path(__file__).read_bytes()),
                 server_generator_sha256=digest(Path(server.__file__).read_bytes()),
                 enchantment_tested=PHASE=='glint',binding_count=2,ordinary_minimum_stable_pixels=80,
                 broadside_minimum_bbox_ratio=.12,glint_minimum_changed_pixels=80,
                 glint_minimum_temporal_pixels=40,server_absence_engine_type_readback=True,
                 production_rendering_accepted=False,enchantment_glint_accepted=False)
    return value


def prepare(output):return server.client_route.prepare(output,snippets,contract,__file__)
def verify(bundle):return server.client_route.verify(bundle,snippets,contract,__file__)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify'))
    parser.add_argument('path')
    parser.add_argument('--phase',choices=('orientation','glint'),default='orientation')
    parser.add_argument('--pose',choices=tuple(ROTATIONS),default='x90')
    args=parser.parse_args()
    configure(args.phase,args.pose)
    result=prepare(args.path) if args.command=='prepare' else verify(args.path)
    print(digest((Path(args.path)/'plan.json').read_bytes()))
