"""Create a separate diagnostic wrapper without modifying the frozen 138 plan."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
SOURCE=WORK.with_name('water-anchor-calibration-v6')/'anchor_game.py'


def main():
    target=WORK/'observer_game.py';assert not target.exists()
    text=SOURCE.read_text('utf8')
    text=text.replace("stone=use_ref(None)\r\n","stone=use_ref(None)\r\n")
    # New visible parent establishes the declared viewport independently from
    # hidden engine controls, whose measured GetSize is allowed to be zero.
    old=" stone=use_ref(None)\n saved=sys._r27_water_anchor_ui"
    new=" stone=use_ref(None)\n viewport=use_ref(None)\n saved=sys._r27_water_anchor_ui"
    assert old in text;text=text.replace(old,new,1)
    text=text.replace("  current['refs'],current['stone']=refs,stone",
                      "  current['refs'],current['stone'],current['viewport']=refs,stone,viewport",1)
    old=""" children=[Image(color=Color(0xF0F0F0FF),style=Style(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=stone,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=Style(position=Position.absolute,left=left,top=top,width=rw,height=rh,zIndex=50))]
 for slot,ref in enumerate(refs):
  children.append(Doll(key=str(slot),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=Style(position=Position.absolute,left=left,top=top+offset,width=rw,height=rh,zIndex=60)))
 return Panel(style=Style(width=width,height=height),children=children)"""
    new=""" children=[Doll(ref=stone,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=Style(position=Position.absolute,left=0,top=0,width=rw,height=rh,zIndex=50))]
 for slot,ref in enumerate(refs):
  children.append(Doll(key=str(slot),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=Style(position=Position.absolute,left=0,top=offset,width=rw,height=rh,zIndex=60)))
 return Panel(style=Style(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=Style(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Panel(ref=viewport,style=Style(position=Position.absolute,left=left,top=top,width=rw,height=rh,zIndex=50),children=children)])"""
    assert old in text;text=text.replace(old,new,1)
    old="""  native.append({'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
   'size':control.GetSize(),'model_id':control.asNeteasePaperDoll().GetModelId()})"""
    new="""  native.append({'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
   'size':control.GetSize(),'actual_visible':control.GetVisible(),
   'model_id':control.asNeteasePaperDoll().GetModelId()})"""
    assert old in text;text=text.replace(old,new,1)
    old="state=None if renderer is None else"
    new="""viewport_ref=saved.get('viewport')
viewport=None
if viewport_ref is not None and viewport_ref.current is not None:
 control=viewport_ref.current
 viewport={'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
  'size':control.GetSize(),'actual_visible':control.GetVisible()}
state=None if renderer is None else"""
    assert old in text;text=text.replace(old,new,1)
    text=text.replace(" 'config':saved['config'],'native':native,'renderer':state,",
        " 'config':saved['config'],'native':native,'viewport_parent':viewport,'renderer':state,",1)
    with target.open('x',encoding='utf8',newline='\n') as stream:stream.write(text)
    binding={'schema':1,'base_path':str(SOURCE),'base_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'observer_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'changes':['Always-visible parent Panel ref around all dolls with identical global intended layout.',
            'Record actual BaseUIControl.GetVisible, parent geometry and all active/hidden doll geometry.',
            'No geometry acceptance is inferred merely from the old renderer logical ready flag.'],
        'frozen_138_plan_changed':False,'game_source_changed':False,'MC_started':False,'formal_A_accepted':False}
    with (WORK/'observer-payload-binding-v1.json').open('x',encoding='utf8') as stream:json.dump(binding,stream,indent=2)
    print(json.dumps(binding))


if __name__=='__main__':main()
