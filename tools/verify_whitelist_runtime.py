"""Whitelist replacement compatibility and actual biome pixels in Python 2.

Uses an isolated instance, scratch archives and a restored in-memory draft.
Does not write world blocks, the library or the OS clipboard.
"""
import base64
import json
import time
from PIL import Image
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from verify_biome_controls import native_click, action
from native_input_mode import set_touch, state


def compatibility():
    # Refresh the final bounds-check method without replacing classes already
    # held by the live editor. All other changes were loaded at game startup.
    source = base64.b64encode((ui.ROOT/'behavior_pack/HelloScript/projection/packed.py').read_bytes()).decode('ascii')
    game('import base64\nfrom HelloScript.projection import packed\n'
         'scope=dict(packed.__dict__)\nexec(compile(base64.b64decode('+repr(source)+'),"packed.py","exec"),scope)\n'
         'packed.IntegerBuffer.__setitem__=scope["IntegerBuffer"].__setitem__.im_func\n_result=True')
    result = game('''import struct,zlib,base64,json
from HelloScript.projection.packed import IntegerBuffer
from HelloScript.projection.model import Document
from HelloScript.projection.codec import to_data
from HelloScript.projection.journal import Journal
from HelloScript.projection.archive import save_steps,load_steps
from HelloScript.projection.sharing_codec import encode_steps,decode_steps,split_text,Inbox
from HelloScript.projection.typography import characters,supported
from HelloScript.projection.bridge import native
checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
for code,values in [('H',[0,255,256,65535]),('i',[-2147483648,-1,0,2147483647])]:
    packed_values=IntegerBuffer(code,values)
    check('buffer '+code,packed_values.tobytes()==struct.pack('<4'+code,*values) and list(packed_values)==values)
value=IntegerBuffer('H',[2,3])
try:value[0]=65536
except struct.error:pass
check('rejected edit preserves data',list(value)==[2,3])
values=[i%3 for i in range(4096)]
payload=base64.b64encode(zlib.compress(struct.pack('<4096H',*values),1)).decode('ascii')
data={'version':2,'name':'annnn币','size':[16,16,16],'biome':'forest','blockCount':2730,
      'palette':[['minecraft:air',0],['minecraft:stone',0],['minecraft:planks',1]],'chunks':[[0,0,0,payload]]}
doc=Document.from_data(data)
check('legacy version 2 bytes',to_data(doc)['chunks']==data['chunks'])
class Pages(object):
    def __init__(self):self.data={}
    def save_archive_page(self,identity,page,data):
        self.data[(identity,page)]=json.loads(json.dumps(data));return True
    def load_archive_page(self,identity,page):return self.data.get((identity,page))
pages=Pages()
meta=list(save_steps(pages,doc,68))[-1]
loaded=list(load_steps(pages,68,meta))[-1]
check('paged archive and biome',loaded.blocks==doc.blocks and loaded.biome==doc.biome and loaded.name==doc.name)
text=list(encode_steps(doc))[-1]['text']
inbox=Inbox();assembled=None
for part in reversed(split_text(text,256)):
    candidate=inbox.add(part)
    if candidate is not None:assembled=candidate
loaded=list(decode_steps(assembled))[-1]['document']
check('segmented sharing and transfer',loaded.blocks==doc.blocks and loaded.biome==doc.biome)
journal=Journal()
air,stone=('minecraft:air',0),('minecraft:stone',0)
for i in range(2500):journal.append(((-2000+i,-64,30000000),air,stone))
check('compressed signed journal',all(journal[i]==((-2000+i,-64,30000000),air,stone) for i in (0,1023,1024,2047,2048,2499)))
check('native UTF8 and narrow unicode',isinstance(native('币'),str) and len(list(characters('A\\U00020000币')))==3 and supported('annnn币'))
_result={'checks':checks,'narrow_unicode':len('\\U00010000')==2,'archive_bytes':len(payload),'share_segments':len(split_text(text,256))}''')
    print(json.dumps(result,ensure_ascii=False),flush=True)
    return result


def settle():
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        value=game('_result={"busy":s.preview_pending or s.tiles.mounting or any(p["pending"] for p in s.tiles.parts.values()),"error":s.preview_error}')
        assert not value['error'],value
        if not value['busy']:
            time.sleep(.5)
            return
        time.sleep(.2)
    raise AssertionError(value)


def main():
    result=compatibility()
    original_touch=state()['simulated']
    game('''fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','grid')
api._whitelist_saved=dict((k,getattr(s,k)) for k in fields)
from HelloScript.projection.model import demo_document
s._loaded(demo_document())
s.direct_mode='browse';s.inspector='layers';s.grid=False;s.focus_view=False;s.emit()
_result=True''')
    try:
        settle()
        frames={}
        for touch in (False,True):
            set_touch(touch)
            settings=ui.nodes('BiomeTintSettings')[0]
            if len(ui.nodes('Action',settings))==1:
                native_click(ui.nodes('Action',settings)[0])
            for label,name in [('沙漠','desert'),('丛林','jungle')]:
                settings=ui.nodes('BiomeTintSettings')[0]
                native_click(action(label,settings))
                ui.check(('F11' if touch else 'PC')+' selects '+name,game('_result=s.editor.document.biome')==name)
                filename='whitelist68_'+('touch_' if touch else 'pc_')+name
                snapshot(filename)
                frames[name]=Image.open(ui.OUT/(filename+'.jpg')).convert('RGB')
            # Restrict evidence to the native viewport, excluding option colors.
            from verify_interaction import pointer
            native=ui.call('native_control',pointer()['id'])['result']
            root=ui.nodes('SafeArea')[0]['children'][0]['layout']
            width,height=frames['desert'].size
            x,y=native['global'];w,h=native['size']
            box=(int(x*width/root['width']),int(y*height/root['height']),
                 int((x+w)*width/root['width']),int((y+h)*height/root['height']))
            pairs=list(zip(frames['desert'].crop(box).getdata(),frames['jungle'].crop(box).getdata()))
            changed=sum(d[0]>j[0]+10 and j[1]>j[0]*1.4 for d,j in pairs)
            neutral=sum(min(d)>100 and max(d)-min(d)<6 and max(abs(a-b) for a,b in zip(d,j))<3 for d,j in pairs)
            ui.check(('F11' if touch else 'PC')+' rendered grass/leaves change color',changed>150)
            ui.check(('F11' if touch else 'PC')+' neutral geometry remains stable',neutral>1000)
            result['touch' if touch else 'pc']={'tinted_pixels':changed,'stable_neutral_pixels':neutral,'viewport':box}
        result['ui_checks']=ui.checks
        (ui.OUT/'whitelist68_runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    finally:
        set_touch(original_touch)
        game('''for k,v in api._whitelist_saved.items():setattr(s,k,v)
s.camera_revision+=1
s.refresh_preview();s.emit()
_result=True''')
        settle()


if __name__=='__main__':main()
