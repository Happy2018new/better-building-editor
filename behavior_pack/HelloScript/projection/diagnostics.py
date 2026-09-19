# -*- coding: utf-8 -*-
"""Bounded editor fixtures, reachable only through the enabled debug protocol."""
from .model import Document, Editor


def inspect(session, value):
    value = value or {}
    fixture = value.get('fixture')
    if fixture:
        if fixture not in ('landmarks', 'offset', 'offset_odd', 'solid', 'demo'):
            raise ValueError('unknown editor fixture')
        if fixture == 'demo':
            session.demo()
        else:
            size = (23, 15, 21) if fixture == 'offset_odd' else (24, 16, 24) if fixture == 'offset' else (256, 384, 256)
            if fixture == 'solid' and 'size' in value:
                size = tuple(value['size'])
            doc = Document(size)
            if fixture == 'solid':
                editor = Editor(doc); editor.run('fill')
            elif fixture.startswith('offset'):
                for x in range(2, 6):
                    for y in range(1, 4):
                        for z in range(3, 9):
                            doc.blocks[(x, y, z)] = ('minecraft:quartz_block', 0)
            else:
                for x in range(256):
                    for z in range(256):
                        if x % 16 in (0, 1) or z % 16 in (0, 1) or x == 255 or z == 255:
                            doc.blocks[(x, 0, z)] = ('minecraft:concrete', 14 if x % 32 == 0 else 3)
                for y in range(384):
                    for x, z in ((0, 0), (255, 0), (255, 255)):
                        doc.blocks[(x, y, z)] = ('minecraft:concrete', (y // 16) % 16)
            session._loaded(doc)
            session.camera_view(35., 25., 1.)
        session.emit()
    if 'focus' in value:
        session.focused = tuple(value['focus'])
        session.emit()
    if 'selection' in value:
        session.editor.select_box(*[tuple(p) for p in value['selection']])
        session.emit()
    if 'camera' in value:
        session.camera_view(*value['camera'])
    if 'pan' in value:
        session.camera_pan = tuple(value['pan'])
    if 'layer' in value:
        session.layer(value['layer'])
    e = session.editor
    return {'size': e.document.size, 'sceneSize': session.scene_size, 'origin': session.scene_origin,
            'sceneScale': session.scene_scale, 'pending': session.preview_pending, 'error': session.preview_error,
            'blocks': len(e.document.blocks), 'model': session.model_name, 'selection': len(e.selection),
            'start': e.start, 'end': e.end, 'anchor': session.box_anchor, 'focused': session.focused,
            'pose': session.camera_pose, 'grid': session.grid, 'pan': session.camera_pan,
            'depth': session.camera_depth, 'depthPlane': session.depth_plane(), 'eraseScope': session.erase_scope,
            'touch': session.touch_mode, 'placementTarget': session.placement_proposal()[0],
            'previewBuilds': session.tiles.builds, 'previewSeconds': session.tiles.seconds,
            'previewTiles': len(session.tiles.parts), 'previewDirty': len(session.tiles.dirty),
            'pointerStats': getattr(session, 'pointer_stats', None),
            'layer': e.layer, 'section': session.section, 'mask': e.mask,
            'brightness': session.brightness, 'displayMode': session.current_display_mode()}
