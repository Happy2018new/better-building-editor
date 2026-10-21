"""Private business regressions and read-only runtime receipt review; never launches MC."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'behavior_pack/modern_projection'),str(ROOT/'tests')]
import compare_topology_v1 as compare
import trial_fixtures_v1 as fixtures
import native_receipts_v2 as native
import analyze_actual_native_v2 as actual
from projection.block_registry import canonical,states,aux_values
from projection.cell import AIR,make_cell,foreground,background
from projection.model import Document
from projection.liquid_product_deployment import candidate_profile
from test_concrete_floor_context import _tile

WIRE='minecraft:redstone_wire'
STONE=('minecraft:stone',0)
WATER=('minecraft:water',0)
POSITIONS=((3,2,3),(15,16,15))
NEGATIVE=('wet-wire','wet-support','reverse-wire','reverse-support',
          'two-solid-wire','two-solid-support','stone-support')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def check_document(doc,dropped,profile):
    before=copy.deepcopy(doc.to_data())
    targets=doc.palette_data()
    old=compare.outputs(compare.base,doc,targets,profile)
    new=compare.outputs(compare.candidate,doc,targets,profile)
    count=0
    for position in doc.blocks:
        prior=[_tile(output,position) for output in old]
        after=[_tile(output,position) for output in new]
        assert prior[0]==prior[1]==prior[2],'Baseline preparation paths disagree'
        assert after[0]==after[1]==after[2],'Candidate preparation paths disagree'
        removed=[row for row in prior[0] if row not in after[0]]
        assert not [row for row in after[0] if row not in prior[0]],'Candidate added native input'
        if position in dropped:
            below=(position[0],position[1]-1,position[2])
            assert removed==[('common',canonical(foreground(doc.blocks[below])),(0,-1,0))]
            count+=1
        else:assert not removed,('Unadmitted target changed',position,removed)
        assert [row for row in prior[0] if row[2]!=(0,-1,0)]==[
          row for row in after[0] if row[2]!=(0,-1,0)],'Another neighbor changed'
        for layer in ('common','extra'):
            own=[row for row in prior[0] if row[0]==layer and row[2]==(0,0,0)]
            assert all(row in after[0] for row in own),'Own native target was removed'
    assert before==doc.to_data(),'Logical two-layer source changed'
    return count


def offline():
    source_sha=sha(ROOT/'behavior_pack/modern_projection/projection/render_context.py')
    candidate_sha=sha(HERE/'candidate-drop-direct-only/render_context.py')
    assert aux_values(WIRE)==tuple(range(16))
    assert [states((WIRE,power)) for power in range(16)]==[{'redstone_signal':power} for power in range(16)]
    colors=[canonical(('minecraft:concrete',color)) for color in range(16)]
    assert len(set(colors))==16
    positive=negative=mixed=changed=0
    for archived in (False,True):
        for color in range(16):
            support=('minecraft:concrete',color) if archived else colors[color]
            for power in range(16):
                for target in POSITIONS:
                    below=(target[0],target[1]-1,target[2])
                    doc=Document((32,32,32),{target:(WIRE,power),below:support})
                    changed+=check_document(doc,{target},None);positive+=1
    # Cross every signal with white and both extrema with every color.
    # This negative cohort is stated explicitly; it is not the full 16x16 product.
    pairs=sorted({(color,power) for color in range(16) for power in (0,15)}|
                 {(0,power) for power in range(16)})
    product_profile=candidate_profile()
    for color,power in pairs:
        support=colors[color];wire=(WIRE,power)
        for kind in NEGATIVE:
            for target in POSITIONS:
                below=(target[0],target[1]-1,target[2])
                front,lower=wire,support
                if kind=='wet-wire':front=make_cell(wire,WATER)
                elif kind=='wet-support':lower=make_cell(support,WATER)
                elif kind=='reverse-wire':front=make_cell(WATER,wire)
                elif kind=='reverse-support':lower=make_cell(WATER,support)
                elif kind=='two-solid-wire':front=make_cell(wire,STONE)
                elif kind=='two-solid-support':lower=make_cell(support,STONE)
                else:lower=STONE
                for profile in (None,product_profile):
                    doc=Document((32,32,32),{target:front,below:lower})
                    assert check_document(doc,set(),profile)==0;negative+=1
    for profile in (None,product_profile):
        cells={};drop=set()
        for index in range(16):
            target=(index*4+1,2,1);below=(target[0],1,1)
            wire=(WIRE,index);support=colors[index]
            cells[target]=make_cell(wire,WATER) if index%4 in (1,3) else wire
            cells[below]=make_cell(support,WATER) if index%4 in (2,3) else support
            if index%4==0:drop.add(target)
        changed+=check_document(Document((64,4,4),cells),drop,profile);mixed+=1
    assert sha(ROOT/'behavior_pack/modern_projection/projection/render_context.py')==source_sha
    assert sha(HERE/'candidate-drop-direct-only/render_context.py')==candidate_sha
    return {'schema':'wire-r27-private-business-offline-v3','passed':True,
      'positive_cases':positive,'negative_cases':negative,'mixed_cache_documents':mixed,
      'changed_target_tiles':changed,'wire_signals':list(range(16)),'concrete_colors':colors,
      'positive_cartesian':'16 signals x 16 colors x named/archive inputs x two chunk positions',
      'negative_signal_color_pairs':pairs,'negative_kinds':NEGATIVE,
      'negative_owner_modes':['None','actual ProductLiquidProfile'],
      'preparation_paths':['reference palette','incremental builder','context batches'],
      'all_other_neighbors_exact':True,'all_own_targets_retained':True,'logical_two_layers_unchanged':True,
      'candidate_sha256':candidate_sha,'baseline_sha256':source_sha,'runtime_calls':0,
      'actual_native_paths_verified':False,'GPU_qualified':False,'manual_closures':0}


def runtime_review(paths):
    reports=[(path,json.loads(path.read_bytes())) for path in paths]
    names=[report['fixture'] for path,report in reports]
    assert len(names)==len(set(names)) and set(names)==set(fixtures.NAMES),'All eight distinct fixtures required'
    results=[]
    expected_plan=sha(HERE/'frozen-trial-plan-v3.json')
    expected_manifest=sha(HERE/'project-manifest-v3.json')
    for path,report in reports:
        assert report['completed'] and report['restored'] and not report['cleanup_errors']
        assert report['runtime_and_host_unchanged']
        assert report['plan_sha256']==expected_plan and report['manifest_sha256']==expected_manifest
        assert report['observer_retirement']['verified'] and report['observer_retirement']['all_phase_exports_exhaustive']
        assert len(report['samples'])==12
        item=fixtures.fixture(report['fixture']);seen=set();maps=[]
        for number,sample in enumerate(report['samples'],1):
            assert sample['completed']
            snapshot=json.loads(path.with_name('phase-%02d-native.json'%number).read_bytes())
            validation=native.validate_phase(snapshot,sample['expected'],sample['helper_selection']['helper_ids'],
              report['audit_begin']['geometry_function_id'],seen)
            assert validation['source_kinds']==['shader-spare-seed','world-prepared']
            maps.append(actual.phase_maps(snapshot))
        changes=[]
        for start in (0,4,8):
            assert [row['mode'] for row in report['samples'][start:start+4]]==['base','repeat','candidate','restored']
            assert maps[start]==maps[start+1]==maps[start+3]
            changes.extend(actual.compare_actual(maps[start],maps[start+2],item))
        results.append({'fixture':report['fixture'],'report_sha256':sha(path),
          'actual_native_phases':12,'actual_full_and_spare_paths_each_phase':True,
          'actual_direct_lower_copy_changes':len(changes),'negative_native_inputs_unchanged':not changes,
          'restoration_verified':True})
    return {'schema':'wire-r27-private-business-runtime-input-review-v3',
      'actual_native_business_inputs_verified':True,'fixtures':results,'runtime_calls':0,
      'scope':'Read-only actual native receipt review. Root must separately approve original PNG shape/thickness; this does not qualify GPU or product integration.',
      'GPU_qualified':False,'manual_closures':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--offline',action='store_true')
    mode.add_argument('--runtime-reports',nargs='+',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.output:assert not args.output.exists(),'Existing regression receipts are never overwritten'
    result=offline() if args.offline else runtime_review(args.runtime_reports)
    if args.output:
        assert args.output.resolve().is_relative_to(HERE)
        with args.output.open('xb') as stream:stream.write((json.dumps(result,indent=2)+'\n').encode('ascii'))
    print(json.dumps(result))


if __name__=='__main__':main()
