import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
from modern_projection.projection.model import Document
from modern_projection.projection.native_render_profile import NativeRenderProfile, production_profile
from modern_projection.projection.geometry_palette import prepare_palette
assert api.GetEngineVersion()=='3.10.0.420447'
if hasattr(sys,'_native_r15_factory'):
 b.factory=sys._native_r15_factory
if True:
 sys._native_r15_factory=b.factory
 class NativeGeometryReceipt(object):
  def __init__(self,target):self.target=target
  def __getattr__(self,name):return getattr(self.target,name)
  def CombineBlockPaletteToGeometry(self,palette,name,mode=0):
   data=palette.SerializeBlockPalette()
   requested=name
   name=name+'_r15_'+str(int(time.time()*1000000))
   result=self.target.CombineBlockPaletteToGeometry(palette,name,mode)
   sys._native_r15_geometry.append({'name':name,'materials':sorted(data['common']),
    'actors':sorted(data.get('actor',{})),'result':result,'requested_name':requested})
   return result
 class NativeFactoryReceipt(object):
  def __init__(self,target):self.target=target
  def __getattr__(self,name):return getattr(self.target,name)
  def CreateBlockGeometry(self,level):
   return NativeGeometryReceipt(self.target.CreateBlockGeometry(level))
 b.factory=NativeFactoryReceipt(b.factory)
sys._native_r15_geometry=[]
if s.projection_active:b.stop_projection()
profile='fallback'
names=('minecraft:chest', 'minecraft:copper_chest', 'minecraft:ender_chest', 'minecraft:bed', 'minecraft:flower_pot')
if profile=='production':
 assert s.native_render_profile==production_profile(api.GetEngineVersion())
else:
 s.native_render_profile=(None if profile=='fallback' else
  NativeRenderProfile(model_local=names) if profile=='model_local' else
  NativeRenderProfile(model_local=names[:-1],context=names[-1:]) if profile=='mixed' else
  NativeRenderProfile(context=names))
doc=Document.from_data(json.loads('{"version": 6, "cellVersion": 1, "chunkEncoding": 1, "registry": {"version": "NEMC 3.9.0.401155", "sha256": "6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01"}, "name": "R15 native body coordinates", "size": [16, 3, 4], "biome": "plains", "blockCount": 26, "materials": [["minecraft:air", {}], ["minecraft:chest", {"minecraft:cardinal_direction": "south"}], ["minecraft:stone", {}], ["minecraft:oak_fence", {}], ["minecraft:copper_chest", {"minecraft:cardinal_direction": "south"}], ["minecraft:ender_chest", {"minecraft:cardinal_direction": "south"}], ["minecraft:bed", {"direction": 0, "head_piece_bit": false, "occupied_bit": false}], ["minecraft:bed", {"direction": 0, "head_piece_bit": true, "occupied_bit": false}], ["minecraft:flower_pot", {"update_bit": true}]], "palette": [0, [1, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "Findable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsIgnoreShuffle"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsOpened"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "Items"], ["list", []]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "Chest"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]]]]], [["text", "render"], ["dict", [[["text", "chestIsGlobalChest"], ["bool", false]], [["text", "chestIsLargeChest"], ["bool", false]], [["text", "chestMainSubChest"], ["bool", true]], [["text", "chestModelOffset"], ["float", "0x0.0p+0"]], [["text", "chestOldOpenness"], ["float", "0x0.0p+0"]], [["text", "chestOpenness"], ["float", "0x0.0p+0"]], [["text", "facingDirection"], ["int", "3"]]]]]]]], 2, 3, [4, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "Findable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsIgnoreShuffle"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsOpened"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "Items"], ["list", []]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "Chest"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "4"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]]]]], [["text", "render"], ["dict", [[["text", "chestCopperType"], ["int", "0"]], [["text", "chestIsCopperChest"], ["bool", true]], [["text", "chestIsGlobalChest"], ["bool", false]], [["text", "chestIsLargeChest"], ["bool", false]], [["text", "chestMainSubChest"], ["bool", true]], [["text", "chestModelOffset"], ["float", "0x0.0p+0"]], [["text", "chestOldOpenness"], ["float", "0x0.0p+0"]], [["text", "chestOpenness"], ["float", "0x0.0p+0"]], [["text", "facingDirection"], ["int", "3"]]]]]]]], [5, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "Findable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsIgnoreShuffle"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "IsOpened"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "Items"], ["list", []]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "EnderChest"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "7"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]]]]], [["text", "render"], ["dict", [[["text", "chestIsGlobalChest"], ["bool", true]], [["text", "chestIsLargeChest"], ["bool", false]], [["text", "chestMainSubChest"], ["bool", true]], [["text", "chestModelOffset"], ["float", "0x0.0p+0"]], [["text", "chestOldOpenness"], ["float", "0x0.0p+0"]], [["text", "chestOpenness"], ["float", "0x0.0p+0"]], [["text", "facingDirection"], ["int", "3"]]]]]]]], [6, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "color"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "14"]]]]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "Bed"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "10"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]]]]], [["text", "render"], ["dict", [[["text", "color"], ["int", "14"]], [["text", "direction"], ["int", "0"]]]]]]]], [7, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "color"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "14"]]]]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "Bed"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "10"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "2"]]]]]]]], [["text", "render"], ["dict", [[["text", "color"], ["int", "14"]], [["text", "direction"], ["int", "0"]]]]]]]], [8, 0, ["dict", [[["text", "__modern_projection_actor__"], ["int", "1"]], [["text", "nbt"], ["dict", [[["text", "PlantBlock"], ["dict", [[["text", "name"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "minecraft:poppy"]]]]], [["text", "states"], ["dict", []]], [["text", "val"], ["dict", [[["text", "__type__"], ["int", "2"]], [["text", "__value__"], ["int", "0"]]]]], [["text", "version"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "18168865"]]]]]]]], [["text", "id"], ["dict", [[["text", "__type__"], ["int", "8"]], [["text", "__value__"], ["text", "FlowerPot"]]]]], [["text", "isMovable"], ["dict", [[["text", "__type__"], ["int", "1"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "x"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "13"]]]]], [["text", "y"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]], [["text", "z"], ["dict", [[["text", "__type__"], ["int", "3"]], [["text", "__value__"], ["int", "1"]]]]]]]], [["text", "render"], ["dict", [[["text", "flowerPotPlant"], ["text", "minecraft:poppy"]]]]]]]]], "chunks": [[0, 0, 0, "1r:eJxjZGBgYGRgAkL8NDOV1T0G04xQPguUZoXSbFCaAygDopmhfATNCKbZUcQu8jEwAACLXgJb"]]}'))
# Each evidence run must exercise a real upload, including equivalent fixtures.
s.tiles.cancel()
s.tiles.parts.clear()
s.tiles.context=None
s._loaded(doc)
s.camera_view(35.,25.,2.)
s.grid=False
s.emit()
owner.open_workspace()
rendered=prepare_palette(doc.palette_data(),native_render_profile=s.native_render_profile)
_result=json.dumps({'profile':profile,'engine':api.GetEngineVersion(),'size':doc.size,
 'materials':sorted(rendered['common']),'actors':sorted(rendered['actor']),
 'identity':s.native_render_profile.identity if s.native_render_profile else None})
