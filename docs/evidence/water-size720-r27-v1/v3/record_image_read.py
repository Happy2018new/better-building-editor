"""Bind the five original images actually opened by the R27 water agent."""
import hashlib
import json
from pathlib import Path
from PIL import Image

WORK = Path(__file__).resolve().parent
names = [
    'diagnostic-east-editor-size720-v1_editor_flow_east_wet.png',
    'diagnostic-east-editor-size720-v1_editor_flow_east_wet_later.png',
    'diagnostic-east-editor-size720-v1_editor_flow_east_wet_burst/frame_000001.png',
    'diagnostic-east-editor-size720-v1_editor_flow_east_wet_burst/frame_000022.png',
    'diagnostic-east-editor-size720-v1_editor_flow_east_wet_burst/frame_000042.png',
]
target = WORK / 'actual-image-read-r27-v1.json'
assert not target.exists()
entries = []
for name in names:
    path = WORK / name
    data = path.read_bytes()
    with Image.open(path) as picture:
        size = list(picture.size)
    entries.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(data).hexdigest(),
                        bytes=len(data), dimensions=size))
target.write_text(json.dumps(dict(schema=1, actually_opened_with_view_image=True,
    diagnostic_spot_check_only=True, water_visible=True, texture_phase_changes_visible=True,
    formal_A_accepted=False, direction_or_speed_qualification_granted=False,
    manual_closures_added=0, entries=entries), indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
