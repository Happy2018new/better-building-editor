"""Attach-only attribution probe. --plan-only imports no game transports."""
import argparse
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import trial_fixtures_v1 as fixtures
import trial_payloads_v3 as payloads
import phase_transport_v5 as phase_transport
import native_receipts_v2 as native_receipts
import session_reader_v3 as session_reader
sys.path.insert(0,str(HERE/'fixed-water-v1'))
import fixed_water_receipts_v1 as water_receipts
import independent_audit_v1 as independent

CAPTURE_SHA='cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
DEADLINE=datetime(2026,10,22,23,15,tzinfo=timezone.utc)
BOUNDARY_START_CUTOFF=datetime(2026,10,22,23,0,tzinfo=timezone.utc)
RESTORE_TARGET=datetime(2026,10,22,23,30,tzinfo=timezone.utc)
FIXTURE_ORDER=fixtures.NAMES
MINIMUM_START_SECONDS={name:(1500 if name=='flat-boundary' else 600) for name in FIXTURE_ORDER}
HELPERS=('_mark_floor_support','_mark_palette_floor_support','_hidden_neighbor')
LOCAL_INPUTS=('trial_capture_v7_fixed_water.py','fixed-water-v1/water_setter_observer.py','fixed-water-v1/test_water_observer_py2.py','fixed-water-v1/fixed_water_receipts_v1.py','fixed-water-v1/water_resource_mapping_v2.py','fixed-water-v1/shader-change-manifest-v1.json','phase_transport_v5.py','test_phase_transport_v5.py','deployed-IPCSystem-v4.py','trial_fixtures_v1.py','trial_payloads_v3.py',
 'independent_audit_v1.py','observer_client_v3.py','source-binding-v2.json',
 'candidate-drop-direct-only/render_context.py','candidate_trace_v2.py','offline_verify_v2.py',
 'native_receipts_v2.py','session_reader_v3.py','test_native_controls_v2.py',
 'test_native_controls_v3.py','test_retirement_v3.py')
HOST_INPUTS=('tools/diagnose_concrete_color_r23.py','tools/verify_debug_blueprints.py',
 'tools/verify_debug_visuals.py','tools/verify_sign_visuals.py',
 'tools/verify_shulker_orientations.py','tools/capture_native_window.py',
 'tools/census_intrinsic_glint_ui_r21.py',
 '.agents/skills/pyreact-debugging/scripts/_session.py',
 '.agents/skills/pyreact-debugging/scripts/mcdk.py',
 '.runtime/round-20261022/concrete-support-v3-runtime/lifecycle.py',
 '.runtime/round-20261022/wire-atomic-watcher-v10/watch_owned_disabled_skin_assert_r27_v10.py',
 '.runtime/round-20261022/wire-atomic-watcher-v10/windows_manifest_reader.py',
 '.runtime/round-20261022/wire-atomic-watcher-v10/status_io.py')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_bytes((json.dumps(value,ensure_ascii=True,indent=2)+'\n').encode('ascii'))


def within_here(path):
    path=path.resolve()
    assert path.is_relative_to(HERE) and path!=HERE,'Output must be inside the private trial directory'
    return path


def check_start_budget(name,now):
    assert name in FIXTURE_ORDER
    assert now<DEADLINE,'No new trial after diagnostic deadline'
    if name=='flat-boundary':
        assert now<BOUNDARY_START_CUTOFF,'No new boundary trial at/after 07:00 CST'
    assert now+timedelta(seconds=MINIMUM_START_SECONDS[name])<=DEADLINE,'Insufficient remaining measured diagnostic budget; stop without starting fixture'


