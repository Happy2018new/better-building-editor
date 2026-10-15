"""Review portal pixels and motion without counting the time/FPS overlays."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def colored(values):
    maximum, minimum = values.max(axis=2), values.min(axis=2)
    return ((maximum-minimum>14) & (maximum>40) &
            ~((values[:,:,2]>215) & (values[:,:,0]<130)))


def analyze(folder, output):
    report_path=folder/'report.json'
    report=json.loads(report_path.read_bytes())
    rows,panels,pixels={},{},{}
    for label,observation in report['captures'].items():
        path=folder/Path(observation['capture']['path']).name
        if digest(path)!=observation['capture']['sha256']:
            raise ValueError('Portal capture changed: '+label)
        with Image.open(path) as original:
            original=original.convert('RGB')
            ratios=(485/1994.,355/1108.,1525/1994.,846/1108.) if label.startswith('editor_') else (.40,.38,.61,.72)
            box=tuple(round(value*(original.width if index%2==0 else original.height))
                      for index,value in enumerate(ratios))
            crop=original.crop(box)
        values=np.asarray(crop,dtype=np.int16)
        mask=colored(values)
        rows[label]={'colored_pixels':int(mask.sum()),'crop':box}
        pixels[label]=(values,mask)
        thumbnail=crop.copy();thumbnail.thumbnail((720,390))
        panel=Image.new('RGB',(740,420),'#e6e8eb')
        panel.paste(thumbnail,((740-thumbnail.width)//2,28))
        ImageDraw.Draw(panel).text((12,8),label,fill='black')
        panels[label]=panel
    motion={}
    for label,(values,mask) in pixels.items():
        if not label.endswith('_motion0'):
            continue
        prefix=label[:-1]
        comparisons=[]
        for sample in (1,2):
            other,other_mask=pixels[prefix+str(sample)]
            delta=np.abs(values-other).max(axis=2)
            comparisons.append({'pair':[label,prefix+str(sample)],
                'changed_colored_pixels':int(((mask|other_mask)&(delta>12)).sum()),
                'mean_delta':float(delta.mean())})
        motion[prefix]=comparisons
    output.mkdir(parents=True,exist_ok=True)
    sheets=[]
    values=list(panels.values())
    for offset in range(0,len(values),6):
        group=values[offset:offset+6]
        sheet=Image.new('RGB',(1480,((len(group)+1)//2)*420),'white')
        for index,panel in enumerate(group):
            sheet.paste(panel,((index%2)*740,(index//2)*420))
        path=output/('review-%02d.png' % (offset//6));sheet.save(path)
        sheets.append({'name':path.name,'sha256':digest(path)})
    analysis={'schema_version':1,'report_sha256':digest(report_path),'rows':rows,
        'motion':motion,'sheets':sheets,'manual_pixel_acceptance':False,
        'limits':'Color and motion counts are diagnostics. World foliage can enter the crop; actual portal pixels must also be reviewed.'}
    (output/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n',encoding='ascii',newline='\n')
    print(json.dumps({'captures':len(rows),'sheets':len(sheets),'motion':motion}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();analyze(args.folder,args.output)


if __name__=='__main__':main()
