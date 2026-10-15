"""Create a portable native shield evidence package without staging files."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from verify import verify

SOURCE = ROOT / '.runtime/shield-authentic-r21-v1'
DEST = ROOT / 'docs/evidence/shield-authentic-r21-v1'
CONTROL = ROOT / '.runtime/shield-r20-control-v7-authentic'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii', newline='\n')


assert not DEST.exists()
checked = verify(SOURCE)
DEST.mkdir(parents=True)
(DEST / '.gitattributes').write_text('* -text\n', encoding='ascii', newline='\n')
for name in ('records', 'images', 'host', 'references'):
    (DEST / name).mkdir()
for path in sorted(SOURCE.glob('*.json')):
    shutil.copy2(path, DEST / 'records' / path.name)
for path in sorted(SOURCE.glob('*.png')):
    shutil.copy2(path, DEST / 'images' / path.name)
for name in ('ready-summary.json', 'launch-inputs.json'):
    shutil.copy2(CONTROL / name, DEST / 'records' / name)
for name in ('host.py', 'client.py', 'server.py', 'offline.py', 'verify.py',
             'freeze_amendment.py', 'package.py'):
    shutil.copy2(HERE / name, DEST / 'host' / name)
for relative in ('.runtime/prepare_shield_r20.py', '.runtime/shield_stop_owned_r20.py',
                 '.runtime/shield_lifecycle_read_r20.py', 'tools/watch_intrinsic_glint_exit_r21.py'):
    shutil.copy2(ROOT / relative, DEST / 'host' / Path(relative).name)
authentic_source = ROOT / 'docs/evidence/shield-native-crafter-r21-v1/records/authentic-shield.json'
shutil.copy2(authentic_source, DEST / 'references/authentic-shield.json')
assert sha(authentic_source) == json.loads((SOURCE / 'inputs.json').read_bytes())['authentic_source_sha256']
save(DEST / 'verification.json', checked)
save(DEST / 'observations.json', {
    'native_ui': {'image': 'images/01-native-ui-unbound.png',
        'authentic_pattern_visible': True, 'base_observed': 'white', 'base_parity_accepted': False},
    'skeleton_binding': {'negative': 'images/01-native-ui-unbound.png',
        'bound_back_surface': 'images/02-native-ui-bound-front.png',
        'actual_pattern_front': 'images/04-bound-back.png',
        'pattern_front_config_yaw': 180, 'base_observed': 'blue',
        'ordered_patterns': ['bo:1', 'cr:14', 'mc:11'],
        'side_and_handle': 'images/05-bound-side.png',
        'attachment_visible_separately_from_host': True,
        'frame_pose_proportions_and_thickness_accepted': False},
    'actual_native_frames': {'images': ['images/06-actual-frame-front.png',
        'images/07-actual-frame-oblique.png'], 'item_rotation': 0,
        'placement_support_face': 2, 'plain_observed': 'flat green interior rectangle',
        'authentic_observed': 'wooden reverse surface; patterned front not visible',
        'exact_authentic_item_tag': True, 'pattern_front_accepted': False,
        'block_aux_and_states_not_recorded': True},
    'workspace': {'images': ['images/08-workspace-candidate-front.png',
        'images/09-workspace-candidate-oblique.png'],
        'owned_native_renderentity_overlay': True, 'item_scene_integration': False,
        'common_depth_occlusion_accepted': False},
    'minimum_frame_followup': {'started': False, 'maximum_images': 4,
        'fixture': 'Same authentic item in two opposing native frames, with sword positive control.',
        'record_before_capture': ['native block aux and states', 'support face',
            'camera outward normal', 'ItemRotation', 'exact tag and ordinary inventory readback'],
        'views': ['outward front and oblique for each opposing face'],
        'decision': 'If both outward faces show reverse wood, record native behavior; only correct local orientation if it varies with native facing.'},
    'banner_item_route': {'item_short_stalk_pose_and_thickness_separate_from_block': True,
        'standing_or_wall_block_geometry_not_item_acceptance': True,
        'qualified': False}, 'production_qualified': False})

font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 18)
sheet = Image.new('RGB', (1110, 770), '#eeeeee')
draw = ImageDraw.Draw(sheet)
panels = [
    ('Native UI: white base', '01-native-ui-unbound.png', (927, 24, 1086, 349)),
    ('Bound shield: blue front', '04-bound-back.png', (855, 522, 942, 573)),
    ('Bound shield: edge / handle', '05-bound-side.png', (803, 520, 844, 575)),
    ('Native frame: plain', '06-actual-frame-front.png', (668, 480, 808, 621)),
    ('Native frame: authentic', '06-actual-frame-front.png', (1016, 480, 1156, 621)),
    ('Workspace: raw overlay', '08-workspace-candidate-front.png', (1032, 434, 1114, 482))]
crops = []
for index, (label, name, box) in enumerate(panels):
    x, y = (index % 3) * 370, (index // 3) * 385
    draw.text((x + 10, y + 10), label, fill='black', font=font)
    draw.text((x + 10, y + 36), name, fill='#444444', font=font)
    with Image.open(SOURCE / name) as original:
        cropped = original.convert('RGB').crop(box)
    scale = min(340. / cropped.width, 295. / cropped.height)
    scaled = cropped.resize((int(cropped.width * scale), int(cropped.height * scale)), Image.Resampling.NEAREST)
    sheet.paste(scaled, (x + (370 - scaled.width) // 2, y + 70 + (295 - scaled.height) // 2))
    crops.append({'source': name, 'source_sha256': sha(SOURCE / name),
                  'crop': box, 'resampling': 'NEAREST', 'destination_size': scaled.size})
sheet.save(DEST / 'inspection-crops.png')
save(DEST / 'inspection-crops.json', {'derived_only': True, 'unedited_originals_in_images': True, 'panels': crops})
(DEST / 'README.md').write_text('''# Authentic Native Shield Rendering Comparison

NEMC 3.10.0.420447; owner `shield-r20-v7-authentic`; game PID 39728,
creation identity `134365633584760870`. Nine unedited owner-bound native WGC
images compare the exact shield output retained by the earlier native crafter
package. No product rendering path is enabled. Four automatic reload flags
are false. The frozen BP/RP digest is
`3ba87e51a23e547b192246790bd40c6999ff5f745accc06cbc3ed5ae6aeee06b`.

## Confirmed Native Positive

The authentic raw item is copied unchanged: outer aux 0, typed integer Base 4,
typed integer inner Damage 0, and ordered `bo:1`, `cr:14`, `mc:11` patterns.
`references/authentic-shield.json` is a byte-exact provenance copy.
`records/inputs.json` retains both the source and submitted payload.

Image 01 shows native SetUiItem controls above three unbound host bodies.
Image 02 shows newly attached shields and sword below the same controls.
This negative/positive pair was actually reviewed before the remaining seven
captures. The small orange markers belong to the host model and are not
accepted as item attachments. The host model is an existing composite item
icon mesh with a root bone; it is not an invisible empty host.

With the fixed bind rotation `(90, 0, 0)` and scale `1/16`, yaw 0 shows the
wooden shield reverse. In image 04, yaw 180 exposes the authentic front with
blue base and all three ordered patterns. Image 05 shows an edge and rear
handle. These establish a real native skeleton item attachment that consumes
the authentic Base tag, including visible thickness. They do not establish
the correct frame-local pose, full item proportions or quantitative thickness.

## Differences And Open Gates

The native UI shield above it shows a white base with the same visible
patterns. The verifier measures zero blue pixels and 12,651 white pixels in
the fixed UI inspection crop, while the bone-front crop contains 1,084 blue
pixels. The exact same authentic userdata is retained for both calls. The
route difference is observed; its cause is not established.

Images 06 and 07 are actual native frames populated through native item use.
Their Item.tag matches the authentic payload exactly and ItemRotation is 0.
The authentic frame exposes wooden reverse material; the plain frame shows
a flat green interior rectangle. Neither is accepted as a patterned-front
reference. Native frame block aux/states were not recorded in this version;
support face 2 and both camera configurations are retained in execute-code
receipts. `observations.json` records the smallest next diagnostic: opposing
native frame faces, explicit states/normals and a sword positive, four images
maximum. That follow-up has not started.

Images 08 and 09 show native RenderEntity attachments as an owned raw overlay
on a real editor workspace containing one stone. This is candidate visibility
and rotation only. Item Scene integration, shared depth/occlusion, opacity,
full/missing projection and correct frame-local pose remain open. The overlay
extends across editor panels and is not an accepted product layout.

Banner item shape, its short lower stalk, item pose and thickness are separate
gates. Standing/wall banner block geometry does not satisfy those gates.

## Restoration And Replay

Fifteen execute-code records preserve exact source and SHA256. All 96 guard
cells, inventory, selected slot, player foot, camera/FOV/locks, editor and
workspace are restored; item bindings and owned actors are removed. No
fixture drops remain and the frozen source closure is unchanged.

The first ordinary stop timed out. No force or repeated close was sent while
the exact process remained live. The observer, attached immediately after
ready, recorded game exit `0xC0000409` and MCDK exit 0. A later stop only
finalized already exited processes. Normal lifecycle acceptance remains false.

Run `python host/verify.py .` from this package. It verifies provenance,
payload equality, source hashes, exact binding/actual-frame readbacks,
restoration, all nine native WGC identity/freshness/hash receipts, the fixed
color crops, exact exits and every manifest byte. `inspection-crops.png` is
a derived nearest-neighbor viewing aid; all originals remain under `images/`.
No session routing token is included. Product qualification remains false.
''', encoding='ascii', newline='\n')
files = {path.relative_to(DEST).as_posix(): {'sha256': sha(path), 'bytes': path.stat().st_size}
         for path in sorted(DEST.rglob('*')) if path.is_file()}
save(DEST / 'manifest.json', {'schema': 1, 'production_qualified': False,
    'native_bound_authentic_shield_positive': True, 'files': files})
verify(DEST)
print(json.dumps({'package': str(DEST), 'files': len(files) + 1,
    'bytes': sum(row['bytes'] for row in files.values()), 'verification': checked,
    'staged': False}))
