saved=getattr(sys,'_client_anchor_depth_probe',None)
_result=True
if saved is not None and saved['nonce']=='d02831073f4641b495dbc983ee45aaa0':
 errors=[]
 if saved['actor'] is not None:
  item=b.factory.CreateItem(b.level)
  for row in saved['attachments']:
   if row['state']=='bound' and row['id'] is not None and not row.get('remove_attempted'):
    row['remove_attempted']=True
    try:
     row['remove_result']=item.SetBindBoneForBindItem(saved['actor'],row['id'],'',True)
     if row['remove_result'] is True:row['state']='removed'
     else:errors.append('Exact owned attachment removal rejected: '+repr(row['id']))
    except Exception as error:errors.append(repr(error))
 _result=json.dumps({'attachments':saved['attachments'],'errors':errors,'actor':saved['actor'],'create':saved['create']})
