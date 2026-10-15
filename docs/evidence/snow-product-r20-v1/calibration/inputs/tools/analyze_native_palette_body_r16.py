"""Retain a compact, positive-controlled record of missing native shelf bodies."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def colors(picture, baseline, region, predicate):
    box = tuple(round(value*(picture.width if index%2 == 0 else picture.height))
                for index,value in enumerate(region))
    return sum(predicate(*pixel) and max(abs(pixel[channel]-reference[channel]) for channel in range(3))>12
               for pixel,reference in zip(picture.crop(box).convert('RGB').getdata(),
                                          baseline.crop(box).convert('RGB').getdata()))


def analyze(path, destination):
    report = json.loads(path.read_bytes())
    if not all(report.get(key) is True for key in ('completed','restored','source_unchanged')):
        raise ValueError('The palette diagnostic was incomplete or not restored')
    if report['palette']['roundtrip_equal'] is not True:
        raise ValueError('A serialization mismatch must be investigated separately')
    rows, pictures = {}, {}
    baselines = {}
    for view in ('south','north','east','west'):
        original = path.parent / Path(report['captures']['empty_'+view]['path']).name
        with Image.open(original) as picture:
            baselines[view] = picture.convert('RGB')
    for label,receipt in report['captures'].items():
        original = path.parent / Path(receipt['path']).name
        if (not receipt['ok'] or not receipt['reliable'] or
                receipt.get('agent_activation_allowed') is not False or
                receipt.get('activation_fallback') is not False or digest(original) != receipt['sha256']):
            raise ValueError('Invalid capture: ' + label)
        with Image.open(original) as picture:
            picture = picture.convert('RGB')
            baseline = baselines[label.rsplit('_',1)[1]]
            shelf = colors(picture,baseline,(.44,.35,.56,.59),lambda r,g,b:r>50 and g>30 and r>g*1.02 and g>b*1.2)
            support = colors(picture,baseline,(.42,.60,.57,.80),lambda r,g,b:g>40 and b>40 and g>r*1.3 and b>r*1.2)
            rows[label] = {'shelf_wood_pixels':shelf,'cyan_support_pixels':support,
                           'sha256':receipt['sha256'],'receipt_reliable':True}
            crop = picture.crop((round(picture.width*.399),round(picture.height*.317),
                                 round(picture.width*.602),round(picture.height*.792)))
            pictures[label] = crop.resize((310,400))
    views = ('south','north','east','west')
    if set(rows) != {route+'_'+view for route in ('world','live','roundtrip','prepared','empty') for view in views}:
        raise ValueError('The four-view path matrix is incomplete')
    observed = all(rows['world_'+view]['shelf_wood_pixels']>1000 and
                   rows['world_'+view]['cyan_support_pixels']>5000 and
                   all(rows[route+'_'+view]['cyan_support_pixels']>5000 and
                       rows[route+'_'+view]['shelf_wood_pixels'] < rows['world_'+view]['shelf_wood_pixels']*.02
                       for route in ('live','roundtrip','prepared')) for view in views)
    destination.mkdir(parents=True,exist_ok=False)
    sheet = Image.new('RGB',(1600,1720),(32,32,32))
    draw = ImageDraw.Draw(sheet)
    for index,label in enumerate(view_route+'_'+view for view in views
                                 for view_route in ('world','live','roundtrip','prepared','empty')):
        sheet.paste(pictures[label],((index%5)*320,(index//5)*430+25))
        draw.text(((index%5)*320+5,(index//5)*430+5),label,fill='white')
    sheet.save(destination/'review.png')
    result = {'schema':1,'engine':'3.10.0.420447','material':['minecraft:oak_shelf',0],
              'report_sha256':digest(path),'rows':rows,'native_body_missing_observed':observed,
              'review_sha256':digest(destination/'review.png'),
              'production_qualification':False,
              'limits':['Only one oak shelf state was measured; other woods and connection roles remain pending.',
                        'This focused review retains source/report hashes, not all original captures.',
                        'Original PNGs and capture receipts remain at '+str(path.parent.resolve())]}
    (destination/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii',newline='\n')
    shutil.copyfile(path,destination/'report.json')
    print(json.dumps({'native_body_missing_observed':observed,'captures':len(rows)}))
    return 0 if observed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    raise SystemExit(analyze(args.report,args.output))
