import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
saved=system.cauldron_audit
target=(saved['actor_origin'][0],saved['actor_origin'][1]+8.,saved['actor_origin'][2])
moved=api.GetEngineCompFactory().CreatePos(saved['entity']).SetPosForClientEntity(target)
saved['actor_origin']=target
_result={'moved':moved,'target':target,'entity':saved['entity'],'ticks':system.render_ticks}
