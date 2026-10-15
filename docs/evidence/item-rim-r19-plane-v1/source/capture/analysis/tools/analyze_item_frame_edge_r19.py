"""Compare fixed-pose depth controls, native tips, and actual frame overlap pixels."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_item_sprite_product import ROOT, expected_mask, LIMITS
from analyze_item_sprite_closeup import native_body_measurement
from analyze_liquid_workspace import rgb, difference_mask, capture_failures, mask_row
from analyze_visible_items_r16 import target, body_region
from item_sprite_capture_contract import camera_matches, snapshot_digest
from item_sprite_edge_pixels import native_edge_measurement


def analyze(source, output):
    report=json.loads(source.read_bytes())
    output.mkdir(parents=True,exist_ok=False)
    rows={row['label']:row for row in report['captures']}
    failures=capture_failures({key:row['capture'] for key,row in rows.items()},report['session'])
    if (not report.get('source_unchanged') or report.get('launch_sources')!=report.get('sources_after')
            or snapshot_digest(report['launch_sources'])!=report.get('launch_sources_sha256')):
        failures.append('Source snapshot drift')
    for row in rows.values():
        if not camera_matches(row['camera'],report['camera']) or not camera_matches(row['camera_after'],report['camera']):
            failures.append('Camera drift: '+row['label'])
    if not report.get('native_restore',{}).get('passed'):
        failures.append('Native world restore missing')
    if not report.get('body_restore'):
        failures.append('Owned body restore missing')
    catalog=json.loads((ROOT/'tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())
    name,aux=report['case']['item']
    resource=next(row['resource'] for row in catalog['items'] if (row['name'],row['aux'])==(name,aux))
    with Image.open(ROOT/'resource_pack/textures/models/modern_projection/item_icons'/(resource+'.png')) as texture:
        row=copy.deepcopy(rows['baseline_shown'])
        row['state']['origin']=report['origin']
        row['camera_expected']=dict(row['camera'],target=target(row['camera']))
        size=(row['capture']['width'],row['capture']['height'])
        expected=expected_mask(report['case']['targets']['plain'],row,texture,catalog['pose'],size,
                               report['camera_calibration'],2,45.)
    region=body_region(expected,64)
    images={label:rgb(row['capture']['path']) for label,row in rows.items()}
    native_hidden=(images['native_hidden_before'].astype(float)+images['native_hidden_after'])/2.
    native_stable=np.max(np.abs(images['native_hidden_before'].astype(np.int16)-
                               images['native_hidden_after'].astype(np.int16)),axis=2)<=3
    native=difference_mask(images['native_shown'],native_hidden,region,LIMITS['rgb_delta']) & native_stable
    isolated=difference_mask(images['body_hidden_item_shown'],images['body_hidden_item_hidden'],region,LIMITS['rgb_delta'])
    frame=difference_mask(images['baseline_hidden'],images['body_hidden_item_hidden'],region,LIMITS['rgb_delta'])
    native_frame_overlap=native & frame
    result={'schema':1,'production_qualified':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'local_gate_sha256':hashlib.sha256((ROOT/'tools/item_sprite_edge_pixels.py').read_bytes()).hexdigest(),
        'capture_failures':failures,'evidence_valid':bool(report['completed'] and not report['cleanup_errors'] and not failures),
        'native_stable_fraction':float(native_stable[region].mean()),'native':mask_row(native),
        'isolated_item':mask_row(isolated),'native_frame_overlap':mask_row(native_frame_overlap),
        'scope':'Depth-only controls at fixed camera, frame, 45-degree rotation and scale; no production acceptance',
        'frame_overlap_definition':'Actual native item pixels over actual empty projected body pixels, measured against the same world background',
        'limitations':['Offset controls are diagnostics; no fitted offset is promoted automatically',
                       'This north-facing view does not accept oblique thickness, other faces or opacity'],
        'states':{}}
    labels=['baseline_shown']+[label for label in rows if label.startswith('offset_')]+['body_hidden_item_shown','baseline_restored']
    bounds=mask_row(native|isolated|expected)['bounds']
    box=(bounds[0]-30,bounds[1]-30,bounds[2]+30,bounds[3]+30)
    panels=[]
    for label in labels:
        hidden=images['body_hidden_item_hidden'] if label=='body_hidden_item_shown' else images['baseline_hidden']
        observed=difference_mask(images[label],hidden,region,LIMITS['rgb_delta'])
        measured={'observed':mask_row(observed),'native_body':native_body_measurement(observed,native),
            'native_edges':native_edge_measurement(observed,native),
            'frame_overlap_edges':native_edge_measurement(observed,native_frame_overlap),
            'isolated_edges':native_edge_measurement(observed,isolated),
            'missing_native_pixels':int((native & ~observed).sum())}
        result['states'][label]=measured
        actual=Image.open(rows[label]['capture']['path']).convert('RGB').crop(box)
        overlay=np.zeros((*observed.shape,3),dtype=np.uint8)
        overlay[native & observed]=(80,190,100)
        overlay[native & ~observed]=(235,60,60)
        overlay[observed & ~native]=(60,120,245)
        for title,image in ((label,actual),(label+' / native overlap',Image.fromarray(overlay).crop(box))):
            image.thumbnail((290,180),Image.Resampling.NEAREST)
            panel=Image.new('RGB',(310,215),'white')
            panel.paste(image,((310-image.width)//2,28+(180-image.height)//2))
            ImageDraw.Draw(panel).text((8,8),title,fill='black')
            panels.append(panel)
    native_image=Image.open(rows['native_shown']['capture']['path']).convert('RGB').crop(box)
    native_image.thumbnail((290,180),Image.Resampling.NEAREST)
    panel=Image.new('RGB',(310,215),'white')
    panel.paste(native_image,((310-native_image.width)//2,28+(180-native_image.height)//2))
    ImageDraw.Draw(panel).text((8,8),'actual native / same pose',fill='black')
    panels.append(panel)
    sheet=Image.new('RGB',(620,215*((len(panels)+1)//2)),'white')
    for index,panel in enumerate(panels):sheet.paste(panel,((index%2)*310,(index//2)*215))
    sheet.save(output/'comparison.png')
    restored=difference_mask(images['baseline_shown'],images['baseline_restored'],region,LIMITS['rgb_delta'])
    result['baseline_restore']={'changed_pixels':int(restored.sum()),'passed':int(restored.sum())<=3}
    result['baseline_clipping_reproduced']=bool(result['evidence_valid'] and
        not result['states']['baseline_shown']['isolated_edges']['passed'] and
        result['states']['body_hidden_item_shown']['native_body']['passed'] and
        result['baseline_restore']['passed'])
    (output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'evidence_valid':result['evidence_valid'],
        'baseline_restore':result['baseline_restore'],'baseline_clipping_reproduced':result['baseline_clipping_reproduced'],
        'states':{label:{key:data[key]['passed'] for key in ('native_body','native_edges','frame_overlap_edges','isolated_edges')}
                  for label,data in result['states'].items()}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    analyze(args.source,args.output)
