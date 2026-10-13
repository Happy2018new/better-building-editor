"""Finite same-actor comparison with pixel gates that never imply product acceptance."""
from copy import deepcopy
import argparse
import json
from pathlib import Path

import execute_item_server_skeleton_r13 as server
import prepare_item_glint_r13 as candidate

shared=server.body_runtime.shared
server.candidate=candidate
server.body_runtime.candidate=candidate
shared.candidate=candidate
ROOT=candidate.ROOT
dependencies,HELPERS,HELPER_PINS=server.dependencies,server.HELPERS,server.HELPER_PINS
preflight=shared.preflight
execute_probe=server.execute_probe
original_layout=shared.layout_readback


def layout_readback(anchor,tree,status,initial):
    adapted=deepcopy(tree)
    pending=[adapted]
    dolls=[]
    while pending:
        node=pending.pop()
        pending.extend(node.get('children',[]))
        if node.get('key')=='native_item_probe_doll':dolls.append(node)
    if len(dolls)!=1 or dolls[0].get('props',{}).get('scale')!=1.4:
        raise ValueError('Frozen prospective PaperDoll scale changed')
    dolls[0]['props']['scale']=.35
    result=original_layout(anchor,adapted,status,initial)
    result['props']['scale']=1.4
    return result


def validate_state(label,status,initial,native,binding_id):
    setup=initial['skeleton_setup']
    if (setup.get('model')!=candidate.MODEL or type(setup.get('model_id')) is not int or setup['model_id']<0 or
        status.get('skeleton_setup')!=setup or type(status.get('model_id')) is not int or status['model_id']<0 or
        status['control']!=label or status['last_submission']!=initial['ui_params'] or
        status['ui_params']!=initial['ui_params'] or status['attachments']!=native['attachments'] or
        native['control']!=label or native['actor']!=initial['actor'] or native['journal']!=status['journal']):
        raise ValueError('Frozen skeleton actor/submission/readback changed')
    renders=[r for r in native['journal'] if r['operation']=='RenderEntity:'+label]
    if len(renders)!=1 or renders[0].get('state')!='returned' or renders[0].get('value') is not True:
        raise ValueError('Native rendering acknowledgment changed')
    expected=[]
    for state in candidate.STATES[:candidate.STATES.index(label)+1]:
        enchanted,rotation=candidate.state_parameters(state)
        if enchanted is not None and state!='ui_enchanted_later':expected.append((state,enchanted,rotation))
    rows=status['attachments']
    if len(rows)!=len(expected):raise ValueError('Owned attachment ledger length changed')
    identities=tuple(row['id'] for row in rows)
    if binding_id is not None and identities[:len(binding_id)]!=binding_id:
        raise ValueError('A previously observed exact item binding ID changed')
    active=candidate.state_parameters(label)[0] is not None
    for index,(row,(state,enchanted,rotation)) in enumerate(zip(rows,expected)):
        if (type(row['id']) is not int or row['id']<0 or row['control']!=state or
            row['item']!={'isEnchanted':enchanted,'newAuxValue':0,'newItemName':'minecraft:diamond_sword','userData':{}} or
            row['offset']!=[0.,0.,0.] or row['rotation']!=list(rotation) or row['scale']!=candidate.ITEM_SCALE or not row['item_nonmutation']):
            raise ValueError('Prospective item payload, rotation or exact owned ID changed')
        if active and index==len(rows)-1:
            readback={'id':row['id'],'offset':[0.,0.,0.],'rotation':list(rotation),'scale':candidate.ITEM_SCALE}
            if row['state']!='bound' or row.get('remove_attempted') or native['native_item']!=readback:
                raise ValueError('Active exact binding readback changed')
        elif row['state']!='removed' or row.get('remove_result') is not True:
            raise ValueError('Earlier owned attachment removal not verified')
    if not active and native['native_item'] is not None:raise ValueError('Unexpected native item after removal')
    return identities