def plan():
    source=json.loads((HERE/'source-binding-v2.json').read_bytes())
    return {'schema':'wire-r28-private-fixed-water-v2-mapping-status-mutex-game-crc32-host-SHA256',
     'runtime_calls':0,'starts_game':False,'writes_production':False,'world_writes':False,
     'candidate_qualified':False,'manual_closures':0,'helpers':HELPERS,
     'local_inputs':[{'path':name,'sha256':sha(HERE/name)} for name in LOCAL_INPUTS],
     'host_inputs':[{'path':name,'sha256':sha(ROOT/name)} for name in HOST_INPUTS],
     'sources':source,'capture_executable_sha256':CAPTURE_SHA,
     'hard_deadline_utc':DEADLINE.isoformat(),
     'boundary_start_before_utc':BOUNDARY_START_CUTOFF.isoformat(),
     'restoration_target_utc':RESTORE_TARGET.isoformat(),
     'fixture_order':FIXTURE_ORDER,'extended_fixture_maximum':7,
     'minimum_start_seconds':MINIMUM_START_SECONDS,
     'timing_basis':'Extra independent bounded water receipts require 600s per fixture. Previous actual fresh flat: 143.34s total / 4.42s restoring; prior boundary failed after 456.47s at 7 complete plus 82/111 chunks of phase8, restoring7.28s. These are observed inputs, not a guarantee. Reserve 300s flat/small negative, 420s ascending/descending, 1500s boundary.',
     'stop_policy':'Stop after any failure; no automatic restart. Start only if remaining time meets measured budget. No flat-boundary start at/after 07:00 CST; diagnostics stop 07:15 CST, target restored by 07:30 CST.',
     'sequence':['base','repeat','candidate','restored'],
     'phase_identity':'New Editor, Document, WorldProjection and work snapshot per phase; retained references prevent id reuse. Compare logical two layers, size, origin, profiles, camera.',
     'native_creation':'Require actual GetBlankBlockPalette/Deserialize/Serialize/Combine chains from audited original geometry frames and both full/spare prepared paths before captures.',
     'reviewed_reader_sha256':session_reader.READER_SHA,'reviewed_watcher_sha256':session_reader.WATCHER_SHA,
     'reviewed_status_io_sha256':session_reader.STATUS_IO_SHA,
     'sentinel':{'fixture':'flat-interior','samples':[['opaque','top'],['opaque','grazing'],['default','top']],
       'stop':'Any unstable baseline mask/pixel, absent actor signal, changed candidate wire mask/pixel, source/camera/resource/assertion failure stops the trial immediately.'},
     'fixtures':[fixtures.fixture(name) for name in FIXTURE_ORDER],
     'extended_requires':'Root review artifact of completed/restored sentinel, explicitly approving original screenshots for wire shape and thickness.',
     'restoration':'Stop projection, original helper objects, observer, camera, visual/document/workspace, preview settle, original cache maps, independent helper/geometry/profile/cache audit.',
     'retirement_receipt':'At most twelve bounded phase keys and 4096 records; return counts and exact restored factory identities, compare every exported phase record. No repeated full native payload.',
     'phase_transport':{'original_complete_JSON':True,'chunk_bytes':262144,'max_phase_bytes_inclusive':134217728,'ordered_length_game_CRC32_required':True,'host_SHA256_explicitly_derived':True,'game_crc32_preflight_before_mutation':True,'no_native_record_or_field_removed':True},
     'flat_max_elapsed_seconds':900,
     'native_resource_boundary':'Python cache maps restored; unique native diagnostic geometry is reclaimed by later ordinary owned-process stop, which this attach-only tool does not perform.',
     'limits':['Red mask/pixel equality is a conservative sentinel, not final mesh/thickness acceptance.',
       'Palette observer bytes unchanged. Separate water receipts cover forwarded native FreeModel/uniform calls; successful setters are acknowledgements, not native readback.',
       'No product integration, no final cold-source acceptance, no manual issue closure.']}


def host_wires(value):
    if isinstance(value,dict):
        if value.get('codec')=='cell.freeze-repr-utf8-base64':
            raw=base64.b64decode(value['base64'],validate=True)
            assert len(raw)==value['bytes'] and b'IntegerBuffer object at' not in raw
            value['host_sha256']=hashlib.sha256(raw).hexdigest()
        else:
            for child in value.values():host_wires(child)
    elif isinstance(value,list):
        for child in value:host_wires(child)


