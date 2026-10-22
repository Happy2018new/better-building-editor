"""Bind independently reviewed sealed V7 and root-approved V4 time maxima."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
V7=HERE.parent/'water-anchor-watcher-v7'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf8')
def main():
 assert not (HERE/'v7-integration.json').exists() and not (HERE/'host-binding-final.json').exists()
 ready=V7/'ready-index.json'
 assert sha(ready)=='5d8df77dd69d3a5057e1995e46ccabb9ba2c1a1f6b3f9ea6e4ee3193e7d7b949'
 seal=json.loads(ready.read_bytes())
 assert all((V7/key).stat().st_size==value['bytes'] and sha(V7/key)==value['sha256'] for key,value in seal['files'].items())
 (HERE/'status_reader.py').write_bytes((V7/'status_reader.py').read_bytes())
 assert sha(HERE/'status_reader.py')=='c9383d0aedfaabdff98a52afcfe1c0d3619291d6d48138495e87f283d958e908'
 provenance=[]
 for name,a,b in (('run_anchor.py','2026-10-23T06:30:00+08:00','2026-10-23T07:20:00+08:00'),
  ('start_watch.py','2026-10-23T06:35:00+08:00','2026-10-23T07:25:00+08:00')):
  path=HERE/name;before=path.read_text('utf8');assert before.count(a)==1
  oldhash=sha(path);path.write_text(before.replace(a,b),encoding='utf8')
  provenance.append({'file':name,'before_sha256':oldhash,'after_sha256':sha(path),'before':a,'after':b,
   'authority':'Root explicitly approved maximum experiment 07:20+08 / watcher 07:25+08; actual launch still separately granted.'})
 external=json.loads((HERE.parent/'portal-gui-anchor-v3/external-host-binding.json').read_bytes())
 for key in list(external):
  if key.startswith('.runtime/round-20261022/water-anchor-watcher-v5/'):del external[key]
 for name in ('watch_owned_disabled_skin_assert_r28_v7.py','windows_manifest_reader.py','atomic_json_writer.py','status_reader.py','ready-index.json'):
  external[(V7/name).relative_to(ROOT).as_posix()]=sha(V7/name)
 assert all(sha(ROOT/key)==value for key,value in external.items())
 write(HERE/'external-host-binding.json',external)
 write(HERE/'v7-integration.json',{'source':str(V7),'ready_index_sha256':sha(ready),
  'status_reader_local_byte_exact':True,'status_reader_sha256':sha(HERE/'status_reader.py'),
  'external_assets':external,'time_maximum_declarations':provenance,
  'runtime_or_historical_session_helper_modified':False,'V3_modified':False,
  'MC_started':False,'watcher_started':False,'launch_granted':False})
 print(json.dumps({'passed':True,'external_assets':len(external),'MC_started':False,'watcher_started':False}))
if __name__=='__main__':main()
