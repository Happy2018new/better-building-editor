"""Run the sealed plain24 host with idempotent world clearing."""
import hashlib
import importlib.util
from pathlib import Path


SOURCE = Path(__file__).with_name('probe_runtime.py')
EXPECTED_SOURCE = '95b36207b495258ead6a791d2e7e5f1b4325010afaf277041fd7422405828336'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED_SOURCE:
    raise ValueError('The sealed base runtime host changed')
SPEC = importlib.util.spec_from_file_location('lectern_runtime_base', SOURCE)
HOST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOST)

CLEAR = '''def clear(position):
 before=info.GetBlockNew(world(position),dimension)
 assert before is not None,(position,before)
 if before.get('name')!='minecraft:air':
  assert info.SetBlockNew(world(position),{'name':'minecraft:air','aux':0},0,dimension,True,False)
 after=info.GetBlockNew(world(position),dimension)
 assert after and after.get('name')=='minecraft:air',(position,after)
'''
HOST.BUILD_WORLD = HOST.SERVER + CLEAR + '''for x in range(4):
 for y in range(4):
  for z in range(3):clear((x,y,z))
for x in (0,2):
 assert info.SetBlockNew(world((x,0,1)),{'name':'minecraft:cyan_concrete','aux':0},0,dimension,True,False)
 assert info.SetBlockNew(world((x,1,1)),{'name':'minecraft:lectern','aux':1},0,dimension,True,False)
extras=%r
for position in extras:
 assert info.SetBlockNew(world(position),{'name':'minecraft:stone','aux':0},0,dimension,True,False)
_result=True
'''
HOST.REMOVE_WORLD = HOST.SERVER + CLEAR + '''keep=%r
for x in range(4):
 for y in range(4):
  for z in range(3):
   if keep and (x,y,z) in ((0,0,1),(2,0,1),(0,1,1),(2,1,1)):continue
   clear((x,y,z))
_result=True
'''
HOST.__file__ = __file__


if __name__ == '__main__':
    HOST.main()
