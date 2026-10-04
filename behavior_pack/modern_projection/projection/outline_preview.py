"""Retained native screen-facing strokes, aligned with the work-grid renderer."""
import math
from .large_preview import SurfacePalette
from .camera import render_bounds

OUTLINE_BLOCK = 'modern_projection:preview_outline'


def outline_palette():
    palette = SurfacePalette((2, 2, 2))
    palette.add((0, 0, 0), (OUTLINE_BLOCK, 0))
    return palette


def outline_color(size, thickness, distance, spectrum=None, invalid=False):
    """Pack 64x128x64 bounds, signed 1/64-block depth and 256 hue phases.

    Dyadic GB fractions preserve all 19/24 bits in native float32 uniforms.
    """
    tag = 224 if spectrum is None else (226 if invalid else 225)
    dimensions = size[0]-1 + (size[1]-1)*64 + (size[2]-1)*8192
    depth = max(0, min(65535, int(math.floor(distance*64.+.5))+32768))
    phase = int((spectrum/6.%1.)*256) if spectrum is not None else 0
    return ((tag+thickness/8.)/255., dimensions/524288., (depth*256+phase)/16777216.)


class OutlinePreview(object):
    def __init__(self):
        self.name = self.signature = self.tint = None
        self.shown = False

    def invalidate(self):
        self.signature = self.tint = None

    def update(self, session, doll, state_image, view, target, plane=None,
               spectrum=None, invalid=False):
        shown = target is not None
        if shown != self.shown:
            doll.SetVisible(shown, False)
            self.shown = shown
            self.invalidate()
        if not shown:
            return
        if self.name is None:
            self.name = session.bridge.geometry(outline_palette())
        size = tuple(target[1][i]-target[0][i]+1 for i in range(3))
        center = tuple(target[0][i]+size[i]/2.-session.scene_origin[i] for i in range(3))
        distance = sum(center[i]*plane[0][i] for i in range(3))-plane[1] if plane else -300.
        rgb = outline_color(size, view.thickness, distance, spectrum, invalid)
        if rgb != self.tint:
            state_image.asImage().SetSpriteColor(rgb)
            self.tint = rgb
        key = (view.signature, target)
        if key == self.signature:
            return
        tx, ty = view.project(center)
        position, extent = render_bounds(view.viewport[0], view.viewport[1],
                                         (tx-view.viewport[0]/2., ty-view.viewport[1]/2.))
        doll.SetPosition((position[0]-view.clip_offset[0], position[1]-view.clip_offset[1]))
        doll.SetSize(extent)
        if doll.asNeteasePaperDoll().RenderBlockGeometryModel({
                'block_geometry_model_name': self.name, 'scale': view.pose[0],
                'init_rot_x': view.pose[1], 'init_rot_y': 0., 'init_rot_z': view.pose[2]}):
            self.signature = key
