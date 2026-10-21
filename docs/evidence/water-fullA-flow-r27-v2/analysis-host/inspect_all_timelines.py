"""Summarize all requested raw timelines without fitting or dropping attempts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
HOST=WORK.with_name('water-merged-fullA-v2')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    output=args.output_root.resolve()
    output.mkdir(exist_ok=False)
    tool_path=WORK.with_name('water-next-A-workflow-v1')/'inspect_timeline.py'
    spec=importlib.util.spec_from_file_location('unchanged_timeline_inspector',tool_path)
    tool=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    source_path=HOST/'product-v2-a-v1.json'
    source_raw=source_path.read_bytes()
    source=json.loads(source_raw)
    plan=json.loads((HOST/'plan-v1.json').read_bytes())
    expected={route+'_'+case+'_wet' for route in plan['routes'] for case in plan['cases']}
    rows={}
    for label,burst in source.get('flow_bursts',{}).items():
        assert label in expected,label
        capture=burst['capture']
        item=capture.get('native_manifest_file')
        if not item:
            rows[label]={'raw_manifest_available':False,'original_capture_valid':capture.get('capture_valid')}
            continue
        path=Path(item['path'])
        raw=path.read_bytes()
        assert sha(raw)==item['sha256'] and len(raw)==item['bytes']
        native=json.loads(raw)
        assert native==capture['native_manifest']
        inspected=tool.inspect(native)
        inspected.update(manifest_path=str(path),manifest_sha256=sha(raw),
            inspector_sha256=sha(tool_path.read_bytes()))
        target=output/(label+'-timeline-v1.json')
        with target.open('x',encoding='ascii') as stream:json.dump(inspected,stream,indent=2)
        rows[label]={key:inspected[key] for key in ('attempts','valid_frames','fixed_measurement_ms',
            'manifest_capture_valid','manifest_temporal_complete','manifest_ok',
            'start_source_gap_ms','tail_source_gap_ms','largest_source_gap',
            'largest_worker_unobserved_interval','source_and_worker_maximum_same_pair',
            'source_gap_limit_ms','source_gap_exceedances')}
        rows[label].update(raw_manifest_available=True,manifest_sha256=sha(raw),timeline_sha256=sha(target.read_bytes()),
            rejected_attempts=[{'sequence':frame['sequence'],'capture_valid':frame['capture_valid'],
                'error':frame.get('error'),'png':frame.get('png')} for frame in native['frames'] if not frame['capture_valid']])
        assert path.read_bytes()==raw
    summary={'schema':1,'source_path':str(source_path),'source_sha256':sha(source_raw),
        'wrapper_sha256':sha(Path(__file__).read_bytes()),'inspector_sha256':sha(tool_path.read_bytes()),
        'rows':rows,'missing_requested_cells':sorted(expected-set(rows)),
        'all_15_raw_timelines_available':set(rows)==expected and all(row['raw_manifest_available'] for row in rows.values()),
        'scope':'Only original recorded QPC clocks; no root cause, trimming, fitting, ROI or threshold changes',
        'formal_A_accepted':False,'world_A_accepted':False,'source_release_qualification_granted':False,
        'manual_closures_added':0}
    with (output/'timeline-summary-v1.json').open('x',encoding='ascii') as stream:json.dump(summary,stream,indent=2)
    assert source_path.read_bytes()==source_raw
    print(json.dumps({'rows':len(rows),'missing_requested_cells':summary['missing_requested_cells'],
        'all_15_raw_timelines_available':summary['all_15_raw_timelines_available'],
        'summary_sha256':sha((output/'timeline-summary-v1.json').read_bytes())}))


if __name__=='__main__':
    main()
