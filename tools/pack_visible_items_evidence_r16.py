"""Archive measured glint review pixels without duplicating full capture bursts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    path = path.resolve()
    return {'path':path.relative_to(ROOT).as_posix(), 'bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True,exist_ok=False)
    index = {'schema':1,'scope':'Compact review package; full paired captures remain in local source directories',
             'production_qualified':False,'sources':{},'raw_captures':{},'files':{}}
    for label,capture,analysis in (
            ('weak-baseline','.runtime/visible-items-r16-glint-zoom-v1',
             '.runtime/visible-items-r16-glint-zoom-v1-analysis-v2'),
            ('native-texture','.runtime/visible-items-r16-glint-zoom-v3',
             '.runtime/visible-items-r16-glint-zoom-v3-analysis')):
        report_path = ROOT/capture/'report.json'
        analysis_path = ROOT/analysis/'analysis.json'
        report = json.loads(report_path.read_bytes())
        result = json.loads(analysis_path.read_bytes())
        if result['source_sha256'] != record(report_path)['sha256'] or not result['evidence_valid']:
            raise ValueError('Review result does not belong to a valid measured source')
        directory = args.output/label
        directory.mkdir()
        index['sources'][label] = {'report':record(report_path),'analysis':record(analysis_path),
            'completed':report['completed'],'cleanup_errors':report['cleanup_errors'],
            'source_unchanged':report['source_unchanged'],
            'launch_sources_sha256':report['launch_sources_sha256'],
            'native_glint_accepted':result['native_closeup']['native_glint_accepted']}
        if index['sources'][label]['native_glint_accepted'] != (label=='native-texture'):
            raise ValueError('Weak baseline/new texture controls no longer have their expected outcomes')
        shutil.copy2(analysis_path,directory/'analysis.json')
        for path in (ROOT/analysis).glob('*-comparison.gif'):
            shutil.copy2(path,directory/path.name)
        rows = report['closeup']['captures']+report['closeup']['native_reference']['captures']
        for row in rows:
            image = Path(row['capture']['path'])
            actual = record(image)
            if actual['sha256'] != row['capture']['sha256']:
                raise ValueError('Measured capture changed after recording')
            included = row['label'] in ('editor_8','world_8','world_missing_8','native_8')
            receipt = image.with_suffix('.capture.json')
            index['raw_captures'][label+':'+row['label']] = dict(actual,included=included,
                receipt=record(receipt),capture_size=[row['capture']['width'],row['capture']['height']])
            if included:
                shutil.copy2(image,directory/image.name)
        outcome = {'schema':1,'completed':report['completed'],'cleanup_errors':report['cleanup_errors'],
            'resource_contract':report.get('resource_contract'),
            'launch_sources_sha256':report['launch_sources_sha256'],
            'source_unchanged':report['source_unchanged'], 'engine':report['engine'],
            'production_qualified':False,'native_glint_accepted':result['native_closeup']['native_glint_accepted'],
            'glint_visibility_comparison':result['native_closeup']['glint_visibility_comparison']}
        (directory/'outcome.json').write_text(json.dumps(outcome,indent=2)+'\n',encoding='ascii')
    compile_path = ROOT/'.runtime/item-icons-r16-shader-compile-v6.json'
    shutil.copy2(compile_path,args.output/'shader-compile.json')
    for path in sorted(args.output.rglob('*')):
        if path.is_file():
            index['files'][path.relative_to(args.output).as_posix()] = record(path)
    (args.output/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'files':len(index['files']),'bytes':sum(row['bytes'] for row in index['files'].values())}))


if __name__=='__main__':
    main()
