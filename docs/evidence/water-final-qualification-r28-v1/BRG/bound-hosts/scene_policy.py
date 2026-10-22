"""Fixed native geometry checks; no image fitting or product qualification."""
import math


def describe_scene(state, expected_gui, wet):
    cache = state['gui_cache']
    errors = []
    if cache['sdk_integer_gui'] != expected_gui or cache['cached_gui'] != expected_gui:
        errors.append('native_gui_cache_mismatch')
    visible = 0
    for entry in state['native_water_controls']:
        if entry['renderer_error']:
            errors.append('renderer_error:' + entry['key'])
        for bank in entry['banks']:
            if bank is None or bank['declared_visible'] is not True:
                continue
            visible += 1
            if not entry['request_ready']:
                errors.append('visible_request_not_ready:' + entry['key'])
            geometry = entry['geometry']
            if not geometry:
                errors.append('visible_geometry_missing:' + entry['key'])
                continue
            for actual, expected in ((bank['position'], geometry[0]), (bank['size'], geometry[1])):
                if (len(actual) != 2 or len(expected) != 2
                        or any(not math.isfinite(float(actual[i])) or abs(actual[i] - expected[i]) > .02 for i in range(2))):
                    errors.append('visible_native_geometry_mismatch:' + entry['key'])
            if bank['surface_visible'] is not True:
                errors.append('visible_surface_not_shown:' + entry['key'])
            if bank['native_model_id'] != bank['renderer_model_id'] or bank['renderer_model_id'] is None:
                errors.append('visible_skeleton_model_identity_mismatch:' + entry['key'])
    if wet and visible == 0:
        errors.append('wet_has_no_visible_water_bank')
    if not wet and visible != 0:
        errors.append('dry_has_visible_water_bank')
    return {'complete': not errors, 'errors': errors, 'visible_banks': visible,
            'scope': 'SDK cache and active skeleton position/size/ID only; hidden zero-size retained',
            'geometry_tolerance_logical': .02}
