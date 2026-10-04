"""Retained work-plane geometry sharing the building's native depth buffer."""
from .large_preview import SurfacePalette
from .camera import render_bounds
from .outline_preview import outline_color

GRID_BLOCK = 'modern_projection:preview_grid'
GRID_TAG = 223


class GridView(object):
    __slots__ = ('project', 'toward', 'plane_offset', 'pose', 'viewport',
                 'clip_offset', 'thickness', 'signature')

    def __init__(self, project, toward, plane_offset, pose, viewport,
                 clip_offset, thickness, signature):
        self.project = project
        self.toward = toward
        self.plane_offset = plane_offset
        self.pose = pose
        self.viewport = viewport
        self.clip_offset = clip_offset
        self.thickness = thickness
        self.signature = signature


def grid_palette(size):
    # Fixed source quads encode all 130 possible lines; the shader selects
    # only the document's X/Z extent. Size and height changes reuse geometry.
    palette = SurfacePalette((2, 2, 2))
    palette.add((0, 0, 0), (GRID_BLOCK, 0))
    return palette


def grid_center(origin, size, layer):
    return (origin[0] + size[0]/2., layer, origin[2] + size[2]/2.)


class GridPreview(object):
    def __init__(self):
        self.size = self.name = self.signature = self.tint = None
        self.shown = False

    def invalidate(self):
        self.signature = self.tint = None

    def update(self, session, doll, state_image, view):
        size, origin, layer = session.scene_size, session.scene_origin, session.editor.layer
        shown = session.grid and origin[1] <= layer < origin[1] + size[1]
        if shown != self.shown:
            doll.SetVisible(shown, False)
            self.shown = shown
            self.invalidate()
        if not shown:
            return
        dimensions = (size[0], size[2])
        if self.name is None:
            self.name = session.bridge.geometry(grid_palette(size))
            self.invalidate()
        self.size = dimensions
        key = (view.signature, dimensions, layer, view.thickness)
        if key == self.signature:
            return
        center = grid_center(origin, size, layer)
        local = tuple(center[i] - origin[i] for i in range(3))
        tx, ty = view.project(local)
        distance = sum(local[i] * view.toward[i] for i in range(3)) - view.plane_offset
        packet = outline_color((size[0], 1, size[2]), view.thickness, distance)
        rgb = ((GRID_TAG + view.thickness/8.)/255.,) + packet[1:]
        if rgb != self.tint:
            state_image.asImage().SetSpriteColor(rgb)
            self.tint = rgb
        position, extent = render_bounds(view.viewport[0], view.viewport[1],
                                         (tx-view.viewport[0]/2., ty-view.viewport[1]/2.))
        doll.SetPosition((position[0]-view.clip_offset[0], position[1]-view.clip_offset[1]))
        doll.SetSize(extent)
        if doll.asNeteasePaperDoll().RenderBlockGeometryModel({
                'block_geometry_model_name': self.name, 'scale': view.pose[0],
                'init_rot_x': view.pose[1], 'init_rot_y': 0., 'init_rot_z': view.pose[2]}):
            self.signature = key
