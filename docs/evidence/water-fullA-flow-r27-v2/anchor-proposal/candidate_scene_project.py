"""Host-only proposal: undo the recorded product GUI anchor, with no pixel fit.

The caller must independently bind the frozen OrbitCamera and actual SDK GUI.
This module never imports a game package or mutates an analyzer/source report.
"""


def scene_project_gui_anchor_v1(points, shape, state, native_gui, OrbitCamera):
    if isinstance(native_gui, bool) or not isinstance(native_gui, (int, float)):
        raise ValueError('A recorded numeric SDK GUI scale is required')
    if not 1. <= native_gui < float('inf') or native_gui != round(native_gui):
        raise ValueError('A positive integer SDK GUI scale is required')
    origin = tuple(axis // 4 * 4 for axis in shape['position'])
    groups = state['liquid_groups']
    identities = {row['key'] for row in groups if tuple(row['origin']) == origin}
    controls = [row for row in state['liquid_control_requests'] if row['key'] in identities
                and row['poses'] and any(row['visible'])]
    if not controls:
        raise ValueError('Water shape has no visible native control')
    row = controls[0]
    slot = row['visible'].index(True)
    position, size, pose = row['doll_positions'][slot], row['doll_sizes'][slot], row['poses'][slot]
    unit = pose[0] * min(size)
    center = (position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / float(native_gui))
    camera = OrbitCamera(*state['camera_pose'])
    right, up, unused = camera.basis()
    result = []
    for point in points:
        offset = tuple(point[i] - origin[i] - 2. for i in range(3))
        result.append((center[0] + unit * sum(offset[i] * right[i] for i in range(3)),
                       center[1] - unit * sum(offset[i] * up[i] for i in range(3))))
    return result
