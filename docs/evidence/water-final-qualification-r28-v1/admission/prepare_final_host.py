"""Freeze D launch inputs after reviewed disposable provisional admission."""
import argparse
import ast
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

WORK=Path(__file__).resolve().parent
ROOT=WORK.parents[2]
BRG=WORK.with_name('water-final-brg-v3')
STATIC=WORK.with_name('water-default-preflight-v1')
FINAL=WORK.with_name('water-default-final-v1')
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provisional-output',required=True,type=Path)
    args=parser.parse_args()
    assert not FINAL.exists()
    manifest_path=args.provisional_output/'qualification.json'
    receipt_path=args.provisional_output/'reviewed-host-receipt-v1.json'
    manifest=json.loads(manifest_path.read_bytes())
    receipt=json.loads(receipt_path.read_bytes())
    assert receipt['provisional_executed'] and receipt['shared_metadata_unchanged']
    assert manifest['stage']=='isolated_candidate' and manifest['gates']['default_path'] is False
    old=json.loads((BRG/'final-source-binding-v1.json').read_bytes())
    baseline=dict(old['source_sha256'],**old['auxiliary_sha256'])
    expected={name:sha(PROJECT/name) for name in baseline}
    differences={name:{'before':baseline[name],'after':value} for name,value in expected.items()
                 if value!=baseline[name]}
    assert set(differences)==set(METADATA)
    assert differences==receipt['actual_after_metadata_changes']
    assert sha(manifest_path)==receipt['manifest_sha256']
    static=json.loads((STATIC/'static-host-index-v1.json').read_bytes())
    assert all(sha(STATIC/name)==value for name,value in static['files_sha256'].items())
    FINAL.mkdir()
    host_names=('guard_policy.py','modal_guard.py','launch_r25.py','start_assert_watch.py',
        'watch_handles.py','retire_helpers.py','scene_game.py','scene_policy.py','scene_restore.py',
        'resize_adapter.py','resize_background.py','observe_cold_default.py','flow_restore.py',
        'world_readback.py','scene_native_layout.py','calibration_host.py','source_provenance.py',
        'run_default.py','run_group.py')
    for name in host_names:
        raw=(STATIC/name).read_bytes()
        ast.parse(raw,filename=name)
        (FINAL/name).write_bytes(raw)
    source={name:expected[name] for name in old['source_sha256']}
    auxiliary={name:expected[name] for name in old['auxiliary_sha256']}
    source_digest=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode('ascii')).hexdigest()
    provenance=dict(old['source_provenance'])
    original=dict(provenance['base_source_sha256'],**provenance['base_auxiliary_sha256'])
    additions=set(expected)-set(original)
    deletions=set(original)-set(expected)
    modifications={name for name in set(original)&set(expected) if original[name]!=expected[name]}
    overlay=FINAL/'source-overlay-v1.zip'
    with zipfile.ZipFile(overlay,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(additions|modifications):
            archive.writestr(name,(PROJECT/name).read_bytes())
    provenance.update(added_files=sorted(additions),deleted_files=sorted(deletions),
        changed_files=sorted(modifications),overlay={'path':str(overlay),'sha256':sha(overlay),'bytes':overlay.stat().st_size},
        default_metadata_changes_vs_current_FA_BRG=sorted(differences),
        predecessor_binding_sha256=sha(BRG/'final-source-binding-v1.json'))
    qualification_path=PROJECT/METADATA[2]
    spec=importlib.util.spec_from_file_location('actual_disposable_D_qualification',qualification_path)
    qualification=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualification)
    assert qualification.PRODUCT_QUALIFIED and qualification.QUALIFICATION_STAGE=='isolated_candidate'
    assert all(qualification.GATES.values())
    assert qualification.QUALIFICATION_SHA256==sha(manifest_path)
    assert qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256==sha(PROJECT/METADATA[0])
    binding=dict(old,owner=PROJECT.name,project=str(PROJECT),source_sha256=source,auxiliary_sha256=auxiliary,
        source_contract_sha256=source_digest,source_provenance=provenance,
        prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        predecessor_binding_sha256=sha(BRG/'final-source-binding-v1.json'),predecessor_owner=old['owner'],
        owner_and_qualification_preserved_sha256={name:expected[name] for name in METADATA},
        owner_contract_sha256=sha(PROJECT/METADATA[0]),qualification_sha256=sha(qualification_path),
        old_qualification_implementation_sha256=qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256,
        owner_or_qualification_regenerated=True,
        current_shared_source_exactly_matches_frozen=False,
        shared_implementation_and_resources_match_FA_BRG=True,
        current_shared_vs_frozen_allowed_metadata_changes=list(METADATA),
        source_cohort_unchanged=False,production_implementation_cohort_unchanged=True,
        default_path_evidence=False,production_admission_performed=False,isolated_candidate_admission_performed=True,
        provisional_manifest={'path':str(manifest_path.resolve()),'sha256':sha(manifest_path)},
        provisional_host_receipt={'path':str(receipt_path.resolve()),'sha256':sha(receipt_path)},
        inherited_results_rewritten=False,resumed_stages_only=['camera','D'])
    write(FINAL/'final-source-binding-v1.json',binding)
    write(FINAL/'product-v2-launch-inputs.json',{key:binding[key] for key in
          ('schema','project','owner','source_sha256','source_contract_sha256','archive','source_provenance')})
    sys.path.insert(0,str(FINAL))
    from source_provenance import verify_source_provenance
    write(FINAL/'source-synthesis-v1.json',verify_source_provenance(binding))
    plan=json.loads((BRG/'plan-v3.json').read_bytes())
    for key in ('B','R','G','stage_mapping_preflight_sha256','known_host_fixes','no_repeat_of_F_or_A'):
        plan.pop(key,None)
    plan.update(owner=PROJECT.name,project=str(PROJECT),stage='reviewed_disposable_cold_default_D',
        source_contract_sha256=source_digest,overlay_archive=provenance['overlay'],
        created_at_utc=datetime.now(timezone.utc).isoformat(),estimated_minutes=[12,30],
        only_camera_and_D=True,profile_assignment_performed=False,
        source_cohort_unchanged=False,production_implementation_cohort_unchanged=True,
        current_FA_BRG_contract_not_relabeled=old['source_contract_sha256'],
        exact_metadata_changes_vs_FA_BRG=differences,
        static_host_index={'path':str(STATIC/'static-host-index-v1.json'),'sha256':sha(STATIC/'static-host-index-v1.json')},
        provisional_manifest_sha256=sha(manifest_path),provisional_host_receipt_sha256=sha(receipt_path),
        D={'routes':['editor','full','missing'],'cases':['source','pool','wet_oak_fence'],
           'controls':'all','frozen':False,'production_default':True,'extras':True,
           'profile_assignment_performed':False,'same_session_camera_required':True},
        predecessor_release_sha256=sha(BRG/'precise-release-audit-v1.json'))
    write(FINAL/'plan-v1.json',plan)
    write(FINAL/'stage-r25.json',{'schema':1,'owner':PROJECT.name,'plan_sha256':sha(FINAL/'plan-v1.json'),
          'formal_A_accepted':False,'manual_closures_added':0,'cold_default_D_only':True})
    old_hosts=json.loads((BRG/'prelaunch-host-binding-v1.json').read_bytes())
    names=[path.name for path in FINAL.iterdir() if path.is_file() and path.name!='final-source-binding-v1.json']
    write(FINAL/'prelaunch-host-binding-v1.json',{'schema':1,
          'source_binding_sha256':sha(FINAL/'final-source-binding-v1.json'),
          'host_sha256':{name:sha(FINAL/name) for name in names},
          'external_host_sha256':old_hosts['external_host_sha256'],
          'startup_contract_sha256':old_hosts['startup_contract_sha256'],
          'static_host_index_sha256':sha(STATIC/'static-host-index-v1.json'),
          'MC_started':False,'frozen_at_utc':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'prepared':True,'MC_started':False,'work':str(FINAL),
                      'plan_sha256':sha(FINAL/'plan-v1.json'),
                      'host_binding_sha256':sha(FINAL/'prelaunch-host-binding-v1.json'),
                      'source_contract_sha256':source_digest,'metadata_changes_only':differences,
                      'host_files_copied_unchanged':len(host_names)},indent=2))


if __name__=='__main__':
    main()
