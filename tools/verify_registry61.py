"""Authoritative states in the embedded runtime and a restored test-world cell."""
import base64
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from verify_projection_outline import server


def install(execute, name, relative):
    path=ui.ROOT/'behavior_pack'/relative
    encoded=base64.b64encode(path.read_bytes()).decode('ascii')
    execute('import base64\nimport '+name+' as module\n'
        'exec(compile(base64.b64decode('+repr(encoded)+'),'+repr(str(path))+',"exec"),module.__dict__)\n_result=True')


def main():
    for execute in (game,server):
        for name in ('block_registry_data','block_registry'):
            install(execute,'modern_projection.projection.'+name,'modern_projection/projection/'+name+'.py')
    install(server,'modern_projection.server_system','modern_projection/server_system.py')
    result=server('''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.block_registry import canonical,states
a=WorldAdapter(p)
origin=f.CreatePos(p).GetFootPos()
point=(int(origin[0]),int(origin[1])+15,int(origin[2]))
previous=a.info.GetBlockNew(point,a.dimension)
assert previous and previous['name']=='minecraft:air',repr(previous)
values=[('minecraft:stained_glass',i) for i in range(16)]
values += [('minecraft:planks',i) for i in range(6)]
values += [('minecraft:log',i) for i in (0,4,8,12)]
values += [('minecraft:oak_stairs',i) for i in (0,4,5)]
values += [('minecraft:wooden_slab',i) for i in (0,8,1,9)]
values += [('minecraft:double_wooden_slab',i) for i in (0,8)]
values += [('minecraft:anvil',5),('minecraft:quartz_block',1)]
reads=[]
try:
    for value in values:
        assert a.valid(value),repr(value)
        expected=canonical(value)
        assert a.write(point,value),repr(value)
        actual=a.read(point)
        assert actual==expected,repr((value,expected,actual))
        reads.append([list(value),list(actual)])
finally:
    assert a.info.SetBlockNew(point,previous,0,a.dimension,True,False)
    assert a.read(point)==('minecraft:air',0)
_result={'count':len(reads),'readback':reads,'restored':True}''')
    ui.check('server writes use the same 37 canonical states as preview',result['count']==37 and result['restored'])
    game('''s.bridge.receive_catalogue({'names':[]})
_result=True''')
    for unused in range(100):
        catalogue=game('''_result={'ready':s.catalogue_ready,'pending':s.catalogue_loading or bool(s.bridge.catalogue_work),
 'size':len(s.block_catalogue),'cyan':[(v['value'],v['name']) for v in s.block_catalogue if v['value'][0]=='minecraft:cyan_stained_glass']}''')
        if not catalogue['pending']:break
        time.sleep(.1)
    ui.check('authoritative catalogue contains localized cyan glass',bool(catalogue['cyan']) and not catalogue['pending'])
    compiled=0
    for path in (ui.ROOT/'behavior_pack/modern_projection').rglob('*.py'):
        if 'pyreact' in path.parts and path.name!='primitives.py':continue
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        game('import base64\ncompile(base64.b64decode('+repr(encoded)+'),'+repr(str(path))+',"exec")\n_result=True')
        compiled+=1
    result.update(catalogue=catalogue,compiled=compiled,checks=ui.checks)
    (ui.OUT/'registry61_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print({'states':result['count'],'compiled':compiled,'catalogue':catalogue},flush=True)


if __name__=='__main__':main()
