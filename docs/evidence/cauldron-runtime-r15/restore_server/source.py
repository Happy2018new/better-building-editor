import mod.server.extraServerApi as api
saved=getattr(api,'_cauldron_audit',None)
results=[]
if saved:
 info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
 for entry in reversed(saved['journal']):
  pos=tuple(entry['pos'])
  changed=info.SetBlockNew(pos,entry['block'],0,0,True,False)
  nbt_write=info.SetBlockEntityData(0,pos,entry['nbt']) if entry['nbt'] is not None else None
  results.append({'pos':pos,'changed':changed,'nbt_write':nbt_write,'actual':info.GetBlockNew(pos,0),'expected':entry['block']})
_result={'rows':results,'restored':bool(saved)}
