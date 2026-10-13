"""Compare native snow and plant visibility at one fixed editor/world position."""
import argparse
import base64
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from verify_debug_blueprints import (BlueprintCheck, Client, INSTALL_PROBE, RESTORE,
                                     write_json)
from verify_debug_visuals import (SAVE_VISUAL, PROJECTION_STATUS, PROJECTION_SOURCE,
                                  camera_restore_code, projection_source_matches)
from verify_missing_neighbor_visuals import camera_matches
from verify_shulker_orientations import viewport_crop, server_run
from _session import load_session
from camera_projection import project_points

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.camera import OrbitCamera
NATIVE_SETUP = '''import json,sys
import mod.server.extraServerApi as server_api
from modern_projection.server_system import WorldAdapter
player=server_api.GetPlayerList()[0]
adapter=WorldAdapter(player)
target=%r
support=(target[0],target[1]-1,target[2])
assert not hasattr(sys,'_snow_visibility_native'), 'Previous native snow fixture needs cleanup'
for pos in (target,support):
 value=adapter.info.GetBlockNew(pos,adapter.dimension)
 assert value is not None and value['name']=='minecraft:air', ('Snow oracle needs empty cells',pos,value)
game=adapter.factory.CreateGame(adapter.level)
clock=adapter.factory.CreateTime(adapter.level)
saved_rules=game.GetGameRulesInfoServer()['cheat_info']
biome=adapter.factory.CreateBiome(player)
saved_biome=biome.GetBiomeName(target)
assert saved_biome, 'Could not read native snow fixture biome'
sys._snow_visibility_native={'target':target,'support':support,'player':player,'dimension':adapter.dimension,
 'time':clock.GetTime(),'daylight_cycle':saved_rules['daylight_cycle'],'biome':saved_biome}
assert biome.SetBiomeByPos(target,'minecraft:ice_plains',adapter.dimension)
assert biome.GetBiomeName(target)=='ice_plains'
assert game.SetGameRulesInfoServer({'cheat_info':{'daylight_cycle':False}})
assert clock.SetTime((clock.GetTime()//24000)*24000+6000)
assert adapter.write(support,('minecraft:dirt',0))
_result=json.dumps(sys._snow_visibility_native)
'''
NATIVE_NEAR_PLAYER = '''import json,sys
import mod.server.extraServerApi as server_api
from modern_projection.server_system import WorldAdapter
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
target=saved['target']
platform=(target[0]-4,target[1]-1,target[2]-4)
front=adapter.info.GetBlockNew(platform,saved['dimension'])
back=adapter.info.GetLiquidBlock(platform,saved['dimension'])
assert front and front['name']=='minecraft:air',(platform,front)
assert back is None or back['name']=='minecraft:air',(platform,back)
position=adapter.factory.CreatePos(saved['player'])
saved['player_foot']=position.GetFootPos()
saved['player_flying']=adapter.factory.CreateFly(saved['player']).IsPlayerFlying()
saved['player_platform']=platform
assert adapter.info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
point=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
assert position.SetFootPos(point)
_result=json.dumps({'before':saved['player_foot'],'after':point,'platform':platform,
 'flight_before':saved['player_flying'],'flight_modified':False})
'''
NATIVE_MUTATE = '''import json,sys
import mod.server.extraServerApi as server_api
from modern_projection.server_system import WorldAdapter
from modern_projection.projection.debug_blueprints import material
from modern_projection.projection import block_registry as registry
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
target=saved['target']
plant,kind,height=%r,%r,%d
support_name='minecraft:podzol' if plant in ('brown_mushroom','red_mushroom') else 'minecraft:dirt'
support_value=(support_name,registry.DEFAULT_AUX[support_name])
if adapter.read(saved['support'])!=support_value:
 assert adapter.write(saved['support'],support_value)
assert adapter.read(saved['support'])==support_value
adapter.write(target,('minecraft:air',0))
if kind!='blank':
 value=material('snow_layer',{'height':height,'covered_bit':False}) if kind=='snow' else material(plant)
 state=server_api.GetEngineCompFactory().CreateBlockState(server_api.GetLevelId())
 aux=state.GetBlockAuxValueFromStates(value[0].encode('utf8'),registry.states(value))
 assert aux is not None and aux>=0, ('Native state mapping unavailable',value)
 assert adapter.info.SetBlockNew(target,{'name':value[0].encode('utf8'),'aux':aux},0,saved['dimension'],True,False), ('Could not place native snow oracle',value)
state=server_api.GetEngineCompFactory().CreateBlockState(server_api.GetLevelId())
_result=json.dumps({'front':adapter.info.GetBlockNew(target,saved['dimension']),
 'states':state.GetBlockStates(target,saved['dimension']),'target':target,'kind':kind,'height':height})
'''
NATIVE_SNOW = '''import json,sys
import mod.server.extraServerApi as server_api
saved=sys._snow_visibility_native
factory=server_api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
result=info.SetSnowBlock(saved['target'],saved['dimension'],%d)
state=factory.CreateBlockState(server_api.GetLevelId())
_result=json.dumps({'result':result,'front':info.GetBlockNew(saved['target'],saved['dimension']),
 'states':state.GetBlockStates(saved['target'],saved['dimension']),'target':saved['target']})
'''
NATIVE_CLEANUP = '''import json,sys
from modern_projection.server_system import WorldAdapter
saved=sys._snow_visibility_native
adapter=WorldAdapter(saved['player'])
results=[]
if 'player_foot' in saved:
 position=adapter.factory.CreatePos(saved['player'])
 assert position.SetFootPos(tuple(saved['player_foot']))
 foot=position.GetFootPos()
 flying=adapter.factory.CreateFly(saved['player']).IsPlayerFlying()
 results.append({'resource':'player','foot':foot,'flight':flying,
  'clean':all(abs(foot[i]-saved['player_foot'][i])<.1 for i in range(3)) and flying==saved['player_flying']})
positions=[saved['target'],saved['support']]
if 'player_platform' in saved:positions.append(saved['player_platform'])
for pos in positions:
 changed=adapter.write(pos,('minecraft:air',0))
 palette=adapter.palette_block.GetBlockPaletteBetweenPos(saved['dimension'],pos,pos,False)
 data=palette.SerializeBlockPalette() if palette is not None else None
 clean=data is not None and all(value[0]=='minecraft:air' for key in ('common','extra') for value in data.get(key,{}))
 results.append({'pos':pos,'changed':changed,'clean':clean})
clock=adapter.factory.CreateTime(adapter.level)
game=adapter.factory.CreateGame(adapter.level)
biome=adapter.factory.CreateBiome(saved['player'])
restored_biome=biome.SetBiomeByPos(saved['target'],saved['biome'],saved['dimension'])
results.append({'resource':'world_biome','clean':bool(restored_biome and biome.GetBiomeName(saved['target'])==saved['biome'])})
results.append({'resource':'world_time','clean':bool(clock.SetTime(saved['time']))})
results.append({'resource':'daylight_cycle','clean':bool(game.SetGameRulesInfoServer({'cheat_info':{'daylight_cycle':saved['daylight_cycle']}}))})
del sys._snow_visibility_native
_result=json.dumps(results)
'''
LOAD = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import _covered_snow,foreground,background,rebase
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection import block_registry as registry
from modern_projection.projection.render_layout import SCHEMA_VERSION as render_layout_version
plant=%r
height=%d
kind=%r
case=VISUAL_CASES['snow_plant_visibility']
focus=case['focus']
row=next(row for row in case['cells'] if row['plant']==plant)
source_pos=row['standalone'] if kind in ('plant','blank') else next(pos for h,pos in row['covered'] if h==height)
source=build(case['fixture'])
value=source.get(source_pos)
if kind=='snow':value=_covered_snow(foreground(value),False)
doc=Document(case['size'],name='Snow plant visibility check')
if kind!='blank':doc.blocks[focus]=rebase(value,tuple(focus[i]-source_pos[i] for i in range(3)))
sys._blueprint_qa_identity='snow.visibility.'+plant+'.'+kind+'.'+str(height)
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
s.emit()
_result=json.dumps({'fixture':case['fixture'],'fixture_schema':case['schema'],
 'source_position':source_pos,'focus':focus,'registry_version':registry.source_version(),
 'registry_fingerprint':registry.fingerprint(),'render_layout_version':render_layout_version,
 'runtime_minecraft_version':api.GetMinecraftVersion() if hasattr(api,'GetMinecraftVersion') else None,
 'front':foreground(doc.get(focus)),'back':background(doc.get(focus)),
 'metadata':{'name':doc.name,'size':doc.size,'blocks':len(doc.blocks)},
 'editor_id':id(s.editor),'document_id':id(doc)})
