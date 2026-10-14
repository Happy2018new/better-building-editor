import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
saved=api._cauldron_audit
info=factory.CreateBlockInfo(saved['player'])
state=factory.CreateBlockState(api.GetLevelId())
_result={'origin':saved['origin'],'runtime':api.GetMinecraftVersion(),'rows':[{'id':r['id'],'pos':r['pos'],'local':r['local'],'block':info.GetBlockNew(tuple(r['pos']),0),'states':state.GetBlockStates(tuple(r['pos']),0),'nbt':info.GetBlockEntityData(0,tuple(r['pos']))} for r in saved['rows']]}
