"""Python 2-compatible water-only submission candidate; importing is inert."""


def entity_draw_pose(renderer, slot, group, pose):
    scale, rx, ry, rz = pose
    params = {'scale': scale, 'render_depth': -50,
              'init_rot_x': rx, 'init_rot_y': ry, 'init_rot_z': rz,
              'skeleton_model_name': group.model_name}
    doll = renderer.dolls[slot]
    if not doll.RenderSkeletonModel(params):
        return False
    params = dict(params)
    del params['skeleton_model_name']
    params['entity_identifier'] = 'minecraft:cow'
    return doll.RenderEntity(params)
