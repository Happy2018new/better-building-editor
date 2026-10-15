"""Python 2-compatible natural-owner A/B instrumentation; importing is inert."""
import time
import json


class WaterDepthAB(object):
    def __init__(self, session, viewport, render, transport, baseline_update):
        self.session, self.viewport = session, viewport
        self.render, self.transport = render, transport
        self.controls = session.liquid_controls
        self.baseline_update = getattr(baseline_update, 'im_func', baseline_update)
        self.candidate_update = viewport.LiquidControls.__dict__['update']
        self.saved_validate = render.SkeletonLiquidRenderer.validate
        self.saved_validate_descriptor = render.SkeletonLiquidRenderer.__dict__['validate']
        self.saved_restore = render.SkeletonLiquidRenderer.__dict__['restore_publication']
        self.saved_pose = render.SkeletonLiquidRenderer.__dict__['_render_pose']
        self.saved_uniforms = transport.validate_uniforms
        self.renderers = tuple(entry['renderer'] for entry in self.controls.registry.values())
        self.saved_native = []
        self.phase, self.row = None, None
        self.installed = False

    def snapshot(self):
        rows = []
        for key, entry in sorted(self.controls.registry.items(), key=lambda item: repr(item[0])):
            renderer = entry['renderer']
            rows.append({'key': repr(key), 'geometry': entry.get('geometry'),
                         'clip_offset': entry.get('clip_offset'),
                         'ready_request': entry.get('ready_request'),
                         'front': renderer.front, 'ids': list(renderer.ids),
                         'visible': list(renderer.visible), 'uniforms': list(renderer.uniforms),
                         'poses': list(renderer.poses), 'pending': renderer.pending,
                         'publication_restore': list(renderer.publication_restore),
                         'doll_positions': [ref.current.GetGlobalPosition() for ref in entry['dolls']],
                         'doll_sizes': [ref.current.GetSize() for ref in entry['dolls']]})
        return json.loads(json.dumps({'entries': rows, 'pending': self.controls.pending,
                'error': self.controls.error, 'camera_pose': self.session.camera_pose,
                'camera_pan': self.session.camera_pan, 'camera_depth': self.session.camera_depth_pose}))

    def begin(self, name, mode='candidate', ticks=60, warmup=5):
        assert self.installed and (self.phase is None or self.phase['done'])
        assert mode in ('baseline', 'candidate', 'clip', 'invalid')
        assert 1 <= ticks <= 60 and 0 <= warmup <= 5
        if mode in ('baseline', 'candidate'):
            for entry in self.controls.registry.values():
                entry.pop('distance_request', None)
        self.phase = {'name': name, 'mode': mode, 'ticks': ticks, 'warmup': warmup,
                      'warmup_rows': [], 'rows': [], 'done': False,
                      'before': self.snapshot(), 'after': None}
        return {'name': name, 'mode': mode, 'natural_ticks': ticks, 'warmup_ticks': warmup}

    def state(self):
        return self.phase

    def install(self):
        assert not self.installed
        engine = self

        def source_uniforms(uniforms):
            if engine.row is not None:
                engine.row['source_validations'] += 1
            return engine.saved_uniforms(uniforms)

        def validate(group, pose):
            if engine.row is not None:
                engine.row['renderer_validations'] += 1
            return engine.saved_validate(group, pose)

        def restore(renderer):
            if engine.row is not None and renderer in engine.renderers:
                engine.row['publication_restores'] += 1
            return engine.saved_restore(renderer)

        def render_pose(renderer, slot, group, pose):
            if engine.row is not None and renderer in engine.renderers:
                engine.row['native_submissions'].append({'slot': slot, 'model': group.model_name,
                                                        'pose': pose})
            return engine.saved_pose(renderer, slot, group, pose)

        class NativeProxy(object):
            def __init__(self, target):
                self.target = target
            def __getattr__(self, name):
                return getattr(self.target, name)
            def SetExtraUniformValue(self, identity, index, value):
                result = self.target.SetExtraUniformValue(identity, index, value)
                if engine.row is not None:
                    engine.row['native_uniform_writes'].append(
                        {'identity': identity, 'index': index, 'value': value, 'returned': result})
                return result

        def timed_update(controls, groups, view_at, pose_at, clip_offset, now):
            if controls is not engine.controls or engine.phase is None:
                return engine.candidate_update(controls, groups, view_at, pose_at, clip_offset, now)
            phase = engine.phase
            original = engine.baseline_update if phase['mode'] == 'baseline' else engine.candidate_update
            collecting = not phase['done']
            row = {'source_validations': 0, 'renderer_validations': 0,
                   'view_callbacks': 0, 'pose_callbacks': 0, 'publication_restores': 0,
                   'native_submissions': [], 'native_uniform_writes': [], 'native_visibility': [],
                   'registry_entries': len(controls.registry), 'requested_groups': len(groups)}

            def current_view(origin):
                row['view_callbacks'] += 1
                view = view_at(origin)
                if view is not None and phase['mode'] == 'clip':
                    view = view._replace(clipped=True)
                elif view is not None and phase['mode'] == 'invalid':
                    view = view._replace(distance=512.)
                return view

            def current_pose(view):
                row['pose_callbacks'] += 1
                return pose_at(view)

            wall, fine = time.time(), time.clock() if hasattr(time, 'clock') else None
            engine.row = row if collecting else None
            try:
                result = original(controls, groups, current_view, current_pose, clip_offset, now)
                row['returned'] = result
                return result
            finally:
                engine.row = None
                if collecting:
                    row['started'] = wall
                    row['wall_ms'] = (time.time() - wall) * 1000.
                    row['high_resolution_wall_ms'] = ((time.clock() - fine) * 1000.
                                                       if fine is not None else None)
                    row['pending'], row['error'] = controls.pending, controls.error
                    row['cached_entries'] = sum('distance_request' in entry
                                                for entry in controls.registry.values())
                    target = phase['warmup_rows'] if len(phase['warmup_rows']) < phase['warmup'] else phase['rows']
                    target.append(row)
                    if len(phase['rows']) == phase['ticks']:
                        phase['done'] = True
                        phase['after'] = engine.snapshot()

        self.transport.validate_uniforms = source_uniforms
        self.render.SkeletonLiquidRenderer.validate = staticmethod(validate)
        self.render.SkeletonLiquidRenderer.restore_publication = restore
        self.render.SkeletonLiquidRenderer._render_pose = render_pose
        self.viewport.LiquidControls.update = timed_update
        for renderer in self.renderers:
            original_model, original_show = renderer.model_component, renderer.show
            self.saved_native.append((renderer, original_model, original_show))
            renderer.model_component = NativeProxy(original_model)
            def wrap_show(show):
                def recorded_show(slot, visible):
                    result = show(slot, visible)
                    if engine.row is not None:
                        engine.row['native_visibility'].append(
                            {'slot': slot, 'visible': visible, 'returned': result})
                    return result
                return recorded_show
            renderer.show = wrap_show(original_show)
        self.installed = True

    def uninstall(self):
        self.viewport.LiquidControls.update = self.candidate_update
        self.render.SkeletonLiquidRenderer.validate = self.saved_validate_descriptor
        self.render.SkeletonLiquidRenderer.restore_publication = self.saved_restore
        self.render.SkeletonLiquidRenderer._render_pose = self.saved_pose
        self.transport.validate_uniforms = self.saved_uniforms
        for renderer, component, show in self.saved_native:
            renderer.model_component, renderer.show = component, show
        self.installed = False
        return {'restored': self.viewport.LiquidControls.__dict__['update'] is self.candidate_update
                and self.render.SkeletonLiquidRenderer.validate is self.saved_validate
                and self.render.SkeletonLiquidRenderer.__dict__['restore_publication'] is self.saved_restore
                and self.render.SkeletonLiquidRenderer.__dict__['_render_pose'] is self.saved_pose
                and self.transport.validate_uniforms is self.saved_uniforms
                and all(renderer.model_component is component and renderer.show is show
                        for renderer, component, show in self.saved_native)}
