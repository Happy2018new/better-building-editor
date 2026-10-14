import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
saved=api._cauldron_audit
player=saved['player']
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(api.GetLevelId())
items=factory.CreateItem(player)
slot=35
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
assert not items.GetPlayerItem(item_type,slot,True)
results=[]
for row in saved['rows']:
 if not row.get('use'):continue
 pos=tuple(row['pos'])
 record={'id':row['id'],'pos':pos,'steps':[]}
 for spec in row['use']:
  item={'itemName':str('minecraft:'+spec['name']),'count':1,'auxValue':spec['aux']}
  items.SetInvItemNum(slot,0)
  spawned=items.SpawnItemToPlayerInv(item,player,slot)
  before=items.GetPlayerItem(item_type,slot,True)
  used=info.PlayerUseItemToPos(pos,item_type,slot,1)
  record['steps'].append({'requested':item,'spawned':spawned,'native_item_before':before,'used':used,'native_item_after':items.GetPlayerItem(item_type,slot,True),'actual':info.GetBlockNew(pos,0),'states':state.GetBlockStates(pos,0),'nbt':info.GetBlockEntityData(0,pos)})
 results.append(record)
items.SetInvItemNum(slot,0)
assert not items.GetPlayerItem(item_type,slot,True)
saved['content']=results
_result={'rows':results,'inventory_restored':True,'runtime':api.GetMinecraftVersion()}
