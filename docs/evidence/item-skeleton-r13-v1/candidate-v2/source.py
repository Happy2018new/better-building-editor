"""Freeze an opaque, ordinary-material skeleton and same-actor sword control.

Candidate resources remain under tools/data. Installing them is explicit and
restricted to an isolated checkout; root production registrations stay intact.
The runtime reuses the audited R14 ownership, camera and marker lifecycle.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid

import prepare_client_anchor_depth_candidate_r15 as previous

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'modern_projection_diagnostic_item_body_r13'
ATTRIBUTE = '_item_skeleton_r13_probe'
POSITIVE_STATES = ('ui_skeleton_positive', 'ui_skeleton_positive_restored')
POSITIVE_NAME = 'skeleton'
POSITIVE_TARGET = 'owned_skeleton_actor'
STATES = (POSITIVE_STATES[0], 'ui_body', 'ui_plain', 'ui_body_restored', POSITIVE_STATES[1])
UI = dict(previous.UI)
RESOURCE_DIR = Path('models/modern_projection/item_diagnostic_r13')
TEXTURE_PATH = 'modern_projection/item_diagnostic_r13/body'
DATA = ROOT / 'tools/data/item-skeleton-candidate-r13-v1'
digest = previous.digest
archived_files = previous.archived_files


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('ascii')


def opaque_mesh():
    """24 ordinary root-weighted vertices, not an encoded liquid mesh."""
    lo, hi = (-.25, 0., -.125), (.25, .5, .125)
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    faces = (
        ((0., 0., -1.), ((x0,y0,z0), (x0,y1,z0), (x1,y1,z0), (x1,y0,z0))),
        ((0., 0., 1.), ((x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1))),
        ((-1., 0., 0.), ((x0,y0,z0), (x0,y0,z1), (x0,y1,z1), (x0,y1,z0))),
        ((1., 0., 0.), ((x1,y0,z0), (x1,y1,z0), (x1,y1,z1), (x1,y0,z1))),
        ((0., -1., 0.), ((x0,y0,z0), (x1,y0,z0), (x1,y0,z1), (x0,y0,z1))),
        ((0., 1., 0.), ((x0,y1,z0), (x0,y1,z1), (x1,y1,z1), (x1,y1,z0))))
    vertices, indices = [], []
    uv = ((0., 1.), (0., 0.), (1., 0.), (1., 1.))
    for normal, positions in faces:
        start = len(vertices)
        vertices.extend({'pos': list(pos), 'normal': list(normal), 'uvcoord': list(tex),
                         'weight': [['root', 1.]]} for pos, tex in zip(positions, uv))
        indices.extend(([start, start+1, start+2], [start, start+2, start+3]))
    return {'mesh': [{'material': TEXTURE_PATH, 'vertices': vertices, 'indices': indices}]}


def resources():
    from io import BytesIO
    from PIL import Image
    texture = BytesIO()
    Image.new('RGBA', (8, 8), (232, 32, 160, 255)).save(texture, format='PNG')
    skeleton = {'boundingbox': [[-.25, 0., -.125], [.25, .5, .125]], 'skeleton': [{
        'name': 'root', 'parent': 'root', 'initpos': [0., 0., 0.],
        'initquaternion': [0., 0., 0., 1.], 'initscale': [1., 1., 1.],
        'offmtx': [[1.,0.,0.,0.], [0.,1.,0.,0.], [0.,0.,1.,0.]],
        'boundingbox': [[-.25,0.,-.125], [.25,.5,.125]]}]}
    registration = {'dy_load': True, 'mesh': str(RESOURCE_DIR/'mesh.json').replace('\\','/')[7:],
                    'skeleton': str(RESOURCE_DIR/'skeleton.json').replace('\\','/')[7:],
                    'animation': {}, 'material': 'entity_for_skeleton',
                    'texture': {'tex0': TEXTURE_PATH}}
    return {str(RESOURCE_DIR/'mesh.json').replace('\\','/'): json_bytes(opaque_mesh()),
            str(RESOURCE_DIR/'skeleton.json').replace('\\','/'): json_bytes(skeleton),
            'textures/models/'+TEXTURE_PATH+'.png': texture.getvalue(),
            'registration.json': json_bytes({MODEL: registration})}


def snippets(nonce):
    programs = {name: source.replace(previous.ATTRIBUTE, ATTRIBUTE)
                for name, source in previous.snippets(nonce).items()
                if name in previous.FILES}
    install = programs['install_client.py']
    setup = """saved['skeleton_setup']={'model':%r,'state':'pending'}
