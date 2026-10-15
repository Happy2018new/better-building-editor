"""Compare uninterrupted native glint frames with the sparse screenshot metric."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

from analyze_item_sprite_closeup import glint_metrics

CONTINUITY_LIMITS={'minimum_duration_seconds':7.,'maximum_frame_gap_seconds':.25,
                   'window_seconds':1.,'window_step_seconds':.5,
                   'minimum_window_body_fraction_rgb_gt8':.05}


def continuous_change_measurement(images,mask,times):
    """Require visible body changes throughout an uninterrupted real-time clip.

    This measures absence of frozen intervals, not texture phase velocity or
    visual parity. Camera, native body, image hashes and ownership are external
    prerequisites enforced by analyze().
    """
    result={'passed':False,'limits':CONTINUITY_LIMITS,'windows':[],
            'scope':'Visible body evolution throughout the clip; no phase-speed claim'}
    if len(images)!=len(times) or len(times)<3 or not mask.any():
        return dict(result,status='INSUFFICIENT_BODY_OR_FRAMES')
    intervals=np.diff(times)
    duration=times[-1]-times[0]
    result.update(duration_seconds=float(duration),maximum_frame_gap_seconds=float(intervals.max()))
    if (duration<CONTINUITY_LIMITS['minimum_duration_seconds'] or
            np.any(intervals<=0.) or intervals.max()>CONTINUITY_LIMITS['maximum_frame_gap_seconds']):
        return dict(result,status='INCOMPLETE_TIMELINE')
    selected=np.stack([image[mask] for image in images])
    elapsed=np.asarray(times)-times[0]
    window=CONTINUITY_LIMITS['window_seconds']
    starts=list(np.arange(0.,duration-window+.000001,CONTINUITY_LIMITS['window_step_seconds']))
    if duration-window>starts[-1]+.000001:starts.append(duration-window)
    for start in starts:
        rows=(elapsed>=start-.000001)&(elapsed<=start+window+.000001)
        fraction=float(np.mean(np.ptp(selected[rows],axis=0).max(axis=1)>8.))
        result['windows'].append({'start_seconds':float(start),'end_seconds':float(start+window),
            'frames':int(rows.sum()),'body_fraction_rgb_gt8':fraction,
            'passed':fraction>=CONTINUITY_LIMITS['minimum_window_body_fraction_rgb_gt8']})
    result.update(status='MEASURED',passed=all(row['passed'] for row in result['windows']))
    return result


def verified_json(path, expected):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Animation evidence changed: '+str(path))
    return json.loads(raw)


def crop(path,bounds):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB').crop(bounds),dtype=np.float32)


def analyze(source, sparse_analysis, output, diagnostic_only=False):
    report=json.loads(source.read_bytes())
    sparse=json.loads(sparse_analysis.read_bytes())
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
    if sparse.get('source_sha256')!=source_sha256:
        raise ValueError('Sparse analysis does not belong to this animation capture')
    if (not report.get('source_unchanged') or not report.get('completed') or report.get('cleanup_errors')
            or sparse.get('capture_failures') or not sparse.get('native_closeup', {}).get('reference_valid')):
        raise ValueError('Base closeup evidence is invalid')
    if not sparse.get('evidence_valid') and not diagnostic_only:
        raise ValueError('Base closeup evidence is invalid; diagnostic-only analysis must be explicit')
    output.mkdir(parents=True,exist_ok=False)
    closeup=report['closeup']
    ordinary={row['label']:row for row in closeup['captures']}
    native={row['label']:row for row in closeup['native_reference']['captures']}
    result={'schema':1,'source':str(source),'product_qualified':False,'routes':{},
            'base_evidence_valid':bool(sparse.get('evidence_valid')), 'diagnostic_only':diagnostic_only,
            'scope':'Contiguous glint motion and plain/empty controls; no geometry or full product admission.',
            'source_sha256':source_sha256,
            'sparse_analysis_sha256':hashlib.sha256(sparse_analysis.read_bytes()).hexdigest(),
            'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for route in ('editor','world','world_missing','native'):
        record=closeup['motion_bursts'][route]
        if not record['stable']:raise ValueError('Dense capture camera drift: '+route)
        receipt=verified_json(Path(record['receipt']),record['sha256'])
        if not receipt['capture_valid'] or not receipt['temporal_complete']:
            raise ValueError('Incomplete dense timeline: '+route)
        if receipt['instance']['game_identity']!=report['session']['game_identity']:
            raise ValueError('Dense capture came from a different game')
        frames=[];times=[]
        for frame in receipt['frames']:
            if frame['png'] is None:continue
            raw=verified_json(Path(frame['receipt']['path']),frame['receipt']['sha256'])
            image_path=Path(frame['png']['path'])
            if hashlib.sha256(image_path.read_bytes()).hexdigest()!=frame['png']['sha256']:
                raise ValueError('Dense image changed: '+str(image_path))
            frames.append(image_path);times.append(raw['frame_qpc_100ns']/1e7)
        rows=native if route=='native' else ordinary
        hidden=rows[route+'_items_hidden' if route in ('editor','native') else 'world_items_hidden']['capture']['path']
        first=rows[route+'_0']['capture']['path']
        metrics={}
        continuity={}
        for mode in ('enchanted','plain'):
            body=sparse['native_closeup']['routes'][route]['items'][mode]['body']
            bounds=body['bounds']
            if not bounds or min(bounds[2]-bounds[0],bounds[3]-bounds[1])<150:
                raise ValueError('Dense glint comparison is too small: '+route+' '+mode)
            bounds=[bounds[0]-2,bounds[1]-2,bounds[2]+3,bounds[3]+3]
            mask=np.max(abs(crop(first,bounds)-crop(hidden,bounds)),axis=2)>8.
            images=[crop(path,bounds) for path in frames]
            measure=glint_metrics(images,mask,times)
            measure['bounds']=bounds
            measure['median_centroid_speed']=float(np.median(measure['highlight_centroid_body_widths_per_second'] or [0.]))
            metrics[mode]=measure
            if mode=='enchanted':
                continuity=continuous_change_measurement(images,mask,times)
                continuity['negative_controls']={
                    'frozen_body_rejected':not continuous_change_measurement([images[0]]*len(images),mask,times)['passed'],
                    'empty_body_rejected':not continuous_change_measurement(images,np.zeros_like(mask),times)['passed']}
                # Preserve real timing; choose at most ten presentation frames
                # per second while every original frame contributes to metrics.
                selected=[0]
                for index,t in enumerate(times[1:],1):
                    if t-times[selected[-1]]>=.1:selected.append(index)
                gif=[Image.fromarray(images[index].astype(np.uint8)) for index in selected]
                duration=[max(10,int(round((times[b]-times[a])*1000/10))*10)
                          for a,b in zip(selected,selected[1:])]
                gif[0].save(output/(route+'.gif'),save_all=True,append_images=gif[1:],
                            duration=duration+[duration[-1]],loop=0,optimize=False,disposal=2)
                sheet=Image.new('RGB',(gif[0].width*4,gif[0].height+22),'white')
                for i,index in enumerate((0,len(gif)//3,2*len(gif)//3,len(gif)-1)):
                    sheet.paste(gif[index],(i*gif[0].width,22))
                    ImageDraw.Draw(sheet).text((i*gif[0].width,2),route+' '+str(index),fill='black')
                sheet.save(output/(route+'.png'))
        result['routes'][route]={'frames':len(frames),'duration_seconds':times[-1]-times[0],
            'median_frame_interval_seconds':float(np.median(np.diff(times))), 'items':metrics,
            'plain_control_passed':metrics['plain']['motion_fraction_rgb_gt8']<=.005,
            'continuous_visible_change':continuity}
    reference=result['routes']['native']['items']['enchanted']['median_centroid_speed']
    result['dense_speed_ratios']={route:data['items']['enchanted']['median_centroid_speed']/max(reference,.001)
                                  for route,data in result['routes'].items() if route!='native'}
    result['dense_speed_ratios_role']='Diagnostic bright-area centroid displacement only; never a texture phase-speed gate'
    result['native_glint_visibility_accepted']=sparse.get('native_closeup',{}).get('native_glint_visibility_accepted',False)
    result['continuous_motion_accepted']=bool(result['base_evidence_valid'] and not diagnostic_only
        and sparse.get('all_bodies_passed')
        and result['native_glint_visibility_accepted'] and all(
            row['plain_control_passed'] and row['continuous_visible_change']['passed']
            and all(row['continuous_visible_change']['negative_controls'].values())
            for row in result['routes'].values()))
    (output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'dense_speed_ratios':result['dense_speed_ratios'],
                      'plain_controls':{k:v['plain_control_passed'] for k,v in result['routes'].items()}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('sparse_analysis',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--diagnostic-only',action='store_true',
                        help='Retain failed geometry calibration while inspecting observed motion; grants no acceptance.')
    args=parser.parse_args();analyze(args.source,args.sparse_analysis,args.output,args.diagnostic_only)
