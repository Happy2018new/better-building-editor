"""Native table boundary pixels: target-owned body against legacy neighbor leak."""
import argparse
import json
from pathlib import Path
import sys
import time

from audit_native_coordinates_r15 import LOAD, OCCUPY, PROJECT
from audit_native_visual_r15 import ROOT, save
from probe_banner_product_r16 import BannerAudit
from probe_book_native_r16 import BookAudit, CANDIDATE_SETUP, CANDIDATE_RESTORE, book_sources, document
from probe_book_body_occupancy_r18 import BOOK_COUNT
from verify_debug_blueprints import CLIENT

FACES = ('down', 'north', 'south', 'east', 'west')
SIDE_NEIGHBORS = ((2, 3, 3), (4, 3, 3), (3, 3, 2), (3, 3, 4))
CAMERAS = {'down': ((7.5, 7., -1.5), (3.5, 3.1, 3.5)),
           'north': ((5., 4.5, -2.), (3.5, 3.25, 3.5)),
           'south': ((2., 4.5, 9.), (3.5, 3.25, 3.5)),
           'east': ((9., 4.5, 5.), (3.5, 3.25, 3.5)),
           'west': ((-2., 4.5, 2.), (3.5, 3.25, 3.5))}
LEGACY = CLIENT+'''from modern_projection.projection import render_context as context
assert not hasattr(sys,'_table_r19_context_saved')
sys._table_r19_context_saved=(context.independent_body,context.context_cell)
context.independent_body=lambda material:False
context.context_cell=lambda cell:cell
_result=True
'''
RESTORE_CONTEXT = CLIENT+'''if hasattr(sys,'_table_r19_context_saved'):
 from modern_projection.projection import render_context as context
 context.independent_body,context.context_cell=sys._table_r19_context_saved
 del sys._table_r19_context_saved
_result=True
'''


def case_documents(face):
    sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
    from projection.model import Document
    native, source = document('enchanting_table')
    original = Document.from_data(native)
    values = {(3, 3, 3): original.get((3, 3, 3))}
    values.update(((x, 2, z), ('minecraft:stone', 0)) for x in range(2, 5) for z in range(2, 5))
    if face != 'down':
        values.update((pos, ('minecraft:smooth_stone_slab', 0)) for pos in SIDE_NEIGHBORS)
    host = Document((7, 7, 7), values)
    support = Document.from_data(host.to_data())
    support.set_cell((3, 3, 3), ('minecraft:air', 0))
    return host.to_data(), support.to_data(), source, values


def camera(audit, face):
    position, target = CAMERAS[face]
    return audit.execute('camera_'+face, CLIENT+'''cam=b.factory.CreateCamera(b.level)
position=tuple(s.origin[i]+%r[i] for i in range(3))
target=tuple(s.origin[i]+%r[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result={'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()}
''' % (position, target))


def projection(audit, face, values):
    table_faces = {'down': ((3., 3., 3.), (4., 3., 3.), (4., 3., 4.), (3., 3., 4.)),
                  'north': ((3., 3., 3.), (4., 3., 3.), (4., 3.75, 3.), (3., 3.75, 3.)),
                  'south': ((3., 3., 4.), (4., 3., 4.), (4., 3.75, 4.), (3., 3.75, 4.)),
                  'east': ((4., 3., 3.), (4., 3., 4.), (4., 3.75, 4.), (4., 3.75, 3.)),
                  'west': ((3., 3., 3.), (3., 3., 4.), (3., 3.75, 4.), (3., 3.75, 3.))}
    def box(pos, height):
        return tuple((pos[0]+x, pos[1]+y, pos[2]+z)
                     for x in (0., 1.) for y in (0., height) for z in (0., 1.))
    supports = [box(pos, .5 if material[0].endswith('slab') else 1.)
                for pos, material in values.items() if pos != (3, 3, 3)]
    return audit.execute('projection_'+face, CLIENT+'''cam=b.factory.CreateCamera(b.level)
def project(points):
 return [cam.WorldToScreenPoint(*(s.origin[i]+point[i] for i in range(3))) for point in points]
_result={'face':project(%r),'target':project(%r),'supports':[project(points) for points in %r],
 'method':'WorldToScreenPoint physical pixels','origin':s.origin}
''' % (table_faces[face], box((3, 3, 3), 1.), supports))


def project(audit, data):
    audit.execute('stop', CLIENT+'b.stop_projection()\n_result=True')
    audit.execute('load', LOAD % ('production', (), json.dumps(data)))
    audit.settle()
    code = (PROJECT % True).replace('s.origin=(0,-57,0)',
        's.origin=sys._table_r19_origin')
    audit.execute('project', code)
    audit.settle(True)