saved['skeleton_setup']['model_id']=b.factory.CreateModel(saved['actor']).SetModel(%r)
saved['skeleton_setup']['state']='returned'
identity=saved['skeleton_setup']['model_id']
assert isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0,saved['skeleton_setup']
""" % (MODEL, MODEL)
    install = previous.replace_once(install, "_result=json.dumps(dict((key,saved[key])", setup+"_result=json.dumps(dict((key,saved[key])")
    install = previous.replace_once(install, "'empty_cells','roi_receipt')))", "'empty_cells','roi_receipt','skeleton_setup')))")
    programs['install_client.py'] = install
    ready = """saved=sys.%s
assert saved['nonce']==%r
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
model_id=b.factory.CreateModel(actor).GetModelId()
_result=json.dumps({'actor':actor,'kind':kind,'model_id':model_id,
 'ready':kind=='modern_projection:anchor' and model_id==saved['skeleton_setup']['model_id'],'clock':time.time()})
""" % (ATTRIBUTE, nonce)
    programs['actor_ready_client.py'] = ready
    status = programs['status_client.py']
    status += """row=json.loads(_result)
identity=row['model_id']
row['skeleton_setup']=saved['skeleton_setup']
row['ready']=row['ready'] and isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
_result=json.dumps(row)
"""
    programs['status_client.py'] = status
    programs['remove_client.py'] = previous.replace_once(
        programs['remove_client.py'], "'create':saved['create']}",
        "'create':saved['create'],'skeleton_setup':saved.get('skeleton_setup')}")
    control = previous.snippets(nonce)['ui_plain_depth15_client.py'].replace(previous.ATTRIBUTE, ATTRIBUTE)
    control = previous.replace_once(control, "label='ui_plain_depth15'", 'label=LABEL_PLACEHOLDER')
    control = control.replace("label=='ui_plain_depth15'", "label=='ui_plain'")
    control = control.replace("label=='ui_empty_restored'", "label=='ui_body_restored'")
    control = control.replace("label in ('ui_plain_depth15','ui_plain_depth50','ui_plain_depth15_repeat')", "label=='ui_plain'")
    control = previous.replace_once(control, 'BindItemToMinecraftModel(', 'BindItemToSkeletonModel(')
    old = """ params['render_depth']=-50 if label=='ui_plain_depth50' else -15
 if label in ('ui_cow_positive','ui_cow_positive_restored'):
  assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
  del params['entity_id']
  params['entity_identifier']='minecraft:cow'
  params['init_rot_y']=60.
"""
    new = """ assert params['entity_id']==saved['actor']
 assert saved['skeleton_setup']['model']==%r
 if label in ('ui_skeleton_positive','ui_skeleton_positive_restored'):
  assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
