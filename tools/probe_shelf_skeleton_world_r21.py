"""Capture one isolated world shelf through the existing owned skeleton renderer."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from PIL import Image

import probe_liquid_pose_channel as native
import probe_native_palette_body_r16 as body
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from probe_product_water import snapshot_sources
from probe_shelf_body_matrix_r20 import CELL_PROJECTION, PLACE, STATES
from probe_shelf_native_shape_r17 import READ_WORLD, VIEWS


MODEL = 'modern_projection_shelf_skeleton_r21_oak_unpowered_world'
PHASES = {'selection': (('selector', 5),),
          'details': (('selector', 5), ('document_normal', 1), ('world_normal', 2),
                      ('intensity', 3), ('tile_light', 4), ('unlit', 6), ('candidate', 0))}
DIRECTIONS = {'south': (0, 128), 'west': (8, 192)}

CREATE = '''import time
from modern_projection.projection.liquid_render import WorldLiquidRenderer
saved=sys._liquid_pose_client
assert not saved.get('shelf_renderer')
bridge=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
saved['shelf_renderer']=WorldLiquidRenderer(bridge,1,saved['dimension'],(16.,16.,16.),(0.,0.,0.))
_result=json.dumps({'adapter':'WorldLiquidRenderer','scale':[16.,16.,16.],
 'rotation':[0.,0.,0.],'anchor':saved['origin'],'model':%r})
'''
SUBMIT = '''import time
from modern_projection.projection.liquid_transport import RenderGroup
saved=sys._liquid_pose_client
mode,rotation=%r
code=float((63<<6)|(rotation<<12))
uniforms=((code,0.,0.,0.),(float(mode),0.,0.,0.),(0.,0.,0.,0.),(39686.,1.,16777215.,1.))
group=RenderGroup(('shelf_body',0),%r,(0,0,0),uniforms)
renderer=saved['shelf_renderer']
assert renderer.begin((group,),saved['origin'],time.clock()),renderer.error
_result=json.dumps({'group':group,'submitted_center':renderer.center(saved['origin'],group.origin),
 'depth_tag':39686.,'mode':mode,'direction_code':rotation})
'''
STATUS = '''import time
saved=sys._liquid_pose_client
renderer=saved['shelf_renderer']
ready=renderer.advance(time.clock())
_result=json.dumps({'ready':ready,'active':len(renderer.active),'staging':len(renderer.staging),
 'retired':len(renderer.retired),'error':renderer.error,'cleanup_errors':renderer.cleanup_errors,
 'models':[{'model_id':record['model_id'],'anchor':record['anchor'],
 'visible':record['visible'],'group':record['group']} for record in renderer.active.values()]})
'''
CLEAN = '''saved=getattr(sys,'_liquid_pose_client',None)
if saved is not None and saved.get('shelf_renderer'):
 renderer=saved['shelf_renderer']
 returned=renderer.close()
 assert returned,(renderer.retired,renderer.cleanup_errors)
 del saved['shelf_renderer']
 _result=json.dumps({'closed':returned,'active':len(renderer.active),
  'staging':len(renderer.staging),'retired':len(renderer.retired),'cleanup_errors':renderer.cleanup_errors})
else:_result=json.dumps({'closed':True,'not_created':True})
'''


def selector_pixels(path, projection):
    points = [row['screen'] for row in projection]
    with Image.open(path).convert('RGB') as image:
        bounds = [max(0, int(math.floor(min(point['screenX'] for point in points)))-4),
                  max(0, int(math.floor(min(point['screenY'] for point in points)))-4),
                  min(image.width, int(math.ceil(max(point['screenX'] for point in points)))+4),
                  min(image.height, int(math.ceil(max(point['screenY'] for point in points)))+4)]
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            return {'passed': False, 'bounds': bounds, 'error': 'Projected native cell has no image area'}
        def count(bitmap):
            return sum(red >= 220 and green <= 24 and blue >= 220 for red, green, blue in bitmap.getdata())
        roi, entire = count(image.crop(bounds)), count(image)
    return {'passed': roi >= 24, 'magenta_pixels_in_native_cell': roi,
            'magenta_pixels_in_frame': entire, 'bounds': bounds,
            'scope': 'Material selector reception in native projected cell; shape acceptance remains false'}


def validate_review(path, direction):
    review = json.loads(path.read_bytes())
    if review.get('root_visual_review_accepted') is not True or review.get('direction') != direction:
        raise ValueError('A root visual review of this direction is required')
    report_path = Path(review['source_report'])
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != review['source_report_sha256']:
        raise ValueError('The reviewed selection report changed')
    report = json.loads(report_path.read_bytes())
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('The reviewed selection capture did not complete and restore')
    if not report.get('selector_readback', {}).get('passed'):
        raise ValueError('The reviewed material selector did not pass')
    capture = report['captures']['selector']
    if hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() != review['selector_sha256']:
        raise ValueError('The reviewed raw selector image changed')
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=PHASES, default='selection')
    parser.add_argument('--direction', choices=DIRECTIONS, default='south')
    parser.add_argument('--review', type=Path)
    parser.add_argument('--south-review', type=Path)
    parser.add_argument('--min-commit-gib', type=float, default=6.)
    args = parser.parse_args()
    if args.output.exists() or not math.isfinite(args.min_commit_gib) or args.min_commit_gib < 6.:
        parser.error('Choose a fresh output and a finite commit threshold of at least 6 GiB')
    review = validate_review(args.review, args.direction) if args.phase == 'details' and args.review else None
    if args.phase == 'details' and review is None:
        parser.error('Read the raw selection captures before admitting detail modes')
    if args.direction != 'south':
        if args.south_review is None:
            parser.error('West requires a root-reviewed south selection first')
        validate_review(args.south_review, 'south')
    session = json.loads(args.session.read_bytes())
    if session['owner'] != args.owner:
        parser.error('Use the owner-bound session')
    project = Path(session['project'])
    os.environ.update(MCDEV_SESSION_FILE=str(args.session.resolve()), MCDEV_OWNER=args.owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    sources = snapshot_sources(project)
    report = {'schema_version': 1, 'phase': args.phase, 'direction': args.direction,
        'completed': False, 'restored': False, 'production_qualified': False,
        'captures': {}, 'cleanup_errors': [], 'resource_samples': [], 'source_sha256': sources,
        'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
        'review': review, 'owner_adapter': 'WorldLiquidRenderer',
        'pose_readback_scope': 'Native camera world/screen/depth and shader normals; model center/scale are submitted owner state'}
    args.output.mkdir(parents=True)
    started = time.monotonic()

    def persist():
        native.write(args.output/'report.json', report)

    def boundary(label):
        sample = commit_at_boundary()
        report['resource_samples'].append(dict(sample, boundary=label))
        persist()
        if sample['commit_available_bytes'] < args.min_commit_gib*1024**3:
            raise RuntimeError('Shelf probe requires the declared available commit margin')
        if time.monotonic()-started > 150.:
            raise RuntimeError('Shelf probe stopped admitting phases after 150 seconds')

    aux, rotation = DIRECTIONS[args.direction]
    material = {'name': 'minecraft:oak_shelf', 'aux': aux}
    with native.Client(timeout=40) as client:
        world = saved = environment = workspace_saved = False
        try:
            boundary('before_fixture')
            workspace_saved = True
            report['workspace'] = native.run(client, body.CLOSE_WORKSPACE)
            deadline = time.monotonic()+10.
            while not native.run(client, body.WORLD_VISIBLE):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Workspace did not close before the shelf probe')
                time.sleep(.2)
            environment = True
            report['environment'] = native.run(client, native.ENVIRONMENT, True)
            world = True
            report['world'] = native.run(client, body.PREPARE % 'minecraft:oak_shelf', True)
            origin = tuple(report['world']['origin'])
            report['placed'] = native.run(client, PLACE % material, True)
            report['states'] = native.run(client, STATES % (material['name'], aux), True)
            if report['states']['minecraft:cardinal_direction'] != args.direction:
                raise RuntimeError('Native shelf state disagrees with the requested direction')
            report['near_player'] = native.run(client, native.NEAR_PLAYER, True)
            saved = True
            native.run(client, (native.SAVE % (origin,)).replace('_result=True',
                "sys._liquid_pose_client['dimension']=%r\n_result=True" % report['world']['dimension']))
            report['camera'] = native.run(client, native.CAMERA.replace(
                'offset=(3.,3.,5.)', 'offset='+repr(VIEWS[args.direction])))
            report['cell_projection'] = native.run(client, CELL_PROJECTION)

            def wait_for(requested):
                deadline = time.monotonic()+15.
                while True:
                    actual = native.run(client, READ_WORLD, True)
                    replica = native.run(client, native.REPLICATION % (origin,))
                    if actual == requested and any(row['name'] == requested['name'] and row['aux'] == requested['aux']
                                                   for row in replica['materials']):
                        return {'world': actual, 'replication': replica}
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Native shelf/air did not settle and replicate: '+repr((actual, replica)))
                    time.sleep(.2)

            def frame(label):
                boundary(label)
                if not native.run(client, body.WORLD_VISIBLE):
                    raise RuntimeError('Workspace obscures the shelf probe')
                time.sleep(.4)
                before = native.run(client, native.CAMERA_CHECK)
                captured = native.capture(str(args.session), args.owner, args.output/(label+'.png'), args.capture_exe)
                after = native.run(client, native.CAMERA_CHECK)
                if before != after:
                    raise RuntimeError('Native camera changed during shelf capture')
                report['captures'][label] = dict(captured, before=before, after=after)
                persist()

            report['native_replication'] = wait_for(material)
            frame('native')
            native.run(client, native.CLEAR, True)
            report['empty_replication'] = wait_for({'name': 'minecraft:air', 'aux': 0})
            frame('empty')
            report['renderer'] = native.run(client, CREATE % MODEL)
            report['modes'] = {}
            for label, mode in PHASES[args.phase]:
                boundary('submit_'+label)
                submitted = native.run(client, SUBMIT % ((mode, rotation), MODEL))
                deadline = time.monotonic()+10.
                while True:
                    status = native.run(client, STATUS)
                    if status['ready']:
                        break
                    if status['error'] or time.monotonic() >= deadline:
                        raise RuntimeError('Owned shelf model did not become ready: '+repr(status))
                    time.sleep(.1)
                report['modes'][label] = {'submitted': submitted, 'owner_state': status}
                frame(label)
                if label == 'selector':
                    report['selector_readback'] = selector_pixels(args.output/'selector.png', report['cell_projection'])
                    persist()
                    if not report['selector_readback']['passed']:
                        raise RuntimeError('Magenta material selector failed in the native cell; open raw images before expanding')
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error)
            persist()
            raise
        finally:
            actions = []
            if saved:
                actions.extend((('renderer', CLEAN, False), ('client', native.CLEAN_CLIENT, False)))
            if world:
                actions.append(('world', native.CLEAN_WORLD, True))
            if environment:
                actions.append(('environment', native.RESTORE_ENVIRONMENT, True))
            if workspace_saved:
                actions.append(('workspace', body.RESTORE_WORKSPACE, False))
            for label, code, server in actions:
                try:
                    report[label+'_restore'] = native.run(client, code, server)
                except Exception as error:
                    report['cleanup_errors'].append(label+': '+str(error))
            report['source_unchanged'] = sources == snapshot_sources(project)
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic()-started
            persist()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()
