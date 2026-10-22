"""Explicit reviewed-host activation around the shared, unchanged qualifier."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
BRG=WORK.with_name('water-final-brg-v3')
FA=WORK.with_name('water-final-matrix-v1')
PROJECT=ROOT/'.runtime/projects/water-r28-default-v1'
METADATA=('tools/data/liquid_product_owner_contract_v1.json',
          'behavior_pack/modern_projection/projection/liquid_product_owner_data.py',
          'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    with path.open('x',encoding='ascii') as stream:
        json.dump(value,stream,indent=2,sort_keys=True)
        stream.write('\n')


def activation():
    """Pin original external hosts and explicitly activate both camera cohorts."""
    binding=json.loads((BRG/'final-source-binding-v1.json').read_bytes())
    hosts=json.loads((BRG/'prelaunch-host-binding-v1.json').read_bytes())
    external={name:sha(ROOT/name) for name in hosts['external_host_sha256']}
    assert external==hosts['external_host_sha256']
    private_scripts=Path(binding['project'])/'.agents/skills/pyreact-debugging/scripts'
    sys.path.insert(0,str(private_scripts))
    sessions=[]
    for name in ('_session','_window'):
        module=importlib.import_module(name)
        path=Path(module.__file__).resolve()
        assert path.parent==private_scripts.resolve()
        relative=path.relative_to(Path(binding['project'])).as_posix()
        assert sha(path)==binding['source_sha256'][relative]
        sessions.append({'module':name,'path':str(path),'sha256':sha(path)})
    sys.path.remove(str(private_scripts))
    contract_path=ROOT/'.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json'
    assert sha(contract_path)==hosts['startup_contract_sha256']
    contract=json.loads(contract_path.read_bytes())
    assert all(sha(Path(name))==value for name,value in contract['sources'].items())
    assert sha(Path(contract['binary']['path']))==contract['binary']['sha256']
    candidate=Path(next(name for name in contract['sources']
                        if name.replace('\\','/').endswith('/capture_native_burst.py'))).parent
    sys.path.insert(0,str(candidate))
    validators=[]
    for name in ('capture_native_burst','capture_native_burst_deferred','capture_native_burst_startup'):
        module=importlib.import_module(name)
        path=Path(module.__file__).resolve()
        assert path.parent==candidate.resolve()
        validators.append({'module':name,'path':str(path),'sha256':sha(path)})
    sys.path.remove(str(candidate))
    cameras=[]
    for label,work in (('FA',FA),('BRG',BRG)):
        expected=json.loads((work/'prelaunch-host-binding-v1.json').read_bytes())
        path=work/'calibration_host.py'
        assert sha(path)==expected['host_sha256']['calibration_host.py']
        spec=importlib.util.spec_from_file_location('reviewed_'+label+'_calibration_host',path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        selected=module.activate()
        report=work/'product-v2-camera-seam-v1.json'
        reference=module.validate_report(report,selected)
        cameras.append({'cohort':label,'activation':selected,'reference':reference,
                        'report_path':str(report),'report_sha256':sha(report)})
    controls=ROOT/'.runtime/round-20261022/water-camera-extractor-seam-candidate-v1/controls-v1/report.json'
    assert sha(controls)=='418aa0076a15767dc4fd05fa40b5d8e6dd1cfbac706a144a71370dd6d701dc7d'
    record=json.loads(controls.read_bytes())
    assert record['passed'] and record['original_inputs_unchanged']
    assert record['actual_raw_positive_cases']==3 and record['synthetic_negative_cases']==9
    assert all(row['candidate_passed'] is row['expected_passed'] for row in record['rows'])
    assert all(sha(Path(name))==value for name,value in record['original_inputs_sha256'].items())
    return {'external_dependencies_checked':len(external),'private_session_modules':sessions,
            'startup_validator_modules':validators,'startup_contract_sha256':sha(contract_path),
            'calibration_cohorts':cameras,'seam_controls_sha256':sha(controls),
            'source_bytes_modified':False,'algorithms_thresholds_or_ROIs_changed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect-only',action='store_true')
    mode.add_argument('--execute-provisional',action='store_true')
    parser.add_argument('--root-review',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    assert not args.output.exists()
    os.environ['OPENBLAS_NUM_THREADS']='1'
    sys.path.insert(0,str(ROOT/'tools'))
    reviewed=activation()
    import qualify_water_product_r16 as qualifier
    import generate_liquid_product_owner_contract as generator
    for module,name in ((qualifier,'qualify_water_product_r16.py'),
                        (generator,'generate_liquid_product_owner_contract.py')):
        assert module.ROOT.resolve()==ROOT.resolve()
        assert Path(module.__file__).resolve()==ROOT/'tools'/name
    assert qualifier.generated is generator.generated
    prep_path=WORK/'disposable-preparation-v1.json'
    prep=json.loads(prep_path.read_bytes())
    assert Path(prep['project']).resolve()==PROJECT.resolve()
    assert sha(Path(qualifier.__file__))==prep['shared_qualifier_sha256']
    assert sha(Path(generator.__file__))==prep['shared_generator_sha256']
    owner,module=generator.generated()
    assert (PROJECT/METADATA[0]).read_bytes()==owner
    assert (PROJECT/METADATA[1]).read_bytes()==module
    baseline=json.loads((BRG/'final-source-binding-v1.json').read_bytes())
    expected=dict(baseline['source_sha256'],**baseline['auxiliary_sha256'])
    before={name:sha(PROJECT/name) for name in expected}
    differences={name:{'before':expected[name],'after':value} for name,value in before.items()
                 if value!=expected[name]}
    assert differences==prep['actual_changes_before_provisional']
    assert set(differences)==set(METADATA[:2])
    shared_before={name:sha(ROOT/name) for name in METADATA}
    draft=json.loads((WORK/'root-scope-review-draft-v1.json').read_bytes())
    for record in draft['reports'].values():
        assert sha(Path(record['path']))==record['sha256']
    contract=json.loads((PROJECT/qualifier.RESOURCE).read_bytes())
    qualifier.verify_contract(contract,PROJECT,ROOT)
    for record in draft['reports'].values():
        qualifier.source_closure(PROJECT,json.loads(Path(record['path']).read_bytes()),contract)
    result={'schema':1,'mode':'inspect_only' if args.inspect_only else 'execute_provisional',
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'host_sha256':sha(Path(__file__)),
            'project':str(PROJECT),'preparation_sha256':sha(prep_path),
            'root_scope_draft_sha256':sha(WORK/'root-scope-review-draft-v1.json'),
            'shared_qualifier_path':str(Path(qualifier.__file__)),'shared_qualifier_ROOT':str(qualifier.ROOT),
            'shared_generator_path':str(Path(generator.__file__)),'shared_generator_ROOT':str(generator.ROOT),
            'shared_qualifier_sha256':sha(Path(qualifier.__file__)),
            'shared_generator_sha256':sha(Path(generator.__file__)),
            'reviewed_host_activation':reviewed,'all_seven_source_closures_passed':True,
            'actual_before_metadata_changes':differences,'MC_started':False,'RPC_dispatched':False,
            'manual_closures_added':0,'provisional_executed':False}
    if args.inspect_only:
        assert {name:sha(PROJECT/name) for name in expected}==before
        assert {name:sha(ROOT/name) for name in METADATA}==shared_before
        result.update(owner_or_qualification_changed=False,shared_metadata_unchanged=True)
        write(args.output,result)
        print(json.dumps({'inspected':True,'path':str(args.output),'sha256':sha(args.output)}))
        return
    assert args.root_review is not None,'Explicit root-reviewed scope and execution receipt required'
    review=json.loads(args.root_review.read_bytes())
    assert review['status']=='confirmed_by_root' and review['reviewer']=='/root'
    assert review['root_confirmation_required'] is False
    assert review['provisional_execution_authorized'] is True
    assert review['reviewed_wrapper_sha256']==sha(Path(__file__))
    assert review['disposable_preparation_sha256']==sha(prep_path)
    for key in ('accepted_scope','preserved_generic_geometry_failures','source_contract_sha256','reports',
                'required_shared_qualifier_sha256','required_shared_generator_sha256',
                'R_or_G_exact_per_case_geometry_accepted','old_failed_reports_regraded'):
        assert review[key]==draft[key],key
    inputs={name:Path(row['path']) for name,row in review['reports'].items()}
    official=argparse.Namespace(project=PROJECT,
        frozen_report=[inputs['F-editor'],inputs['F-full'],inputs['F-missing']],
        animated_report=inputs['A'],biome_report=inputs['B'],reverse_report=inputs['R'],gallery_report=inputs['G'],
        default_report=None,output=args.output,admit_candidate=True,accept_reviewed=True,
        native_world_geometry=True,native_editor_gui=True)
    manifest=qualifier.qualify(official)
    assert manifest['stage']=='isolated_candidate' and manifest['gates']['default_path'] is False
    assert all(value is True for name,value in manifest['gates'].items() if name!='default_path')
    assert {name:sha(ROOT/name) for name in METADATA}==shared_before
    after={name:sha(PROJECT/name) for name in expected}
    changed={name:{'before':expected[name],'after':value} for name,value in after.items() if value!=expected[name]}
    assert set(changed)==set(METADATA)
    assert all(before[name]==after[name] for name in expected if name!=METADATA[2])
    result.update(provisional_executed=True,shared_metadata_unchanged=True,
                  root_review_path=str(args.root_review),root_review_sha256=sha(args.root_review),
                  actual_after_metadata_changes=changed,manifest_sha256=sha(args.output/'qualification.json'),
                  manifest_default_path=False,shared_production_qualified=False)
    write(args.output/'reviewed-host-receipt-v1.json',result)
    print(json.dumps({'provisional':True,'output':str(args.output),
                      'manifest_sha256':sha(args.output/'qualification.json'),'only_three_metadata_changed':True,
                      'shared_metadata_unchanged':True,'MC_started':False}))


if __name__=='__main__':
    main()
