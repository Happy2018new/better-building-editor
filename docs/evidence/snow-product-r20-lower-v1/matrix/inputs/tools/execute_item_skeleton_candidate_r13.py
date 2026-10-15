"""Score and execute the same-actor opaque-skeleton control with finite R15 IO."""
import argparse
import json
from pathlib import Path

from isolated_diagnostic_module import load
import prepare_item_skeleton_candidate_r13 as candidate

shared=load('execute_client_anchor_depth_candidate_r15')

shared.candidate = candidate
ROOT = candidate.ROOT
dependencies = shared.dependencies
HELPERS = shared.HELPERS
HELPER_PINS = shared.HELPER_PINS
preflight = shared.preflight
execute_probe = shared.execute_probe


def validate_state(label, status, initial, native, binding_id):
    expected = dict(initial['ui_params'])
    setup = initial['skeleton_setup']
    if (setup.get('model')!=candidate.MODEL or type(setup.get('model_id')) is not int or setup['model_id']<0 or
            status.get('skeleton_setup')!=setup or type(status.get('model_id')) is not int or status['model_id']<0 or
            status['control']!=label or status['last_submission']!=expected or
            status['ui_params']!=expected or status['attachments']!=native['attachments'] or
            native['control']!=label or native['actor']!=initial['actor'] or native['journal']!=status['journal']):
        raise ValueError('Actual same-actor skeleton/model/submission identity changed')
    renders=[row for row in native['journal'] if row['operation']=='RenderEntity:'+label]
    if len(renders)!=1 or renders[0].get('state')!='returned' or renders[0].get('value') is not True:
        raise ValueError('Native RenderEntity acknowledgement changed')
    attachments=status['attachments']
    if label in (candidate.STATES[0],'ui_body'):
        if attachments or native['native_item'] is not None:
            raise ValueError('Item was bound before the opaque-body positive gate')
        return binding_id
    if len(attachments)!=1:
        raise ValueError('Exactly one owned attachment is required')
    row=attachments[0]
    identity=row['id']
    if type(identity) is not int or identity<0 or (binding_id is not None and identity!=binding_id):
        raise ValueError('Owned item binding identity changed')
    if (row['item']!={'isEnchanted':False,'newAuxValue':0,'newItemName':'minecraft:diamond_sword','userData':{}} or
            row['offset']!=[0.,0.,0.] or row['rotation']!=[0.,0.,0.] or row['scale']!=1. or not row['item_nonmutation']):
        raise ValueError('Original ordinary sword payload or transform changed')
    if label=='ui_plain':
        expected_item={'id':identity,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}
        if row['state']!='bound' or native['native_item']!=expected_item or row.get('remove_attempted'):
            raise ValueError('Native skeleton binding readback changed')
    elif row['state']!='removed' or row.get('remove_result') is not True or native['native_item'] is not None:
        raise ValueError('Owned item removal changed')
    return identity


def score_probe(report, allow_partial=False):
    from PIL import Image
    helpers=dependencies()
    capture_payload=helpers['flat_frame_item_visual_checks'].capture_payload
    count=helpers['verify_snow_plant_visibility'].count
    anchor=helpers['probe_client_anchor_paper_doll']
    if report['plan_sha256']!=candidate.EXACT_PLAN_SHA256:
        raise ValueError('Exact prospective skeleton candidate changed')
    if not allow_partial and (not report.get('completed') or not report.get('restored') or report.get('cleanup_errors')):
        raise ValueError('Complete restored skeleton runtime is required')
    if list(report['states'])!=list(candidate.STATES)[:len(report['states'])]:
        raise ValueError('Prospective skeleton state order changed')
    images, body_pixels={},{}
    markers=True
    last_clock=report['actor_ready']['clock']
    layout_expected=None
    binding_id=None
    for label,row in report['states'].items():
        if len(row['frames'])!=2:
            raise ValueError('Two fresh frames per state are required')
        images[label]=[]
        for frame in row['frames']:
            if frame['fixed_roi']!=[0,111,1994,1105]:
                raise ValueError('Frozen UI ROI changed')
            status=frame['status']
            binding_id=validate_state(label,status,report['initial'],row['native'],binding_id)
            if (status['clock']<=last_clock or not status['camera_matches'] or not status['player_foot_matches'] or
                    not status['root_visible'] or status['actor']!=report['initial']['actor']):
                raise ValueError('Skeleton frame clock, actor, camera or foot changed')
            last_clock=status['clock']
            layout=shared.layout_readback(anchor,frame['tree'],status,report['initial'])
            if layout!=frame['layout'] or (layout_expected is not None and layout!=layout_expected):
                raise ValueError('Frozen native layout changed')
            layout_expected=layout
            mapping=anchor.base.marker_mapping(frame['capture'],layout,report['frozen_marker_calibration'])
            markers=markers and mapping['passed'] and mapping==frame['marker_mapping']
            if anchor.base.frame_crop(layout,frame['capture']['size'],mapping)!=frame['paper_doll_roi']:
                raise ValueError('Native PaperDoll ROI changed')
            with Image.open(capture_payload(frame['capture'])) as source:
                if list(source.size)!=[1994,1105]:
                    raise ValueError('Native capture extent changed')
                images[label].append(source.convert('RGB').crop(tuple(shared.positive_roi(frame))))
        if label in candidate.POSITIVE_STATES:
            body_pixels[label]=[shared.cow_pixels(frame) for frame in row['frames']]
    positive=bool(markers and body_pixels and all(value>=80 for values in body_pixels.values() for value in values))
    score={'schema':1,'ui_marker_gate_passed':markers,'skeleton_positive_pixels':body_pixels,
           'positive_skeleton_gate_passed':positive,'classification':'partial_controls',
           'production_rendering_accepted':False,'editor_frame_content_accepted':False,
           'shared_depth_accepted':False,'enchantment_glint_accepted':False,'enchantment_tested':False}
    if not all(label in images for label in candidate.STATES):
        return score
    refs=images['ui_body']+images['ui_body_restored']
    plain=count(anchor.stable_difference(images['ui_plain'],refs))
    restored=count(anchor.stable_difference(images['ui_body_restored'],images['ui_body']))
    if not positive or restored>2:
        classification='invalid_body_or_restore_controls'
    elif plain>=80:
        classification='same_actor_skeleton_ordinary_item_positive_requires_visual_review'
    else:
        classification='same_actor_skeleton_ordinary_item_zero_with_body_positive'
    score.update(stable_plain_pixels=plain,restored_difference_pixels=restored,
                 classification=classification,visual_review_required=True)
    return score


shared.validate_state=validate_state
shared.score_probe=score_probe


def main():
    parser=argparse.ArgumentParser(description='Offline skeleton score only; no SDK dispatch')
    parser.add_argument('report')
    parser.add_argument('--output',required=True)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args()
    bundle=Path(args.candidate).resolve(strict=True)
    candidate.verify(bundle)
    candidate.EXACT_PLAN_SHA256=candidate.digest((bundle/'plan.json').read_bytes())
    output=Path(args.output)
    if output.exists() or output.with_name(output.name+'.tmp').exists():
        raise ValueError('Preserve existing offline score evidence')
    source=Path(args.report).resolve(strict=True)
    score=score_probe(json.loads(source.read_bytes()),args.allow_partial)
    score.update(runtime_report={'path':str(source),'sha256':candidate.digest(source.read_bytes())},
                 scorer_sha256=candidate.digest(Path(__file__).read_bytes()))
    dependencies()['execute_frame_item_translation'].save_report(output,score)
    print(json.dumps(score))


if __name__=='__main__':
    main()
