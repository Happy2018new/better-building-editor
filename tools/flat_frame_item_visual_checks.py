"""Content-only controls for the provisional flat frame item channel."""
import time

from PIL import Image, ImageChops, ImageFilter

from verify_debug_visuals import PROJECTION_STATUS
from verify_sign_visuals import world_sample
from verify_shulker_orientations import viewport_crop
from verify_snow_plant_visibility import changed, count

SWITCH = '''from modern_projection.projection import static_frame_item_data
for profile in static_frame_item_data.FRAME_ITEMS.values():profile['accepted']=%r
# Profile toggles do not change document content, so invalidate diagnostic caches.
for part in s.tiles.parts.values():
 part['source']=None
 part['data']=({}, {}, {}, ())
 part['cache']={}
_result=True
'''


def content_mask(shown, body, crop, threshold=25):
    with Image.open(shown) as first, Image.open(body) as second:
        if first.size != second.size:
            raise AssertionError('Frame item control dimensions changed')
        frame = first.convert('RGB').crop(crop)
        mask = changed(frame, second.convert('RGB').crop(crop), threshold)
    return frame, mask


def alpha_measure(full, faded, hidden, crop, mask, opacity=.2):
    frames = [Image.open(path).convert('RGB').crop(crop) for path in (full, faded, hidden)]
    eligible = mask.filter(ImageFilter.MinFilter(3)).tobytes()
    signals = [[], []]
    for channel in range(3):
        values = [frame.split()[channel].tobytes() for frame in frames]
        for opaque, translucent, empty, use in zip(*values, eligible):
            if use:
                signals[0].append(opaque - empty)
                signals[1].append(translucent - empty)
    energy = sum(value * value for value in signals[0])
    if len(signals[0]) < 60 or energy <= 100:
        return {'passed': False, 'reason': 'The item opacity control has no opaque pixel signal'}
    gain = sum(left * right for left, right in zip(*signals)) / float(energy)
    residual = (sum((right - opacity * left) ** 2 for left, right in zip(*signals)) / energy) ** .5
    return {'passed': abs(gain - opacity) <= .05 and residual <= .12,
            'requested_opacity': opacity, 'measured_contrast_gain': gain,
            'relative_blend_residual': residual, 'samples': len(signals[0]),
            'limits': {'absolute_gain_error': .05, 'relative_blend_residual': .12}}


def load_candidate(check, load_code, enabled):
    check.run(SWITCH % enabled)
    check.run('owner.open_workspace()\n_result=True')
    check.wait('candidate workspace opens', lambda nav: nav['open'] and not nav['transition'], check.navigation)
    loaded = check.run(load_code)
    check.editor_preview('current item candidate', loaded['metadata'], loaded['editor_id'], loaded['document_id'])
    return loaded


def alpha_ownership_controls(check, label, shown, crop, result, record):
    """Identify body/item ownership without changing the frozen composite gates."""
    result.update(scope='SDK geometry visibility controls at the unchanged camera', captures={})
    for owner in ('blank', 'body', 'item'):
        result['captures'][owner] = {}
        for opacity in ((0.,) if owner == 'blank' else (1., .2, 0.)):
            state = check.run('''shader=b.projection_shader
assert shader is not None and shader.local
s.opacity=%r
b.update_projection_opacity()
rows=[]
for bank,parts in enumerate(shader.parts):
 for name,(origin,context) in parts.items():
  visible=(bank==shader.bank and name in shader.active_parts[bank] and
           ((%r=='body' and context) or (%r=='item' and not context)))
  assert shader.render.SetActorBlockGeometryVisible(name,visible)
  rows.append({'name':name,'bank':bank,'context':context,'visible':visible})
_result=json.dumps({'parts':rows,'uniforms':shader.uniforms,'opacity':s.opacity})
''' % (opacity, owner, owner))
            time.sleep(.3)
            shot = check.capture(label + '_owner_' + owner + '_alpha' + str(opacity).replace('.', '_'))
            result['captures'][owner][str(opacity)] = {'capture': shot, 'state': state}
            record()
    blank = result['captures']['blank']['0.0']['capture']['path']
    unused, blank_mask = content_mask(blank, shown['hidden_screenshot']['path'], crop, 12)
    result['blank_residual_pixels_gt_12'] = count(blank_mask)
    for owner in ('body', 'item'):
        samples = result['captures'][owner]
        paths = [samples[str(value)]['capture']['path'] for value in (1., .2, 0.)]
        unused, mask = content_mask(paths[0], blank, crop)
        unused, zero = content_mask(paths[2], blank, crop, 12)
        result[owner] = {'opaque_pixels': count(mask),
                         'alpha02': alpha_measure(paths[0], paths[1], blank, crop, mask),
                         'alpha0_residual_pixels_gt_12': count(ImageChops.multiply(zero, mask)),
                         'alpha0_total_residual_pixels_gt_12': count(zero)}
    return result


