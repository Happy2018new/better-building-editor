"""Run the reviewed frozen native controls with a predeclared cold UV marker."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from liquid_coordinate_markers import check_frozen_sources,fingerprint,write

if '--coordinate-plan' not in sys.argv:
    raise ValueError('A frozen coordinate plan is required')
index=sys.argv.index('--coordinate-plan')
PLAN=Path(sys.argv[index+1]).resolve()
del sys.argv[index:index+2]
FIXTURE=ROOT/'.runtime/capture_static_water_controls_r9.py'
spec=importlib.util.spec_from_file_location('coordinate_static_fixture',FIXTURE)
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ORIGINAL=base.frozen.execute_controls


def execute(harness,options,runtime_args,report):
    from _session import load_session
    from _window import background_guard_state
    import verify_wet_actor_visuals as wet
    plan=json.loads(PLAN.read_bytes())
    check_frozen_sources(plan)
    expected=[row['case'] for row in plan['geometry_sequences']]
    if options.case!=expected or options.cell_origin!=plan['origin']:
        raise ValueError('Cases or geometry origin changed after plan freeze')
    if plan['generator']!=fingerprint(ROOT/'tools/liquid_coordinate_markers.py'):
        raise ValueError('Frozen marker generator changed')
    for row in plan['assets']:
        if fingerprint(row['target'])['sha256']!=row['generated']['sha256']:
            raise ValueError('Cold installed bitmap changed')
    for reference in plan['geometry_analysis_sources']+[plan['geometry_analysis'],plan['geometry_contract']]:
        if fingerprint(reference['path'])['sha256']!=reference['sha256']:
            raise ValueError('Independent geometry evidence changed')
    sources=[]
    for sequence in plan['geometry_sequences']:
        document=base.source_document(sequence['case'])
        cells=[(tuple(options.cell_origin[i]+pos[i]-base.FOCUS[i] for i in range(3)),base.frozen.encode(value))
               for pos,value in document.blocks.items()]
        platform=wet.camera_side_platform(cells,tuple(plan['camera_offset']))
        source=base.fixture_plan(sequence['case'],tuple(options.cell_origin),platform)
        if json.loads(json.dumps(source['controls']))!=sequence['controls']:
            raise ValueError('Exact source controls differ from the independent geometry reference')
        sources.append(source)
    preflight=runtime_args.output.with_name(runtime_args.output.stem+'_preflight.json')
    write(preflight,{'created_at':datetime.now(timezone.utc).isoformat(),'plan':fingerprint(PLAN),
        'session_binding':report['session_binding'],'source_plans':sources,'runner':fingerprint(Path(__file__)),
        'fixture_adapter':fingerprint(FIXTURE),'calibration':report['calibration'],
        'native_uv_accepted':False,'production_accepted':False})
    report.update(coordinate_plan=fingerprint(PLAN),coordinate_preflight=fingerprint(preflight),
                  coordinate_runner=fingerprint(Path(__file__)),native_uv_accepted=False,production_accepted=False)
    harness.checkpoint()
    frame=harness.frame
    def guarded_frame(label,pose):
        if datetime.now(timezone.utc)>=datetime(2026,10,12,8,20,tzinfo=timezone.utc):
            raise RuntimeError('Native experiment deadline reached; restore')
        session=load_session(live=True)
        status=background_guard_state(session['game_pid'],Path(session['game_executable']).name)
        if not status['window_noactivate'] or not status['background_safe']:
            raise RuntimeError('Owned background contract changed')
        return frame(label,pose)
    harness.frame=guarded_frame
    try:return ORIGINAL(harness,options,runtime_args,report)
    finally:harness.frame=frame


base.frozen.execute_controls=execute
if __name__=='__main__':raise SystemExit(base.frozen.main())
