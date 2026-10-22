"""Read cold D with explicitly activated same-session camera; no gate writes."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
FINAL=WORK.with_name('water-default-final-v1')
PROJECT=ROOT/'.runtime/projects/water-r28-default-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    assert not args.output.exists()
    spec=importlib.util.spec_from_file_location('approved_provisional_host',WORK/'qualify_provisional_v2.py')
    host=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    sys.path.insert(0,str(ROOT/'tools'))
    activation=host.activation()
    binding=json.loads((FINAL/'final-source-binding-v1.json').read_bytes())
    hosts=json.loads((FINAL/'prelaunch-host-binding-v1.json').read_bytes())
    camera_host=FINAL/'calibration_host.py'
    assert sha(camera_host)==hosts['host_sha256']['calibration_host.py']
    spec=importlib.util.spec_from_file_location('reviewed_D_calibration_host',camera_host)
    calibration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calibration)
    camera_activation=calibration.activate()
    camera_reference=calibration.validate_report(FINAL/'product-v2-camera-seam-v1.json',camera_activation)
    import qualify_water_product_r16 as q
    assert q.ROOT==ROOT
    assert Path(q.__file__).resolve()==ROOT/'tools/qualify_water_product_r16.py'
    before={name:sha(PROJECT/name) for name in binding['owner_and_qualification_preserved_sha256']}
    path=FINAL/'default-r28-d.json'
    contract=json.loads((PROJECT/q.RESOURCE).read_bytes())
    row,analysis=q.collect(path,PROJECT,contract,native_world_geometry=True,native_editor_gui=True)
    q.default_path(row,analysis)
    expected=dict(binding['source_sha256'],**binding['auxiliary_sha256'])
    assert all(sha(PROJECT/name)==value for name,value in expected.items())
    assert row['source_contract_sha256']==binding['source_contract_sha256']
    assert {name:sha(PROJECT/name) for name in before}==before
    profile=row['profile']
    result={'schema':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
            'passed_original_default_path_requirements':True,'source_contract_sha256':binding['source_contract_sha256'],
            'source_report':str(path),'source_report_sha256':sha(path),
            'source_binding_sha256':sha(FINAL/'final-source-binding-v1.json'),
            'original_qualifier_sha256':sha(Path(q.__file__)),
            'reviewed_FA_BRG_host_activation':activation,'reviewed_D_camera_activation':camera_activation,
            'reviewed_D_camera_reference':camera_reference,'production_default_requested':row['production_default_requested'],
            'profile':profile,'default_visibility':q.visible_rows(row,('source','pool','wet_oak_fence'),q.ROUTES),
            'exact_occupancy_remove_one_restore_four_passed':True,
            'failed_geometry':[key for key,value in analysis['geometry'].items() if not value['passed']],
            'failed_alpha':[key for key,value in analysis['alpha_controls'].items() if not value['passed']],
            'failed_transparency':[key for key,value in analysis['transparency'].items() if not value['passed']],
            'animation':analysis['animation'],'evidence_valid':analysis['evidence_valid'],
            'all_source_and_auxiliary_unchanged':True,'owner_and_gate_unchanged':True,
            'qualification_performed':False,'pixels_root_reviewed':False,
            'manual_closures_added':0,'MC_started':False,'host_sha256':sha(Path(__file__))}
    args.output.mkdir()
    for name,value in (('default-product-analysis.json',analysis),('summary.json',result)):
        with (args.output/name).open('x',encoding='ascii') as stream:
            json.dump(value,stream,indent=2,sort_keys=True)
            stream.write('\n')
    print(json.dumps({'passed':True,'output':str(args.output),'summary_sha256':sha(args.output/'summary.json'),
                      'failed_geometry':result['failed_geometry'],'evidence_valid':analysis['evidence_valid']},indent=2))


if __name__=='__main__':
    main()
