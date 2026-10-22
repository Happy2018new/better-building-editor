
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
