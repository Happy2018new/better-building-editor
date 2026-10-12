saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='7ee4f8762d504c39a330693190cb19e9':
 itemcomp=b.factory.CreateItem(b.level)
 errors=[]
 for row in saved['attachments']:
  if row['state']=='bound' and row['id'] is not None:
   row['remove_attempted']=True
   try:
    row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['player'],row['id'],'',False)
    if row['remove_result'] is True:row['state']='removed'
    else:errors.append('remove rejected: '+repr(row['id']))
   except Exception as error:errors.append(repr(error))
  elif row['state']=='pending':errors.append('unresolved pending attachment: '+repr(row))
 _result=json.dumps({'attachments':saved['attachments'],'errors':errors})
