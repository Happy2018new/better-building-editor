"""Publish compact snow evidence without IPC tokens or unrelated window metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value, runtime):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value and 'size' in value:
            return {key: (Path(item).name if key=='path' else item)
                    for key,item in value.items() if key in ('path','sha256','size','bytes','mime')}
        return {key: compact(item, runtime) for key,item in value.items()
                if key not in ('capture','session_file','guard','foreground','foreground_before',
                               'foreground_after','foreground_title','workers') and
                not any(word in key.lower() for word in ('token','password','authorization','secret'))}
    if isinstance(value, list): return [compact(item,runtime) for item in value]
    if isinstance(value, str) and str(runtime) in value:
        return value.replace(str(runtime),'<retained-runtime>')
    return value


def gallery(report, mode, output):
    rows = []
    for plant in report['plants']:
        cases = [row for row in report['rows'] if row['plant']==plant and row['kind'] in ('plant','covered')]
        height = report['heights'][plant]
        targets = [('plant',0),('covered',height[0]),('covered',height[-2]),('covered',height[-1])]
        samples = [next((row for row in cases if (row['kind'],row['height'])==target),None) for target in targets]
        if all(samples): rows.append((plant,samples))
    if not rows:return None
    sheet = Image.new('RGB',(1280,220*len(rows)),(225,228,232))
    draw = ImageDraw.Draw(sheet)
    for index,(plant,samples) in enumerate(rows):
        for column,row in enumerate(samples):
            record = row['editor'] if mode=='editor' else row['world'][mode]['screenshot']
            with Image.open(record['path']) as original:
                width,height=original.size
                crop = row['editor_crop'] if mode=='editor' else (width//4,height//4,width*3//4,height*3//4)
                tile = original.convert('RGB').crop(crop)
                tile.thumbnail((314,190),Image.Resampling.LANCZOS)
                x,y=column*320,index*220
                sheet.paste(tile,(x+(320-tile.width)//2,y+20+(190-tile.height)//2))
                draw.text((x+5,y+3),plant+' '+row['kind']+' h'+str(row['height']),fill='black')
    path=output/(mode+'_contact_sheet.png')
    sheet.save(path)
    return {'path':path.name,'sha256':sha(path),'plants':len(rows),'tile_policy':'Same source full screenshot crop, no pixel recoloring'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    manifest={'schema':1,'source_reports':{},'artifacts':{},'scope':'Curated evidence; exact original reports and all native PNGs remain in owned runtime'}
    for name in ('calibration','positive','screen','all-heights','catalogue','report'):
        source=args.runtime/(name+'.json')
        if not source.exists():continue
        report=json.loads(source.read_bytes())
        manifest['source_reports'][name]={'original_sha256':sha(source),'completed':report.get('completed'),
                                         'passed':report.get('passed'),'restored':report.get('restored')}
        (args.output/(name+'.json')).write_text(json.dumps(compact(report,args.runtime),ensure_ascii=True,indent=2)+'\n',encoding='ascii')
        if name=='catalogue':
            for mode in ('editor','full','missing'):
                item=gallery(report,mode,args.output)
                if item:manifest['artifacts'][mode]=item
    for name in ('positive_short_grass_covered_h0_missing_world_closeup_native.png',
                 'positive_short_grass_covered_h0_missing_world_hidden_native.png',
                 'screen_fern_covered_h5_full_world_closeup_native.png'):
        source=args.runtime/name
        if source.exists():
            shutil.copyfile(source,args.output/name)
            manifest['artifacts'][name]={'path':name,'sha256':sha(source),'native_full_frame':True}
    for version,name in ((2,'positive'),(3,'screen'),(4,'positive'),(5,'calibration'),(6,'positive')):
        source=args.runtime.parent/('snow-centered-r14-product-v'+str(version))/(name+'.json')
        if not source.exists():continue
        label='historical_v%d_%s' % (version,name)
        report=json.loads(source.read_bytes())
        manifest['source_reports'][label]={'original_sha256':sha(source),'completed':report.get('completed'),
                                          'passed':report.get('passed'),'restored':report.get('restored')}
        (args.output/(label+'.json')).write_text(json.dumps(compact(report,source.parent),ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    for version,name in ((4,'positive_short_grass_covered_h0_missing_world_closeup_native.png'),
                         (4,'positive_short_grass_covered_h0_missing_world_hidden_native.png'),
                         (5,'calibration_right_signal_outline_comparison.png')):
        source=args.runtime.parent/('snow-centered-r14-product-v'+str(version))/name
        label='historical_v%d_%s' % (version,name)
        if source.exists():
            shutil.copyfile(source,args.output/label)
            manifest['artifacts'][label]={'path':label,'sha256':sha(source),'original_failure_retained':True}
    inputs=args.output/'inputs'
    inputs.mkdir(exist_ok=True)
    shutil.copyfile(Path(__file__),inputs/'publish_centered_snow.py')
    (args.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=True,indent=2)+'\n',encoding='ascii')
    print(json.dumps(manifest,ensure_ascii=True))


if __name__=='__main__':main()
