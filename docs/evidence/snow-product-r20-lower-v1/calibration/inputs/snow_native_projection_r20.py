"""Use calibrated physical camera pixels for the R20 snow cell hull."""
import math

from PIL import Image, ImageDraw

from verify_snow_plant_visibility import convex_hull


def physical_roi(projected, screenshot_size, crop):
    if len(projected) != 8 or not all(row.get('isInScreen') is True for row in projected):
        raise ValueError('Snow cell requires eight visible native corners')
    points = [(row['screenX'], row['screenY']) for row in projected]
    if not all(math.isfinite(x) and math.isfinite(y) and 0 <= x < screenshot_size[0]
               and 0 <= y < screenshot_size[1] for x, y in points):
        raise ValueError('Snow native corners are not physical pixels in this capture')
    polygon = convex_hull((x - crop[0], y - crop[1]) for x, y in points)
    mask = Image.new('L', (crop[2] - crop[0], crop[3] - crop[1]))
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    if mask.getbbox() is None or mask.histogram()[255] < 80:
        raise ValueError('Snow native cell hull is empty or too small')
    return mask, polygon


def world_cell_roi(check, crop, screenshot_size, base, pose, calibration):
    data = check.run('''base=%r
cam=b.factory.CreateCamera(b.level)
points=[tuple(base[i]+delta[i] for i in range(3))
 for delta in ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))]
native=[cam.WorldToScreenPoint(*point) for point in points]
_result=json.dumps({'points':points,'native':native,'fov':cam.GetFov(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'version':api.GetMinecraftVersion(),
 'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''' % (tuple(base),))
    if (calibration.get('native_projection', {}).get('coordinate_units') != 'physical_pixels'
            or not calibration.get('native_projection', {}).get('validation')):
        raise ValueError('Snow native pixel units lack visible same-session cube calibration')
    if data['version'] != calibration['runtime_minecraft_version']:
        raise ValueError('Snow native projection runtime version changed')
    if any(abs(data['position'][i] - pose['position'][i]) > .02 for i in range(3)):
        raise ValueError('Snow camera moved before native cell projection')
    if any(abs((data['rotation'][i] - pose['rotation'][i] + 180.) % 360. - 180.) > .2 for i in range(3)):
        raise ValueError('Snow camera rotated before native cell projection')
    mask, polygon = physical_roi(data['native'], screenshot_size, crop)
    return mask, {'method': 'Same-session cube-validated native WorldToScreenPoint physical pixels',
                  'coordinate_units': 'physical_pixels', 'polygon': polygon,
                  'camera': pose, 'native_readback': data, 'screen': data['screen'],
                  'world_base': base, 'bounds': mask.getbbox(),
                  'calibration': calibration, 'logical_screen_scale_applied': False}
