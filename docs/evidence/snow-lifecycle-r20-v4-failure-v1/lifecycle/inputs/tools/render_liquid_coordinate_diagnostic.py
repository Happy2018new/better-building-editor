"""Render unchanged native sample grids and fixed texel-border residual bins."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from diagnose_liquid_coordinate_sampling import nearest_templates
from liquid_coordinate_markers import check_frozen_sources,fingerprint,ranks,validate_sequences,write
from measure_native_liquid_side_uv import Hypothesis,oriented_uv,spatial_templates

BORDER_BINS=(0.,.1,.2,.3,.4,.5)


def border_distance(grid,hypothesis,width):
    u,height,top=(np.asarray(grid[key],float) for key in ('u','height','top'))
    v={'bottom':lambda:1-height,'top':lambda:height,'stretch':lambda:1-height/top}[hypothesis.side_v]()
    u,v=oriented_uv(u,v,hypothesis.orientation)
    span=width if hypothesis.region=='full' else width/2.
    # Quadrant offsets are integers, so they cannot change distance to a texel border.
    coordinates=(u*(span-1)+.5,v*(span-1)+.5) if hypothesis.pixel_mapping=='centers' else (u*span,v*span)
    distances=[np.minimum(value%1,1-value%1) for value in coordinates]
    return np.minimum(*distances)


def render(input_path,output_dir):
    if output_dir.exists():raise ValueError('Use a fresh diagnostic image directory')
    baseline=json.loads(input_path.read_bytes())
    validate_sequences(baseline['sampled_sequences'])
    plan=json.loads(Path(baseline['plan']['path']).read_bytes())
    if fingerprint(baseline['plan']['path'])!=baseline['plan']:raise ValueError('Frozen plan changed')
    check_frozen_sources(plan)
    asset=next(row for row in plan['assets'] if Path(row['generated']['path']).name=='water_flow_grey.png')
    if fingerprint(asset['generated']['path'])!=asset['generated']:raise ValueError('Frozen marker changed')
    with Image.open(asset['generated']['path']) as image:frame=np.asarray(image.convert('RGBA'))[:asset['dimensions'][0]]
    hypothesis=Hypothesis(**baseline['selected']);n=len(plan['sample_grid']['u'])
    panels={};diagnostics=[]
    for sequence in baseline['sampled_sequences']:
        grid={key:np.asarray(sequence['grid'][key],float) for key in ('u','height','top')}
        expected=spatial_templates(frame[None,:,:,:3].astype(float),grid,hypothesis)[0]
        nearest=nearest_templates(frame,grid,hypothesis);observed=np.asarray(sequence['observed'],float)
        expected_rank,observed_rank=ranks(expected),ranks(observed)
        error=observed_rank-expected_rank;distance=border_distance(grid,hypothesis,len(frame))
        bins=[]
        for low,high in zip(BORDER_BINS[:-1],BORDER_BINS[1:]):
            selected=(distance>=low)&(distance<high if high<.5 else distance<=high)
            bins.append({'minimum_distance_texels':low,'maximum_distance_texels':high,'samples':int(selected.sum()),
                         'rank_rmse':float(np.sqrt(np.mean(error[selected]**2))) if selected.any() else None})
        diagnostics.append({'sequence':sequence['id'],'border_distance_bins':bins})
        arrays=[expected,nearest,observed,expected_rank*255,observed_rank*255,np.abs(error)*255]
        for index in range(len(observed)//(n*n)):
            tiles=[]
            for array in arrays:
                pixels=np.clip(array[index*n*n:(index+1)*n*n],0,255).astype(np.uint8).reshape(n,n,3)
                tiles.append(Image.fromarray(np.flipud(pixels)).resize((160,160),Image.Resampling.NEAREST))
            depth=sequence['id'].split('/')[0]
            panels.setdefault(depth,[]).append((sequence['id']+' / surface '+str(index),tiles))
    output_dir.mkdir(parents=True)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
    outputs={}
    headers=['Source bilinear','Source nearest','Native RGB','Source RGB ranks','Native RGB ranks','Abs rank error']
    for depth,rows in panels.items():
        canvas=Image.new('RGB',(1230,60+len(rows)*190),'white');draw=ImageDraw.Draw(canvas)
        draw.text((12,8),'Depth '+depth+'; fixed source/camera/geometry/sample points; each tile is 16 x 16 samples',fill='black',font=font)
        for index,header in enumerate(headers):draw.text((210+index*170,35),header,fill='black',font=font)
        for index,(label,tiles) in enumerate(rows):
            y=60+index*190;draw.text((12,y+12),label,fill='black',font=font)
            for column,tile in enumerate(tiles):canvas.paste(tile,(210+column*170,y))
        path=output_dir/('depth-'+depth+'-grids.png');canvas.save(path);outputs[depth]=fingerprint(path)
    result={'schema':1,'input':fingerprint(input_path),'renderer':fingerprint(Path(__file__)),
            'images':outputs,'selected':baseline['selected'],'border_bins':list(BORDER_BINS),
            'residuals':diagnostics,'scope':'Post-observation visualization only; no sample relocation, exclusion, geometry/camera fitting, photometric fitting, or native acceptance',
            'rank_display':'Candidate-independent within-sequence channel ranks scaled by255; errors use fixed0..1 rank units',
            'native_uv_accepted':False,'production_accepted':False}
    write(output_dir/'report.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();result=render(args.input,args.output_dir)
    print(json.dumps({'images':result['images'],'residuals':result['residuals']}))


if __name__=='__main__':main()
