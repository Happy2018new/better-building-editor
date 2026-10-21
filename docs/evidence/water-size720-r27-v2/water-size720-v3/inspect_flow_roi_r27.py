"""Map the unchanged analyzer's physical samples onto an actual diagnostic frame."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    path = WORK/'diagnostic-east-editor-size720-v1.json'
    source = json.loads(path.read_bytes())
    burst = source['flow_bursts']['editor_flow_east_wet']
    row = burst['row']
    shape = next(value for value in row['ready']['shapes']
        if value['faces'] & 1 and tuple(value['position']) == (2,3,3))
    frame = WORK/'diagnostic-east-editor-size720-v1_editor_flow_east_wet_burst/frame_000001.png'
    with Image.open(frame).convert('RGB') as image:
        points, spacing = flow.physical_points(shape, 0)
        mapped = np.asarray(flow.project(points, shape, row, source, image.size))
        draw = ImageDraw.Draw(image)
        grid = mapped.reshape(flow.GRID, flow.GRID, 2)
        corners = [tuple(grid[y,x]) for y,x in ((0,0),(0,-1),(-1,-1),(-1,0))]
        draw.line(corners+[corners[0]], fill=(255,0,0), width=2)
        for y in range(0, flow.GRID, 8):
            for x in range(0, flow.GRID, 8):
                px, py = grid[y,x]
                draw.ellipse((px-1,py-1,px+1,py+1), fill=(255,30,220))
        image.save(WORK/'flow-roi-overlay-r27-v1.png')
    result = dict(schema=1, read_only=True, MC_started=False, formal_A_accepted=False,
        report_sha256=sha(path), frame_sha256=sha(frame), analyzer_sha256=sha(Path(flow.__file__)),
        sample_position=[2,3,3], physical_grid_spacing=spacing,
        mapped_bounds=[mapped.min(axis=0).tolist(),mapped.max(axis=0).tolist()],
        scene_state=burst['before'], ready_keys=sorted(row['ready']),
        screen_size=row['ready']['screen_size'], shape=shape,
        overlay_sha256=sha(WORK/'flow-roi-overlay-r27-v1.png'))
    target = WORK/'flow-roi-readonly-r27-v1.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(dict(mapped_bounds=result['mapped_bounds'], screen_size=result['screen_size'],
        ready_keys=result['ready_keys'], result_sha256=sha(target))))


if __name__ == '__main__':
    main()
