"""Replay original flow analyzer with the exact reviewed startup-v2 validator."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
HOST=WORK.with_name('water-merged-fullA-v2')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--partial-diagnostics',action='store_true')
    args=parser.parse_args()
    output=args.output_root.resolve()
    output.mkdir(exist_ok=False)
    os.environ['OPENBLAS_NUM_THREADS']='1'
    binding=json.loads((HOST/'final-source-binding-v1.json').read_bytes())
    project=Path(binding['project'])
    plan=json.loads((HOST/'plan-v1.json').read_bytes())
    contract_path=Path(plan['startup_host_contract']['path'])
    assert sha(contract_path)==plan['startup_host_contract']['sha256']
    contract=json.loads(contract_path.read_bytes())
    for name,expected in contract['sources'].items():
        assert sha(Path(name))==expected,name
    assert sha(Path(contract['binary']['path']))==contract['binary']['sha256']
    candidate=Path(next(name for name in contract['sources'] if name.endswith('/capture_native_burst.py') or name.endswith('\\capture_native_burst.py'))).parent
    sys.path.insert(0,str(project/'tools'))
    sys.path.insert(0,str(candidate))
    modules=[]
    for name in ('capture_native_burst','capture_native_burst_deferred','capture_native_burst_startup'):
        module=importlib.import_module(name)
        assert Path(module.__file__).resolve().parent==candidate.resolve()
        modules.append({'module':name,'path':str(Path(module.__file__).resolve()),'sha256':sha(Path(module.__file__))})
    sys.path.remove(str(candidate))
    sys.path.insert(0,str(HOST))
    import calibration_host
    calibration_activation=calibration_host.activate()
    calibration_binding=calibration_host.validate_report(HOST/'product-v2-camera-seam-v1.json',calibration_activation)
    analyzer=importlib.import_module('analyze_product_water_flow')
    assert Path(analyzer.__file__).resolve().parent==(project/'tools').resolve()
    for name in ('analyze_product_water_flow.py','analyze_product_water.py','water_capture_contract.py'):
        assert sha(project/'tools'/name)==binding['source_sha256']['tools/'+name],name
    source=HOST/'product-v2-a-v1.json'
    before=sha(source)
    receipt={'schema':1,'started_at':time.time(),'completed':False,
        'source_path':str(source),'source_sha256':before,
        'wrapper_sha256':sha(Path(__file__)),'analyzer_sha256':sha(Path(analyzer.__file__)),
        'startup_host_contract_sha256':sha(contract_path),'actual_validator_modules':modules,
        'versioned_calibration_host':calibration_activation,'new_calibration_source':calibration_binding,
        'original_analyzer_bytes_preserved':True,'partial_diagnostics':args.partial_diagnostics,
        'ROI_or_threshold_changes':False,'MC_started':False,'RPC_dispatched':False,
        'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0}
    try:
        result=analyzer.analyze_flow(source,args.partial_diagnostics)
        target=output/'flow-analysis-v1.json'
        with target.open('x',encoding='ascii') as stream:
            json.dump(result,stream,indent=2)
            stream.write('\n')
        receipt.update(completed=True,passed=result['passed'],analysis_sha256=sha(target),
            row_count=len(result['rows']))
        return 0 if result['passed'] else 1
    finally:
        receipt['source_sha256_after']=sha(source)
        receipt['source_unchanged']=receipt['source_sha256_after']==before
        receipt['elapsed_seconds']=time.time()-receipt['started_at']
        with (output/'analysis-host-receipt-v1.json').open('x',encoding='ascii') as stream:
            json.dump(receipt,stream,indent=2)
        print(json.dumps({key:receipt.get(key) for key in ('completed','passed','row_count','source_unchanged','elapsed_seconds')}))
        assert receipt['source_unchanged']


if __name__=='__main__':
    raise SystemExit(main())