def runtime_matches(project,manifest_path):
    manifest=json.loads(manifest_path.read_bytes())
    expected={row['path']:row['sha256'] for row in manifest['source_files']}
    assert len(expected)==len(manifest['source_files'])
    actual={path.relative_to(project).as_posix():sha(path)
      for name in ('behavior_pack','resource_pack') for path in (project/name).rglob('*')
      if path.is_file() and path.suffix not in ('.pyc','.pyo') and '__pycache__' not in path.parts}
    actual['.mcdev.json']=sha(project/'.mcdev.json')
    assert actual==expected,'Exact frozen base runtime source mismatch'
    for row in json.loads((HERE/'source-binding-v2.json').read_bytes())['rows']:
        assert actual[row['path']]==row['sha256'],'Trial base dependency mismatch: '+row['path']
    return sha(manifest_path)


def validate_retirement(receipt,folder,report):
    assert receipt['schema']=='wire-native-retirement-v3'
    assert all(receipt[key] is True for key in ('retired','factory_restored','observer_removed','module_removed'))
    assert 'records' not in receipt and len(json.dumps(receipt).encode('ascii'))<=8192
    installed=report['observer_install']
    assert installed['installed'] and installed['record_count']==0
    assert receipt['original_factory_id']==receipt['restored_factory_id']==installed['original_factory_id']
    assert receipt['installed_factory_id']==installed['installed_factory_id']
    expected={};total=0;files=[]
    for path in sorted(folder.glob('phase-*-native.json')):
        snapshot=json.loads(path.read_bytes());key=snapshot['phase_key']
        assert key not in expected,'Repeated exported phase key'
        counts={'CreatePalette':0,'Deserialize':0,'Combine':0}
        for record in snapshot['records']:
            assert record['phase_key']==key
            counts[record['phase']]+=1;total+=1
        expected[key]=counts
        files.append({'path':path.name,'sha256':sha(path),'records':len(snapshot['records'])})
    assert expected==receipt['phase_counts'] and total==receipt['record_count'],'Retired native count differs from exhaustive phase exports'
    return {'verified':True,'all_phase_exports_exhaustive':True,'record_count':total,'phase_count':len(expected),
      'phase_files':files,'receipt_bytes':len(json.dumps(receipt).encode('ascii')),'factory_restored_same_object':True}


