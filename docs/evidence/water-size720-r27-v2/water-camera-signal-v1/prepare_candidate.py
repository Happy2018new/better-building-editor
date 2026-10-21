"""Freeze a private four-line signal change without touching shared tools."""
import difflib
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
source = ROOT / 'tools/verify_camera_projection.py'
raw = source.read_bytes()
old = b'    mask = largest_component(ImageChops.multiply(mask, contribution))'
new = (b'    seed = ImageChops.multiply(mask, contribution)\r\n'
       b'    closed = seed.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))\r\n'
       b'    # Bridge only a one-pixel seam supported by the shown-minus-hidden signal.\r\n'
       b'    mask = largest_component(ImageChops.lighter(seed, ImageChops.multiply(closed, contribution)))')
assert raw.count(old) == 1
candidate = raw.replace(old, new)
target = WORK / 'candidate/tools/verify_camera_projection.py'
target.parent.mkdir(parents=True, exist_ok=True)
assert not target.exists()
target.write_bytes(candidate)
patch = ''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),
    candidate.decode('utf-8').splitlines(True), fromfile='a/tools/verify_camera_projection.py',
    tofile='b/tools/verify_camera_projection.py'))
(WORK / 'camera-signal-v1.patch').write_text(patch, encoding='utf-8', newline='')
binding = dict(schema=1, private_candidate_only=True, shared_tool_modified=False,
    base_path=str(source), base_sha256=hashlib.sha256(raw).hexdigest(),
    candidate_path=str(target), candidate_sha256=hashlib.sha256(candidate).hexdigest(),
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
    single_change='Contribution-supported 3x3 closing before largest-component selection',
    neutral_spread_less_than=13, red_brightness_greater_than=50,
    contribution_greater_than=20, inherited_final_morphology_unchanged=True,
    analytic_geometry_used_to_fill=False, runtime_qualification_granted=False)
(WORK / 'binding-v1.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
assert source.read_bytes() == raw
print(json.dumps(binding))
