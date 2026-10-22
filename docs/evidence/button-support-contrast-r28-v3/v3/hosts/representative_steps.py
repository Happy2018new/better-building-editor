"""Explicit private representative steps, copied without import side effects.

Bindings are supplied by run_lineage_runtime; original hosts remain unchanged.
"""
def pose(check, focus, yaw, pitch, zoom, label, capture=True):
    check.run('s.grid=False\ns.focused=%r\ns.camera_focus_request=%r\n_result=True' %
              (tuple(focus), tuple(value + .5 for value in focus)))
    check.wait('focus consumed ' + label, lambda row: row['request'] is None and row['pivot'] is not None,
               lambda: check.run('_result=json.dumps({"request":s.camera_focus_request,"pivot":s.camera_pivot})'))
    check.run('s.camera_view(%r,%r,%r)\n_result=True' % (yaw, pitch, zoom))
    previous = [None]
    def stable(row):
        near = (abs((row['pose'][0] - yaw + 180.) % 360. - 180.) < .03 and
                abs(row['pose'][1] - pitch) < .03 and abs(row['pose'][2] - zoom) < .003)
        same, previous[0] = row == previous[0], row
        return near and same
    state = check.wait('two equal actual poses ' + label, stable, lambda: check.run(
        '_result=json.dumps({"pose":s.camera_pose,"pivot":s.camera_pivot,"pan":s.camera_pan})'))
    check.editor_preview('pose settled ' + label)
    return {'actual': state, 'requested': (yaw, pitch, zoom),
            'capture': check.capture(label) if capture else None}

def workspace(check):
    check.run('b.stop_projection()\nowner.open_workspace()\n_result=True')
    check.wait('workspace restored', lambda nav: nav['open'] and not nav['transition'], check.navigation)

def representative(check, report, plan, save):
    short, operation = plan['card'], plan['operation']
    originals = tuple(tuple(point) for point in plan['points'])
    identity = PREFIX + short
    row = {'identity': identity, 'operation': operation, 'plan': plan,
           'stages': [], 'manual_acceptance': False}
    report['representatives'].append(row)
    row['card'] = check.load_card(identity)
    oracle = base.Editor(base.build(identity))
    base.prepare(oracle, identity)
    row['initial_data'] = base.verify(check, oracle, short + ' public baseline', report)
    row['before_editor'] = pose(check, base.CASES[identity]['focus'], 35., 25., 4., short + '_before')
    original_state = base.expected(oracle)
    row['transform'] = base.transform(check, oracle, operation, evidence=report)
    changed = base.expected(oracle) != original_state
    assert changed is plan['changes_expected'], (short, changed, plan)
    row['changed'] = changed
    lo, hi = base.CASES[identity]['selection']
    def target(point):
        if operation == 'rotate_y90':
            return (lo[0] + hi[2] - point[2], point[1], lo[2] + point[0] - lo[0])
        assert operation == 'mirror_x', operation
        return (hi[0] + lo[0] - point[0], point[1], point[2])
    points = tuple(target(point) for point in originals)
    after_focus = target(base.CASES[identity]['focus'])
    row['after_focus'] = after_focus
    row['after_editor'] = pose(check, after_focus, 35., 25., 4., short + '_after')
    row['points'] = points
    focus = points[0]  # Integer native cell anchor; camera target adds .5 separately.
    offset = (-5., 4., -7.)
    check.run("sys._transforms_r27['camera_mutated']=True\n_result=True")
    row['full'] = bounded_world(check, short, focus, offset, 1.)
    workspace(check)
    save()
    if plan['missing']:
        controlled_missing(check, report, row, oracle, short, points, focus, offset, save)
    if changed:
        assert oracle.undo()
        check.run('assert s.action(s.editor.undo)\n_result=True')
        row['undo'] = base.verify(check, oracle, short + ':undo', report)
        restored = base.expected(oracle)
        mismatch = [key for key in ('selection', 'start', 'end', 'undo', 'locked_layers')
                    if restored[key] != original_state[key]]
        if base.document_semantics(restored['document']) != base.document_semantics(original_state['document']):
            mismatch.append('document_semantics')
        assert not mismatch, (short, mismatch)
        assert restored['redo'] == 1
    else:
        assert not oracle.undo_stack and not oracle.redo_stack
        row['no_op'] = base.verify(check, oracle, short + ':unchanged-no-history', report)
        assert base.expected(oracle) == original_state
    if plan['sdk_storage']:
        assert changed, 'SDK replay requires a changed representative'
        assert oracle.redo()
        check.run('assert s.action(s.editor.redo)\n_result=True')
        row['redo'] = base.verify(check, oracle, short + ':redo-before-storage', report)
        row['storage'] = {}
        storage.run(check, oracle, row['storage'])
        check.run('doc=s.editor.document\n'
            'sys._blueprint_qa_expected={"metadata":{"name":doc.name,"size":doc.size,"blocks":len(doc.blocks)},'
            '"editor_id":id(s.editor),"document_id":id(doc),"previous_document_id":None}\n_result=True')
        reloaded = base.Editor(base.Document.from_data(oracle.document.to_data()))
        row['reloaded_data'] = base.verify(check, reloaded, short + ':sdk-reloaded', report)
        row['reloaded_editor'] = pose(check, after_focus, 35., 25., 4., short + '_sdk_reloaded')
    row['completed'] = True
    save()


