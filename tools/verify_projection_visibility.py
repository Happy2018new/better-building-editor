"""World projection angles, camera anchor stability and transform cost regression.

Run through run_live_check in an independent managed test world. No world block,
library, preferences or clipboard writes. Camera/player/draft restored in finally.
"""
import json
import sys
import time
from PIL import Image, ImageChops
import verify_ui as ui
from verify_font_share_polish import game
from verify_projection_outline import server
from verify_complete_projection import snapshot


def difference(a,b):
    first=Image.open(ui.OUT/(a+'.jpg')).convert('RGB')
    second=Image.open(ui.OUT/(b+'.jpg')).convert('RGB')
    delta=ImageChops.difference(first,second)
    w,h=delta.size
    data=delta.crop((w//8,h//5,w*7//8,h*4//5)).getdata()
    return sum(max(pixel)>35 for pixel in data)


def main():
    tag=sys.argv[1] if len(sys.argv)>1 else 'fixed'
    fixture=ui.OUT/'stage51_current_document.json'
    if fixture.exists():
        payload=fixture.read_text(encoding='utf8')
    else:
        sys.path.insert(0,str(ui.ROOT/'behavior_pack/HelloScript'))
        from projection.model import Document
        def inside(x,y,z):
            return ((x+.5-32.)/32.)**2+((y+.5-64.)/64.)**2+((z+.5-32.)/32.)**2<=1.
        blocks={}
        for y in range(128):
            for z in range(64):
                for x in range(64):
                    if inside(x,y,z) and any(not inside(x+dx,y+dy,z+dz) for dx,dy,dz in
                        ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))):
                        blocks[x,y,z]=('minecraft:quartz_block',0)
        payload=json.dumps(Document((64,128,64),blocks).to_data())
    server('api._angles62_player=(f.CreatePos(p).GetFootPos(),f.CreateFly(p).IsPlayerFlying())\n_result=True')
    game('''import json
from HelloScript.pyreact import navigator
from HelloScript.projection.model import Document,Editor
b=s.bridge;cam=b.factory.CreateCamera(b.level)
api._angles62_saved=(s.editor,s.origin,s.opacity,s.solo_layer,s.projection_missing,s.projection_outline,
 s.reduced_motion,s.projection_active,cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw(),s.editor.message)
s.editor=Editor(Document.from_data(json.loads('''+repr(payload)+''')))
s.solo_layer=False;s.projection_missing=False;s.projection_outline=True;s.reduced_motion=True;s.opacity=.5
o=b.player_origin();s.origin=(o[0]-32,max(160,o[1]+40),o[2]-32)
navigator.pop();b.project()
_result=True''')
    results=[]
    try:
        for unused in range(150):
            ready=game('_result=bool(b.projection_work and b.projection_work.ready and b.entity and b.projection_outline.entity)')
            if ready:break
            time.sleep(.2)
        assert ready,'projection never became ready'
        game('cam.LockModCameraPitch(True);cam.LockModCameraYaw(True);cam.DepartCamera()\n_result=True')
        cases=[('near_lower',(32.,1.7,-4.),(32.,8.,32.)),
               ('near_lower_right',(32.,1.7,-4.),(57.,8.,32.)),
               ('corner_level',(-1.,1.7,-1.),(32.,1.7,32.)),
               ('corner_down',(-1.,1.7,-1.),(10.,-4.,10.)),
               ('inside_floor',(32.,1.7,32.),(45.,-2.,45.)),
               ('inside_side',(32.,64.,32.),(63.,64.,32.)),
               ('outside',(-58.,64.,-58.),(32.,64.,32.))]
        for label,relative,target in cases:
            pose=game('''o=b.projection_outline.bounds[0]
relative='''+repr(relative)+''';target='''+repr(target)+'''
pos=tuple(o[i]+relative[i] for i in range(3));point=tuple(o[i]+target[i] for i in range(3))
rot=api.GetRotFromDir(tuple(point[i]-pos[i] for i in range(3)))
api._angles62_pose=(pos,(rot[0],rot[1]+180.,0.))
_result=pos''')
            foot=(pose[0],pose[1]-1.62,pose[2])
            server('f.CreateFly(p).ChangePlayerFlyState(True)\nf.CreatePos(p).SetFootPos('+repr(foot)+')\n_result=True')
            time.sleep(.3)
            game('''cam.SetCameraPos(api._angles62_pose[0]);cam.SetCameraRotation(api._angles62_pose[1])
ar=b.factory.CreateActorRender(b.entity);orr=b.factory.CreateActorRender(b.projection_outline.entity)
ar.SetNotRenderAtAll(False);orr.SetNotRenderAtAll(False)
_result=True''')
            time.sleep(.35)
            name='angles62_'+tag+'_'+label
            snapshot(name)
            game('ar.SetNotRenderAtAll(True)\n_result=True');time.sleep(.2)
            snapshot(name+'_no_model')
            game('orr.SetNotRenderAtAll(True)\n_result=True');time.sleep(.2)
            snapshot(name+'_empty')
            results.append(dict(view=label,modelPixels=difference(name,name+'_no_model'),
                outlinePixels=difference(name+'_no_model',name+'_empty')))
            print(results[-1],flush=True)
        by_view={v['view']:v for v in results}
        assert by_view['corner_down']['outlinePixels']>2000,results
        assert by_view['inside_floor']['modelPixels']>20000,results
        assert by_view['inside_side']['modelPixels']>20000,results
        # At the outside view the old centre anchor is visible as well. Compare
        # identical images with both anchor strategies, without rebuilding.
        game("ar.SetNotRenderAtAll(False);orr.SetNotRenderAtAll(False)\n_result=True")
        time.sleep(.3)
        snapshot('visibility_'+tag+'_follow')
        game("""api._visibility_follow=b.follow_projection
b.follow_projection=lambda:None
e,model,origin,current=b.projection_mesh
centre=tuple(origin[i]+b.projection_work.document.size[i]*.5 for i in range(3))
b.factory.CreatePos(e).SetPosForClientEntity(centre)
ar.SetActorBlockGeometryOffset(model,(centre[0]-origin[0]-.5,origin[1]-centre[1],centre[2]-origin[2]-.5))
b.factory.CreatePos(b.projection_outline.entity).SetPosForClientEntity(centre)
orr.SetEntityExtraUniforms(2,(0.,0.,0.,0.))
_result=True""")
        time.sleep(.3)
        snapshot('visibility_'+tag+'_centre_reference')
        alignment=difference('visibility_'+tag+'_follow','visibility_'+tag+'_centre_reference')
        print({'anchorAlignmentDifferentPixels':alignment},flush=True)
        assert alignment<1200,'camera anchor moved visible geometry: '+str(alignment)
        game("""b.follow_projection=api._visibility_follow
b._projection_follow_position=None
b.projection_mesh=(e,model,origin,centre)
b.projection_outline.render_position=centre
b.follow_projection()
_result=True""")
        # Profile only the transform update, excluding IPC and screenshots.
        game("""import time
api._visibility_samples=[]
def instrument(original, samples):
    def follow():
        start=time.clock()
        original()
        samples.append((time.clock()-start)*1000.)
    return follow
b.follow_projection=instrument(b.follow_projection,api._visibility_samples)
api._visibility_ids=(b.entity,b.projection_work.model,b.projection_outline.entity)
_result=True""")
        for index in range(24):
            game('cam.SetCameraRotation((10.,'+str(index*15.)+',0.))\n_result=True')
            time.sleep(.04)
        sample=game("""values=sorted(api._visibility_samples)
_result={'frames':len(values),'p95_ms':values[int((len(values)-1)*.95)],'max_ms':max(values),
'sameModels':api._visibility_ids==(b.entity,b.projection_work.model,b.projection_outline.entity)}
b.follow_projection=api._visibility_follow
""")
        assert sample['sameModels']
        print(sample,flush=True)
        (ui.OUT/('projection_visibility_'+tag+'.json')).write_text(json.dumps(
            dict(angles=results,alignment=alignment,transformProfile=sample),indent=2),encoding='utf8')
    finally:
        game('if hasattr(api,"_visibility_follow"): b.follow_projection=api._visibility_follow\nb.stop_projection()\n_result=True')
        server('f.CreatePos(p).SetFootPos(api._angles62_player[0])\nf.CreateFly(p).ChangePlayerFlyState(api._angles62_player[1])\n_result=True')
        game('''v=api._angles62_saved
s.editor,s.origin,s.opacity,s.solo_layer,s.projection_missing,s.projection_outline,s.reduced_motion=v[:7]
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(v[8]);cam.LockModCameraYaw(v[9])
if v[7]:b.project()
s.editor.message=v[10]
from HelloScript.projection.ui import Workspace
navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')


if __name__=='__main__':main()
