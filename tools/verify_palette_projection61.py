"""Exact whole ellipsoid, native state roundtrip and visual block variants."""
import base64
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from verify_projection_outline import server


def install():
    for name in ('block_registry_data','block_registry','materials','world_projection','bridge'):
        path=ui.ROOT/('behavior_pack/HelloScript/projection/'+name+'.py')
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        game('import base64\nfrom HelloScript.projection import '+name+' as module\n'
            'exec(compile(base64.b64decode('+repr(encoded)+'),'+repr(str(path))+',"exec"),module.__dict__)\n_result=True')
    game('''from HelloScript.projection.bridge import ClientBridge
b=s.bridge
b.__class__=ClientBridge
if 'geometry' in b.__dict__:del b.__dict__['geometry']
_result=True''')


def main():
    install()
    original=game('''import json
from HelloScript.pyreact import navigator
from HelloScript.projection.model import Document,Editor
b=s.bridge
cam=b.factory.CreateCamera(b.level)
api._p61_saved=(s.editor,s.origin,s.opacity,s.solo_layer,s.projection_missing,
    s.projection_active,cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw(),s.editor.message)
api._p61_draft=json.dumps(s.editor.document.to_data(),sort_keys=True)
_result={'active':s.projection_active,'blocks':len(s.editor.document.blocks)}''')
    payload=(ui.OUT/'stage51_current_document.json').read_text(encoding='utf8')
    entities=[]
    server('api._p61_saved_player=(f.CreatePos(p).GetFootPos(),f.CreateFly(p).IsPlayerFlying())\n_result=True')
    try:
        game('''from HelloScript.projection.block_registry import canonical,states
from HelloScript.projection.bridge import native
values=[('minecraft:stained_glass',i) for i in range(16)]
values += [('minecraft:planks',i) for i in range(6)]
values += [('minecraft:log',i) for i in (0,4,8)]
values += [('minecraft:oak_stairs',i) for i in (0,4,5)]
values += [('minecraft:wooden_slab',i) for i in (0,8,1,9)]
doc=Document((16,3,4),dict(((i%16,i//16,0),v) for i,v in enumerate(values)))
data=doc.palette_data()
data['common']=dict(((native(canonical(k)[0]),canonical(k)[1]),v) for k,v in data['common'].items())
data['states']=dict((k,dict((native(key),native(val)) for key,val in states(k).items())) for k in data['common'])
data=dict((native(k),v) for k,v in data.items())
p=b.factory.CreateBlock(b.level).GetBlankBlockPalette()
assert p.DeserializeBlockPalette(data)
out=p.SerializeBlockPalette()
assert out['common']==data['common'],repr(out)
assert out['states']==data['states'],repr(out)
api._p61_variants=doc
_result={'variants':len(values),'typedStates':len(out['states'])}''')
        ui.check('32 representative native variants survive palette serialization exactly',True)
        # The test draft is never persisted; one snapshot produces one actor.
        game('''s.editor=Editor(Document.from_data(json.loads('''+repr(payload)+''')))
s.solo_layer=False;s.projection_missing=False;s.opacity=.42
p=b.player_origin();s.origin=(p[0]-32,p[1]+6,p[2]-32)
navigator.pop()
b.project()
_result=True''')
        started=time.perf_counter()
        for unused in range(180):
            result=game('''w=b.projection_work
_result={'ready':w.ready,'error':w.error,'total':w.total,'completed':len(w.completed),
    'actors':len(b.projection_entities)+(1 if b.entity else 0),'blocks':len(w.document.blocks),'size':w.document.size}''')
            if result['ready'] or result['error']:break
            time.sleep(.2)
        result['seconds']=time.perf_counter()-started
        ui.check('64x128x64 ellipsoid uses exactly one complete world model',
            result['ready'] and not result['error'] and result['actors']==1 and result['size']==[64,128,64])
        game('''api._p61_entity=b.entity
cam.LockModCameraPitch(True);cam.LockModCameraYaw(True);cam.DepartCamera()
_result=True''')
        for label,offset,target in [('outside',(90.,64.,-90.),(0.,64.,0.)),
                                     ('inside_upper',(0.,64.,0.),(10.,100.,20.)),
                                     ('inside_lower',(0.,64.,0.),(20.,8.,0.))]:
            pose=game('''o=b.projection_work.origin
offset='''+repr(offset)+''';target='''+repr(target)+'''
pos=(o[0]+32+offset[0],o[1]+offset[1],o[2]+32+offset[2])
point=(o[0]+32+target[0],o[1]+target[1],o[2]+32+target[2])
rot=api.GetRotFromDir(tuple(point[i]-pos[i] for i in range(3)))
api._p61_pose=(pos,(rot[0],rot[1]+180.,0.))
cam.SetCameraPos(pos);cam.SetCameraRotation(api._p61_pose[1])
assert b.entity==api._p61_entity and not b.projection_entities
_result={'pos':pos,'rot':rot,'distance':b.factory.CreateActorRender(b.player).GetEntityRenderDistance(),
 'actor':b.factory.CreatePos(b.entity).GetPos(),'origin':o}''')
            print(pose,flush=True)
            server('f.CreateFly(p).ChangePlayerFlyState(True)\nf.CreatePos(p).SetFootPos('+repr(tuple(pose['pos']))+')\n_result=True')
            time.sleep(.5)
            game('cam.SetCameraPos(api._p61_pose[0]);cam.SetCameraRotation(api._p61_pose[1])\n_result=True')
            time.sleep(.6);snapshot('projection61_'+label)
        binfo=game('''b.stop_projection()
name=b.geometry(api._p61_variants,name='palette61_variants')
p=b.player_origin();o=(p[0]-8.,p[1]+5.,p[2])
e=b.system.CreateClientEntityByTypeStr(b'modern_projection:anchor',o,(0.,0.))
api._p61_variant_actor=(e,name,o)
_result=e''')
        entities.append(binfo)
        time.sleep(.3)
        game('''e,name,o=api._p61_variant_actor
r=b.factory.CreateActorRender(e)
assert r.AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
assert r.EnableActorBlockGeometryTransparent(name,True)
assert r.SetActorBlockGeometryTransparency(name,1.)
assert r.SetEntityExtraUniforms(4,(19487.,0.,0.,0.))
pos=(o[0]+8.,o[1]+5.,o[2]-18.)
point=(o[0]+8.,o[1]+1.,o[2])
rot=api.GetRotFromDir(tuple(point[i]-pos[i] for i in range(3)))
cam.SetCameraPos(pos);cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''')
        time.sleep(.6);snapshot('palette61_variants')
        (ui.OUT/'projection61_checks.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(result,flush=True)
    finally:
        server('f.CreatePos(p).SetFootPos(api._p61_saved_player[0])\nf.CreateFly(p).ChangePlayerFlyState(api._p61_saved_player[1])\n_result=True')
        game('''b.stop_projection()
if hasattr(api,'_p61_variant_actor'):b.system.DestroyClientEntity(api._p61_variant_actor[0])
saved=api._p61_saved
s.editor,s.origin,s.opacity,s.solo_layer,s.projection_missing=saved[:5]
cam.ResetCameraPos();cam.UnDepartCamera()
cam.LockModCameraPitch(saved[6]);cam.LockModCameraYaw(saved[7])
if saved[5]:b.project()
s.editor.message=saved[8]
assert json.dumps(s.editor.document.to_data(),sort_keys=True)==api._p61_draft
from HelloScript.projection.ui import Workspace
if not navigator.contains('modern_projection_workspace'):
    navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')


if __name__=='__main__':main()
