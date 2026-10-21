"""Explicit versioned host-only seam extractor; frozen project bytes stay intact."""
import hashlib
import importlib.util
import json
from pathlib import Path

WORK=Path(__file__).resolve().parent
CANDIDATE=WORK.with_name('water-camera-extractor-seam-candidate-v1')/'candidate_extractor.py'
EXPECTED='3626da674b63219e8ea9094217ef1a6d9ec0de9b795dd42573c89d318a95225f'
VERSION='single_stone_actual_one_pixel_antialias_seam_v1'

SINGLE_STONE_CODE='''from modern_projection.projection.cell import foreground,background,actor_data
doc=s.editor.document
work=b.projection_work
model=b.projection_mesh[1] if b.projection_mesh else None
parts=b.context_models.get(model,())
ids=list(b.projection_entities.values())+([b.entity] if b.entity else [])
scales=[b.factory.CreateActorRender(b.entity).GetActorBlockGeometryScale(name) for name,origin,context in parts] if b.entity else []
def single_stone(document):
 return (document is not None and tuple(document.size)==(3,3,3) and len(document.blocks)==1
  and set(document.blocks)==set(((1,1,1),)) and foreground(document.get((1,1,1)))==('minecraft:stone',0)
  and background(document.get((1,1,1)))==('minecraft:air',0) and actor_data(document.get((1,1,1))) is None)
_result=json.dumps({'identity':sys._blueprint_qa_identity,'source_single_stone':single_stone(doc),
 'source_cells':[(pos,foreground(value),background(value)) for pos,value in sorted(doc.blocks.items())],
 'work_single_stone':work is not None and single_stone(work.document),
 'work_current':work is not None and work.ready and work.serial==b.projection_serial and work.document.blocks==doc.blocks,
 'projection_active':s.projection_active,'actor_count':len(ids),'actor_ids':ids,
 'geometry_parts':parts,'SDK_geometry_scales':scales,
 'SDK_camera_position':b.factory.CreateCamera(b.level).GetPosition(),
 'SDK_camera_rotation':b.factory.CreateCamera(b.level).GetCameraRotation()})
'''


def fixture_valid(value):
    return (value['identity']=='camera.calibration.stone' and value['source_single_stone']
        and value['work_single_stone'] and value['work_current'] and value['projection_active']
        and value['actor_count']==1 and bool(value['geometry_parts']) and
        len(value['SDK_geometry_scales'])==len(value['geometry_parts']) and
        all(scale is not None and len(scale)==3 and all(abs(axis-1.)<1e-9 for axis in scale)
            for scale in value['SDK_geometry_scales']))


def activate():
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()==EXPECTED
    import verify_camera_projection as tool
    spec=importlib.util.spec_from_file_location('versioned_water_camera_seam_v1',CANDIDATE)
    candidate=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    tool.stone_signal=candidate.stone_signal
    return {'schema':1,'version':VERSION,'candidate_path':str(CANDIDATE),
        'candidate_sha256':EXPECTED,'host_path':str(Path(__file__)),
        'host_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'project_source_bytes_modified':False,'new_calibration_host_evidence':True,
        'old_failed_report_revised':False,'production_qualification_modified':False,
        'expected_silhouette_used_to_build_mask':False}


def validate_report(path,activation):
    report=json.loads(Path(path).read_bytes())
    assert report['versioned_calibration_host']==activation,'Calibration extractor host differs'
    assert report['passed'] and report['completed'] and report['restored'] and not report['cleanup_errors']
    assert report['single_stone_fixture_observations']
    assert len(report['single_stone_fixture_observations'])==12
    assert all(fixture_valid(row['state']) for row in report['single_stone_fixture_observations'])
    return {'version':VERSION,'actual_fixture_observations':12,
        'camera_report_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
