"""Python 2-compatible settled-pool controls; no class-global replacements."""
import json
import types


def plain(value):
    return json.loads(json.dumps(value))


class SettledPool(object):
    def __init__(self, session, candidate):
        controls = session.liquid_controls
        assert not controls.closed and not controls.pending and controls.error is None
        self.session, self.controls, self.candidate = session, controls, candidate
        self.closed = controls.closed
        self.rows = []
        self.depth = session.camera_depth
        for key, entry in sorted(controls.registry.items(), key=lambda item: repr(item[0])):
            renderer = entry['renderer']
            assert not renderer.closed and renderer.pending is None and renderer.error is None
            slot = renderer.front
            assert renderer.groups[slot] is not None and renderer.visible[slot]
            self.rows.append({'key': repr(key), 'entry': entry, 'renderer': renderer,
                'slot': slot, 'group': renderer.groups[slot], 'pose': renderer.poses[slot],
                'saved_pose': renderer._render_pose,
                'instance_pose': renderer.__dict__.get('_render_pose'),
                'had_instance_pose': '_render_pose' in renderer.__dict__,
                'visibility': tuple(renderer.visible)})
        assert len(self.rows) == 8, 'The existing frozen pool must have eight water groups'
        self.initial = self.snapshot()
        self.last_ids, self.stable_polls = None, 0
        self.suspended = False

    def suspend(self):
        self.controls.closed = True
        self.suspended = True

    def snapshot(self):
        rows, used = [], []
        for row in self.rows:
            renderer, entry = row['renderer'], row['entry']
            banks = [doll.GetModelId() for doll in renderer.dolls]
            used.extend(identity for identity in banks if identity != -1)
            rows.append({'key': row['key'], 'front': renderer.front, 'actual_ids': banks,
                'cached_ids': list(renderer.ids), 'visible': list(renderer.visible),
                'models': [group.model_name if group is not None else None for group in renderer.groups],
                'uniforms': [group.uniforms if group is not None else None for group in renderer.groups],
                'poses': list(renderer.poses), 'geometry': entry.get('geometry'),
                'clip_offset': entry.get('clip_offset'),
                'positions': [ref.current.GetGlobalPosition() for ref in entry['dolls']],
                'sizes': [ref.current.GetSize() for ref in entry['dolls']]})
        assert len(used) == len(set(used)), 'Owned model IDs alias across banks/groups'
        return plain({'entries': rows, 'camera_pose': self.session.camera_pose,
            'camera_pan': self.session.camera_pan, 'depth': self.session.camera_depth,
            'actual_depth': self.session.camera_depth_pose})

    def submit(self, mode):
        assert self.suspended and mode in ('S', 'SE')
        self.last_ids, self.stable_polls = None, 0
        submitted = []
        for row in self.rows:
            renderer, slot = row['renderer'], row['slot']
            method = row['saved_pose'] if mode == 'S' else None
            ok = (method(slot, row['group'], row['pose']) if method is not None else
                  self.candidate(renderer, slot, row['group'], row['pose']))
            submitted.append({'key': row['key'], 'returned': bool(ok), 'mode': mode,
                'model': row['group'].model_name, 'pose': row['pose'], 'render_depth': -50})
            assert ok, 'Native water submission rejected: ' + row['key']
        return plain(submitted)

    def poll_ids(self):
        state = self.snapshot()
        ids = [row['actual_ids'][row['front']] for row in state['entries']]
        if any(identity == -1 for identity in ids):
            self.stable_polls = 0
        else:
            self.stable_polls = self.stable_polls + 1 if ids == self.last_ids else 1
        self.last_ids = ids
        return {'ready': self.stable_polls >= 2, 'ids': ids, 'state': state}

    def payload(self, hidden=False):
        result = []
        for row in self.rows:
            renderer, slot, group = row['renderer'], row['slot'], row['group']
            identity = renderer.dolls[slot].GetModelId()
            assert identity != -1
            values = group.uniforms
            if hidden:
                values = values[:3] + (values[3][:3] + (0.,),)
            actual = []
            for index, value in enumerate(values, 1):
                assert renderer.model_component.SetExtraUniformValue(identity, index, value)
                readback = renderer.model_component.GetExtraUniformValue(identity, index)
                assert readback is not None and len(readback) == 4
                assert all(abs(a-b) < .0001 for a, b in zip(readback, value)), (index, readback, value)
                actual.append(readback)
            result.append({'key': row['key'], 'id': identity, 'actual_uniforms': actual,
                           'hidden': hidden, 'tag': int(actual[3][0]) & 255})
        assert all(row['tag'] == 134 for row in result)
        return plain(result)

    def release_for_depth(self):
        assert self.suspended
        for row in self.rows:
            renderer = row['renderer']
            try:
                method = types.MethodType(self.candidate, renderer, type(renderer))
            except TypeError:
                method = types.MethodType(self.candidate, renderer)
            renderer._render_pose = method
        self.controls.closed = self.closed
        self.suspended = False
        return {'released': True, 'per_owner_only': True}

    def restore_methods(self):
        for row in self.rows:
            renderer = row['renderer']
            if row['had_instance_pose']:
                renderer._render_pose = row['instance_pose']
            else:
                renderer.__dict__.pop('_render_pose', None)
        return {'restored': all(row['renderer']._render_pose == row['saved_pose'] for row in self.rows)}

    def restore_submissions(self):
        rows = []
        self.last_ids, self.stable_polls = None, 0
        for row in self.rows:
            try:
                ok = row['saved_pose'](row['slot'], row['group'], row['pose'])
                error = None
            except (ValueError, TypeError, RuntimeError) as exc:
                ok, error = False, repr(exc)
            rows.append({'key': row['key'], 'returned': bool(ok), 'error': error})
        return {'restored': all(row['returned'] for row in rows), 'rows': rows}

    def finish(self):
        methods = self.restore_methods()
        self.controls.closed = self.closed
        self.suspended = False
        assert methods['restored']
        assert self.session.camera_depth == self.depth
        state = self.snapshot()
        assert state == self.initial, 'Restored native pool differs from its original state'
        return {'restored': True, 'control_closed': self.controls.closed,
                'methods': methods, 'state': state}