def capture(audit, row, face, state, expected):
    before = audit.execute(state+'_before_owner', BOOK_COUNT)
    row['captures'][state] = BannerAudit.frame(audit, face+'_'+state)
    after = audit.execute(state+'_after_owner', BOOK_COUNT)
    if expected is not None and (before != expected or after != expected):
        raise ValueError('Unstable book visibility during table body boundary capture')
    row['visibility'][state] = [before, after]


def settle_count(audit, expected):
    deadline = time.monotonic()+30.
    while time.monotonic() < deadline:
        if audit.execute('book_count', BOOK_COUNT) == expected:
            audit.settle(True)
            time.sleep(.8)
            return
        time.sleep(.4)
    raise TimeoutError('Real occupancy did not reach its table/book visibility')


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    audit = BookAudit(args)
    report = {'schema_version': 1, 'stage': 'body_boundary_pixels', 'engine': '3.10.0.420447',
              'product_qualified': False, 'completed': False, 'restored': False,
              'source_unchanged': False, 'cleanup_errors': [], 'views': {},
              'negative_route': 'legacy_neighbor_context',
              'production_default_requested': args.production_default,
              'profile_assignment_performed': not args.production_default,
              'installed_sources': book_sources(args.project)}
    occupied = ()
    try:
        if args.production_default:
            report['default_profile'] = audit.execute('default_profile', CLIENT+'''from modern_projection.projection import static_table
assert static_table.CANDIDATE_ENABLED is False
assert static_table.table_proxy(('minecraft:enchanting_table',0))==(static_table.TABLE_PROXY,0)
assert s.book_profile is not None
_result={'identity':s.book_profile.identity,'body_candidate_override':static_table.CANDIDATE_ENABLED}
''')
        else:
            report['candidate_setup'] = audit.execute('candidate_setup', CANDIDATE_SETUP)
        audit.execute('origin', CLIENT+'''foot=b.player_position.GetFootPos()
assert not hasattr(sys,'_table_r19_origin')
sys._table_r19_origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))
_result=sys._table_r19_origin
''')
        for face in FACES:
            host, support, source, values = case_documents(face)
            row = {'captures': {}, 'visibility': {}, 'source_document': host,
                   'support_document': support, 'source': source,
                   'occupied_world_retained_for_controls': False}
            report['views'][face] = row
            project(audit, host)
            camera(audit, face)
            row['projection'] = projection(audit, face, values)
            capture(audit, row, face, 'shown', 1)
            origin = row['projection']['origin']
            occupied = (tuple(origin[i]+3 for i in range(3)),)
            row['occupy'] = audit.execute('occupy', OCCUPY % (occupied, False), False)
            settle_count(audit, 0)
            capture(audit, row, face, 'occupied', 0)
            audit.execute('legacy_negative_route', LEGACY)
            project(audit, host)
            camera(audit, face)
            capture(audit, row, face, 'legacy_negative', 0)
            audit.execute('restore_context', RESTORE_CONTEXT)
            project(audit, support)
            camera(audit, face)
            capture(audit, row, face, 'support_control', 0)
            audit.execute('stop_for_blank', CLIENT+'b.stop_projection()\n_result=True')
            time.sleep(.8)
            capture(audit, row, face, 'blank', None)
            row['occupied_world_retained_for_controls'] = True
            row['restore'] = audit.execute('restore', OCCUPY % (occupied, True), False)
            occupied = ()
            project(audit, host)
            camera(audit, face)
            capture(audit, row, face, 'restored', 1)
            save(args.output/'report.json', report)
        report['completed'] = True
    finally:
        if occupied:
            try:
                audit.execute('restore_occupied', OCCUPY % (occupied, True), False)
            except Exception as error:
                report['cleanup_errors'].append('occupancy: '+str(error))
        try:
            audit.execute('restore_context', RESTORE_CONTEXT)
            audit.execute('cleanup', CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
if hasattr(sys,'_table_r19_origin'):del sys._table_r19_origin
_result=True
''')
            if not args.production_default:
                report['candidate_restoration'] = audit.execute('restore_profile', CANDIDATE_RESTORE)
            report['restored'] = not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append('cleanup: '+str(error))
        report['source_unchanged'] = report['installed_sources'] == book_sources(args.project)
        save(args.output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged', 'cleanup_errors')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--production-default', action='store_true')
    run(parser.parse_args())
