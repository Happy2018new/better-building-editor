"""Compare one native projected cube with a real cube at the same camera."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT,save
from audit_native_coordinates_r15 import LOAD,PROJECT,OCCUPY
from probe_banner_product_r16 import BannerAudit
from verify_debug_blueprints import CLIENT


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
    from projection.model import Document
    from projection.debug_blueprints import material
    doc=Document((8,8,8),name='Cyan seam isolated native comparison')
    doc.blocks[(3,2,3)]=material('cyan_concrete')
    audit=BannerAudit(args)
    report={'schema':1,'engine':'3.10.0.420447','completed':False,'restored':False,
            'captures':{},'rows':{},'cleanup_errors':[],'book_companion_enabled':False}
    occupied=()
    try:
        report['rows']['loaded']=audit.execute('load',LOAD % ('production',(),json.dumps(doc.to_data())))
        audit.settle()
        code=(PROJECT % False).replace('s.origin=(0,-57,0)',
            'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+3,int(foot[2]))')
        audit.execute('project',code);audit.settle(True)
        report['rows']['source']=audit.execute('source',CLIENT+'''_result=json.dumps({
'document':s.editor.document.to_data(),'origin':s.origin,'opacity':s.opacity,
'entity':b.entity,'mesh':b.projection_mesh,'book_profile':getattr(s,'book_profile',None) is not None,
'portal_profile':s.portal_profile.identity if s.portal_profile else None,
'uniforms':b.projection_shader.uniforms})
''')
        position=tuple(report['rows']['source']['origin'][index]+(3,2,3)[index] for index in range(3))
        for yaw in (45.,135.):
            import math
            point=(position[0]+.5,position[1]+.5,position[2]+.5)
            delta=(math.sin(math.radians(yaw))*3.,1.9,-math.cos(math.radians(yaw))*3.)
            camera=tuple(point[index]+delta[index] for index in range(3))
            camera_code=CLIENT+'''cam=b.factory.CreateCamera(b.level)
target=%r
position=%r
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''' % (point,camera)
            report['rows']['camera'+str(yaw)]=audit.execute('camera',camera_code)
            time.sleep(1.)
            label='projection_yaw'+str(yaw)
            report['captures'][label]=audit.frame(label)
        audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
        occupied=(position,)
        real_code=(OCCUPY % (occupied,False)).replace("'minecraft:stone'","'minecraft:cyan_concrete'")
        report['rows']['real_write']=audit.execute('real_write',real_code,False)
        time.sleep(10.)
        report['rows']['client_real']=audit.execute('client_real',CLIENT+
            '_result=json.dumps(b.factory.CreateBlockInfo(b.level).GetBlock(%r))' % (position,))
        if report['rows']['client_real']!=['minecraft:cyan_concrete',0]:
            raise ValueError('Real cyan control has not reached the client')
        for yaw in (45.,135.):
            import math
            point=(position[0]+.5,position[1]+.5,position[2]+.5)
            delta=(math.sin(math.radians(yaw))*3.,1.9,-math.cos(math.radians(yaw))*3.)
            camera=tuple(point[index]+delta[index] for index in range(3))
            code=CLIENT+'''cam=b.factory.CreateCamera(b.level)
target=%r
position=%r
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True
''' % (point,camera)
            audit.execute('same_camera',code);time.sleep(1.)
            label='real_yaw'+str(yaw)
            report['captures'][label]=audit.frame(label)
        report['rows']['world_restoration']=audit.execute('restore_world',OCCUPY % (occupied,True),False)
        occupied=()
        report['completed']=True
    finally:
        if occupied:
            try:audit.execute('restore_world_final',OCCUPY % (occupied,True),False)
            except Exception as error:report['cleanup_errors'].append(str(error))
        try:
            audit.execute('cleanup',CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''')
        except Exception as error:report['cleanup_errors'].append(str(error))
        report['restored']=not report['cleanup_errors']
        save(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],
                      'captures':len(report['captures'])}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--owner',required=True)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
