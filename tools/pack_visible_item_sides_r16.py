"""Archive a bounded native side-view failure without claiming qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(before, after, output):
    output.mkdir(parents=True, exist_ok=False)
    summary = {'schema': 1, 'production_qualified': False, 'captures': {},
               'scope': 'Selected unaltered native captures and replay summaries; full raw reports remain local',
               'finding': 'Side-wall neighbor generation fixed; editor oblique occlusion remains unqualified'}
    panels = []
    for variant, folder in (('before', before), ('after', after)):
        report_path, analysis_path = folder/'report.json', folder.with_name(folder.name+'-analysis')/'analysis.json'
        report = json.loads(report_path.read_bytes())
        analysis = json.loads(analysis_path.read_bytes())
        if (not report['completed'] or report['cleanup_errors'] or not report['source_unchanged'] or
                not analysis['evidence_valid'] or analysis['source_sha256'] != digest(report_path)):
            raise ValueError('Side-view archive requires complete, stable, replayed evidence')
        case = analysis['cases'][0]
        if case['id'] != 'orientation.frame_f2_r0':
            raise ValueError('Expected the same public north-facing frame fixture')
        item = {'source_report_sha256': digest(report_path),
                'source_analysis_sha256': digest(analysis_path),
                'resource_contract': report['resource_contract'],
                'evidence_valid': analysis['evidence_valid'],
                'all_bodies_passed': analysis['all_bodies_passed'],
                'case': case, 'files': []}
        destination = output/variant
        destination.mkdir()
        for capture in report['captures']:
            label = capture['label']
            if not label.startswith(case['id']+'_'):
                continue
            source = folder/(label+'.png')
            target = destination/source.name
            shutil.copyfile(source, target)
            item['files'].append({'path': target.relative_to(output).as_posix(),
                                  'sha256': digest(source)})
        for route in ('editor','full','native'):
            label = case['id']+'_'+route+'_shown.png'
            source = destination/label
            image = Image.open(source).convert('RGB')
            metrics = case['routes'][route]
            boxes = [row[kind]['bounds'] for row in metrics.values()
                     for kind in ('declared','observed') if row[kind]['bounds']]
            bounds = (max(0,min(box[0] for box in boxes)-60),
                      max(0,min(box[1] for box in boxes)-70),
                      min(image.width,max(box[2] for box in boxes)+60),
                      min(image.height,max(box[3] for box in boxes)+70))
            crop = image.crop(bounds)
            crop.thumbnail((590,390),Image.Resampling.NEAREST)
            panel = Image.new('RGB',(610,430),'white')
            panel.paste(crop,((610-crop.width)//2,35+(390-crop.height)//2))
            ImageDraw.Draw(panel).text((12,10),variant+' / '+route,fill='black')
            panels.append(panel)
        summary['captures'][variant] = item
    sheet = Image.new('RGB',(1830,860),'white')
    for index,panel in enumerate(panels):
        sheet.paste(panel,((index%3)*610,(index//3)*430))
    sheet.save(output/'review.png')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='ascii')
    return {'files':sum(1 for path in output.rglob('*') if path.is_file()),
            'bytes':sum(path.stat().st_size for path in output.rglob('*') if path.is_file())}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before',type=Path)
    parser.add_argument('after',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    print(json.dumps(pack(args.before,args.after,args.output)))