'''


def green_mask(frame):
    red, green, blue = frame.convert('RGB').split()
    # Dry-biome grass may be yellow; blue sky and neutral snow are excluded.
    first = ImageChops.subtract(green, red.point(lambda value: int(value * .85))).point(lambda value: 255 if value > 0 else 0)
    second = ImageChops.subtract(green, blue.point(lambda value: min(255, int(value * 1.05)))).point(lambda value: 255 if value > 0 else 0)
    brightness = green.point(lambda value: 255 if value > 25 else 0)
    light = ImageChops.darker(ImageChops.darker(red, green), blue)
    shade = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    chroma = ImageChops.subtract(shade, light).point(lambda value: 255 if value > 24 else 0)
    return ImageChops.multiply(ImageChops.multiply(ImageChops.multiply(first, second), brightness), chroma)


def snow_plant_mask(frame):
    red, green, blue = frame.convert('RGB').split()
    light = ImageChops.darker(ImageChops.darker(red, green), blue)
    shade = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    neutral = ImageChops.subtract(shade, light).point(lambda value: 255 if value < 24 else 0)
    snow = ImageChops.multiply(neutral, light.point(lambda value: 255 if value > 100 else 0))
    return ImageChops.lighter(snow, green_mask(frame))


def maximum(frame):
    red, green, blue = frame.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def count(mask):
    return mask.histogram()[255]


def changed(first, second, threshold=20):
    return maximum(ImageChops.difference(first, second)).point(lambda value: 255 if value > threshold else 0)


def capture_frame(path, crop, hidden, segmented=False, geometry=None, roi=None):
    with Image.open(path) as source:
        frame = source.convert('RGB').crop(crop)
    with Image.open(hidden) as source:
        reference = source.convert('RGB').crop(crop)
    presence = changed(frame, reference)
    if segmented:
        presence = ImageChops.multiply(presence, snow_plant_mask(frame))
    if roi is not None:
        presence = ImageChops.multiply(presence, roi)
    result = {'image': frame, 'object': presence,
              'green': ImageChops.multiply(green_mask(frame), presence)}
    if geometry is not None:
        result['geometry'] = geometry
    return result


def convex_hull(points):
    ordered = sorted(set(points))
    if len(ordered) < 3:
        return ordered

    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

    sides = []
    for values in (ordered, list(reversed(ordered))):
        side = []
        for point in values:
            while len(side) >= 2 and cross(side[-2], side[-1], point) <= 0:
                side.pop()
            side.append(point)
        sides.append(side[:-1])
    return sides[0] + sides[1]


def editor_snow_geometry(crop, camera_state, focus, height):
    """Opaque snow hull from the calibrated editor camera, including white faces."""
    width, pixels_high = crop[2]-crop[0], crop[3]-crop[1]
    camera = OrbitCamera(*camera_state['pose'])
    camera.pivot = tuple(camera_state['pivot']) if camera_state['pivot'] is not None else None
    camera.pan = tuple(camera_state['pan'])
    size = tuple(camera_state['size'])
    unit = min(width, pixels_high) * camera.zoom * .72 / max(size)
    project = camera.projector(size, width, pixels_high, unit)
    points = [project((focus[0]+x, focus[1]+y, focus[2]+z))
              for x in (0., 1.) for y in (0., (height+1)/8.) for z in (0., 1.)]
    polygon = convex_hull(points)
    mask = Image.new('L', (width, pixels_high))
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return mask, {'polygon': polygon, 'bounds': mask.getbbox(), 'unit': unit,
                  'method': 'OrbitCamera affine projector at the actual preview pose',
                  'height_blocks': (height+1)/8., 'camera': camera_state}


def editor_cross_above_snow(crop, camera_state, focus, height, model, texture):
    """Project opaque plant texels above snow; screen hulls cannot express depth."""
    width, pixels_high = crop[2]-crop[0], crop[3]-crop[1]
    camera = OrbitCamera(*camera_state['pose'])
    camera.pivot = tuple(camera_state['pivot']) if camera_state['pivot'] is not None else None
    camera.pan = tuple(camera_state['pan'])
    size = tuple(camera_state['size'])
    unit = min(width, pixels_high) * camera.zoom * .72 / max(size)
    project = camera.projector(size, width, pixels_high, unit)
    mask = Image.new('L', (width, pixels_high))
    draw = ImageDraw.Draw(mask)
    assert camera.pitch > 0, 'Above-snow texels require a camera above the snow surface'
    snow_top = (height+1)/8.
    for bone in model['netease:block_geometry']['bones']:
        angle = math.radians(bone['rotation'][1])
        px, unused, pz = bone['pivot']
        for cube in bone['cubes']:
            ox, oy, oz = cube['origin']
            sx, sy, sz = cube['size']
            assert sz == 0 and bone['rotation'][0] == bone['rotation'][2] == 0

            def point(u, y):
                dx, dz = ox+sx*u-px, oz-pz
                x = px+dx*math.cos(angle)+dz*math.sin(angle)
                z = pz-dx*math.sin(angle)+dz*math.cos(angle)
                return project((focus[0]-x/16., focus[1]+y, focus[2]+z/16.))

            for row in range(texture.height):
                low = max(snow_top, (oy+sy*(1.-(row+1)/float(texture.height)))/16.)
                high = (oy+sy*(1.-row/float(texture.height)))/16.
                if high <= low:
                    continue
                for col in range(texture.width):
                    if texture.getpixel((col, row))[3] <= 127:
                        continue
                    left, right = col/float(texture.width), (col+1)/float(texture.width)
                    # Both native faces have mirrored winding; the standalone
                    # pixel mask selects the face actually visible in this pose.
                    for a, b in ((left, right), (1.-right, 1.-left)):
                        draw.polygon((point(a, low), point(b, low), point(b, high), point(a, high)), fill=255)
    return mask


def cross_assets(session, plant):
    native_name = {'short_grass': 'tallgrass', 'fern': 'fern'}.get(plant)
    native_root = Path(session['game_executable']).parent / 'data/resource_packs/vanilla'
    if native_name is None:
        from projection.geometry_palette import PLANT_PROXIES
        from generate_static_plant_proxies import SOURCE
        if ('minecraft:'+plant, 0) not in PLANT_PROXIES:
            return None
        source = json.loads(SOURCE.read_text(encoding='utf8'))
        record = source.get('plants', {}).get(plant)
        if record is None:
            raise ValueError('Registered static plant has no versioned alpha source: '+plant)
        texture_path = native_root/record['texture_path']
        if hashlib.sha256(texture_path.read_bytes()).hexdigest() != source['sha256']['texture_'+plant]:
            raise ValueError('Installed static plant alpha source changed: '+plant)
    else:
        texture_path = native_root/'textures/blocks'/(native_name+'.tga')
    model_path = ROOT / 'resource_pack/models/netease_block' / ('preview_'+plant+'.json')
    texture_raw, model_raw = texture_path.read_bytes(), model_path.read_bytes()
    with Image.open(texture_path) as source:
        texture = source.convert('RGBA')
    return json.loads(model_raw), texture, {
        'model': str(model_path), 'model_sha256': hashlib.sha256(model_raw).hexdigest(),
        'texture': str(texture_path), 'texture_sha256': hashlib.sha256(texture_raw).hexdigest(),
        'texture_size': texture.size, 'texture_alpha_bounds': texture.getchannel('A').getbbox(),
        'method': 'Actual proxy model and native TGA alpha, clipped by world-space snow height'}


def world_cell_roi(check, crop, screenshot_size, base, pose, calibration):
    data = check.run('''base=%r
