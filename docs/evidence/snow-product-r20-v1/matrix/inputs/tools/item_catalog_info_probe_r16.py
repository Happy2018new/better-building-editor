import mod.client.extraClientApi as api
component=api.GetEngineCompFactory().CreateItem(api.GetLevelId())
names=('minecraft:diamond_sword','minecraft:stone','minecraft:banner','minecraft:apple',
       'minecraft:bow','minecraft:potion','minecraft:filled_map','minecraft:bed','minecraft:oak_shelf')
_result=[{'name':name,'info':component.GetItemBasicInfo(name,0),
          'texture':component.GetItemTexture(name+':0')} for name in names]
