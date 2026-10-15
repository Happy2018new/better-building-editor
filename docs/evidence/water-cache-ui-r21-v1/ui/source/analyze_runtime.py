"""Offline paired-pixel measurements; never promotes the water repair."""
import hashlib
import json
import os
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
from PIL import Image
import numpy as np

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'result'
ROI = (470, 354, 1540, 848)


def analyze():
    report = json.loads((OUTPUT / 'report.json').read_bytes())
    assert report['completed'] and report['restored'] and report['source_unchanged']
    phases = ('skeleton_baseline', 'candidate', 'skeleton_restore', 'candidate_repeat', 'final_skeleton')
    frames = {}
    for phase in phases:
        for control in ('wet', 'hidden'):
            label = phase + '_' + control
            receipt = report['captures'][label]
            path = OUTPUT / Path(receipt['path']).name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == receipt['sha256']
            image = Image.open(path).convert('RGB')
            assert image.size == (1994, 1105), 'Fixed old reference ROI cannot be silently rescaled'
            frames[label] = np.asarray(image.crop(ROI)).astype(np.int16)
    def changed(a, b):
        return int(np.count_nonzero(np.max(np.abs(a-b), axis=2) >= 8))
    counts = {phase: changed(frames[phase + '_wet'], frames[phase + '_hidden']) for phase in phases}
    baseline_may_be_visible = counts['skeleton_baseline'] > 0
    result = {'schema': 1, 'roi': ROI, 'pixel_difference_threshold': 8,
        'independent_water_changed_pixels': counts, 'repair_accepted': False,
        'assessment': ('inconclusive_for_invisible_state_repair_baseline_has_signal'
                       if baseline_may_be_visible else 'await_native_visual_and_reversibility_review'),
        'candidate_repeat_wet_difference': changed(frames['candidate_wet'], frames['candidate_repeat_wet']),
        'skeleton_restore_wet_difference': changed(frames['skeleton_baseline_wet'], frames['skeleton_restore_wet']),
        'final_skeleton_wet_difference': changed(frames['skeleton_baseline_wet'], frames['final_skeleton_wet']),
        'required_visual_review': ['any cow pixels reject', 'wrong water geometry rejects',
            'depth/occlusion change rejects', 'failed skeleton restoration rejects'],
        'production_qualified': False}
    with (OUTPUT / 'analysis.json').open('x', encoding='ascii') as handle:
        handle.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    analyze()