""" % MODEL
    control = previous.replace_once(control, old, new)
    programs.update({label+'_client.py': control.replace('LABEL_PLACEHOLDER', repr(label)) for label in STATES})
    for name, source in programs.items():
        ast.parse(source, filename=name)
    return programs


def contract():
    return {'schema': 1, 'candidate': 'same_actor_opaque_skeleton_ordinary_item', 'states': list(STATES),
            'public_blueprint': 'test.entities.appearances', 'model': MODEL, 'ui': UI,
            'frames_per_state': 2, 'ordinary_minimum_stable_pixels': 80, 'difference_channel_threshold': 25,
            'restored_maximum_pixels': 2, 'physical_size': [1994,1105], 'fixed_ui_roi': [0,111,1994,1105],
            'same_entity_id_for_render_and_bind': True, 'binding_count': 1, 'bone': 'root',
            'item_offset': [0.,0.,0.], 'item_rotation_zyx': [0.,0.,0.], 'item_scale': 1.,
            'material': 'entity_for_skeleton', 'native_retries': 0, 'background_only': True,
            'production_modified': False, 'production_rendering_accepted': False,
            'enchantment_glint_accepted': False, 'enchantment_tested': False,
            'source_sha256': digest(Path(__file__).read_bytes())}


def prepare(output):
    output = Path(output).absolute()
    if output.exists():
        raise ValueError('Preserve the earlier skeleton candidate')
    nonce = uuid.uuid4().hex
    files = {name: source.encode('ascii') for name, source in snippets(nonce).items()}
    files.update({'source.py': Path(__file__).read_bytes(),
                  'plain.json': (previous.BUNDLE/'plain.json').read_bytes()})
    files.update({'resources/'+name: raw for name, raw in resources().items()})
    plan = dict(contract(), nonce=nonce, files=[{'path': name, 'bytes': len(raw), 'sha256': digest(raw)}
                                              for name, raw in sorted(files.items())])
    output.mkdir(parents=True)
    for name, raw in files.items():
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (output/'plan.json').write_bytes(json_bytes(plan))
    verify(output)
    return plan


def verify(bundle):
    bundle = Path(bundle).resolve(strict=True)
    plan = json.loads((bundle/'plan.json').read_bytes())
    if any(plan.get(key) != value for key, value in contract().items()):
        raise ValueError('Frozen skeleton contract changed')
    nonce = plan['nonce']
    if len(nonce)!=32 or any(char not in '0123456789abcdef' for char in nonce):
        raise ValueError('Candidate nonce changed')
    expected = {name: source.encode('ascii') for name, source in snippets(nonce).items()}
    expected.update({'source.py': Path(__file__).read_bytes(), 'plain.json': (previous.BUNDLE/'plain.json').read_bytes()})
    expected.update({'resources/'+name: raw for name, raw in resources().items()})
    if {row['path'] for row in plan['files']} != set(expected) or len(plan['files']) != len(expected):
        raise ValueError('Candidate inventory changed')
    for row in plan['files']:
        raw = (bundle/row['path']).read_bytes()
        if raw!=expected[row['path']] or len(raw)!=row['bytes'] or digest(raw)!=row['sha256']:
            raise ValueError('Frozen candidate bytes changed: '+row['path'])
    return plan


def install(bundle, receipt):
    """Save exact registration bytes before an isolated diagnostic install."""
    bundle, receipt = Path(bundle).resolve(strict=True), Path(receipt).absolute()
    verify(bundle)
    if receipt.exists():
        raise ValueError('Preserve the original diagnostic installation receipt')
    common = (ROOT/'.git')
    if not common.is_file():
        raise ValueError('Diagnostic install requires a separate Git worktree')
    target = ROOT/'resource_pack/models/netease_models.json'
    original = target.read_bytes()
    registration = json.loads(original)
    if MODEL in registration:
        raise ValueError('Diagnostic model is already registered')
    registration.update(json.loads((bundle/'resources/registration.json').read_bytes()))
    installed = json_bytes(registration)
    paths = [name for name in resources() if name!='registration.json']
    if any((ROOT/'resource_pack'/name).exists() for name in paths):
        raise ValueError('Diagnostic destination already exists')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    original_path = receipt.with_name(receipt.name+'.original.bin')
    if original_path.exists():
        raise ValueError('Preserve original registration bytes')
    original_path.write_bytes(original)
    report = {'schema':1, 'project':str(ROOT), 'candidate_sha256':digest((bundle/'plan.json').read_bytes()),
              'registration_original_sha256':digest(original), 'registration_installed_sha256':digest(installed),
              'original_path':str(original_path), 'paths':{name:digest((bundle/'resources'/name).read_bytes()) for name in paths},
              'restored':False}
    receipt.write_bytes(json_bytes(report))
    for name in paths:
        destination = ROOT/'resource_pack'/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes((bundle/'resources'/name).read_bytes())
    target.write_bytes(installed)
    return report


def restore(receipt):
    receipt = Path(receipt).resolve(strict=True)
    report = json.loads(receipt.read_bytes())
    if report['project']!=str(ROOT) or report['restored']:
        raise ValueError('Exact unrestored installation receipt required')
    target = ROOT/'resource_pack/models/netease_models.json'
    original = Path(report['original_path']).read_bytes()
    current = target.read_bytes()
    if (digest(original)!=report['registration_original_sha256'] or
            digest(current) not in (report['registration_original_sha256'],report['registration_installed_sha256'])):
        raise ValueError('Registration changed independently; preserve it for manual recovery')
    written=[]
    for name,sha in report['paths'].items():
        resource=ROOT/'resource_pack'/name
        if not resource.exists():
            continue
        if not resource.is_file() or digest(resource.read_bytes())!=sha:
            raise ValueError('Diagnostic resource changed independently: '+name)
        written.append(resource)
    if current!=original:
        target.write_bytes(original)
    for resource in written:
        resource.unlink()
    report['restored']=True
    receipt.write_bytes(json_bytes(report))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify','install','restore'))
    parser.add_argument('path')
    parser.add_argument('--receipt')
    args=parser.parse_args()
    if args.command=='install':
        if not args.receipt:parser.error('--receipt is required')
        value=install(args.path,args.receipt)
    elif args.command=='restore':value=restore(args.path)
    else:value=prepare(args.path) if args.command=='prepare' else verify(args.path)
    print(json.dumps({'validated':True,'files':len(value.get('files',[])), 'restored':value.get('restored',False),
                      'sdk_dispatch_attempted':False}))


if __name__=='__main__':
    main()
