"""Recover native cauldron tint using simultaneous white/black references."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from analyze_cauldron_surface_r15 import camera_matrix, project


def sample_colors(folder, pixel_offset, height):
    report = json.loads((folder/'report.json').read_bytes())
    before, after = report['before'], report['after']
    for key in ('states', 'nbt'):
        if before[key] != after[key]:
            raise ValueError('Native source changed during color capture: '+key)
    # Native float settling is accepted only when every sampled screen point
    # remains well within one pixel. Large horizon/pose changes still fail.
    before_pixels = np.array([[p['screen']['screenX'], p['screen']['screenY']]
                              for p in before['points']])
    after_pixels = np.array([[p['screen']['screenX'], p['screen']['screenY']]
                             for p in after['points']])
    if (len(before_pixels) != 125 or before_pixels.shape != after_pixels.shape or
            any(a['local'] != b['local'] for a, b in zip(before['points'], after['points']))):
        raise ValueError('Camera projection sample layout changed during color capture')
    drift = float(np.max(np.linalg.norm(before_pixels-after_pixels, axis=1)))
    if drift > .05:
        raise ValueError('Native camera moved during color capture: %.6f px' % drift)
    if np.linalg.norm(np.asarray(before['camera_position'])-after['camera_position']) > .00001:
        raise ValueError('Native camera position changed during color capture')
    if before['states'] != {'cauldron_liquid': 'water', 'fill_level': 6}:
        raise ValueError('Color references require a full native water-family cauldron')
    matrix, unused_error = camera_matrix(before['points'])
    matrix[0] += pixel_offset[0]*matrix[2]
    matrix[1] += pixel_offset[1]*matrix[2]
    image = np.asarray(Image.open(folder/'frame.png').convert('RGB'))
    samples, valid = [], np.ones(256, dtype=bool)
    for offset in (0., 2., 4.):
        points = [(offset+x, height, z) for x in np.linspace(.25,.75,16)
                  for z in np.linspace(.3,.8,16)]
        pixels = project(matrix, points)
        values = []
        for index, (x, y) in enumerate(pixels):
            # Exclude the native crosshair rather than treating it as a texel.
            if abs(x-image.shape[1]/2.) < 25 and abs(y-image.shape[0]/2.) < 25:
                valid[index] = False
            ix, iy = int(x), int(y)
            values.append(np.median(image[iy-1:iy+2,ix-1:ix+2],axis=(0,1)))
        samples.append(np.array(values))
    target, white, black = samples
    denominator = white-black
    valid &= np.all(denominator > 30, axis=1)
    rgb = (target[valid]-black[valid])/denominator[valid]*255.
    if len(rgb) < 160:
        raise ValueError('Too few simultaneous calibrated color samples')
    median = np.median(rgb,axis=0)
    return {'source': str(folder), 'rgb_float': median.tolist(),
            'rgb': np.clip(np.rint(median),0,255).astype(int).tolist(),
            'sample_count': len(rgb), 'rgb_percentiles_10_90': np.percentile(rgb,[10,90],axis=0).tolist(),
            'native_nbt': before['nbt'], 'native_block': before['block'],
            'image_sha256': hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest(),
            'method': 'median corresponding-UV (target-black)/(white-black), same native frame',
            'camera_projection_drift_pixels': drift,
            'product_acceptance_claimed': False}


def uv_edges(folder, pixel_offset, height):
    report = json.loads((folder/'report.json').read_bytes())
    matrix, unused = camera_matrix(report['before']['points'])
    matrix[0] += pixel_offset[0]*matrix[2]
    matrix[1] += pixel_offset[1]*matrix[2]
    image = np.asarray(Image.open(folder/'frame.png').convert('RGB'),dtype=float)
    difference = np.linalg.norm(image[:,1:]-image[:,:-1],axis=2)
    ys, xs = np.nonzero(difference>15.)
    homography = np.column_stack((matrix[:,0],matrix[:,2],matrix[:,1]*height+matrix[:,3]))
    points = np.column_stack((xs+.5,ys,np.ones(len(xs)))) @ np.linalg.inv(homography).T
    xz = points[:,:2]/points[:,2:]
    x,z = xz.T
    r,g,b = image[ys,xs].T
    valid = ((x>.15)&(x<.85)&(z>.2)&(z<.8)&(r>g+10)&(g>b+10))
    x = x[valid]
    if len(x)<100:
        raise ValueError('Too few native texture boundaries for a UV measurement')
    candidates = {'block_coordinates_inset_region': x*16.,
                  'full_texture_stretched_to_basin': (x-.125)/.75*16.}
    return {'edge_samples':len(x), 'source':str(folder),
            'fractional_texel_boundary_error':{name:float(np.median(np.abs(value-np.rint(value))))
                                              for name,value in candidates.items()},
            'image_sha256':hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--height',type=float,required=True)
    parser.add_argument('--uv',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    calibration=json.loads(args.calibration.read_bytes())['pixel_calibration']['pixel_offset']
    result=(uv_edges if args.uv else sample_colors)(args.source,calibration,args.height)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
