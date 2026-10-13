"""Capture packed uniform values and four-cell carriers in an owned background game."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import probe_liquid_pose_channel as base
from generate_liquid_uniform_fixture import identifier, TAG
from _session import load_session

GENERATE = '''saved=sys._liquid_pose_client
origin=tuple(saved['origin'])
name=%r
positions=%r
block=factory.CreateBlock(level)
raw=saved.get('uniform_source_raw')
if raw is None:
 source=block.GetBlockPaletteBetweenPos(origin,origin,False)
 raw=source.SerializeBlockPalette()
 saved['uniform_source_raw']=raw
assert tuple(raw['volume'])==(1,1,1) and not raw.get('actor')
assert len(raw['common'])==1 and all(indices==[0] for indices in raw['common'].values())
sx=max(pos[0] for pos in positions)+1
sy=max(pos[1] for pos in positions)+1
sz=max(pos[2] for pos in positions)+1
indices=sorted((y*sx+x)*sz+z for x,y,z in positions)
raw=dict(raw,volume=(sz,sx,sy),common=dict((key,indices) for key in raw['common']))
geometry=factory.CreateBlockGeometry(level)
paths=[]
for key in ('live','roundtrip'):
 palette=block.GetBlankBlockPalette()
 started=time.time()
 assert palette.DeserializeBlockPalette(raw)
 deserialize_seconds=time.time()-started
 assert palette.SerializeBlockPalette()==raw
 requested=name+'_'+key
 started=time.time()
 returned=geometry.CombineBlockPaletteToGeometry(palette,requested,0)
 assert returned==requested
 paths.append({'path':key,'requested':requested,'returned':returned,
               'deserialize_seconds':deserialize_seconds,'combine_seconds':time.time()-started})
saved['paths']=paths
if saved['entity']:
 api.GetSystem('ModernProjection','ModernProjectionClientSystem').DestroyClientEntity(saved['entity'])
saved['attached']=None
saved['entity']=api.GetSystem('ModernProjection','ModernProjectionClientSystem').CreateClientEntityByTypeStr(
 'modern_projection:anchor',origin,(0.,0.))
assert saved['entity']
_result=json.dumps({'paths':paths,'entity':saved['entity'],'volume':raw['volume'],
                   'common_indices':indices,'carrier_positions':positions,
                   'palette_source':'constructed_from_verified_native_single_cell'})
'''
CAMERA = '''origin=tuple(sys._liquid_pose_client['origin'])
target=tuple(origin[i]+%r[i] for i in range(3))
offset=%r
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=factory.CreateCamera(level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''
SET_UNIFORMS = '''saved=sys._liquid_pose_client
render=factory.CreateActorRender(saved['entity'])
values=%r
for group,value in values:
 assert render.SetEntityExtraUniforms(group,value)
_result=json.dumps({'entity':saved['entity'],'attached':saved['attached'],'uniforms':values})
'''

HEIGHT_CODES = ((0,255,1,254),(15,16,63,64),(127,128,254,255),(1,254,16,15))


class MemoryCounters(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
        'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]


def metrics(session_file, owner):
    session = load_session(session_file, owner, live=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE,ctypes.POINTER(MemoryCounters),wintypes.DWORD)
    handle = kernel.OpenProcess(0x0410,False,session['game_pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        memory = MemoryCounters()
        memory.cb = ctypes.sizeof(memory)
        count = wintypes.DWORD()
        if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(memory),memory.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        if not kernel.GetProcessHandleCount(handle,ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'time':time.time(),'game_pid':session['game_pid'],'game_identity':session['game_identity'],
                'working_set_bytes':memory.WorkingSetSize,'peak_working_set_bytes':memory.PeakWorkingSetSize,
                'private_commit_bytes':memory.PagefileUsage,'handles':count.value}
    finally:
        kernel.CloseHandle(handle)


def uniforms(mode, indices=(0,5,42,63), heights=HEIGHT_CODES, opacity=1., tint=16777215):
    packed = [value for h00,h10,h11,h01 in heights for value in (h00+256*h10,h11+256*h01)]
    return [(1,tuple(indices)),(2,tuple(packed[:4])),(3,tuple(packed[4:])),(4,(TAG,opacity,tint,mode))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--capture-exe',required=True,type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('The report must be fresh')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),MCDEV_OWNER=args.owner)
    session = load_session(args.session,args.owner,live=True)
    if Path(session['project']).resolve()!=base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema':1,'completed':False,'restored':False,'height_codes':HEIGHT_CODES,
              'native_input_format_accepted':False,'native_geometry_accepted':False,'accuracy_accepted':False,
              'animated_sampling_accepted':False,'production_memory_accepted':False,
              'source_sha256':{Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                               Path(base.__file__).name:hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest()},
              'metrics':[],'captures':{},'scope':'Packed uniform and carrier diagnostics only'}
    def snapshot(label):
        row=dict(metrics(args.session,args.owner),label=label)
        report['metrics'].append(row)
        base.write(args.output,report)
    def frame(label):
        output=args.output.with_name(args.output.stem+'_'+label+'.png')
        capture=base.capture(args.session,args.owner,output,args.capture_exe)
        report['captures'][label]=capture
        base.write(args.output,report)
        return capture
    with base.Client(timeout=45) as client:
        try:
            snapshot('before_fixture')
            report['environment']=base.run(client,base.ENVIRONMENT,True)
            report['world_setup']=base.run(client,base.PREPARE % identifier(),True)
            origin=tuple(report['world_setup']['origin'])
            report['near_player']=base.run(client,base.NEAR_PLAYER,True)
            expected=report['near_player']['after']
            deadline=time.monotonic()+10.
            while True:
                replica=base.run(client,base.REPLICATION % (origin,))
                ready=(replica['foot'] is not None and
                       all(abs(replica['foot'][i]-expected[i])<.1 for i in range(3)) and
                       any(row['name']==identifier() and row['indices']==[0] for row in replica['materials']))
                if ready or time.monotonic()>=deadline:
                    break
                time.sleep(.2)
            report['replication']=dict(replica,ready=ready)
            assert ready,replica
            base.run(client,base.SAVE % (origin,))
            time.sleep(3.)
            report['diagnostic_camera']=base.run(client,CAMERA % ((1.75,.5,.5),(0.,4.,6.)))
            time.sleep(.4)
            frame('world_source')
            report['diagnostic_geometry']=base.run(client,'import time\n'+GENERATE % (
                'liquid_uniform_diag_'+uuid.uuid4().hex,[(slot,0,0) for slot in range(4)]))
            snapshot('after_diagnostic_combine')
            base.run(client,base.CLEAR,True)
            time.sleep(.35)
            frame('empty')
            report['uniform_observations']={}
            for key in ('live','roundtrip'):
                base.run(client,base.ATTACH % (key,(-.5,0.,-.5),(TAG,1.,16777215.,2.),uniforms(2)[:3]))
                for mode,label in ((2,'heights_012'),(5,'height_3'),(3,'corner_phase'),(4,'cell_addresses')):
                    report['uniform_observations'][key+'_'+label]=base.run(client,SET_UNIFORMS % uniforms(mode))
                    time.sleep(.2)
                    frame(key+'_'+label)
            snapshot('after_diagnostic_captures')
            report['surface_geometry']=base.run(client,'import time\n'+GENERATE % (
                'liquid_uniform_surface_'+uuid.uuid4().hex,[(slot,kind,0) for slot in range(4) for kind in range(7)]))
            report['surface_camera']=base.run(client,CAMERA % ((1.,.5,1.),(3.,3.,5.)))
            source_uniforms=uniforms(0,indices=(0,1,4,5))
            for key in ('live','roundtrip'):
                report[key+'_attachment']=base.run(client,base.ATTACH % (
                    key,(-.5,0.,-.5),(TAG,1.,16777215.,0.),source_uniforms[:3]))
                time.sleep(.3)
                frame(key+'_native_tile')
                if key=='live':
                    report['same_attachment_before']=base.run(client,SET_UNIFORMS % source_uniforms)
                    time.sleep(1.1)
                    frame('live_native_tile_later')
                    report['same_attachment_after']=base.run(client,SET_UNIFORMS % source_uniforms)
            snapshot('after_surface_captures')
            report['completed']=True
        except Exception as error:
            report['error']='%s: %s' % (type(error).__name__,error)
            raise
        finally:
            cleanup_errors=[]
            restore_environment=('import sys\nif hasattr(sys,"_context_environment_saved"):\n'+
                                 ''.join(' '+line+'\n' for line in base.RESTORE_ENVIRONMENT.splitlines())+
                                 'else:\n _result=True\n')
            for key,code,server in (('client_cleanup',base.CLEAN_CLIENT,False),
                                    ('world_cleanup',base.CLEAN_WORLD,True),
                                    ('environment_cleanup',restore_environment,True)):
                try:
                    report[key]=base.run(client,code,server)
                except Exception as error:
                    report[key]=False
                    cleanup_errors.append({'step':key,'error':'%s: %s' % (type(error).__name__,error)})
            report['cleanup_errors']=cleanup_errors
            report['restored']=bool(report['client_cleanup'] and isinstance(report['world_cleanup'],dict) and
                                     report['world_cleanup'].get('restored') and report['environment_cleanup'])
            snapshot('after_cleanup')
            base.write(args.output,report)
            if cleanup_errors:
                raise RuntimeError('Native cleanup failed: '+repr(cleanup_errors))
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],
                      'output':str(args.output.resolve()),'metrics':report['metrics']}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
