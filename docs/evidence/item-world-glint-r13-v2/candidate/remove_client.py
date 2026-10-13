saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=True
if saved is not None and saved['nonce']=='6a73798d9ff44f93b1b9a2ca624820ef':
 errors=[]
 if saved['actor'] is not None:
  item=b.factory.CreateItem(b.level)
  for row in saved['attachments']:
   if row['state']=='bound' and row['id'] is not None and not row.get('remove_attempted'):
    row['remove_attempted']=True
    try:
     row['remove_result']=item.SetBindBoneForBindItem(saved['actor'],row['id'],'',False)
     if row['remove_result'] is True:row['state']='removed'
     else:errors.append('Exact owned attachment removal rejected: '+repr(row['id']))
    except Exception as error:errors.append(repr(error))
 _result=json.dumps({'attachments':saved['attachments'],'errors':errors,'actor':saved['actor'],'create':saved['create'],'skeleton_setup':saved.get('skeleton_setup')})
