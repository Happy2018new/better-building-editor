"""Score public flat-icon bodies against bitmap geometry and real frame controls."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection.item_icon_data import ITEMS
from analyze_item_sprite_product import expected_mask,body_measurement,temporal_measurement,mask_row,expanded,LIMITS
from analyze_item_sprite_closeup import native_body_measurement,native_comparison
from analyze_liquid_workspace import capture_failures,rgb,difference_mask
from item_sprite_capture_contract import scene_layout,paired_layout_matches,camera_matches,snapshot_digest


def target(camera):
    pitch,yaw=map(math.radians,camera['rotation'][:2])
    direction=(math.sin(yaw)*math.cos(pitch),-math.sin(pitch),-math.cos(yaw)*math.cos(pitch))
    return [camera['position'][axis]+direction[axis] for axis in range(3)]


def empty_body_measurement(shown,hidden,expected):
    unexpected=difference_mask(shown,hidden,expanded(expected),LIMITS['rgb_delta'])
    return {'unexpected_pixels':int(unexpected.sum()),
            'passed':int(unexpected.sum())<=LIMITS['maximum_control_motion_pixels']}


def analyze(source,output,world_plain_only=False):
    report=json.loads(source.read_bytes())
    output.mkdir(parents=True,exist_ok=False)
    captures=dict((row['label'],row) for row in report['captures'])
    failures=capture_failures(dict((key,row['capture']) for key,row in captures.items()),report['session'])
    if (not report.get('source_unchanged') or report.get('launch_sources')!=report.get('sources_after') or
            snapshot_digest(report.get('launch_sources',{}))!=report.get('launch_sources_sha256')):
        failures.append('Source snapshot changed during capture or was not verified')
    if report.get('native_item_shader_errors'):
        failures.append('Native item shader compilation failed')
    result={'schema':1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'capture_failures':failures,'cases':[],'production_qualified':False,
            'scope':'Static measured flat-icon geometry and actual native frame body; animation measured separately'}
    result['resource_contract']=report.get('resource_contract')
    result['profile_mode']=report.get('profile_mode','candidate')
    result['view_configuration']=report.get('view_configuration',{})
    plain_only=bool(world_plain_only or result['view_configuration'].get('native_target_plain'))
    result['world_measured_modes']=['plain'] if plain_only else ['plain','enchanted']
    result['requested_cases']=report.get('requested_cases',[case['id'] for case in report['cases']])
    result['completed_cases']=[case['id'] for case in report['cases']
                               if case.get('measurement_completed',report['completed'])]
    result['matrix_completed']=set(result['requested_cases'])==set(result['completed_cases'])
    if not result['completed_cases'] and not report.get('closeup',{}).get('completed'):
        failures.append('No fully measured cases')
    if len(result['completed_cases'])!=len(report['cases']):
        failures.append('A case did not complete its measurements and restoration')
    calibration=report['camera_calibration']
    pose=json.loads((ROOT/'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())['pose']
    crops=[]
    for case in report['cases']:
        if case['id'] not in result['completed_cases']:
            continue
        if case['source'] is None:
            continue
        name,aux=case['source']['item']
        resource=ITEMS[(name,aux)]['ui_model'].removeprefix('modern_projection_item_icon_')
        texture_path=ROOT/'resource_pack/textures/models/modern_projection/item_icons'/(resource+'.png')
        with Image.open(texture_path).convert('RGBA') as texture:
            measured={'id':case['id'],'item':(name,aux),'routes':{}}
            observed_masks={}
            native=case['native_reference']['prepare']['rows'][0]['position']
            positions=case['source'].get('targets',{'plain':(2,3,2),'enchanted':(5,3,2)})
            origin=tuple(native[axis]-positions['plain'][axis] for axis in range(3))
            facing=case['source'].get('facing',2)
            rotation=case['source'].get('rotation_degrees',0.)
            for route in ('editor','full','missing','native'):
                prefix=case['id']+'_'+route
                raw=captures[prefix+'_shown']
                row=copy.deepcopy(raw)
                row['label']='editor_'+case['id'] if route=='editor' else route+'_'+case['id']
                row['state']['origin']=origin
                if route!='editor':
                    row['camera_expected']=dict(raw['camera'],target=target(raw['camera']))
                shown=rgb(raw['capture']['path'])
                hidden_before=rgb(captures[prefix+'_hidden_before']['capture']['path'])
                hidden_after=rgb(captures[prefix+'_hidden_after']['capture']['path'])
                hidden=(hidden_before.astype(np.float64)+hidden_after)/2.
                stable=np.max(np.abs(hidden_before.astype(np.int16)-hidden_after.astype(np.int16)),axis=2)<=3
                size=(shown.shape[1],shown.shape[0])
                rows={}
                for mode,position in positions.items():
                    if route=='native' and mode!='plain':
                        continue
                    if route!='editor' and plain_only and mode!='plain':
                        continue
                    expected=expected_mask(position,row,texture,pose,size,calibration,facing,rotation)
                    body=body_measurement(shown,hidden,expected)
                    observed_masks[(route,mode)]=difference_mask(shown,hidden,expanded(expected),LIMITS['rgb_delta'])
                    body['stable_hidden_fraction']=float(stable[expected].mean()) if expected.any() else 0.
                    rows[mode]=body
                    bounds=mask_row(expected)['bounds']
                    if bounds:
                        box=(max(0,bounds[0]-20),max(0,bounds[1]-20),min(size[0],bounds[2]+20),min(size[1],bounds[3]+20))
                        crop=Image.open(raw['capture']['path']).crop(box).convert('RGB')
                        canvas=Image.new('RGB',(160,180),'white')
                        crop.thumbnail((150,150))
                        canvas.paste(crop,((160-crop.width)//2,25))
                        ImageDraw.Draw(canvas).text((3,3),case['id'].split('.')[-1]+' '+route+' '+mode,fill='black')
                        crops.append(canvas)
                measured['routes'][route]=rows
                if route=='editor':
                    for suffix in ('hidden_before','hidden_after'):
                        if not paired_layout_matches(raw['state'],captures[prefix+'_'+suffix]['state']):
                            failures.append(prefix+' layout differs')
                else:
                    for suffix in ('hidden_before','hidden_after'):
                        if not camera_matches(raw['camera'],captures[prefix+'_'+suffix]['camera']):
                            failures.append(prefix+' camera differs')
            measured['native_body_comparison']={}
            if not case['native_reference'].get('restored'):
                failures.append(case['id']+' native reference was not restored')
            native_mask=observed_masks[('native','plain')]
            for route in ('full','missing'):
                if not camera_matches(captures[case['id']+'_'+route+'_shown']['camera'],
                                      captures[case['id']+'_native_shown']['camera']):
                    failures.append(case['id']+' '+route+' native reference camera differs')
                product=observed_masks[(route,'plain')]
                measured['native_body_comparison'][route]=native_body_measurement(product,native_mask)
                measured['native_body_comparison'][route]['negative_controls']={
                    'blank_rejected':not native_body_measurement(np.zeros_like(product),native_mask)['passed'],
                    'shifted_rejected':not native_body_measurement(np.roll(product,8,axis=1),native_mask)['passed']}
            result['cases'].append(measured)
    if crops:
        sheet=Image.new('RGB',(160*7,180*math.ceil(len(crops)/7)),'white')
        for index,crop in enumerate(crops):
            sheet.paste(crop,((index%7)*160,(index//7)*180))
        sheet.save(output/'contact-sheet.png')
        result['contact_sheet']=str(output/'contact-sheet.png')
    closeup=report.get('closeup',{})
    rows=dict((row['label'],row) for row in closeup.get('captures',()))
    if closeup:
        failures.extend(capture_failures(dict((key,row['capture']) for key,row in rows.items()),report['session']))
    if closeup and (not closeup.get('completed') or closeup.get('cleanup_errors')):
        failures.append('Closeup did not complete or restore')
    result['closeup']={}
    sword=ITEMS[('minecraft:diamond_sword',0)]['ui_model'].removeprefix('modern_projection_item_icon_')
    with Image.open(ROOT/'resource_pack/textures/models/modern_projection/item_icons'/(sword+'.png')) as texture:
        if not closeup:
            texture=None
        for route in ('editor','world'):
            if texture is None:
                continue
            sequence=[rows[route+'_'+str(index)] for index in range(20)]
            hidden=rgb(rows[route+'_items_hidden']['capture']['path'])
            images=[rgb(row['capture']['path']) for row in sequence]
            size=(images[0].shape[1],images[0].shape[0])
            items={}
            for mode,position in closeup['fixture']['positions'].items():
                expected=expected_mask(position,sequence[0],texture,pose,size,calibration)
                body=(empty_body_measurement(images[0],hidden,expected) if mode=='empty' else
                      body_measurement(images[0],hidden,expected))
                items[mode]={'body':body,
                             'motion':temporal_measurement(images,expected,mode=='enchanted')}
            result['closeup'][route]=items
        if texture is not None:
            native_source=dict(report,camera_calibration={'data':calibration})
            result['native_closeup']=native_comparison(native_source,rows,texture,{'frame_pose':pose},size,output)
            failures.extend(result['native_closeup']['capture_failures'])
    result['evidence_valid']=report['completed'] and not failures and not report['cleanup_errors'] and calibration['passed']
    body_results=[body['passed'] for case in result['cases'] for route in case['routes'].values() for body in route.values()]
    body_results.extend(row['body']['passed'] for route in result['closeup'].values() for row in route.values())
    result['all_bodies_passed']=bool(body_results) and all(body_results)
    (output/'analysis.json').write_text(json.dumps(result,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'evidence_valid':result['evidence_valid'],'all_bodies_passed':result['all_bodies_passed'],
        'failed':[(case['id'],route,mode,body['iou']) for case in result['cases'] for route,items in case['routes'].items()
                  for mode,body in items.items() if not body['passed']]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--world-plain-only',action='store_true')
    args=parser.parse_args()
    analyze(args.source,args.output,args.world_plain_only)
