"""Measure localized filled/empty and temporal cauldron pixels, retaining limits."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def rgb(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.int16)


def components(mask):
    labels, count = ndimage.label(mask)
    if not count:
        raise ValueError('No independently visible content differs from the empty shell')
    sizes = np.bincount(labels.ravel());sizes[0] = 0
    return labels == int(np.argmax(sizes))


def analyze(report_path, output):
    report = json.loads(report_path.read_bytes())
    if not report['completed'] or not report['restored'] or report['cleanup_errors'] or not report['source_unchanged']:
        raise ValueError('Runtime capture did not complete and restore unchanged sources')
    result = {'schema': 1, 'report': str(report_path),
              'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
              'rows': {}, 'exact_native_parity_claimed': False, 'manual_review_required': True}
    cards = []
    for label, row in report['rows'].items():
        if row['control'] != 'filled':
            continue
        empty_label = label[:-6]+'empty'
        if empty_label not in report['captures']:
            continue
        filled_path = Path(report['captures'][label]['path'])
        empty_path = Path(report['captures'][empty_label]['path'])
        filled, empty = rgb(filled_path), rgb(empty_path)
        if filled.shape != empty.shape:
            raise ValueError('Capture size changed')
        difference = np.max(np.abs(filled-empty), axis=2)
        roi = np.zeros(difference.shape, dtype=bool)
        height, width = difference.shape
        # Restrict to the actual rendered view, excluding UI/HUD text changes.
        if row['route'] == 'editor':
            roi[int(height*.32):int(height*.76),int(width*.24):int(width*.77)] = True
        else:
            roi[int(height*.2):int(height*.85),int(width*.2):int(width*.8)] = True
        surface = components((difference > 16) & roi)
        if surface.sum() < 80:
            raise ValueError('Too few visible cauldron content pixels: '+label)
        ys, xs = np.nonzero(surface)
        pixel = {'content_pixels': int(surface.sum()), 'bounds': [int(xs.min()),int(ys.min()),
                  int(xs.max())+1,int(ys.max())+1],
                 'rgb_median': np.median(filled[surface],axis=0).tolist(),
                 'filled_sha256': hashlib.sha256(filled_path.read_bytes()).hexdigest(),
                 'empty_sha256': hashlib.sha256(empty_path.read_bytes()).hexdigest()}
        later_label = label+'_later'
        if later_label in report['captures']:
            later_path = Path(report['captures'][later_label]['path'])
            later = rgb(later_path)
            inner = ndimage.binary_erosion(surface, iterations=2)
            temporal = np.max(np.abs(filled-later), axis=2)
            pixel['temporal_samples'] = int(inner.sum())
            pixel['temporal_changed_pixels'] = int(np.sum((temporal > 6) & inner))
            pixel['temporal_changed_fraction'] = float(np.mean(temporal[inner] > 6))
            pixel['later_sha256'] = hashlib.sha256(later_path.read_bytes()).hexdigest()
        result['rows'][label] = pixel
        margin = 20
        bounds = (max(0,xs.min()-margin),max(0,ys.min()-margin),
                  min(width,xs.max()+margin+1),min(height,ys.max()+margin+1))
        card = Image.open(filled_path).convert('RGB').crop(bounds).resize((260,260))
        tile = Image.new('RGB',(260,290),'white');tile.paste(card,(0,25))
        ImageDraw.Draw(tile).text((4,4),label,fill='black');cards.append(tile)
    if not result['rows']:
        raise ValueError('No paired visible contents were captured')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    columns = 6
    sheet = Image.new('RGB',(columns*260,((len(cards)+columns-1)//columns)*290),'white')
    for index, card in enumerate(cards):
        sheet.paste(card,(index%columns*260,index//columns*290))
    sheet.save(output.with_suffix('.png'))
    return result


def analyze_biomes(report_path, output, matrix_analysis):
    report=json.loads(report_path.read_bytes())
    if (not report['completed'] or not report['restored'] or report['cleanup_errors'] or
            not report['source_unchanged'] or not report['profile']['default_enabled']):
        raise ValueError('Default biome capture did not complete and restore')
    matrix=json.loads(matrix_analysis.read_bytes())
    result={'schema':1,'report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
            'matrix_analysis_sha256':hashlib.sha256(matrix_analysis.read_bytes()).hexdigest(),
            'default_profile':True,'rows':{},'exact_native_parity_claimed':False}
    cards=[]
    for route in ('editor','full','missing'):
        bounds=matrix['rows'][route+'_water6_filled']['bounds']
        x0,y0,x1,y1=bounds
        # This small central region is inside the measured finite liquid plane.
        region=(int(x0+(x1-x0)*.35),int(y0+(y1-y0)*.4),
                int(x0+(x1-x0)*.65),int(y0+(y1-y0)*.65))
        samples={}
        for biome in ('plains','swampland'):
            label=route+'_water6_filled_biome_'+biome
            receipt=report['captures'][label]
            local=report_path.parent/Path(receipt['path']).name
            path=local if local.exists() else Path(receipt['path'])
            if not receipt['reliable'] or hashlib.sha256(path.read_bytes()).hexdigest()!=receipt['sha256']:
                raise ValueError('Biome capture changed or is unreliable')
            image=Image.open(path).convert('RGB')
            pixels=np.asarray(image.crop(region),dtype=np.int16)
            if pixels.shape[0]*pixels.shape[1]<80:
                raise ValueError('Not enough independent biome pixels')
            median=np.median(pixels.reshape(-1,3),axis=0)
            samples[biome]=median
            result['rows'][label]={'sample_bounds':region,'samples':pixels.shape[0]*pixels.shape[1],
                                  'rgb_median':median.tolist(),'capture_sha256':receipt['sha256']}
            crop=image.crop((x0-20,y0-20,x1+20,y1+20)).resize((260,260))
            tile=Image.new('RGB',(260,290),'white');tile.paste(crop,(0,25))
            ImageDraw.Draw(tile).text((4,4),label,fill='black');cards.append(tile)
        if (samples['plains'][2]<=samples['plains'][1] or
                samples['swampland'][1]<=samples['swampland'][2] or
                np.mean(np.abs(samples['plains']-samples['swampland']))<12.):
            raise ValueError('Visible water did not change from blue to the swamp preset: '+route)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    sheet=Image.new('RGB',(520,870),'white')
    for index,card in enumerate(cards):
        sheet.paste(card,(index%2*260,index//2*290))
    sheet.save(output.with_suffix('.png'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--biome-matrix',type=Path,
                        help='Use measured finite-plane bounds for default biome smoke')
    args = parser.parse_args()
    result = (analyze_biomes(args.report,args.output,args.biome_matrix) if args.biome_matrix else
              analyze(args.report,args.output))
    print(json.dumps({'rows':len(result['rows']),'output':str(args.output)}))


if __name__ == '__main__':
    main()
