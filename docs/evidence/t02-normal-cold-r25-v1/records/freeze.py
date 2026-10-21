"""Freeze one explicitly approved integration commit; this does not start Minecraft."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OWNER='r25-t02-normal-v1'
PROJECT=ROOT/'.runtime/projects'/OWNER
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--commit',required=True)
args=parser.parse_args()
assert re.fullmatch('[0-9a-f]{40}',args.commit)
assert subprocess.check_output(['git','rev-parse',args.commit+'^{commit}'],cwd=ROOT,text=True).strip()==args.commit
assert not PROJECT.exists()
assert not (HERE/'source-manifest.json').exists()
config_path=ROOT/'.mcdev.json'
config=json.loads(config_path.read_bytes())
keys=['auto_hot_reload_mods','auto_hot_reload_ui','auto_hot_reload_materials','auto_hot_reload_shaders']
assert all(config[key] is False for key in keys)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
archive=HERE/'source-runtime.zip'
subprocess.run(['git','archive','--format=zip','--output='+str(archive),args.commit,
                'behavior_pack','resource_pack'],cwd=ROOT,check=True)
PROJECT.mkdir(parents=True)
runtime={}
with zipfile.ZipFile(archive) as bundle:
    for member in bundle.infolist():
        if member.is_dir():continue
        relative=Path(member.filename)
        assert relative.parts[0] in ('behavior_pack','resource_pack')
        assert not relative.is_absolute() and '..' not in relative.parts
        if relative.suffix in ('.pyc','.pyo') or '__pycache__' in relative.parts:continue
        target=PROJECT/relative
        assert target.resolve().is_relative_to(PROJECT.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(bundle.read(member))
        runtime[relative.as_posix()]=sha(target)
assert runtime
shutil.copyfile(config_path,PROJECT/'.mcdev.json')
hosts={}
host_sources=list((ROOT/'tools').glob('*.py'))
host_sources+=list((ROOT/'.agents/skills/pyreact-debugging/scripts').glob('*.py'))
host_sources+=list((ROOT/'tools/native_wgc').glob('*'))
for source in host_sources:
    if not source.is_file():continue
    relative=source.relative_to(ROOT)
    target=PROJECT/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target);hosts[relative.as_posix()]=sha(target)
manifest={'schema':1,'owner':OWNER,'project':str(PROJECT),'source_commit':args.commit,
          'created_at':datetime.now(timezone.utc).isoformat(),'files':runtime,'host_files':hosts,
          'evidence_hosts':{path.name:sha(path) for path in HERE.glob('*.py')},
          'mcdev_sha256':sha(PROJECT/'.mcdev.json'),'source_archive_sha256':sha(archive),
          'auto_hot_reload':{key:False for key in keys},'manual_issues_closed':0,
          'production_files_modified':False,'candidate_profile_assignment':False,
          'source_archive_method':'git archive exact integration commit; pyc/pyo excluded from runtime'}
(HERE/'source-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n',encoding='utf8')
print(json.dumps({'owner':OWNER,'project':str(PROJECT),'commit':args.commit,'runtime_files':len(runtime),
 'host_files':len(hosts),'source_manifest_sha256':sha(HERE/'source-manifest.json'),
 'source_archive_sha256':sha(archive),'mc_started':False}))
