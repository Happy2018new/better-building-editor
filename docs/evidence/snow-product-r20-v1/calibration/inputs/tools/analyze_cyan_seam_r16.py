"""Crop matched projection/real cube captures without declaring seam acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image,ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads((args.folder/'report.json').read_bytes())
    if not report['completed'] or not report['restored'] or report['cleanup_errors']:
        raise ValueError('Comparison did not complete and restore')
    if report['rows'].get('client_real')!=['minecraft:cyan_concrete',0]:
        raise ValueError('Comparison lacks a visible real block control')
    args.output.mkdir(parents=True,exist_ok=False)
    rows=[]
    for yaw in (45.,135.):
        sheet=Image.new('RGB',(1100,740),'white')
        for index,kind in enumerate(('projection','real')):
            label=kind+'_yaw'+str(yaw)
            capture=report['captures'][label]['capture']
            path=args.folder/Path(capture['path']).name
            if digest(path)!=capture['sha256'] or not capture['ok'] or not capture['reliable']:
                raise ValueError('Comparison pixels changed or were not reliable')
            with Image.open(path) as original:
                crop=original.convert('RGB').crop((770,350,1230,800))
            crop=crop.resize((1012,990))
            crop.thumbnail((530,700))
            sheet.paste(crop,(index*550+10,30))
            ImageDraw.Draw(sheet).text((index*550+10,8),label,fill='black')
        destination=args.output/('yaw%d.png' % yaw)
        sheet.save(destination)
        rows.append({'file':destination.name,'sha256':digest(destination)})
    result={'schema':1,'report_sha256':digest(args.folder/'report.json'),'sheets':rows,
            'manual_pixel_acceptance':False,
            'limits':'Matched-camera crop only; no automatic seam threshold is asserted.'}
    (args.output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii',newline='\n')
    print(json.dumps({'sheets':len(rows),'client_real_verified':True}))


if __name__=='__main__':main()
