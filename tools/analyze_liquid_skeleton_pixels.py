"""Replay fixed, separately framed skeleton-model positive/negative controls."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from probe_liquid_uniform_transport import HEIGHT_CODES

TOLERANCE=1
MIN_PIXELS=100


def color_mask(image,color,roi):
    delta=ImageChops.difference(image,Image.new('RGB',image.size,color))
    r,g,b=delta.split()
    maximum=ImageChops.lighter(ImageChops.lighter(r,g),b)
    match=maximum.point(lambda value:255 if value<=TOLERANCE else 0)
    outside=Image.new('L',image.size)
    outside.paste(255,roi)
    return ImageChops.multiply(match,outside)


def analyze(path):
    report=json.loads(path.read_bytes())
    captures=report['captures']
    screen=report['ui_setup']['screen_size']
    first=captures['independent']
    colors=[tuple(row[:3]) for row in HEIGHT_CODES]
    reverse=list(reversed(colors))
    rois=[]
    with Image.open(first['path']).convert('RGB') as image:
        scale=(image.width/float(screen[0]),image.height/float(screen[1]))
        for control in report['render']['controls']:
            pos,size=control['position'],control['size']
            rois.append(tuple(int(round(value)) for value in (
                pos[0]*scale[0],pos[1]*scale[1],(pos[0]+size[0])*scale[0],(pos[1]+size[1])*scale[1])))
        masks=[[color_mask(image,color,roi).filter(ImageFilter.MinFilter(3))
                for color in palette] for roi,palette in zip(rois,(colors,reverse))]
    masks_framed=True
    mask_records=[]
    for roi,group in zip(rois,masks):
        records=[]
        for mask in group:
            bounds=mask.getbbox()
            count=mask.histogram()[255]
            framed=bool(bounds and all(bounds[i]>roi[i]+2 for i in (0,1)) and
                        all(bounds[i]<roi[i]-2 for i in (2,3)) and count>=MIN_PIXELS)
            masks_framed=masks_framed and framed
            records.append({'bounds':bounds,'pixels':count,'framed':framed})
        mask_records.append(records)
    zero=(255,0,255) if report.get('extended_uniforms') else (0,0,0)
    expected={
        'default_zero':([zero]*4,[zero]*4),
        'independent':(colors,reverse),
        'left_reversed':(reverse,reverse),
        'left_zero':([zero]*4,reverse),
        'right_original':([zero]*4,colors),
        'repeat_independent':(colors,reverse)}
    if report.get('extended_uniforms'):
        fourth=[(row[3],slot*85,index*4) for slot,(row,index) in enumerate(zip(HEIGHT_CODES,(0,5,42,63)))]
        reverse_fourth=[(row[3],slot*85,index*4) for slot,(row,index) in enumerate(zip(reversed(HEIGHT_CODES),(0,5,42,63)))]
        expected.update({
            'left_fourth':(fourth,reverse),
            'right_fourth':(fourth,reverse_fourth),
            'left_badtag':([(255,0,255)]*4,reverse_fourth),
            'left_tint':([(18,52,86)]*4,reverse_fourth),
            'right_tint':([(18,52,86)]*4,[(171,205,239)]*4),
            'left_opacity_code':([(18,52,128)]*4,[(171,205,239)]*4),
            'right_opacity_code':([(18,52,128)]*4,[(255,255,64)]*4)})
    rows={}
    identity=(first['owner'],first['game_pid'],first['game_identity'])
    captures_verified=True
    for label,palettes in expected.items():
        capture=captures[label]
        image_path=Path(capture['path'])
        captures_verified=captures_verified and all(capture.get(key) for key in
            ('ok','reliable','background_only','background_safe')) and (
            capture['owner'],capture['game_pid'],capture['game_identity'])==identity and (
            capture['frame']['frame_qpc_100ns']>=capture['frame']['request_qpc_100ns']) and (
            hashlib.sha256(image_path.read_bytes()).hexdigest()==capture['sha256'])
        with Image.open(image_path).convert('RGB') as image:
            rows[label]=[]
            for roi,group,palette in zip(rois,masks,palettes):
                samples=[]
                for mask,color in zip(group,palette):
                    count=ImageChops.multiply(color_mask(image,color,roi),mask).histogram()[255]
                    total=mask.histogram()[255]
                    samples.append({'expected_rgb':color,'pixels':count,'mask_pixels':total,
                                    'passed':count>=MIN_PIXELS and count==total})
                rows[label].append(samples)
    ids=report['model_ids']['ids']
    ids_stable=len(set(ids))==2 and all(value!=-1 for value in ids) and all(
        observation['ids']==ids and all(row['returned'] for row in observation['uniform_calls'])
        for observation in report['observations'].values())
    accepted=bool(report['completed'] and report['restored'] and not report.get('cleanup_error') and
                  captures_verified and masks_framed and ids_stable and
                  all(sample['passed'] for groups in rows.values() for group in groups for sample in group))
    return {'schema':1,'input_report':str(path.resolve()),
            'input_report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'control_rois':rois,'masks':mask_records,'rows':rows,
            'minimum_pixels':MIN_PIXELS,'rgb_tolerance':TOLERANCE,
            'extended_uniforms':bool(report.get('extended_uniforms')),
            'mask_source':'Independent frame, exact declared colors, eroded by3pixels; one mask per slot/control',
            'captures_verified':captures_verified,'models_distinct_and_stable':ids_stable,
            'planes_fully_framed':masks_framed,'supplied_skeleton_codes_observed':accepted,
            'scope':'Independent static skeleton vec4 payloads and zero/reversal controls only',
            'editor_liquid_backend_accepted':False,'native_geometry_accepted':False,
            'animated_sampling_accepted':False,'production_memory_accepted':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis report')
    report=analyze(args.input)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'supplied_skeleton_codes_observed':report['supplied_skeleton_codes_observed'],
                      'planes_fully_framed':report['planes_fully_framed']}))
    return 0 if report['supplied_skeleton_codes_observed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
