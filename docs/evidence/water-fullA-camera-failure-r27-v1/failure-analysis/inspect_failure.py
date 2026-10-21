"""Replay the original extraction stages; retain the failed original camera gate."""
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image,ImageChops,ImageDraw

WORK=Path(__file__).resolve().parent
HOST=WORK.with_name('water-merged-fullA-v1')
ROOT=WORK.parents[2]
PROJECT=ROOT/'.runtime/projects/water-r27-merged-flow-editor-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    out=WORK/'camera-failure-readonly-v1.json'
    assert not out.exists()
    report_path=HOST/'product-v2-camera-native-v1.json'
    report_raw=report_path.read_bytes()
    camera=json.loads(report_raw)
    sys.path.insert(0,str(PROJECT/'tools'))
    import verify_camera_projection as original
    paths=[report_path,HOST/'group-execution-v1.json',HOST/'independent-restore-v1.json',
        HOST/'launch/exact-exit.json',HOST/'world-baseline-v1.json']
    source_binding=json.loads((HOST/'final-source-binding-v1.json').read_bytes())
    assert sha(Path(original.__file__).read_bytes())==source_binding['source_sha256']['tools/verify_camera_projection.py']
    row=next(row for row in camera['views'] if row['view']=='tilted')
    for item in (row['shown'],row['hidden']):
        path=Path(item['path']);paths.append(path)
        assert sha(path.read_bytes())==item['sha256']
    before={str(path):sha(path.read_bytes()) for path in paths}
    shown=Image.open(row['shown']['path']).convert('RGB')
    hidden=Image.open(row['hidden']['path']).convert('RGB')
    red,green,blue=shown.split()
    spread=original.maximum(Image.merge('RGB',(ImageChops.difference(red,green),
        ImageChops.difference(red,blue),ImageChops.difference(green,blue))))
    neutral=spread.point(lambda value:255 if value<13 else 0)
    brightness=red.point(lambda value:255 if value>50 else 0)
    center=Image.new('L',shown.size)
    ImageDraw.Draw(center).rectangle((shown.width*.3,shown.height*.25,shown.width*.7,shown.height*.75),fill=255)
    contribution=original.maximum(ImageChops.difference(shown,hidden)).point(lambda value:255 if value>20 else 0)
    raw=ImageChops.multiply(ImageChops.multiply(ImageChops.multiply(neutral,brightness),center),contribution)
    left,top,right,bottom=raw.getbbox()
    pixels=raw.load()
    remaining={(x,y) for y in range(top,bottom) for x in range(left,right) if pixels[x,y]}
    components=[]
    while remaining:
        first=remaining.pop();pending=deque((first,));items={first}
        while pending:
            x,y=pending.popleft()
            for point in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if point in remaining:
                    remaining.remove(point);items.add(point);pending.append(point)
        components.append(items)
    components.sort(key=len,reverse=True)
    component_rows=[]
    for index,component in enumerate(components):
        component_rows.append({'rank':index+1,'pixels':len(component),
            'bounds':[min(p[0] for p in component),min(p[1] for p in component),
                      max(p[0] for p in component)+1,max(p[1] for p in component)+1]})
    derived={}
    for name,image in (('original_pre_component_mask.png',raw),
                       ('original_final_mask_replay.png',original.stone_signal(row['shown']['path'],row['hidden']['path']))):
        path=WORK/name
        assert not path.exists()
        image.save(path)
        derived[name]={'path':str(path),'sha256':sha(path.read_bytes()),'bounds':image.getbbox(),'pixels':image.histogram()[255]}
    assert ImageChops.difference(Image.open(row['signal']).convert('L'),
        Image.open(WORK/'original_final_mask_replay.png').convert('L')).getbbox() is None
    sample=[]
    # These are inspection coordinates inside the original full-size extraction;
    # they never replace its fixed center rectangle or any qualification ROI.
    for y in range(334,343):
        value=shown.getpixel((640,y))
        sample.append({'y':y,'selected_pixels_original_bbox':sum(bool(pixels[x,y]) for x in range(left,right)),
            'center_shown_rgb':value,'center_shown_channel_spread':max(value)-min(value),
            'center_contribution_selected':bool(contribution.getpixel((640,y))),
            'center_neutral_selected':bool(neutral.getpixel((640,y)))})
    group=json.loads((HOST/'group-execution-v1.json').read_bytes())
    restore=json.loads((HOST/'independent-restore-v1.json').read_bytes())
    exit_report=json.loads((HOST/'launch/exact-exit.json').read_bytes())
    result={'schema':1,'passed':False,'scope':'Read-only explanation of original failed calibration extraction; no new acceptance gate',
        'original_camera_report_sha256':sha(report_raw),'inspector_sha256':sha(Path(__file__).read_bytes()),
        'original_analyzer_sha256':sha(Path(original.__file__).read_bytes()),
        'original_camera_passed':camera['passed'],'original_camera_completed':camera['completed'],
        'original_camera_restored':camera['restored'],'original_cleanup_errors':camera['cleanup_errors'],
        'original_limits':camera['limits'],'original_common_vertical_fov':camera['vertical_fov'],
        'original_view_results':[{key:item[key] for key in ('view','passed','fit','camera','pose')} for item in camera['views']],
        'tilted_raw_mask_bounds':raw.getbbox(),'tilted_raw_mask_pixels':raw.histogram()[255],
        'four_neighbor_components':component_rows,'original_row_pixel_observations':sample,'derived_stage_images':derived,
        'observation':'Original neutral test rejects the one-pixel seam row; four-neighbor components split top and front; original largest_component retains only front.',
        'rendered_top_missing_claimed':False,
        'rendered_water_geometry_or_camera_verified':False,'A_cells_attempted':0,'A_bursts_attempted':0,
        'camera_fixture_relation':{'calibration_cube_only':True,'stone_fixture':camera['fixture'],
            'water_world_fixture_created':False,
            'note':'The original stone calibration gate failed before product probe starts; no actual water surface or water world camera was captured in this session.'},
        'group_completed':group['completed'],'group_elapsed_seconds':group['elapsed_seconds'],
        'independent_restore_passed':restore['restored'],'source_unchanged_in_original_independent_restore':restore['source_unchanged'],
        'ordinary_stop_exit_code':group['ordinary_stop']['exit_code'],'exact_identities_absent':group['exact_identities_absent'],
        'final_same_handle_exit':exit_report,'observed_inputs_sha256_before':before,
        'observed_inputs_unchanged':all(sha(Path(path).read_bytes())==expected for path,expected in before.items()),
        'source_or_original_report_mutated':False,'ROI_or_threshold_or_FOV_fitting_changed':False,
        'formal_A_accepted':False,'world_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0}
    assert result['observed_inputs_unchanged']
    with out.open('x',encoding='ascii') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({'report_sha256':sha(out.read_bytes()),'components':component_rows,
        'original_gate_passed':camera['passed'],'A_cells_attempted':0,'observed_inputs_unchanged':True}))


if __name__=='__main__':
    main()
