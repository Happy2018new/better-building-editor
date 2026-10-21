"""Read-only geometric overlap and alternate-axis diagnostics, without new acceptance."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PROJECT = ROOT/'.runtime/projects/water-r25-final41-v2'
sys.path.insert(0, str(PROJECT/'tools'))
import analyze_product_water_flow as flow
import analyze_product_water as water


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(result):
    return {key:value for key,value in result.items() if key not in ('pairs', 'reversed_time_control')}


def main():
    report_path = WORK/'diagnostic-east-editor-size720-v1.json'
    report = json.loads(report_path.read_bytes())
    burst = report['flow_bursts']['editor_flow_east_wet']
    row = burst['row']
    shape = next(item for item in row['ready']['shapes'] if item['faces'] & 1 and tuple(item['position']) == (2,3,3))
    points, spacing = flow.physical_points(shape, 0)
    points = np.asarray(points)
    images, times = flow.burst_frames(burst['capture'])
    with Image.open(images[0]).convert('RGB') as image:
        mapped = np.asarray(water.project(points, shape, row, report, image.size))
        depth = np.asarray(water.OrbitCamera(*row['ready']['camera_pose']).basis()[2])
        sample_depth = points @ depth
        occluded = np.zeros(len(points), dtype=bool)
        overlays = ImageDraw.Draw(image)
        overlaps = []
        for item, polygon in water.water_polygons(row['ready']['shapes']):
            polygon = np.asarray(polygon)
            screen = np.asarray(water.project(polygon, item, row, report, image.size))
            overlays.line([tuple(point) for point in screen]+[tuple(screen[0])], fill=(255,50,50), width=1)
            local = np.zeros(len(points), dtype=bool)
            for indices in ((0,1,2),(0,2,3)):
                vertices = screen[list(indices)]
                matrix = np.column_stack((vertices[1]-vertices[0], vertices[2]-vertices[0]))
                if abs(np.linalg.det(matrix)) < 1e-10:
                    continue
                uv = (mapped-vertices[0]) @ np.linalg.inv(matrix).T
                inside = (uv[:,0] >= -1e-7) & (uv[:,1] >= -1e-7) & (uv.sum(axis=1) <= 1+1e-7)
                depths = polygon[list(indices)] @ depth
                at_depth = depths[0] + uv[:,0]*(depths[1]-depths[0]) + uv[:,1]*(depths[2]-depths[0])
                local |= inside & (at_depth > sample_depth + 1e-5)
            if local.any():
                overlaps.append(dict(position=item['position'], faces=item['faces'], closer_sample_points=int(local.sum())))
            occluded |= local
        image.save(WORK/'flow-all-faces-overlay-r27-v1.png')
    signal, unused = flow.physical_samples(images, shape, 0, row, report)
    alternate = {}
    for axis in (0,1):
        for sign in (-1,1):
            alternate['axis%d_sign%d' % (axis,sign)] = compact(flow.controlled_motion(signal, times, axis, sign, spacing, 16))
    panels = []
    for index in (0,len(signal)//2,len(signal)-1):
        pixels = np.clip(signal[index],0,255).astype(np.uint8)
        panels.append(Image.fromarray(pixels).resize((288,288)))
    contact = Image.new('RGB',(864,288))
    for index,panel in enumerate(panels):
        contact.paste(panel,(index*288,0))
    contact.save(WORK/'flow-mapped-signal-contact-r27-v1.png')
    result = dict(schema=1, read_only=True, MC_started=False, formal_A_accepted=False,
        report_sha256=sha(report_path), host_sha256=sha(Path(__file__)),
        native_image_size=[1280,720], total_sample_points=len(points),
        analytically_closer_water_face_points=int(occluded.sum()), closer_water_faces=overlaps,
        overlap_limitations='Geometry overlap is a diagnostic; it is not a pixel mask or native depth oracle.',
        alternate_axes_are_diagnostics_only=alternate,
        overlay_sha256=sha(WORK/'flow-all-faces-overlay-r27-v1.png'),
        signal_contact_sha256=sha(WORK/'flow-mapped-signal-contact-r27-v1.png'))
    target = WORK/'flow-occlusion-readonly-r27-v1.json'
    with target.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(dict(closer_points=int(occluded.sum()),total_points=len(points),
        alternate_axes={key:value['passed'] for key,value in alternate.items()}, result_sha256=sha(target))))


if __name__ == '__main__':
    main()