def controlled_missing(check, report, row, oracle, short, points, focus, offset, save):
    token, attempted = uuid.uuid4().hex, False
    try:
        attempted = True
        check.run(missing.INSTALL % (points, token))
        check.run('s.projection_missing=True\nb.project()\n_result=True')
        check.wait('controlled missing starts', missing.ready, lambda: check.run(missing.STATE))
        check.run('navigator.pop()\n_result=True')
        check.wait('world workspace closed', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
        row['native_camera'] = check.run('focus=%r\noffset=%r\ntarget=tuple(s.origin[i]+focus[i]+.5 for i in range(3))\nposition=tuple(target[i]+offset[i] for i in range(3))\nrotation=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))\ncam=factory.CreateCamera(level)\ncam.DepartCamera()\ncam.LockModCameraPitch(True)\ncam.LockModCameraYaw(True)\nassert cam.SetCameraPos(position)\nassert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))\n_result=json.dumps({"target":target,"position":cam.GetPosition(),"rotation":cam.GetCameraRotation()})' % (focus, offset))
        stages = [('empty', ())]
        if len(points) > 1:
            stages.append(('single_half', points[:1]))
        stages.extend((('occupied', points), ('restored', ())))
        previous = None
        target = base.document_semantics(missing.snapshot_document(oracle.document))
        for label, occupied in stages:
            expected = [2 if point in occupied else 1 for point in points]
            if previous is not None:
                check.run('sys._transform_missing_r23_occupied.clear()\nsys._transform_missing_r23_occupied.update(%r)\nfor pos in sys._transform_missing_r23_saved["points"]:b.projection_occupancy.read(pos)\n_result=True' % (occupied,))
                check.wait('new occupancy commit', lambda state: missing.ready(state) and state['commits'] > previous and state['observations'] == expected, lambda: check.run(missing.STATE))
            record = {'label': label, 'expected_observations': expected}
            row['stages'].append(record)
            missing.capture(check, short + '_missing_' + label, expected, base.document_semantics, target, record)
            record['typed_document'] = base.verify(check, oracle, short + ':missing:' + label, report)
            previous = record['final']['commits']
            save()
        row['missing_completed'] = True
    finally:
        check.run('b.stop_projection()\n_result=True')
        if attempted:
            check.run(missing.restore_owned(token))
        workspace(check)
        row['observer_restored'] = True
        save()