def candidate_scopes(check, identity, case, offset, load_code, editor_shot, result, record,
                     depth_delta=None, alpha_ownership=False):
    """Keep the blueprint and Item NBT identical while toggling only the profile."""
    crop = viewport_crop(check, editor_shot)
    document = check.run('_result=json.dumps(s.editor.document.to_data())')
    load_candidate(check, load_code, False)
    if check.run('_result=json.dumps(s.editor.document.to_data())') != document:
        raise AssertionError('Disabling the item profile changed document content')
    time.sleep(.3)
    editor_body = check.capture(identity + '_candidate_editor_body')
    editor, mask = content_mask(editor_shot['path'], editor_body['path'], crop)
    result['editor'] = {'shown': editor_shot, 'body': editor_body, 'crop': crop,
                        'item_pixels': count(mask), 'passed': count(mask) >= 80}
    record()
    body = world_sample(check, identity + '_candidate_world_body', case['focus'], offset,
                        1., case['projection_height'], mesh_origin=True)
    result['world_body'] = body
    record()
    for mode, missing in (('full', False), ('missing', True)):
        load_candidate(check, load_code, True)
        if check.run('_result=json.dumps(s.editor.document.to_data())') != document:
            raise AssertionError('Enabling the item profile changed document content')
        shown = world_sample(check, identity + '_candidate_' + mode, case['focus'], offset,
                             1., case['projection_height'], missing=missing, mesh_origin=True)
        if depth_delta is not None:
            adjusted = check.run('''shader=b.projection_work.shader
assert b.projection_work.ready and shader.local
rows=[]
for name,origin,context in b.context_models[b.projection_mesh[1]]:
 if context:continue
 before=shader.offset(shader.anchor,origin)
 # The native model rotates 180 degrees around Y before its actor offset.
 after=(before[0],before[1],before[2]-%r)
 assert b.factory.CreateActorRender(b.entity).SetActorBlockGeometryOffset(name,after)
 rows.append({'name':name,'before':before,'after':after,'logical_world_delta':(0.,0.,%r)})
assert len(rows)==1,rows
_result=json.dumps(rows)
''' % (depth_delta, depth_delta))
            time.sleep(.4)
            shown['original_screenshot'] = shown['screenshot']
            shown['screenshot'] = check.capture(identity + '_candidate_' + mode + '_world_depth_translation')
            shown['semantic_depth_diagnostic'] = adjusted
        width, height = shown['screenshot']['size']
        world_crop = (width // 3, height // 3, width * 2 // 3, height * 2 // 3)
        item_frame, item_mask = content_mask(shown['screenshot']['path'], body['screenshot']['path'], world_crop)
        result[mode] = {'shown': shown, 'crop': world_crop, 'item_pixels': count(item_mask),
                        'presence_passed': count(item_mask) >= 80}
        record()
        check.run('s.opacity=.2\nb.update_projection_opacity()\n_result=True')
        time.sleep(.3)
        faded = check.capture(identity + '_candidate_' + mode + '_alpha02')
        measure = alpha_measure(shown['screenshot']['path'], faded['path'],
                                shown['hidden_screenshot']['path'], world_crop, item_mask)
        measure['capture'] = faded
        result[mode]['alpha02'] = measure
        check.run('s.opacity=0.\nb.update_projection_opacity()\n_result=True')
        time.sleep(.3)
        zero = check.capture(identity + '_candidate_' + mode + '_alpha0')
        zero_frame, zero_mask = content_mask(zero['path'], shown['hidden_screenshot']['path'], world_crop, 12)
        residual = count(ImageChops.multiply(zero_mask, item_mask))
        result[mode]['alpha0'] = {'capture': zero, 'item_residual_pixels_gt_12': residual,
                                 'passed': residual <= 2, 'maximum_pixels': 2}
        if alpha_ownership and mode == 'full':
            result[mode]['alpha_ownership'] = {}
            alpha_ownership_controls(check, identity + '_candidate_' + mode, shown, world_crop,
                                     result[mode]['alpha_ownership'], record)
            check.run('''shader=b.projection_shader
for bank,parts in enumerate(shader.parts):
 for name in parts:
  assert shader.render.SetActorBlockGeometryVisible(name,bank==shader.bank and name in shader.active_parts[bank])
_result=True
''')
        check.run('s.opacity=1.\nb.update_projection_opacity()\n_result=True')
        result[mode]['source'] = check.run(PROJECTION_STATUS)
        record()
    check.run('b.stop_projection()\n_result=True')
    owners = check.run('''_result=json.dumps({'actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing':bool(b.preparing_entity),'shader':b.projection_shader is not None,
 'occupancy':b.projection_occupancy is not None})''')
    result['stop_owners'] = dict(owners, passed=not any(owners.values()))
    result['document_nonmutation'] = check.run('_result=json.dumps(s.editor.document.to_data())') == document
    record()
    return result
