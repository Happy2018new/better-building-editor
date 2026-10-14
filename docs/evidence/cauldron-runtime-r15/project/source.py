import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
system=api.GetSystem('NemcProjectionCleanDemo','Client')
origin=(-8, -60, 8)
start=(origin[0],origin[1]-1,origin[2])
end=(origin[0]+18,origin[1]+1,origin[2]+18)
palette=factory.CreateBlock(api.GetLevelId()).GetBlockPaletteBetweenPos(start,end,False)
assert palette is not None
source=palette.SerializeBlockPalette()
name='cauldron_audit_r15'
geometry=factory.CreateBlockGeometry(api.GetLevelId()).CombineBlockPaletteToGeometry(palette,name,0)
assert geometry is not None
actor_origin=(origin[0]+24,origin[1]-1,origin[2])
entity=system.CreateClientEntityByTypeStr('minecraft:armor_stand',actor_origin,(0.,0.))
assert entity is not None
system.cauldron_audit={'entity':entity,'origin':origin,'actor_origin':actor_origin,'geometry_name':name}
attached=factory.CreateActorRender(entity).AddActorBlockGeometry(name,(-.5,0.,-.5),(0.,180.,0.))
_result={'entity':entity,'name':name,'geometry_result':geometry,'attached':attached,'actor_origin':actor_origin,'source':source,'ticks':system.render_ticks,'runtime':api.GetMinecraftVersion()}
