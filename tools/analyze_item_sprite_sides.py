"""Measure extruded silhouette, plane and actual native side-view differences."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_item_sprite_product import (ROOT, item_polygons, project_editor, expected_mask,
                                        expanded, LIMITS)
from analyze_item_sprite_closeup import native_body_measurement
from analyze_visible_items_r16 import target
from analyze_liquid_workspace import difference_mask, mask_row, rgb
from camera_projection import project_points


def convex_hull(points):
    points = sorted(set(points))
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    parts = []
    for order in (points,reversed(points)):
        hull = []
        for point in order:
            while len(hull)>1 and cross(hull[-2],hull[-1],point)<=0:
                hull.pop()
            hull.append(point)
        parts.append(hull[:-1])
    return parts[0]+parts[1]


def extruded_mask(position,row,texture,pose,size,calibration,facing=2,rotation=0.):
    """Project each opaque texel prism independently of the generated mesh."""
    back = dict(pose,front_z_pixels=pose['front_z_pixels']+pose['thickness_pixels'])
    front_planes = item_polygons(position,texture,pose,rotation,facing)
    back_planes = item_polygons(position,texture,back,rotation,facing)
    image = Image.new('1',size)
    draw = ImageDraw.Draw(image)
    for front,rear in zip(front_planes,back_planes):
        vertices = front+rear
        if row['label'].startswith('editor_'):
            projected = project_editor(vertices,position,row['state'],size)
        else:
            camera = row['camera_expected']
            vertices = [tuple(point[axis]+row['state']['origin'][axis] for axis in range(3))
                        for point in vertices]
            projected = project_points(vertices,camera['position'],camera['target'],size,
                                       calibration['vertical_fov'])
            if any(point['depth']<=.05 for point in projected):
                raise ValueError('A tested texel crosses the camera near plane')
            projected = [(point['screenX'],point['screenY']) for point in projected]
        hull = convex_hull(projected)
        if len(hull)>=3:
            draw.polygon(hull,fill=1)
    return np.asarray(image,dtype=bool)


def overlap(observed,expected):
    return {'observed':mask_row(observed),'expected':mask_row(expected),
            'iou':float((observed&expected).sum())/max(1,int((observed|expected).sum()))}


def analyze(source,output):
    report = json.loads(source.read_bytes())
    if not report['completed'] or report['cleanup_errors'] or not report['source_unchanged']:
        raise ValueError('Side analysis requires completed stable capture and restoration')
    output.mkdir(parents=True,exist_ok=False)
    case = report['cases'][0]
    if not case.get('measurement_completed') or not case['native_reference']['restored']:
        raise ValueError('Side analysis requires completed actual native reference')
    name,aux = case['source']['item']
    catalog = json.loads((ROOT/'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())
    key = next(row['resource'] for row in catalog['items'] if (row['name'],row['aux'])==(name,aux))
    texture = Image.open(ROOT/'resource_pack/textures/models/modern_projection/item_icons'/(key+'.png')).convert('RGBA')
    captures = {row['label']:row for row in report['captures']}
    position = case['source'].get('targets',{'plain':(2,3,2)})['plain']
    native = case['native_reference']['prepare']['rows'][0]['position']
    origin = tuple(native[axis]-position[axis] for axis in range(3))
    facing,rotation = case['source'].get('facing',2),case['source'].get('rotation_degrees',0.)
    result = {'schema':1,'production_qualified':False,
              'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'resource_contract':report['resource_contract'],'routes':{},
              'limitations':['Convex texel-prism union includes no frame occlusion or lighting model',
                             'Polygon rasterization is diagnostic; actual native masks remain independent',
                             'Depth fit is diagnostic, not a qualification or reason to alter thresholds']}
    observed_masks = {}
    panels = []
    for route in ('editor','full','missing','native'):
        prefix = case['id']+'_'+route
        shown_row = captures[prefix+'_shown']
        row = copy.deepcopy(shown_row)
        row['label'] = 'editor_'+case['id'] if route=='editor' else route+'_'+case['id']
        row['state']['origin'] = origin
        if route!='editor':
            row['camera_expected'] = dict(row['camera'],target=target(row['camera']))
        shown = rgb(shown_row['capture']['path'])
        hidden_before = rgb(captures[prefix+'_hidden_before']['capture']['path'])
        hidden_after = rgb(captures[prefix+'_hidden_after']['capture']['path'])
        hidden = (hidden_before.astype(np.float64)+hidden_after)/2.
        stable = np.max(np.abs(hidden_before.astype(np.int16)-hidden_after.astype(np.int16)),axis=2)<=3
        size = (shown.shape[1],shown.shape[0])
        geometric = extruded_mask(position,row,texture,catalog['pose'],size,report['camera_calibration'],facing,rotation)
        plane = expected_mask(position,row,texture,catalog['pose'],size,report['camera_calibration'],facing,rotation)
        region = expanded(geometric,33)
        observed = difference_mask(shown,hidden,region,LIMITS['rgb_delta']) & stable
        observed_masks[route] = observed
        data = overlap(observed,geometric)
        data['plane_only'] = overlap(observed,plane)
        data['stable_fraction'] = float(stable[region].mean())
        data['depth_fits'] = []
        for thickness in (.0,.25,.5,.75,1.):
            candidate = dict(catalog['pose'],thickness_pixels=thickness)
            fitted = extruded_mask(position,row,texture,candidate,size,report['camera_calibration'],facing,rotation)
            data['depth_fits'].append(dict(overlap(observed,fitted),thickness_pixels=thickness))
        if route=='native':
            data['plane_fits'] = []
            for offset in (-.5,-.375,-.25,-.125,0.,.125,.25,.375,.5):
                candidate = dict(catalog['pose'],front_z_pixels=catalog['pose']['front_z_pixels']+offset)
                fitted = extruded_mask(position,row,texture,candidate,size,report['camera_calibration'],facing,rotation)
                data['plane_fits'].append(dict(overlap(observed,fitted),front_offset_pixels=offset))
        result['routes'][route] = data
        bounds = mask_row(observed|geometric)['bounds']
        box = (max(0,bounds[0]-25),max(0,bounds[1]-25),min(size[0],bounds[2]+25),min(size[1],bounds[3]+25))
        images = [Image.open(shown_row['capture']['path']).convert('RGB').crop(box),
                  Image.fromarray((observed*255).astype('uint8')).convert('RGB').crop(box),
                  Image.fromarray((geometric*255).astype('uint8')).convert('RGB').crop(box)]
        for label,image in zip(('actual','observed','extruded'),images):
            image.thumbnail((290,290),Image.Resampling.NEAREST)
            panel = Image.new('RGB',(310,320),'white')
            panel.paste(image,((310-image.width)//2,25+(290-image.height)//2))
            ImageDraw.Draw(panel).text((10,8),route+' / '+label,fill='black')
            panels.append(panel)
    result['native_comparison'] = {route:native_body_measurement(observed_masks[route],observed_masks['native'])
                                   for route in ('full','missing')}
    sheet = Image.new('RGB',(930,1280),'white')
    for index,panel in enumerate(panels):
        sheet.paste(panel,((index%3)*310,(index//3)*320))
    sheet.save(output/'review.png')
    (output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps(result['native_comparison']))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    analyze(args.source,args.output)