cam=b.factory.CreateCamera(b.level)
points=[tuple(base[i]+delta[i] for i in range(3))
 for delta in ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))]
native=[cam.WorldToScreenPoint(*point) for point in points] if hasattr(cam,'WorldToScreenPoint') else None
_result=json.dumps({'points':points,'native':native,'fov':cam.GetFov(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'version':api.GetMinecraftVersion()})
''' % (tuple(base),))
    if data['native'] is not None:
        projected = data['native']
        method = 'native WorldToScreenPoint'
    else:
        assert calibration is not None and calibration['completed'] and calibration['passed'], 'A native cube camera calibration is required on this game version'
        session_file = os.environ.get('MCDEV_SESSION_FILE')
        assert session_file and Path(calibration['session_file']).resolve() == Path(session_file).resolve(), 'Calibration belongs to another instance'
        assert calibration['runtime_minecraft_version'] == data['version'], 'Calibration game version changed'
        assert abs(calibration['reported_fov']-data['fov']) < .01, 'Camera FOV changed since calibration'
        assert abs(calibration['screen_aspect']-data['screen'][0]/data['screen'][1]) < .01, 'Viewport aspect changed since calibration'
        projected = project_points(data['points'], pose['position'], pose['target'],
                                   data['screen'], calibration['vertical_fov'], pose['rotation'][2])
        method = 'native-cube calibrated perspective projection'
    assert all(row['isInScreen'] for row in projected), 'Plant cell lies outside the screen'
    scale = (screenshot_size[0]/data['screen'][0], screenshot_size[1]/data['screen'][1])
    polygon = convex_hull((row['screenX']*scale[0]-crop[0], row['screenY']*scale[1]-crop[1])
                          for row in projected)
    mask = Image.new('L', (crop[2]-crop[0], crop[3]-crop[1]))
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    return mask, {'method': method, 'polygon': polygon, 'camera': pose, 'screen': data['screen'],
                  'world_base': base, 'bounds': mask.getbbox(), 'calibration': calibration}


def analyze(frame, crop, output):
    frame['green'].save(output)
    presence_path = output.with_name(output.stem + '_presence.png')
    frame['object'].save(presence_path)
    return {'green_pixels': count(frame['green']), 'bounds': frame['green'].getbbox(),
            'object_pixels': count(frame['object']), 'object_bounds': frame['object'].getbbox(),
            'crop': crop, 'mask': str(output.resolve()), 'presence_mask': str(presence_path.resolve())}


def bands(mask):
    bounds = mask.getbbox()
    if bounds is None:
        return mask.copy(), mask.copy()
    left, top, right, bottom = bounds
    height = bottom - top
    upper, lower = Image.new('L', mask.size), Image.new('L', mask.size)
    ImageDraw.Draw(upper).rectangle((left, top, right - 1, top + max(1, height // 5)), fill=255)
    ImageDraw.Draw(lower).rectangle((left, bottom - max(1, height * 3 // 10), right - 1, bottom - 1), fill=255)
    return ImageChops.multiply(mask, upper), ImageChops.multiply(mask, lower)


def compare_controls(plant, snow, covered, height, minimum=80):
    if len({row['image'].size for row in (plant, snow, covered)}) != 1:
        raise AssertionError('Snow controls must have identical crop dimensions')
    plant_mask, snow_mask = plant['object'], snow.get('geometry', snow['object'])
    footprint = plant_mask.filter(ImageFilter.MaxFilter(5))
    difference = ImageChops.multiply(changed(covered['image'], snow['image']),
                                     ImageChops.lighter(covered['object'], snow_mask))
    contribution = ImageChops.multiply(difference, footprint)
    upper, lower = bands(plant_mask)
    # Only require foliage in an upper region that the independent opaque
    # snow control does not cover in this camera. Plant texture bounds vary.
    visible_texels = plant.get('above_snow', {}).get(height)
    if visible_texels is None:
        upper = ImageChops.subtract(upper, snow_mask.filter(ImageFilter.MaxFilter(3)))
    else:
        # Texture geometry already defines the exposed region independently of the observed bounding box.
        upper = ImageChops.multiply(plant_mask, visible_texels)
    upper_count, lower_count = count(upper), count(lower)
    uncovered = count(ImageChops.subtract(plant_mask, snow_mask.filter(ImageFilter.MaxFilter(3))))
    fully_occluded = (uncovered <= count(plant_mask)*.02 if visible_texels is None
                      else count(visible_texels) == 0)
    upper_observed = contribution if visible_texels is None else contribution.filter(ImageFilter.MaxFilter(7))
    upper_retained = count(ImageChops.multiply(upper_observed, upper)) / max(1, upper_count)
    lower_retained = count(ImageChops.multiply(contribution, lower)) / max(1, lower_count)
    covered_lower_by_snow = count(ImageChops.multiply(snow_mask, lower)) / max(1, lower_count)
    outside = ImageChops.multiply(difference, ImageChops.invert(footprint))
    outside_ratio = count(outside) / max(1, count(difference))
    snow_outside = ImageChops.multiply(snow_mask, ImageChops.invert(footprint))
    snow_retained = 1. - count(ImageChops.multiply(outside, snow_outside)) / max(1, count(snow_outside))
    matched = ImageChops.multiply(contribution, plant_mask)
    color_changed = changed(covered['image'], plant['image'], 35)
    color_match = 1. - count(ImageChops.multiply(color_changed, matched)) / max(1, count(matched))
    observability = (count(plant_mask) >= minimum and count(snow['object']) >= minimum and
                     (fully_occluded or upper_count >= max(8, minimum // 10)) and
                     lower_count >= max(12, minimum // 4))
    if height >= 5:
        observability = observability and covered_lower_by_snow >= .65
    checks = {
        'observable_controls': observability,
        'foliage_stays_at_standalone_position': outside_ratio <= .15,
        'remaining_foliage_matches_standalone': color_match >= .60,
        'snow_stays_at_control_position': snow_retained >= .90,
    }
    if fully_occluded:
        checks['fully_covered_plant_stays_occluded'] = count(contribution) <= max(8, minimum // 10)
    else:
        checks['plant_contributes_beyond_snow'] = count(contribution) >= max(20, minimum // 4)
        checks['upper_foliage_retained'] = upper_retained >= .65
    if height >= 5:
        checks['high_snow_occludes_lower_foliage'] = lower_retained <= .25
    return {'height': height, 'passed': all(checks.values()), 'valid_baseline': observability,
            'checks': checks, 'failures': [key for key, value in checks.items() if not value],
            'plant_pixels': count(plant_mask), 'snow_pixels': count(snow_mask),
            'covered_contribution_pixels': count(contribution), 'upper_pixels': upper_count,
            'standalone_uncovered_pixels': uncovered, 'fully_occluded_by_snow_control': fully_occluded,
            'lower_pixels': lower_count, 'upper_retained': upper_retained,
            'lower_retained': lower_retained, 'lower_snow_control_coverage': covered_lower_by_snow,
            'outside_standalone_ratio': outside_ratio, 'remaining_color_match': color_match,
            'upper_geometry': 'native alpha texels above snow' if visible_texels is not None else 'snow silhouette difference',
            'upper_edge_tolerance_pixels': 3 if visible_texels is not None else 0,
            'snow_outside_plant_retained': snow_retained,
            'limits': {'minimum_baseline_pixels': minimum, 'upper_retention': .65,
                       'high_lower_retention': .25, 'high_lower_snow_coverage': .65,
                       'outside_standalone_ratio': .15, 'color_match': .60, 'snow_retention': .90}}


def scope_checks(frames, plants, heights, minimum=80):
    rows = []
    for plant in plants:
        per_height = [compare_controls(frames[(plant, 'plant', 0)], frames[(plant, 'snow', height)],
                                       frames[(plant, 'covered', height)], height, minimum)
                      for height in heights]
        values = dict((row['height'], row) for row in per_height)
        comparative = (0 in values and 5 in values and
                       values[0]['lower_retained'] - values[5]['lower_retained'] >= .20)
        rows.append({'plant': plant, 'heights': per_height, 'height_pair_passed': comparative,
                     'passed': all(row['passed'] for row in per_height) and comparative,
                     'height_pair_contract': 'height 5 removes at least 20% more baseline lower foliage than height 0'})
    return {'passed': bool(rows) and all(row['passed'] for row in rows), 'plants': rows,
            'required_heights_complete': set(heights) == {0, 5},
            'scope': 'Fixed-camera visible upper and occluded lower foliage, snow position and two-height difference; no world writes'}


def compare_native(reference, actual, minimum=80, foliage=True):
    """Match native-world silhouettes; do not assume foliage survives deep snow."""
    if reference['image'].size != actual['image'].size:
        raise AssertionError('Native and projection crops must have identical dimensions')
    rows = {}
    for key in ('object', 'green'):
        if key == 'green' and not foliage:
            continue
        expected, observed = reference[key], actual[key]
        expected_count, observed_count = count(expected), count(observed)
        expected_expanded = expected.filter(ImageFilter.MaxFilter(7))
        observed_expanded = observed.filter(ImageFilter.MaxFilter(7))
        recall = count(ImageChops.multiply(expected, observed_expanded)) / max(1, expected_count)
        precision = count(ImageChops.multiply(observed, expected_expanded)) / max(1, observed_count)
        absent = expected_count < minimum // 4
        passed = (observed_count < minimum // 2 if absent else
                  recall >= .75 and precision >= .75 and
                  .5 <= observed_count / expected_count <= 2.)
        rows[key] = {'passed': passed, 'expected_pixels': expected_count,
                     'observed_pixels': observed_count, 'native_absent': absent,
                     'recall': recall, 'precision': precision, 'edge_tolerance_pixels': 3}
    return {'passed': all(row['passed'] for row in rows.values()), 'masks': rows,
            'scope': 'Actual native world at the same cell, camera and crop; silhouette and foliage coverage'}


def native_capture(check, plant, kind, height, target, offset, settle_seconds=.4):
    check.run('b.stop_projection()\n_result=True')
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('close workspace for native snow oracle',
                   lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    readback = server_run(check.client, NATIVE_MUTATE % (plant, kind, height))
    if kind == 'covered':
        time.sleep(.2)
        readback = server_run(check.client, NATIVE_SNOW % (height + 1))
        assert readback['result'], readback
    name = 'minecraft:air' if kind == 'blank' else ('minecraft:snow_layer' if kind in ('snow', 'covered') else 'minecraft:' + plant)
    assert readback['front']['name'] == name, readback
    if kind in ('snow', 'covered'):
        assert readback['states']['height'] == height, readback
        assert bool(readback['states']['covered_bit']) == (kind == 'covered'), readback
    pose = check.run('''target=%r
offset=%r
center=tuple(v+.5 for v in target)
position=tuple(center[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(center[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
_result=json.dumps({'target':center,'position':position,'rotation':rotation})
''' % (target, offset))
    camera_code = ('cam=b.factory.CreateCamera(b.level)\n_result=json.dumps({'
                   '"position":cam.GetPosition(),"rotation":cam.GetCameraRotation()})')
    check.wait('native snow camera', lambda value: camera_matches(value, pose), lambda: check.run(camera_code))
    def replicated(data):
        front = data.get('common', [])
        back = data.get('extra', [])
        if kind == 'blank':
            return all(row[0] == 'minecraft:air' for row in front + back)
        return (any(row[0] == name for row in front) and
                (kind != 'covered' or any(row[0] == 'minecraft:' + plant for row in back)))
    palette = check.wait('native snow client replication', replicated,
        lambda: check.run('''target=%r
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps(dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra')))
''' % (target,)))
    time.sleep(settle_seconds)
    shot = check.capture('%s_%s_h%d_native' % (plant, kind, height))
    server_run(check.client, NATIVE_MUTATE % (plant, 'blank', 0))
    check.wait('native snow oracle cleared on client',
        lambda data: all(row[0] == 'minecraft:air' for rows in data.values() for row in rows),
        lambda: check.run('''target=%r
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(target,target,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps(dict((key,[[value[0],value[1],indices] for value,indices in data.get(key,{}).items()]) for key in ('common','extra')))
''' % (target,)))
    time.sleep(max(.2, settle_seconds))
    hidden = check.capture('%s_%s_h%d_native_hidden' % (plant, kind, height))
    return {'readback': readback, 'client_palette': palette, 'pose': pose, 'screenshot': shot,
            'hidden_screenshot': hidden}


def projection_camera_pose(check, label, focus, offset):
    result = check.run('''import traceback
focus=%r
offset=%r
diagnostic={'stage':'inputs','origin':s.origin,'focus':focus,'offset':offset}
try:
 diagnostic['stage']='target'
 target=tuple(s.origin[i]+focus[i]+.5 for i in range(3))
 diagnostic['target']=target
 diagnostic['stage']='position'
 position=tuple(target[i]+offset[i] for i in range(3))
 diagnostic['position']=position
 diagnostic['stage']='GetRotFromDir'
 direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
 diagnostic['direction']=direction
 diagnostic['stage']='rotation'
 rotation=(direction[0],direction[1]+180.,0.)
 diagnostic['rotation']=rotation
 diagnostic['stage']='CreateCamera'
 cam=b.factory.CreateCamera(b.level)
 diagnostic['stage']='DepartCamera'
 cam.DepartCamera()
 diagnostic['stage']='LockModCameraPitch'
 diagnostic['pitch_lock_result']=cam.LockModCameraPitch(True)
 diagnostic['stage']='LockModCameraYaw'
 diagnostic['yaw_lock_result']=cam.LockModCameraYaw(True)
 diagnostic['stage']='SetCameraPos'
 diagnostic['position_result']=cam.SetCameraPos(position)
 assert diagnostic['position_result']
 diagnostic['stage']='SetCameraRotation'
 diagnostic['rotation_result']=cam.SetCameraRotation(rotation)
 assert diagnostic['rotation_result']
 diagnostic['stage']='complete'
 diagnostic['pose']={'target':target,'position':position,'rotation':rotation}
except Exception as error:
 diagnostic['error_type']=type(error).__name__
 diagnostic['error']=str(error)
 diagnostic['traceback']=traceback.format_exc()
_result=json.dumps(diagnostic)
''' % (focus, offset))
    if 'error_type' in result:
        path = check.output.with_name(check.output.stem+'_'+label+'_camera_error.json')
        write_json(path, result)
        raise RuntimeError('Snow projection camera failed at %s; evidence %s: %s\n%s' %
                           (result['stage'], path, result['error'], result['traceback']))
    return result['pose']


def projection_capture(check, label, focus, offset, missing=False, fixture_lift_y=0, world_target=None):
    native_before = check.run('_result=len(sys._blueprint_qa_records)')
    check.run('''focus=%r
foot=b.player_origin()
world_target=%r
s.origin=(tuple(world_target[i]-focus[i] for i in range(3)) if world_target is not None else
 (foot[0]+6-focus[0],foot[1]+8-focus[1]+%r,foot[2]+6-focus[2]))
s.opacity=1.
s.projection_missing=%r
s.projection_outline=False
b.project()
_result=True
''' % (focus, world_target, fixture_lift_y, missing))

    def ready(state):
        if state['error']:
            raise AssertionError(state)
        return (state['active'] and state['ready'] and not state['preparing'] and
                state['actors'] == 1 and state['mesh'] and state['scale'] is not None)

    state = check.wait('snow native projection', ready, lambda: check.run(PROJECTION_STATUS))
    source = check.run(PROJECTION_SOURCE)
    assert projection_source_matches(source, source), source
    if check.navigation()['open']:
        check.run('navigator.pop()\n_result=True')
        check.wait('close workspace for snow projection',
                   lambda nav: not nav['open'] and not nav['transition'], check.navigation)
    pose = projection_camera_pose(check, label, focus, offset)
    camera_code = ('cam=b.factory.CreateCamera(b.level)\n_result=json.dumps({'
                   '"position":cam.GetPosition(),"rotation":cam.GetCameraRotation()})')
    check.wait('snow world camera', lambda value: camera_matches(value, pose), lambda: check.run(camera_code))
    time.sleep(.45)
    shown = check.capture(label + '_world_closeup')
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.3)
        hidden = check.capture(label + '_world_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    final = check.run(PROJECTION_STATUS)
    actual_camera = check.run(camera_code)
    assert camera_matches(actual_camera, pose), (actual_camera, pose)
    assert state['actor'] == final['actor'] and state['mesh'][:3] == final['mesh'][:3], (state, final)
    saved_player = (state['player'] if world_target is not None else
                    check.run('_result=json.dumps(sys._blueprint_visual_saved["player"])'))
    assert saved_player == final['player'], (saved_player, final['player'])
    calls = check.run('_result=json.dumps(sys._blueprint_qa_records[%d:])' % native_before)
    current_source = check.run(PROJECTION_SOURCE)
    assert projection_source_matches(current_source, source), (source, current_source)
    assert all(row.get('result') and not row.get('error') and
               row.get('editor_id') == source['editor_id'] and
               row.get('document_id') == source['document_id'] and row.get('nonce') == source['nonce']
               for row in calls), calls
    state.update(pose=pose, final=final, camera=actual_camera, screenshot=shown,
                 hidden_screenshot=hidden, native_calls=calls, source=current_source,
                 native_evidence='current_source_submission' if calls else 'current_source_cached_geometry')
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plant', action='append', choices=('short_grass', 'fern', 'dandelion', 'poppy', 'blue_orchid', 'allium'))
    parser.add_argument('--height', type=int, action='append', choices=(0, 5))
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--native-resolution', action='store_true')
    parser.add_argument('--min-pixels', type=int, default=80)
    parser.add_argument('--raw-plants', action='store_true',
                        help='Diagnostic: bypass grass/fern proxies; always restored afterwards')
    parser.add_argument('--camera-calibration', type=Path,
                        help='Native cube calibration for this instance when WorldToScreenPoint is unavailable')
    args = parser.parse_args()
    if args.timeout <= 0 or args.min_pixels <= 0:
        parser.error('Timeout and minimum observable pixels must be positive')
    plants = tuple(dict.fromkeys(args.plant or ('short_grass', 'fern')))
    heights = sorted(set(args.height or (0, 5)))
    session = load_session(live=True)
    calibration = (json.loads(args.camera_calibration.read_text(encoding='utf8'))
                   if args.camera_calibration is not None else None)
    frames = {'editor': {}, 'projection': {}}
    evidence = {'schema': 5, 'completed': False, 'passed': False, 'rows': [],
                'scopes': {'editor': {'passed': False}, 'projection': {'passed': False}},
                'scope': 'Independent editor and actual projection assertions with standalone, snow and combined controls at heights 0 and 5.',
                'native_reference': {'captured': False,
                                     'capability_source': 'tools/data/native_snow_overlays_nemc_3.9.0.401155.json',
                                     'method': 'Place actual blocks at the exact projection focus cell; SetSnowBlock heights 1 and 6; verify native states 0 and 5; capture each native control and its immediately cleared background at the same measured side camera; segment foliage and neutral snow to exclude support and sky.'}}
    evidence['raw_plants_diagnostic'] = args.raw_plants
    evidence['native_resolution'] = args.native_resolution
    installed = visual_saved = native_created = raw_saved = False
    try:
        with Client(timeout=30) as client:
            from verify_sign_visuals import SignCheck
            check = SignCheck(client, args.output, args.timeout, args.native_resolution)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                check.refresh()
                if args.raw_plants:
                    check.run('''from modern_projection.projection import geometry_palette
sys._snow_raw_plant_proxies=dict(geometry_palette.PLANT_PROXIES)
for key in (('minecraft:short_grass',0),('minecraft:fern',0)):
 geometry_palette.PLANT_PROXIES.pop(key,None)
_result=True
''')
                    raw_saved = True
                blueprint_path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                case = check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                                 'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                                 '_result=json.dumps(refreshed.VISUAL_CASES["snow_plant_visibility"])' %
                                 (base64.b64encode(blueprint_path.read_bytes()).decode('ascii'), str(blueprint_path)))
                focus = tuple(case['focus'])
                evidence['focus'] = focus
                evidence['blueprint_case'] = case
                native_target = tuple(check.run('_result=json.dumps(tuple(b.player_origin()[i]+(6,8,6)[i] for i in range(3)))'))
                evidence['native_reference']['fixture'] = server_run(client, NATIVE_SETUP % (native_target,))
                native_created = True
                for plant in plants:
                    assets = cross_assets(session, plant)
                    if assets is not None:
                        evidence.setdefault('plant_assets', {})[plant] = assets[2]
                    cases = [('blank', 0), ('plant', 0)] + [(kind, height)
                            for height in heights for kind in ('snow', 'covered')]
                    editor_crop = None
                    blank_editor = None
                    for kind, height in cases:
                        label = '%s_%s_h%d' % (plant, kind, height)
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        source = check.run(LOAD % (plant, height, kind))
                        state = check.editor_preview('snow visibility preview', source['metadata'],
                                                     source['editor_id'], source['document_id'])
                        if kind != 'blank':
                            assert state['model_name'] and state['parts'] and state['renderer_active'], state
                        camera = check.wait('fixed editor camera',
                                            lambda pose: all(abs(pose[i] - case['camera']['editor'][i]) < .01 for i in range(3)),
                                            lambda: check.run('_result=json.dumps(s.camera_pose)'))
                        time.sleep(.3)
                        editor = check.capture(label + '_editor')
                        actual_crop = viewport_crop(check, editor)
                        if editor_crop is not None:
                            assert actual_crop == editor_crop, (editor_crop, actual_crop)
                        editor_crop = actual_crop
                        if kind == 'blank':
                            blank_editor = editor['path']
                            native = native_capture(check, plant, kind, height, native_target,
                                                    tuple(case['camera']['world_offset']))
                            evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height,
                                                     'source': source, 'editor': editor, 'editor_crop': editor_crop,
                                                     'editor_camera': camera, 'native': native})
                            write_json(args.output, evidence)
                            continue
                        editor_state = check.run('_result=json.dumps({"pose":s.camera_pose,'
                                                 '"pan":s.camera_pan,"pivot":s.camera_pivot,'
                                                 '"size":s.scene_size})')
                        geometry = geometry_record = None
                        if kind == 'snow':
                            geometry, geometry_record = editor_snow_geometry(editor_crop, editor_state, focus, height)
                        editor_frame = capture_frame(editor['path'], editor_crop, blank_editor, geometry=geometry)
                        upper_geometry_record = None
                        if kind == 'plant' and assets is not None:
                            model, texture, unused = assets
                            editor_frame['above_snow'] = {
                                h: editor_cross_above_snow(editor_crop, editor_state, focus, h, model, texture)
                                for h in heights}
                            upper_geometry_record = {}
                            for h, mask in editor_frame['above_snow'].items():
                                path = args.output.with_name(args.output.stem+'_'+plant+'_h%d_upper_geometry.png' % h)
                                mask.save(path)
                                upper_geometry_record[h] = {'mask': str(path.resolve()),
                                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bounds': mask.getbbox()}
                        frames['editor'][(plant, kind, height)] = editor_frame
                        pixels = analyze(editor_frame, editor_crop,
                                         args.output.with_name(args.output.stem + '_' + label + '_editor_mask.png'))
                        world = projection_capture(check, label, focus, tuple(case['camera']['world_offset']))
                        width, height_pixels = world['screenshot']['size']
                        crop = (width // 4, height_pixels // 4, width * 3 // 4, height_pixels * 3 // 4)
                        roi, roi_record = world_cell_roi(check, crop, (width, height_pixels), native_target,
                                                         world['pose'], calibration)
                        projection_frame = capture_frame(world['screenshot']['path'], crop,
                                                         world['hidden_screenshot']['path'], segmented=True, roi=roi)
                        frames['projection'][(plant, kind, height)] = projection_frame
                        world_pixels = analyze(projection_frame, crop,
                                               args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'))
                        native = native_capture(check, plant, kind, height, native_target,
                                                tuple(case['camera']['world_offset']))
                        assert native['pose'] == world['pose'], (native['pose'], world['pose'])
                        native_frame = capture_frame(native['screenshot']['path'], crop,
                                                     native['hidden_screenshot']['path'], segmented=True, roi=roi)
                        native['pixels'] = analyze(native_frame, crop,
                            args.output.with_name(args.output.stem + '_' + label + '_native_mask.png'))
                        native_comparison = compare_native(native_frame, projection_frame, args.min_pixels,
                                                           foliage=kind != 'snow')
                        stable_source = check.run('from modern_projection.projection.cell import foreground,background\n'
                                                  '_result=json.dumps({"front":foreground(s.editor.document.get(%r)),'
                                                  '"back":background(s.editor.document.get(%r)),'
                                                  '"runtime":api.GetMinecraftVersion() if hasattr(api,"GetMinecraftVersion") else None})' %
                                                  (focus, focus))
                        assert (stable_source['front'], stable_source['back'], stable_source['runtime']) == (
                            source['front'], source['back'], source['runtime_minecraft_version']), (source, stable_source)
                        evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height, 'source': source,
                                                 'editor': editor, 'editor_pixels': pixels, 'editor_camera': camera,
                                                 'editor_state': editor_state, 'editor_geometry': geometry_record,
                                                 'upper_geometry': upper_geometry_record,
                                                 'world_roi': roi_record,
                                                 'world': world, 'world_pixels': world_pixels,
                                                 'native': native, 'native_comparison': native_comparison})
                        write_json(args.output, evidence)
                        print(json.dumps({'label': label, 'editor': pixels['green_pixels'],
                                          'world': world_pixels['green_pixels']}), flush=True)
                        check.run('b.stop_projection()\n_result=True')
                        check.run(camera_restore_code(False))
                    completed_plants = plants[:plants.index(plant) + 1]
                    for scope, sampled in frames.items():
                        evidence['scopes'][scope] = scope_checks(sampled, completed_plants, heights, args.min_pixels)
                        for result in evidence['scopes'][scope]['plants']:
                            plant_frame = sampled[(result['plant'], 'plant', 0)]
                            for row in result['heights']:
                                snow_frame = sampled[(result['plant'], 'snow', row['height'])]
                                covered_frame = sampled[(result['plant'], 'covered', row['height'])]
                                contribution = ImageChops.multiply(changed(covered_frame['image'], snow_frame['image']),
                                                                    plant_frame['object'].filter(ImageFilter.MaxFilter(5)))
                                path = args.output.with_name(args.output.stem + '_%s_%s_h%d_contribution.png' %
                                                             (scope, result['plant'], row['height']))
                                contribution.save(path)
                                row['contribution_mask'] = str(path.resolve())
                    write_json(args.output, evidence)
                comparisons = [row['native_comparison'] for row in evidence['rows'] if 'native_comparison' in row]
                evidence['native_reference']['captured'] = True
                evidence['native_reference']['passed'] = bool(comparisons) and all(row['passed'] for row in comparisons)
                projection_checks = evidence['scopes']['projection']
                projection_checks['semantic_controls'] = dict(projection_checks)
                projection_checks['native_comparisons'] = comparisons
                projection_checks['passed'] = evidence['native_reference']['passed'] and set(heights) == {0, 5}
                versions = [dict((key, row['source'][key]) for key in (
                    'fixture', 'fixture_schema', 'registry_version', 'registry_fingerprint',
                    'runtime_minecraft_version', 'render_layout_version')) for row in evidence['rows']]
                version_stable = bool(versions) and all(value == versions[0] for value in versions)
                version_present = bool(versions and all(versions[0].values()))
                evidence['runtime_reference'] = versions[0] if versions else None
                evidence['runtime_reference_passed'] = version_stable and version_present
                for scope in evidence['scopes'].values():
                    scope['runtime_reference_passed'] = evidence['runtime_reference_passed']
                    scope['passed'] = scope['passed'] and evidence['runtime_reference_passed']
                evidence['completed'] = True
                evidence['passed'] = all(scope['passed'] for scope in evidence['scopes'].values())
            finally:
                prior_error = sys.exc_info()[0]
                cleanup_errors = []
                actions = []
                if raw_saved:
                    actions.append(('plant_proxies', lambda: check.run('''geometry_palette.PLANT_PROXIES.clear()
geometry_palette.PLANT_PROXIES.update(sys._snow_raw_plant_proxies)
del sys._snow_raw_plant_proxies
_result=True
''')))
                if native_created:
                    actions.append(('native_fixture', lambda: server_run(client, NATIVE_CLEANUP)))
                if visual_saved:
                    actions.extend((
                        ('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                        ('camera', lambda: check.run(camera_restore_code(False))),
                        ('visual_fields', lambda: check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')),
                    ))
                for label, action in actions:
                    try:
                        result = action()
                        if label == 'native_fixture':
                            if not result or not all(row['clean'] for row in result):
                                raise RuntimeError('Native snow fixture cleanup did not restore every cell: %r' % (result,))
                            evidence['native_reference']['cleaned'] = True
                    except Exception as cleanup_error:
                        cleanup_errors.append('%s: %s' % (label, cleanup_error))
                if installed:
                    try:
                        was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                        check.run(RESTORE)
                        if was_open:
                            check.run('owner.open_workspace()\n_result=True')
                            check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        elif check.navigation()['open']:
                            check.run('navigator.pop()\n_result=True')
                            check.wait('restore closed workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                        evidence['restored'] = True
                    except Exception as cleanup_error:
                        cleanup_errors.append('workspace: %s' % cleanup_error)
                if cleanup_errors:
                    evidence['cleanup_errors'] = cleanup_errors
                    evidence['completed'] = evidence['passed'] = False
                    if prior_error is None:
                        raise RuntimeError('Snow acceptance cleanup failed: ' + '; '.join(cleanup_errors))
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    print(json.dumps({'evidence': str(args.output.resolve()), 'completed': evidence['completed'],
                      'passed': evidence['passed'],
                      'editor_passed': evidence['scopes']['editor']['passed'],
                      'projection_passed': evidence['scopes']['projection']['passed']}))
    return 0 if evidence['completed'] and evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
