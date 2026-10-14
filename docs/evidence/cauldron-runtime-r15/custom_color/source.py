import mod.server.extraServerApi as api
saved=api._cauldron_audit
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
rows=dict((r['id'],r) for r in saved['rows'])
results=[]
for name, value in (('dyed_red', -65536), ('dyed_red_blue', 16711680)):
 pos=tuple(rows[name]['pos'])
 nbt=info.GetBlockEntityData(0,pos)
 nbt['CustomColor']={'__type__':3,'__value__':value}
 written=info.SetBlockEntityData(0,pos,nbt)
 read=info.GetBlockEntityData(0,pos)
 results.append({'id':name,'value_written':value,'set_result':written,'readback':read})
_result={'rows':results}
