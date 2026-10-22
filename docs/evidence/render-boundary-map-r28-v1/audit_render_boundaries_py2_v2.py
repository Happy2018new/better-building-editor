"""Read exact Git sources with both real parsers; static graph, no imports."""
import ast,base64,hashlib,json,subprocess
from collections import deque
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.runtime/round-20261023/render-boundary-map-v2';OUT.mkdir(exist_ok=False)
COMMIT='b70ce7bf13ad6a4472f2b089ac812c162b174861'
objects={}
for row in subprocess.check_output(['git','ls-tree','-rz',COMMIT,'behavior_pack/modern_projection'],cwd=ROOT).split(b'\0'):
 if row:
  header,path=row.split(b'\t',1);path=path.decode('utf8')
  if path.endswith('.py'):objects[path]=header.split()[2].decode('ascii')
proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
sources={}
try:
 for path,oid in objects.items():
  proc.stdin.write((oid+'\n').encode('ascii'));proc.stdin.flush();actual,kind,size=proc.stdout.readline().split()
  assert actual.decode()==oid and kind==b'blob'
  sources[path]=proc.stdout.read(int(size));assert proc.stdout.read(1)==b'\n'
finally:
 proc.stdin.close();assert proc.wait()==0
parser=r'''
import ast,base64,json,sys
sources=json.load(sys.stdin);result={}
for path,encoded in sources.items():
 data=base64.b64decode(encoded);tree=ast.parse(data,filename=path)
 imports=[];definitions=[];dynamic=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.append({'level':0,'module':None,'names':[a.name for a in node.names],'line':node.lineno})
  elif isinstance(node,ast.ImportFrom):imports.append({'level':node.level,'module':node.module,'names':[a.name for a in node.names],'line':node.lineno})
  elif isinstance(node,(ast.FunctionDef,ast.ClassDef)):definitions.append({'name':node.name,'kind':type(node).__name__,'line':node.lineno})
  elif isinstance(node,ast.Call) and ((isinstance(node.func,ast.Name) and node.func.id=='__import__') or (isinstance(node.func,ast.Attribute) and node.func.attr=='import_module')):dynamic.append(node.lineno)
 result[path]={'imports':imports,'definitions':definitions,'dynamic_import_calls':dynamic}
json.dump({'python':sys.version,'parsed':result},sys.stdout,sort_keys=True)
'''
(OUT/'parse_imports_py2.py').write_text(parser,encoding='ascii')
encoded=json.dumps({path:base64.b64encode(data).decode('ascii') for path,data in sources.items()}).encode('ascii')
run=subprocess.run(['D:/Program/Python27/python.exe','-B',str(OUT/'parse_imports_py2.py')],input=encoded,capture_output=True)
(OUT/'parser-stderr.txt').write_bytes(run.stderr);assert run.returncode==0,run.stderr.decode('utf8','replace')
parsed=json.loads(run.stdout);(OUT/'parsed-py2.json').write_bytes(run.stdout)
parity=0;py3_failures=[]
for path,data in sources.items():
 try:tree=ast.parse(data,filename=path)
 except SyntaxError as error:py3_failures.append({'path':path,'line':error.lineno,'reason':error.msg});continue
 imports=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):imports.append({'level':0,'module':None,'names':[a.name for a in node.names],'line':node.lineno})
  elif isinstance(node,ast.ImportFrom):imports.append({'level':node.level,'module':node.module,'names':[a.name for a in node.names],'line':node.lineno})
 assert sorted(imports,key=lambda r:(r['line'],str(r)))==sorted(parsed['parsed'][path]['imports'],key=lambda r:(r['line'],str(r))),path
 parity+=1
def module(path):
 parts=list(Path(path).relative_to('behavior_pack/modern_projection').with_suffix('').parts)
 if parts[-1]=='__init__':parts.pop()
 return '.'.join(['modern_projection']+parts)
names={module(path):path for path in sources};records={}
for name,path in names.items():
 package=name if path.endswith('/__init__.py') else name.rpartition('.')[0]
 row={'path':path,'git_blob':objects[path],'sha256':hashlib.sha256(sources[path]).hexdigest(),
      'local_imports':[],'external_imports':[],'definitions':parsed['parsed'][path]['definitions'],
      'dynamic_import_calls':parsed['parsed'][path]['dynamic_import_calls']}
 for item in parsed['parsed'][path]['imports']:
  if item['module'] is None and item['level']==0:targets=item['names']
  else:
   if item['level']:
    base=package.split('.')[:len(package.split('.'))-item['level']+1]
    if item['module']:base+=item['module'].split('.')
    origin='.'.join(base)
   else:origin=item['module'] or ''
   targets=[origin]+[(origin+'.' if origin else '')+value for value in item['names'] if value!='*']
  local=sorted(set(target for target in targets if target in names))
  if local:row['local_imports'] += [{'module':target,'line':item['line']} for target in local]
  else:row['external_imports'].append({'modules':targets,'line':item['line']})
 records[name]=row
contract=json.loads(subprocess.check_output(['git','show',COMMIT+':tools/data/liquid_product_owner_contract_v1.json'],cwd=ROOT))
seeds=sorted(module(p) for p in contract['source_sha256'] if p in sources)
seen=set(seeds);queue=deque(seeds)
while queue:
 for edge in records[queue.popleft()]['local_imports']:
  if edge['module'] not in seen:seen.add(edge['module']);queue.append(edge['module'])
layout='modern_projection.projection.render_layout'
summary={'source_commit':COMMIT,'created_at_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Conservative syntactic imports, including optional/function-local imports; not executable dependency closure, resource graph or qualification',
 'actual_parser_python':parsed['python'],'parsed_modules':len(records),'python3_import_parity_modules':parity,
 'python3_only_parse_failures':py3_failures,'water_contract_entries':len(contract['source_sha256']),
 'water_python_seeds':len(seeds),'syntactic_local_reachable_modules':len(seen),
 'reachable_outside_explicit_contract':sorted(records[n]['path'] for n in seen if n not in seeds),
 'layout_direct_importers':[{'path':r['path'],'lines':[e['line'] for e in r['local_imports'] if e['module']==layout]}
  for r in records.values() if any(e['module']==layout for e in r['local_imports'])],
 'scene_owner_effects':[d for d in records['modern_projection.projection.scene']['definitions'] if d['name'] in ('own_liquid','own_items','own_cauldrons','own_portals','own_books')],
 'source_archives_written':False,'production_changed':False,'libraries_changed':False,'qualification_changed':False,'MC_started':False,'manual_issues_closed':0}
for name,value in (('module-imports.json',records),('summary.json',summary)):
 (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:summary[k] for k in ('parsed_modules','python3_import_parity_modules','python3_only_parse_failures','syntactic_local_reachable_modules')}))
