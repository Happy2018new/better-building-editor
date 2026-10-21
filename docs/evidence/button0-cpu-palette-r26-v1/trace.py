from __future__ import print_function
import sys,json,hashlib,subprocess
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root/'behavior_pack/modern_projection'))
from projection.debug_transform_acceptance import build
from projection.large_preview import build_preview
from projection.geometry_palette import prepare_palette
from projection.cell import foreground
from projection import block_registry
source_commit='c531b2f4802577e160b26105c6d73cd8322ff89f'
files=['debug_transform_acceptance.py','large_preview.py','geometry_palette.py','bridge.py','tiles.py','block_registry.py','block_registry_data.py']
source_binding=[]
for name in files:
    rel='behavior_pack/modern_projection/projection/'+name
    b=(root/rel).read_bytes()
    original=subprocess.check_output(['git','show',source_commit+':'+rel])
    if b!=original:raise ValueError('CPU source differs from T02 cold commit: '+rel)
    source_binding.append({'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'matches_cold_commit':True})
doc=build('test.transforms.acceptance.t02')
original=dict(doc.blocks.items())
button=(3,3,27);support=(3,4,27)
def indices(palette,pos):
    sz,sx,sy=palette['volume'];idx=pos[1]*sz*sx+pos[0]*sz+pos[2]
    return {'index':idx,'values':[list(value) for value,positions in palette['common'].items() if idx in positions],'states':[record for value,record in palette.get('states',{}).items() if idx in palette['common'].get(value,())]}
rows=[]
for name,layer,region,local in [('full',None,None,False),('single_y3',3,None,False),('full_chunk_y0_z16',None,((0,0,16),(16,10,32)),True),('single_chunk_y0_z16',3,((0,0,16),(16,10,32)),True)]:
    final=None
    for result in build_preview(doc,layer=layer,region=region,local=local):
        if result is not None:final=result
    surface,origin,scale=final
    raw=surface.palette_data()
    prepared=prepare_palette(raw,overlay_base=surface.size[1]+1,render_origin=origin)
    local_button=tuple(button[i]-origin[i] for i in range(3));local_support=tuple(support[i]-origin[i] for i in range(3))
    rb=indices(raw,local_button);pb=indices(prepared,local_button)
    rs=indices(raw,local_support);ps=indices(prepared,local_support)
    assert pb['values']==[['minecraft:stone_button',0]]
    assert pb['states']==[{'button_pressed_bit':False,'facing_direction':0}],pb
    assert bool(ps['values'])==(layer is None)
    rows.append({'mode':name,'region':region,'origin':origin,'surface_count':surface.count,'surface_button':rb,'prepared_button':pb,'surface_support':rs,'prepared_support':ps})
assert original==dict(doc.blocks.items())
report={'kind':'offline_cpu_palette_trace','source_commit':source_commit,'source_binding':source_binding,'rows':rows,'document_unchanged':True,'new_manual_closures':0,'claims':['button_0 remains stone_button aux0 with facing_direction0 and unpressed bit in full and single CPU palettes, including its local editor chunk','full retains supporting stone; single Y3 filters supporting Y4 while retaining button'],'not_claimed':['Live game GPU output','Exact runtime palette capture','Native mesh geometry/attachment correctness','Root cause of complete-scene occlusion','Any six-face manual acceptance']}
out=root/'.runtime/round-20261021/button0-cpu-palette-v1/report.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'modes':len(rows),'source_files_exact':len(source_binding),'document_unchanged':True,'button_preserved_all_modes':True,'live_game':False}))
