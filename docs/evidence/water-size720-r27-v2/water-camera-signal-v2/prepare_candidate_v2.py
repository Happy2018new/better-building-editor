"""Keep v1 unchanged; constrain every final new pixel to observed contribution."""
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
       b'    baseline = largest_component(seed)\r\n'
       b'    baseline = fill_enclosed_holes(baseline).filter(ImageFilter.MedianFilter(3))\r\n'
       b'    baseline = baseline.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))\r\n'
       b'    closed = seed.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))\r\n'
       b'    mask = largest_component(ImageChops.lighter(seed, ImageChops.multiply(closed, contribution)))')
assert raw.count(old) == 1
line_end = b'\r\n' if b'\r\n' in raw else b'\n'
new = new.replace(b'\r\n', line_end)
candidate = raw.replace(old, new)
before = (b'    outline = outline.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))\r\n'
          b'    assert ImageChops.multiply(outline, contribution).histogram()[255] >= 1000,')
after = (b'    outline = outline.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))\r\n'
         b'    # Preserve the old silhouette; final added pixels require measured contribution.\r\n'
         b'    outline = ImageChops.lighter(baseline, ImageChops.multiply(outline, contribution))\r\n'
         b'    assert ImageChops.multiply(outline, contribution).histogram()[255] >= 1000,')
before = before.replace(b'\r\n', line_end)
after = after.replace(b'\r\n', line_end)
assert candidate.count(before) == 1
candidate = candidate.replace(before, after)
target = WORK / 'candidate/tools/verify_camera_projection.py'
target.parent.mkdir(parents=True, exist_ok=True)
assert not target.exists()
target.write_bytes(candidate)
patch = ''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),
    candidate.decode('utf-8').splitlines(True), fromfile='a/tools/verify_camera_projection.py',
    tofile='b/tools/verify_camera_projection.py'))
(WORK / 'camera-signal-v2.patch').write_text(patch, encoding='utf-8', newline='')
binding = dict(schema=2, private_candidate_only=True, shared_tool_modified=False,
    base_path=str(source), base_sha256=hashlib.sha256(raw).hexdigest(),
    candidate_path=str(target), candidate_sha256=hashlib.sha256(candidate).hexdigest(),
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
    final_formula='old_outline OR (new_outline AND contribution_gt_20)',
    v1_retained=True, v1_indirect_fill_counterexample_retained=True,
    neutral_spread_less_than=13, red_brightness_greater_than=50,
    contribution_greater_than=20, original_outline_is_preserved=True,
    every_final_added_pixel_requires_contribution=True,
    analytic_geometry_used_to_fill=False, runtime_qualification_granted=False)
(WORK / 'binding-v1.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')
assert source.read_bytes() == raw
print(json.dumps(binding))
