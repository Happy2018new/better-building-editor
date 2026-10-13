from modern_projection.pyreact import Component,Image,Color,PaperDoll,Style,use_ref,AlignItems,JustifyContent,PaperDollRenderType,Position
saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='fd2c58cd04174a4e88235c6a5afc6b55' and not saved['push_attempted']
saved['control']='ui_empty'
screen=saved['size_inputs']
saved['markers']=[{'key':key,'rgb':rgb,'x':8. if index%2==0 else screen[0]-14.,
 'y':8. if index<2 else screen[1]-14.,'size':6.} for index,(key,rgb) in enumerate(saved['markers'])]
@Component
def ClientAnchorPaperDollProbe():
 root_ref=use_ref(None)
 ref=use_ref(None)
 marker_refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 saved['root_ref'],saved['ref'],saved['marker_refs']=root_ref,ref,marker_refs
 children=[PaperDoll(key='native_item_probe_doll',ref=ref,renderType=PaperDollRenderType.entity,
  entityId=saved['actor'],scale=.35,renderDepth=-15,initRotX=0.,initRotY=0.,initRotZ=0.,
  style=Style(width=saved['declared_size'],height=saved['declared_size']))]
 for index,marker in enumerate(saved['markers']):
  rgb=marker['rgb']
  children.append(Image(key=marker['key'],ref=marker_refs[index],
   color=Color((rgb[0]<<24)|(rgb[1]<<16)|(rgb[2]<<8)|255),
   style=Style(position=Position.absolute,left=marker['x'],top=marker['y'],width=6.,height=6.)))
 return Image(key='native_item_probe_root',ref=root_ref,color=Color(0xF7F9FCFF),
  style=Style(width='100%',height='100%',alignItems=AlignItems.center,justifyContent=JustifyContent.center),children=children)
saved['push_attempted']=True
assert navigator.push(ClientAnchorPaperDollProbe(),key=saved['key'])
_result=True