def run(args,frozen):
    # Nothing above this boundary resolves a session, imports a transport, or calls MC.
    sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.agents/skills/pyreact-debugging/scripts'),
      str(ROOT/'.runtime/round-20261022/concrete-support-v3-runtime')]
    import lifecycle
    import diagnose_concrete_color_r23 as full
    from _session import process_identity
    from verify_debug_blueprints import Client,CLIENT,INSTALL_PROBE,RESTORE
    from verify_debug_visuals import (SAVE_VISUAL,PROJECTION_STATUS,PROJECTION_SOURCE,
      projection_source_matches,camera_restore_code)
    from verify_sign_visuals import SignCheck
    from verify_shulker_orientations import wait_camera_pose
    from PIL import Image,ImageChops,ImageDraw

    check_start_budget(args.fixture,datetime.now(timezone.utc))
    assert args.session and args.owner and args.project and args.manifest and args.watch and args.watch_binding and args.capture_exe
    project=args.project.resolve(strict=True)
    manifest=args.manifest.resolve(strict=True)
    read_events=[]
    row=session_reader.load_session(args.session,args.owner,True,read_events)
    assert Path(row['project']).resolve()==project
    assert sha(args.capture_exe)==CAPTURE_SHA
    assert row['noactivation']['requested'] and row['noactivation']['window_noactivate']
    manifest_sha=runtime_matches(project,manifest)
    if args.fixture!='flat-interior':
        assert args.sentinel_review,'Extended fixtures are gated by root screenshot review'
        review=json.loads(args.sentinel_review.read_bytes())
        sentinel_path=Path(review['report']).resolve(strict=True)
        assert sha(sentinel_path)==review['report_sha256']
        sentinel=json.loads(sentinel_path.read_bytes())
        assert sentinel['completed'] and sentinel['restored'] and sentinel['fixture']=='flat-interior'
        assert sentinel['manifest_sha256']==manifest_sha and sentinel['plan_sha256']==sha(args.plan)
        assert review['wire_shape_approved'] is True and review['wire_thickness_approved'] is True
    folder=within_here(args.output)
    folder.mkdir(parents=True,exist_ok=False)
    os.environ.update(MCDEV_SESSION_FILE=row['session_file'],MCDEV_OWNER=row['owner'],
      MCDEV_MCP_URL=row['mcp_url'],MCDEV_GAME_PID=str(row['game_pid']),
      MCDEV_NATIVE_CAPTURE_EXE=str(args.capture_exe.resolve()))
    report={'completed':False,'restored':False,'fixture':args.fixture,'world_writes':False,
      'plan_sha256':sha(args.plan),'manifest_sha256':manifest_sha,'samples':[],
      'manual_closures':0,'GPU_qualified':False,'cleanup_errors':[],
      'native_resources_reclaimed':False,'host_inputs':[],'read_events':read_events}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name and Path(name).is_file() and Path(name).resolve().is_relative_to(ROOT):
            report['host_inputs'].append({'path':str(Path(name).resolve()),'sha256':sha(Path(name))})
    gate={'binding':{key:row[key] for key in ('id','owner','project','session_file',
      'game_pid','game_identity','mcdk_pid','mcdk_identity')},'restore_mode':False,
      'boundaries':[],'RPCs':[],'captures':[]}
    previous={}
    trial_started=time.monotonic()

    def save():
        write(folder/'report.json',report);write(folder/'gate.json',gate)

    def boundary(phase):
        current=session_reader.load_session(row['session_file'],row['owner'],True,read_events)
        assert all(current[key]==row[key] for key in gate['binding'])
        sample=lifecycle.snapshot(current)
        sample.update(phase=phase,restoring=gate['restore_mode'])
        gate['boundaries'].append(sample);save()
        if gate['restore_mode']:return
        assert args.fixture!='flat-interior' or time.monotonic()-trial_started<900,'Flat exceeded fifteen minute budget; restore and stop'
        assert datetime.now(timezone.utc)<DEADLINE,'Hard diagnostic deadline; restore'
        assert sample['memory']['commit_available_bytes']>=6*1024**3
        for name in ('game','mcdk'):
            handles=sample[name]['handles']
            assert handles is not None and handles<250000
            assert name not in previous or handles-previous[name]<10000
            previous[name]=handles
        binding=session_reader.read_json(args.watch_binding,read_events)
        assert binding['watcher_sha256']==session_reader.WATCHER_SHA and binding['reader_sha256']==session_reader.READER_SHA
        assert binding['status_io_sha256']==session_reader.STATUS_IO_SHA
        assert Path(binding['output']).resolve()==args.watch.parent.resolve()
        assert process_identity(binding['watcher_pid'])==binding['watcher_identity']
        watch=session_reader.read_status_json(args.watch,read_events)
        assert watch['owners']==[row['owner']]
        assert not watch['errors'] and not watch['other_assertions'],watch
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(watch['checked_at'])).total_seconds()
        assert 0<=age<60,'Assertion watcher stale'

    class Check(SignCheck):
        def run(self,code):
            boundary('rpc')
            number=len(gate['RPCs'])+1
            raw=(CLIENT+code).encode('utf8')
            (folder/('rpc-%04d.py'%number)).write_bytes(raw)
            entry={'number':number,'sha256':hashlib.sha256(raw).hexdigest(),'restoring':gate['restore_mode']}
            gate['RPCs'].append(entry);save()
            try:
                result=super().run(code);host_wires(result)
                write(folder/('rpc-%04d-result.json'%number),result)
                entry['acknowledged']=True
                return result
            except Exception as error:
                entry['error']='%s: %s'%(type(error).__name__,error);raise
            finally:save()
        def capture(self,label,tree=None):
            boundary('capture:'+label)
            before=water.snapshot(self,label+':before')
            result=super().capture(label,tree)
            after=water.snapshot(self,label+':after')
            result['water_receipts']={'before':before,'after':after}
            assert result['capture']['window']['pid']==row['game_pid']
            gate['captures'].append({'label':label,'record':result});save()
            return result

    def wire_metric(shown,hidden,screen,label):
        with Image.open(shown['path']) as first,Image.open(hidden['path']) as second:
            first,second=first.convert('RGB'),second.convert('RGB')
        assert first.size==second.size
        points=screen['regions']['wire']
        assert all(point['isInScreen'] for point in points)
        xs,ys=[p['screenX'] for p in points],[p['screenY'] for p in points]
        box=(int(min(xs))-1,int(min(ys))-1,int(max(xs))+2,int(max(ys))+2)
        assert 0<=box[0]<box[2]<=first.width and 0<=box[1]<box[3]<=first.height
        a,b=first.crop(box),second.crop(box)
        pixels=[]
        for (red,green,blue),other in zip(a.getdata(),b.getdata()):
            pixels.append(255 if red>48 and red>green*1.5 and red>blue*1.5
              and max(abs(red-other[0]),abs(green-other[1]),abs(blue-other[2]))>12 else 0)
        mask=Image.new('L',a.size);mask.putdata(pixels)
        assert mask.histogram()[255]>=16,'Absent opaque red-wire contribution; stop'
        masked=ImageChops.multiply(a,mask.convert('RGB'))
        path=folder/(label+'_wire-mask.png');mask.save(path)
        roi_path=folder/(label+'_wire-roi.png');a.save(roi_path)
        return {'box':box,'wire_pixels':mask.histogram()[255],
          'mask_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),
          'wire_rgb_sha256':hashlib.sha256(masked.tobytes()).hexdigest(),
          'mask':full.image_record(path),'roi':full.image_record(roi_path)}

    audit=installed=visual=observed=hook=False
    water=water_receipts.WaterReceiptSink(folder/'water-receipts',HERE/'fixed-water-v1/water_setter_observer.py')
    with Client(timeout=30) as client:
        check=Check(client,folder/'report.json',60,native_resolution=True,background_only=True,
          native_capture_helper=ROOT/'tools/capture_native_window.py')
        try:
            report['transport_preflight']=check.run(phase_transport.PREFLIGHT)
            assert report['transport_preflight']['crc32']=='cbf43926'
            check.run("assert not any(hasattr(sys,name) for name in ('_books_wire_independent','_books_wire_hook','_books_wire_observer_module','_books_wire_observer','_blueprint_qa_saved','_blueprint_visual_saved','_concrete_color_r23'))\n_result=True")
            audit=True;report['audit_begin']=check.run(independent.BEGIN+payloads.AUDIT_EXTRA_BEGIN)
            installed=True;check.run(INSTALL_PROBE)
            visual=True;check.run(SAVE_VISUAL)
            hook=True;check.run(payloads.HOOK_INSTALL%(base64.b64encode((HERE/'candidate-drop-direct-only/render_context.py').read_bytes()).decode('ascii'),base64.b64encode((HERE/'candidate_trace_v2.py').read_bytes()).decode('ascii')))
            observed=True;report['observer_install']=check.run(payloads.OBSERVER_INSTALL%base64.b64encode((HERE/'observer_client_v3.py').read_bytes()).decode('ascii'))
            report['water_observer_install']=water.install(check)
            report['profile']=check.run(payloads.PROFILE)
            from projection.block_registry import fingerprint
            report['setup']=check.run(full.BEGIN%fingerprint())
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('workspace closed',lambda value:not value['open'] and not value['transition'],check.navigation)
            item=fixtures.fixture(args.fixture)
            physical_focus=tuple(item['focus'][i]+item['origin_shift'][i] for i in range(3))
            points={'wire':[tuple(point[i]+item['origin_shift'][i] for i in range(3)) for point in item['wire_bounds_points']]}
            points.update((name,[tuple(point[i]+item['origin_shift'][i] for i in range(3)) for point in values])
              for name,values in item['color_regions'].items())
            logical_reference=None
            seen_objects=set();seen_serials=set();seen_palette_ids=set()
            for opacity_name,pose_name in (('opaque','top'),('opaque','grazing'),('default','top')):
                opacity=1. if opacity_name=='opaque' else full.default_opacity(project)
                pose=check.run(full.CAMERA%(physical_focus,item['poses'][pose_name]));wait_camera_pose(check,pose)
                fixed_screen=baseline=None
                for mode in ('base','repeat','candidate','restored'):
                    check.run('b.stop_projection()\n_result=True')
                    check.wait('projection stopped',lambda value:not value['active'] and not value['preparing'] and value['actors']==0,lambda:check.run(PROJECTION_STATUS))
                    selected=check.run(payloads.MODE%mode)
                    phase_key='%s:%s:%s:%s'%(item['id'],opacity_name,pose_name,mode)
                    expected=check.run(payloads.LOAD%(item,opacity,phase_key))
                    if logical_reference is None:logical_reference=expected
                    assert all(expected[key]==logical_reference[key] for key in ('fixture','logical_document','origin','size','profile_id'))
                    object_ids={expected[key] for key in ('editor_id','document_id','work_id','work_document_id')}
                    assert len(object_ids)==4 and not object_ids.intersection(seen_objects),'Phase object was reused'
                    assert expected['serial'] not in seen_serials,'WorldProjection serial was reused'
                    seen_objects.update(object_ids);seen_serials.add(expected['serial'])
                    check.wait('projection ready',full.ready,lambda:check.run(PROJECTION_STATUS))
                    source=check.run(PROJECTION_SOURCE)
                    assert projection_source_matches(source,source) and not source['missing']
                    assert all(source[key]==expected[key] for key in ('fixture','editor_id','document_id','nonce'))
                    snapshot=phase_transport.collect(check,payloads.READ_PHASE,folder,len(report['samples'])+1,phase_key,host_wires)
                    creation=native_receipts.validate_phase(snapshot,expected,selected['helper_ids'],report['audit_begin']['geometry_function_id'],seen_palette_ids)
                    write(folder/('phase-%02d-native.json'%(len(report['samples'])+1)),snapshot)
                    state=check.run(full.STATE)
                    assert state['document_preserved'] and state['snapshot_preserved']
                    assert check.run(payloads.PROFILE)==report['profile']
                    time.sleep(.35)
                    screen=check.run(full.SCREEN%(points,))
                    if fixed_screen is None:fixed_screen=screen
                    assert full.screen_matches(screen,fixed_screen),'Fixed screen ROI moved'
                    label='%s_%s_%s'%(opacity_name,pose_name,mode)
                    entry={'label':label,'mode':mode,'source':source,'state':state,'screen':screen,'expected':expected,'helper_selection':selected,'native_creation':creation}
                    report['samples'].append(entry);save()
                    shown=check.capture(label+'_shown');entry['shown']=shown;save()
                    try:
                        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
                        time.sleep(.35)
                        hidden=check.capture(label+'_hidden');entry['hidden']=hidden;save()
                    finally:check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
                    assert check.run(full.STATE)==state,'State moved during shown/hidden capture'
                    assert projection_source_matches(check.run(PROJECTION_SOURCE),source)
                    if opacity_name=='opaque':
                        metric=wire_metric(shown,hidden,screen,label);entry['wire']=metric;save()
                        if baseline is None:baseline=metric
                        else:
                            assert all(metric[key]==baseline[key] for key in ('box','wire_pixels','mask_sha256','wire_rgb_sha256')),'Wire contribution changed: '+label
                    if pose_name=='top':
                        with Image.open(shown['path']) as a,Image.open(hidden['path']) as b_image:
                            color_screen={'regions':{name:values for name,values in screen['regions'].items() if name!='wire'},'screen_size':screen['screen_size']}
                            entry['colors']=full.region_metrics(a.convert('RGB'),b_image.convert('RGB'),full.masks_for_regions(a.size,color_screen))
                        assert all(value['actor_signal_pixels_above_12']>=16 for value in entry['colors'].values())
                    entry['completed']=True;save()
            report['completed']=True
        except Exception as error:
            report['error']='%s: %s'%(type(error).__name__,error);save();raise
        finally:
            gate['restore_mode']=True;save()
            actions=[('stop_projection','b.stop_projection()\n_result=True')]
            if water.install_attempted:actions.append(('water_observer',None))
            if hook:actions.append(('original_helpers',payloads.HOOK_RETIRE))
            if observed:actions.append(('observer',payloads.OBSERVER_RETIRE))
            if visual:actions.extend((('camera',camera_restore_code(False)),('visual',"saved=sys._blueprint_visual_saved\ns.origin=saved['origin']\ns.opacity=saved['opacity']\ns.projection_missing=saved['missing']\ns.projection_outline=saved['outline']\ndel sys._blueprint_visual_saved\n_result=True")))
            if installed:actions.extend((('workspace_state',"_result=sys._blueprint_qa_saved['workspace']"),('document',RESTORE)))
            actions.append(('diagnostic_marker',"if hasattr(sys,'_concrete_color_r23'):del sys._concrete_color_r23\n_result=True"))
            was_open=False
            for label,code in actions:
                try:
                    if label=='water_observer':
                        report['water_retirement']=water.retire(check);save()
                        assert report['water_retirement']['passed'],report['water_retirement']['errors']
                        from water_resource_mapping_v2 import verify_mapping
                        report['water_mapping']=verify_mapping(project,folder/'water-receipts',args.fixture);save()
                        continue
                    marker={'original_helpers':'_books_wire_hook','observer':'_books_wire_observer_module',
                      'camera':'_blueprint_visual_saved','visual':'_blueprint_visual_saved',
                      'workspace_state':'_blueprint_qa_saved','document':'_blueprint_qa_saved'}.get(label)
                    if marker:code="if hasattr(sys,%r):\n"%marker+'\n'.join(' '+line for line in code.splitlines())+"\nelse:_result={'skipped_missing_marker':True}"
                    result=check.run(code)
                    if label=='workspace_state' and isinstance(result,bool):was_open=result
                    if label=='observer':
                        write(folder/'observer-retirement.json',result)
                        report['observer_retirement']=validate_retirement(result,folder,report);save()
                except Exception as error:report['cleanup_errors'].append({'step':label,'error':'%s: %s'%(type(error).__name__,error)})
            if installed:
                try:check.run('owner.open_workspace()\n_result=True' if was_open else 'if navigator.top is not None:navigator.pop()\n_result=True')
                except Exception as error:report['cleanup_errors'].append({'step':'workspace','error':str(error)})
            if audit:
                try:
                    check.wait('restore preview ready',lambda value:value['ready'],lambda:check.run("_result=json.dumps({'ready':s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty and not navigator.is_transitioning})"))
                    check.run(payloads.CACHE_RESTORE)
                    result=check.run(independent.CHECK+payloads.AUDIT_EXTRA_CHECK)
                    report['independent_audit']=result;save()
                    assert result['restored'],result
                    check.run("del sys._books_wire_independent\n_result=True")
                except Exception as error:report['cleanup_errors'].append({'step':'independent_audit','error':'%s: %s'%(type(error).__name__,error)})
            try:
                runtime_matches(project,manifest)
                assert all(sha(Path(value['path']))==value['sha256'] for value in report['host_inputs'])
                assert json.loads(json.dumps(plan()))==json.loads(json.dumps(frozen)),'Frozen trial inputs changed during the run'
                assert sha(args.capture_exe)==CAPTURE_SHA
                report['runtime_and_host_unchanged']=True
            except Exception as error:report['cleanup_errors'].append({'step':'source_unchanged','error':str(error)})
            report['restored']=audit and not report['cleanup_errors'];save()
            if report['cleanup_errors']:raise RuntimeError(report['cleanup_errors'])
    print(json.dumps({key:report[key] for key in ('completed','restored','fixture','manual_closures','GPU_qualified')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan-only',action='store_true');mode.add_argument('--run',action='store_true')
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--fixture',choices=FIXTURE_ORDER,default='flat-interior')
    parser.add_argument('--session');parser.add_argument('--owner')
    for name in ('project','manifest','watch','watch-binding','capture-exe','sentinel-review'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    frozen=plan()
    if args.plan_only:
        target=within_here(args.plan)
        assert not target.exists(),'Freeze plans are not overwritten'
        write(target,frozen)
        print(json.dumps({'plan':str(target),'sha256':sha(target),'runtime_calls':0}));return
    assert json.loads(args.plan.read_bytes())==json.loads(json.dumps(frozen)),'Frozen host inputs or plan changed'
    assert args.output,'Explicit private output is required'
    return run(args,frozen)


if __name__=='__main__':raise SystemExit(main())
