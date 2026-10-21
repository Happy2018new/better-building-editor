"""Predeclared layout-only anchor hypothesis; no phase/texture/ROI optimization."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PROJECT = ROOT / '.runtime/projects/water-r25-final41-v2'
sys.path.insert(0, str(PROJECT/'tools'))
import analyze_product_water as water


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def control(shape, state):
    origin=tuple(axis//4*4 for axis in shape['position'])
    keys={item['key'] for item in state['liquid_groups'] if tuple(item['origin'])==origin}
    entry=next(item for item in state['liquid_control_requests']
        if item['key'] in keys and item['poses'] and any(item['visible']))
    slot=entry['visible'].index(True)
    return entry['doll_positions'][slot],entry['doll_sizes'][slot],entry['poses'][slot]


def projection(points,shape,row,report,size,gui_override=None):
    original=np.asarray(water.project(points,shape,row,report,size))
    position,doll_size,pose=control(shape,row['ready'])
    screen=row['ready']['screen_size']
    gui=round(size[0]/screen[0]) if gui_override is None else gui_override
    assert gui>=1
    # The native physical anchor is hypothesized to be min(logical control size).
    # The product/analyzer currently compensate one logical quarter (GUI=4).
    native_y_shift=-min(doll_size)*(1./gui-.25)*size[1]/screen[1]
    return original+np.array([0.,native_y_shift]),native_y_shift


def raster(polygons,size):
    result=Image.new('L',size)
    draw=ImageDraw.Draw(result)
    for polygon in polygons:draw.polygon([tuple(point) for point in polygon],fill=255)
    return np.asarray(result)>0


def metrics(expected,signal,region):
    expected=expected & region
    actual=signal & region
    intersection=int((expected & actual).sum())
    union=int((expected | actual).sum())
    return dict(iou=intersection/union if union else 0.,expected_pixels=int(expected.sum()),
        signal_pixels=int(actual.sum()),intersection=intersection,union=union)


def main():
    sources=[ROOT/'.runtime/round-20261020/water-mixed/product-v2-a-v3.json',
        WORK/'diagnostic-east-editor-size720-v1.json']
    all_rows=[]
    for path in sources:
        report=json.loads(path.read_bytes())
        row=report['flow_bursts']['editor_flow_east_wet']['row']
        frame=Path(report['flow_bursts']['editor_flow_east_wet']['capture']['output_directory'])/'frame_000001.png'
        image=Image.open(frame).convert('RGB')
        size=image.size
        pixels=np.asarray(image,dtype=np.int16)
        r,g,b=pixels[:,:,0],pixels[:,:,1],pixels[:,:,2]
        # Diagnostic color signal only. Predeclared broad water-blue range rejects
        # grayscale stone, near-white UI and saturated blue grid lines.
        signal=(b-r>15)&(b-g<30)&(g-r>5)&(r>75)&(r<220)&(b<240)
        gui=round(size[0]/row['ready']['screen_size'][0])
        full=np.zeros((size[1],size[0]),dtype=bool)
        draw=ImageDraw.Draw(image)
        groups=[]
        for position in ((2,3,3),(4,3,3)):
            selected=[shape for shape in row['ready']['shapes'] if tuple(shape['position'])==position]
            original=[];hypothesis=[];wrong=[]
            shifts=[]
            for shape in selected:
                for unused,polygon in water.water_polygons([shape]):
                    old=np.asarray(water.project(polygon,shape,row,report,size))
                    new,shift=projection(polygon,shape,row,report,size)
                    alternate,_=projection(polygon,shape,row,report,size,gui_override=3)
                    original.append(old);hypothesis.append(new);wrong.append(alternate)
                    shifts.append(shift)
                    draw.line([tuple(point) for point in old]+[tuple(old[0])],fill=(255,0,0),width=1)
                    draw.line([tuple(point) for point in new]+[tuple(new[0])],fill=(0,210,160),width=1)
            bounds=np.asarray(hypothesis).reshape(-1,2)
            position_ui,doll_size,pose=control(selected[0],row['ready'])
            record=dict(shape_position=position,short_side=min(doll_size),native_y_shift=shifts[0],
                all_faces_same_translation=len(set(shifts))==1,
                hypothesis_bounds=[bounds.min(axis=0).tolist(),bounds.max(axis=0).tolist()],
                control_position=position_ui,control_size=doll_size,pose=pose,
                pixel_metrics_limit='Color signal is diagnostic; no geometry/flow/alpha gate is granted.')
            # The rightmost group is spatially isolated; the first group is clipped
            # at 720p and overlaps another, so do not claim a mask fit there.
            if position==(4,3,3):
                mask=raster(hypothesis,size)
                # Region comes from the declared union and expands by ten pixels;
                # it is fixed before inspecting a pixel metric, with no search.
                region=np.zeros(mask.shape,dtype=bool)
                lo=np.floor(bounds.min(axis=0)).astype(int)-10
                hi=np.ceil(bounds.max(axis=0)).astype(int)+11
                region[max(0,lo[1]):min(size[1],hi[1]),max(0,lo[0]):min(size[0],hi[0])]=True
                variants={'original_gui4_formula':original,'layout_gui_formula':hypothesis,
                    'wrong_gui3':wrong,
                    'wrong_translation_sign':[poly-np.array([0.,2*shifts[0]]) for poly in hypothesis],
                    'up20_negative':[poly-np.array([0.,20.]) for poly in hypothesis],
                    'down20_negative':[poly+np.array([0.,20.]) for poly in hypothesis]}
                record['diagnostic_masks']={name:metrics(raster(polys,size),signal,region)
                    for name,polys in variants.items()}
            groups.append(record)
        output=WORK/('anchor-layout-overlay-old-gui4-v1.png' if gui==4 else 'anchor-layout-overlay-new-gui2-v1.png')
        image.save(output)
        all_rows.append(dict(report=str(path),report_sha256=sha(path),frame=str(frame),frame_sha256=sha(frame),
            native_size=size,SDK_screen=row['ready']['screen_size'],
            native_to_SDK_scale=[size[i]/row['ready']['screen_size'][i] for i in range(2)],
            inferred_integer_gui_scale=gui,groups=groups,overlay=str(output),overlay_sha256=sha(output)))
    result=dict(schema=1,read_only=True,MC_started=False,formal_A_accepted=False,
        thresholds_unchanged=True,original_reports_preserved=True,host_sha256=sha(Path(__file__)),
        hypothesis='The native physical centre-to-anchor offset equals min(logical doll size); logical offset is min(size)/integer_GUI_scale. Existing ui_offset/analyzer use /4.',
        caveat='This translates declared geometry only to diagnose native anchor behavior. It must not be used to move the flow ROI or qualify the visibly displaced product. Native neutral geometry controls are required before changing production.',
        records=all_rows)
    target=WORK/'anchor-layout-hypothesis-r27-v1.json'
    with target.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(dict(sha256=sha(target),records=[dict(gui=row['inferred_integer_gui_scale'],groups=row['groups']) for row in all_rows])))


if __name__=='__main__':main()
