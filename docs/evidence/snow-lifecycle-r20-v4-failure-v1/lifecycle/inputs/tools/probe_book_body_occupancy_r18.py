"""Isolated table bottom-plane proof; never grants product qualification."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT, save
from audit_native_coordinates_r15 import LOAD, PROJECT, OCCUPY
from probe_banner_product_r16 import BannerAudit
from probe_book_native_r16 import (BookAudit, book_sources, document,
                                   CANDIDATE_SETUP, CANDIDATE_RESTORE)
from verify_debug_blueprints import CLIENT

BOOK_COUNT = CLIENT+'''owners=getattr(b.projection_liquid,'companions',())
_result=sum(len(v.renderer.active) for v in owners if type(v).__name__=='BookProjection')
'''


def world_camera(audit, low, reverse=False):
    target = (3.5, 3.1 if low else 3.5, 3.5)
    position = (7.5, 3.0 if low else 7.0, -1.5)
    if reverse:
        position = (-.5, position[1], 8.5)
    return audit.execute('close_camera', CLIENT+'''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+%r[i] for i in range(3))
position=tuple(s.origin[i]+%r[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''' % (target, position))


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    audit = BookAudit(args)
    data, source = document('enchanting_table')
    sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
    from projection.model import Document
    host = Document.from_data(data)
    if args.side_neighbors:
        for position in ((2, 3, 3), (4, 3, 3), (3, 3, 2), (3, 3, 4)):
            host.set_cell(position, ('minecraft:smooth_stone_slab', 0))
        data = host.to_data()
    support = Document.from_data(data)
    support.set_cell((3, 3, 3), ('minecraft:air', 0))
    report = {'schema_version': 1, 'stage': 'body_boundary_diagnostic',
        'engine': '3.10.0.420447', 'product_qualified': False,
        'completed': False, 'restored': False, 'captures': {}, 'rows': {},
        'cleanup_errors': [], 'installed_sources': book_sources(args.project),
        'source': source, 'source_document': data}
    report['side_neighbors'] = args.side_neighbors
    occupied = ()
    try:
        report['candidate_setup'] = audit.execute('candidate_setup', CANDIDATE_SETUP)
        audit.execute('load', LOAD % ('production', (), json.dumps(data)))
        audit.settle()
        for yaw, pitch in ((35., 25.), (215., 25.), (35., 75.), (35., 5.)):
            label = 'editor_yaw%d_pitch%d' % (yaw, pitch)
            audit.execute(label, CLIENT+'s.camera_view(%r,%r,4.)\ns.emit("view")\n_result=True' % (yaw,pitch))
            time.sleep(.8)
            report['captures'][label] = BannerAudit.frame(audit, label)
        for low in (False, True):
            view = 'low' if low else 'high'
            audit.execute('load', LOAD % ('production', (), json.dumps(data)))
            audit.settle()
            code = (PROJECT % True).replace('s.origin=(0,-57,0)',
                'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
            audit.execute('project', code)
            audit.settle(True)
            report['rows'][view+'_camera'] = world_camera(audit, low, args.side_neighbors and low)
            label = 'missing_'+view+'_shown'
            report['captures'][label] = BannerAudit.frame(audit, label)
            origin = audit.execute('origin', CLIENT+'_result=json.dumps(s.origin)')
            occupied = (tuple(origin[i]+3 for i in range(3)),)
            for restore, state, expected in ((False, 'occupied', 0), (True, 'restored', 1)):
                label = 'missing_'+view+'_'+state
                report['rows'][label] = audit.execute(label, OCCUPY % (occupied, restore), False)
                if restore:
                    occupied = ()
                deadline = time.monotonic()+25.
                while time.monotonic() < deadline:
                    count = audit.execute('book_count', BOOK_COUNT)
                    if count == expected:
                        break
                    time.sleep(.4)
                else:
                    raise TimeoutError('Book occupancy did not settle')
                audit.settle(True)
                time.sleep(1.)
                before_count = audit.execute(label+'_count_before_capture', BOOK_COUNT)
                report['captures'][label] = BannerAudit.frame(audit, label)
                after_count = audit.execute(label+'_count_after_capture', BOOK_COUNT)
                report['rows'][label+'_visibility'] = {'expected': expected,
                    'before_capture': before_count, 'after_capture': after_count,
                    'readback_matched': before_count == after_count == expected}
            audit.execute('stop', CLIENT+'b.stop_projection()\n_result=True')
            audit.execute('support_control', LOAD % ('production', (), json.dumps(support.to_data())))
            audit.settle()
            audit.execute('project', code)
            audit.settle(True)
            world_camera(audit, low, args.side_neighbors and low)
            label = 'missing_'+view+'_support_control'
            report['captures'][label] = BannerAudit.frame(audit, label)
            audit.execute('stop', CLIENT+'b.stop_projection()\n_result=True')
        report['completed'] = True
    finally:
        if occupied:
            try:
                audit.execute('restore_occupied', OCCUPY % (occupied, True), False)
            except Exception as error:
                report['cleanup_errors'].append(str(error))
        try:
            audit.execute('cleanup', CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''')
            report['candidate_restoration'] = audit.execute('restore_profile', CANDIDATE_RESTORE)
            report['restored'] = not report['cleanup_errors']
        except Exception as error:
            report['cleanup_errors'].append(str(error))
        report['source_unchanged'] = report['installed_sources'] == book_sources(args.project)
        save(args.output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed','restored','source_unchanged','cleanup_errors')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--side-neighbors', action='store_true',
                        help='Add four half-height neighbors and inspect the reverse view too.')
    run(parser.parse_args())
