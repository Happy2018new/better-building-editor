# -*- coding: utf-8 -*-
"""Bounded editor fixtures, reachable only through the enabled debug protocol."""
from .model import Document, Editor, MAX_AXES, demo_document
from .input_mode import current_mode


def inspect(session, value):
    value = value or {}
    if value.get('reloadShaders') is True:
        import mod.client.extraClientApi as clientApi
        # Reload on a later game frame; synchronous reload during an IPC
        # callback can stall the render thread waiting for that callback.
        session.bridge.later(.05, lambda: clientApi.ReloadOneShader("modern_projection_biome_blocks.vertex"))
        session.bridge.later(.1, lambda: clientApi.ReloadOneShader("modern_projection_biome_blocks.fragment"))
    fixture = value.get('fixture')
    if fixture:
        if fixture not in ('interior', 'landmarks', 'offset', 'offset_odd', 'solid', 'demo', 'demo_large'):
            raise ValueError('unknown editor fixture')
        if fixture == 'demo':
            session.demo()
        else:
            size = (23, 15, 21) if fixture == 'offset_odd' else (24, 16, 24) if fixture == 'offset' else MAX_AXES
            if fixture in ('solid', 'interior') and 'size' in value:
                size = tuple(value['size'])
            doc = Document(size)
            if fixture == 'demo_large':
                doc.blocks = demo_document().blocks.copy()
            elif fixture == 'interior':
                editor = Editor(doc); editor.run('shell')
                doc.blocks[(size[0]//2, size[1]//2, size[2]//2)] = ('minecraft:gold_block', 0)
            elif fixture == 'solid':
                editor = Editor(doc); editor.run('fill')
            elif fixture.startswith('offset'):
                for x in range(2, 6):
                    for y in range(1, 4):
                        for z in range(3, 9):
                            doc.blocks[(x, y, z)] = ('minecraft:quartz_block', 0)
            else:
                for x in range(size[0]):
                    for z in range(size[2]):
                        if x % 16 in (0, 1) or z % 16 in (0, 1) or x == size[0]-1 or z == size[2]-1:
                            doc.blocks[(x, 0, z)] = ('minecraft:concrete', 14 if x % 32 == 0 else 3)
                for y in range(size[1]):
                    for x, z in ((0, 0), (size[0]-1, 0), (size[0]-1, size[2]-1)):
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
    liquid = getattr(session, 'liquid_preview', None)
    liquid_controls = getattr(session, 'liquid_controls', None)
    items = getattr(session, 'item_preview', None)
    item_controls = getattr(session, 'item_controls', None)
    cauldrons = getattr(session, 'cauldron_preview', None)
    cauldron_controls = getattr(session, 'cauldron_controls', None)
    portals = getattr(session, 'portal_preview', None)
    portal_controls = getattr(session, 'portal_controls', None)
    books = getattr(session, 'book_preview', None)
    book_controls = getattr(session, 'book_controls', None)
    return {'size': e.document.size, 'sceneSize': session.scene_size, 'origin': session.scene_origin,
            'sceneScale': session.scene_scale, 'pending': session.preview_pending, 'error': session.preview_error,
            'liquid': {'enabled': getattr(session, 'liquid_profile', None) is not None,
                       'groups': len(liquid.groups) if liquid is not None else 0,
                       'revision': liquid.revision if liquid is not None else 0,
                       'planReady': liquid is not None and liquid.published == liquid.signature(),
                       'controlsPending': liquid_controls.pending if liquid_controls is not None else False,
                       'error': getattr(session, 'liquid_error', '')},
            'items': {'enabled': getattr(session, 'item_profile', None) is not None,
                      'groups': len(items.groups) if items is not None else 0,
                      'revision': items.revision if items is not None else 0,
                      'planReady': items is not None and items.published == items.signature(),
                      'controlsPending': item_controls.pending if item_controls is not None else False,
                      'error': getattr(session, 'item_error', '')},
            'cauldrons': {'enabled': getattr(session, 'cauldron_profile', None) is not None,
                          'groups': len(cauldrons.groups) if cauldrons is not None else 0,
                          'revision': cauldrons.revision if cauldrons is not None else 0,
                          'planReady': cauldrons is not None and cauldrons.published == cauldrons.signature(),
                          'controlsPending': cauldron_controls.pending if cauldron_controls is not None else False,
                          'error': getattr(session, 'cauldron_error', '')},
            'portals': {'enabled': getattr(session, 'portal_profile', None) is not None,
                        'groups': len(portals.groups) if portals is not None else 0,
                        'revision': portals.revision if portals is not None else 0,
                        'planReady': portals is not None and portals.published == portals.signature(),
                        'controlsPending': portal_controls.pending if portal_controls is not None else False,
                        'error': getattr(session, 'portal_error', '')},
            'books': {'enabled': getattr(session, 'book_profile', None) is not None,
                      'groups': len(books.groups) if books is not None else 0,
                      'revision': books.revision if books is not None else 0,
                      'planReady': books is not None and books.published == books.signature(),
                      'controlsPending': book_controls.pending if book_controls is not None else False,
                      'error': getattr(session, 'book_error', '')},
            'blocks': len(e.document.blocks), 'model': session.model_name, 'selection': len(e.selection),
            'start': e.start, 'end': e.end, 'anchor': session.box_anchor, 'focused': session.focused,
            'pose': session.camera_pose, 'grid': session.grid, 'pan': session.camera_pan,
            'depth': session.camera_depth_pose, 'depthTarget': session.camera_depth,
            'depthPlane': session.depth_plane(), 'eraseScope': session.erase_scope,
            'touch': session.touch_mode, 'inputMode': current_mode(), 'cameraPivot': session.camera_pivot,
            'cameraReset': session.camera_reset_revision,
            'previewBuilds': session.tiles.builds, 'previewSeconds': session.tiles.seconds,
            'previewExtractions': session.tiles.extractions,
            'editActive': session.edit_job is not None,
            'performance': session.performance,
            'editProgress': (session.edit_job.processed, session.edit_job.total) if session.edit_job else None,
            'previewTiles': len(session.tiles.parts), 'previewDirty': len(session.tiles.dirty),
            'previewSlots': len(session.tiles.slots), 'previewProgress': session.tiles.progress(),
            'cursorCell': getattr(session, 'cursor_cell', None),
            'nativeCells': sum(p['size'][0]*p['size'][1]*p['size'][2] for k,p in session.tiles.parts.items() if k in session.tiles.slots),
            'pointerStats': getattr(session, 'pointer_stats', None),
            'layer': e.layer, 'section': session.section, 'mask': e.mask,
            'brightness': session.brightness, 'displayMode': session.current_display_mode()}
