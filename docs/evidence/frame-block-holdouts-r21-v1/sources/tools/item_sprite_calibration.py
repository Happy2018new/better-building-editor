"""Independent stone-camera calibration inside the owned item test session."""
import time

from capture_native_window import capture
from item_sprite_capture_contract import camera_matches
from verify_camera_projection import LOAD_CUBE, POSE, CAMERA, analyze_calibration
from verify_debug_visuals import PROJECTION_STATUS


def calibrate(check, session, owner, output, wgc, save, before_capture=None):
    evidence = {'schema': 1, 'completed': False, 'passed': False, 'restored': False,
                'fixture_identity': 'camera.calibration.stone', 'views': [],
                'session': session, 'cleanup_errors': []}
    saved = False
    try:
        check.run("assert not hasattr(sys,'_item_camera_saved')\n"
                  "sys._item_camera_saved={'document':s.editor.document,'origin':s.origin,"
                  "'opacity':s.opacity,'missing':s.projection_missing,'outline':s.projection_outline}\n_result=True")
        saved = True
        # Keep the reference cube above nearby mountains and foliage. Their
        # temporal fog changes can join the differenced cube silhouette even
        # though its camera is stable. Preserve the original pixel tolerances.
        evidence['fixture'] = check.run(LOAD_CUBE % 57)
        state = check.wait('independent stone camera cube',
            lambda row: row['active'] and row['ready'] and not row['preparing']
            and row['actors'] == 1 and bool(row['mesh']), lambda: check.run(PROJECTION_STATUS))
        if check.navigation()['open']:
            check.run('navigator.pop()\n_result=True')
            check.wait('closed camera calibration workspace',
                lambda row: not row['open'] and not row['transition'], check.navigation)
        for label, offset in (('front', (0., 0., 6.)), ('right', (6., 0., 0.)),
                              ('tilted', (0., -3., 6.))):
            pose = check.run(POSE % (offset,))
            observation = check.run(CAMERA)
            expected = dict(pose, screen=observation['screen'], fov=observation['fov'])
            camera = check.wait('independent stone camera '+label,
                lambda row: camera_matches(row, expected), lambda: check.run(CAMERA))
            time.sleep(.4)
            if before_capture:
                before_capture()
            shown = capture(session['session_file'], owner, output/('camera_'+label+'_shown.png'), wgc)
            try:
                check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
                time.sleep(.25)
                if before_capture:
                    before_capture()
                hidden = capture(session['session_file'], owner, output/('camera_'+label+'_hidden.png'), wgc)
            finally:
                check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
            after = check.run(CAMERA)
            final = check.run(PROJECTION_STATUS)
            assert camera_matches(after, expected), (after, expected)
            assert state['mesh'][:3] == final['mesh'][:3], (state, final)
            for row in (shown, hidden):
                row['size'] = [row['width'], row['height']]
            evidence['views'].append({'view': label, 'pose': pose, 'camera': camera,
                'camera_after': after, 'shown': shown, 'hidden': hidden, 'passed': False,
                'signal': str(output/('camera_'+label+'_signal.png')),
                'outline_comparison': str(output/('camera_'+label+'_outline.png'))})
            save('camera.json', evidence)
        evidence['completed'] = True
        evidence['reported_fov'] = evidence['views'][0]['camera']['fov']
        evidence['engine_screen'] = evidence['views'][0]['camera']['screen']
        evidence['capture_size'] = evidence['views'][0]['shown']['size']
        analyze_calibration(evidence)
    except Exception as error:
        evidence['error'] = type(error).__name__+': '+str(error)
    finally:
        if saved:
            try:
                check.run("b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\n"
                    "cam.ResetCameraPos()\ncam.LockModCameraPitch(False)\ncam.LockModCameraYaw(False)\n"
                    "cam.UnDepartCamera()\nsaved=sys._item_camera_saved\n"
                    "s._loaded(saved['document'])\ns.origin=saved['origin']\ns.opacity=saved['opacity']\n"
                    "s.projection_missing=saved['missing']\ns.projection_outline=saved['outline']\n"
                    "del sys._item_camera_saved\n_result=True")
                evidence['restored'] = True
            except Exception as error:
                evidence['cleanup_errors'].append(type(error).__name__+': '+str(error))
        evidence['passed'] = evidence['passed'] and evidence['restored'] and not evidence['cleanup_errors']
        save('camera.json', evidence)
    return evidence