def score_probe(report,allow_partial=False):
    from PIL import Image,ImageChops
    helpers=dependencies()
    anchor=helpers['probe_client_anchor_paper_doll']
    count=helpers['verify_snow_plant_visibility'].count
    capture_payload=helpers['flat_frame_item_visual_checks'].capture_payload
    if report['plan_sha256']!=candidate.EXACT_PLAN_SHA256:raise ValueError('Frozen plan hash changed')
    if not allow_partial and (not report.get('completed') or not report.get('restored') or report.get('cleanup_errors')):
        raise ValueError('Complete restored probe required')
    if list(report['states'])!=list(candidate.STATES)[:len(report['states'])]:raise ValueError('Frozen state ordering changed')
    images,positive={},{}
    markers=True
    clock=report['actor_ready']['clock']
    layout=None
    binding_id=None
    for label,row in report['states'].items():
        if len(row['frames'])!=2:raise ValueError('Two advancing captures per state required')
        images[label]=[]
        for frame in row['frames']:
            status=frame['status']
            binding_id=validate_state(label,status,report['initial'],row['native'],binding_id)
            if (status['clock']<=clock or not status['camera_matches'] or not status['player_foot_matches'] or
                not status['root_visible'] or status['actor']!=report['initial']['actor'] or frame['fixed_roi']!=[0,111,1994,1105]):
                raise ValueError('Capture clock, view, exact actor or frozen ROI changed')
            clock=status['clock']
            actual=layout_readback(anchor,frame['tree'],status,report['initial'])
            if actual!=frame['layout'] or layout is not None and layout!=actual:raise ValueError('Frozen layout changed')
            layout=actual
            mapping=anchor.base.marker_mapping(frame['capture'],layout,report['frozen_marker_calibration'])
            markers=markers and mapping['passed'] and mapping==frame['marker_mapping']
            if anchor.base.frame_crop(layout,frame['capture']['size'],mapping)!=frame['paper_doll_roi']:
                raise ValueError('Native capture mapping changed')
            with Image.open(capture_payload(frame['capture'])) as image:
                if list(image.size)!=[1994,1105]:raise ValueError('Physical capture size changed')
                images[label].append(image.convert('RGB').crop(tuple(shared.positive_roi(frame))))
        if label in candidate.POSITIVE_STATES:
            positive[label]=[shared.cow_pixels(frame) for frame in row['frames']]
    gate=bool(markers and positive and all(v>=80 for values in positive.values() for v in values))
    score={'schema':1,'phase':candidate.PHASE,'ui_marker_gate_passed':markers,'skeleton_positive_pixels':positive,
           'positive_skeleton_gate_passed':gate,'classification':'partial_controls',
           'production_rendering_accepted':False,'editor_frame_content_accepted':False,'projection_frame_content_accepted':False,
           'shared_depth_accepted':False,'enchantment_glint_accepted':False,'enchantment_tested':candidate.PHASE=='glint'}
    if not all(state in images for state in candidate.STATES):return score
    references=images['ui_body']+images['ui_body_restored']
    restored=count(anchor.stable_difference(images['ui_body_restored'],images['ui_body']))
    plain={}
    masks={}
    for label in candidate.STATES:
        if not label.startswith('ui_plain_'):continue
        mask=anchor.stable_difference(images[label],references)
        masks[label]=mask
        bbox=mask.getbbox()
        ratio=0. if bbox is None else min(bbox[2]-bbox[0],bbox[3]-bbox[1])/float(max(bbox[2]-bbox[0],bbox[3]-bbox[1]))
        interior=bbox is not None and bbox[0]>1 and bbox[1]>1 and bbox[2]<mask.width-1 and bbox[3]<mask.height-1
        plain[label]={'stable_pixels':count(mask),'bbox':bbox,'bbox_ratio':ratio,'inside_frozen_doll_roi':interior}
    qualifying=[(p['stable_pixels'],label) for label,p in plain.items() if p['stable_pixels']>=80 and p['bbox_ratio']>=.12 and p['inside_frozen_doll_roi']]
    score.update(ordinary_poses=plain,restored_difference_pixels=restored,
                 ordinary_broadside_gate=bool(gate and restored<=2 and qualifying))
    if candidate.PHASE=='orientation':
        score.update(selected_pose=max(qualifying)[1].removeprefix('ui_plain_') if qualifying else None,
                     classification='ordinary_broadside_positive_requires_visual_review' if score['ordinary_broadside_gate'] else 'ordinary_broadside_failed')
        return score
    plain_label='ui_plain_'+candidate.POSE
    item_mask=masks[plain_label]
    enchanted=images['ui_enchanted']+images['ui_enchanted_later']
    changed=count(ImageChops.multiply(anchor.stable_difference(enchanted,images[plain_label]),item_mask))
    temporal=Image.new('L',item_mask.size)
    for a,b in zip(enchanted,enchanted[1:]):
        temporal=ImageChops.lighter(temporal,ImageChops.multiply(anchor.stable_difference([a],[b]),item_mask))
    temporal_pixels=count(temporal)
    ordinary_drift=count(anchor.stable_difference([images[plain_label][0]],[images[plain_label][1]]))
    glint=score['ordinary_broadside_gate'] and changed>=80 and temporal_pixels>=40 and ordinary_drift<=2
    score.update(glint_changed_pixels=changed,glint_temporal_pixels=temporal_pixels,ordinary_temporal_pixels=ordinary_drift,
                 diagnostic_glint_gate_passed=glint,classification='same_pose_glint_positive_requires_visual_review' if glint else 'same_pose_glint_failed',
                 visual_review_required=True)
    return score


shared.layout_readback=layout_readback
shared.validate_state=validate_state
shared.score_probe=score_probe


def main():
    parser=argparse.ArgumentParser(description='Offline exact frozen comparison; no SDK calls')
    parser.add_argument('report')
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    plan=json.loads((Path(args.candidate)/'plan.json').read_bytes())
    candidate.configure(plan['phase'],plan['selected_pose'])
    candidate.verify(args.candidate)
    candidate.EXACT_PLAN_SHA256=candidate.digest((Path(args.candidate)/'plan.json').read_bytes())
    output=Path(args.output)
    if output.exists():raise ValueError('Preserve prior score')
    source=Path(args.report)
    score=score_probe(json.loads(source.read_bytes()))
    score.update(runtime_sha256=candidate.digest(source.read_bytes()),scorer_sha256=candidate.digest(Path(__file__).read_bytes()))
    dependencies()['execute_frame_item_translation'].save_report(output,score)
    print(json.dumps(score))


if __name__=='__main__':main()
