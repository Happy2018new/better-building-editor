"""Start the existing exact owner-scoped watcher only after separate root grant."""
import hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OWNER='portal-r28-gui-anchor-v4'
def main():
 bound=json.loads((HERE/'external-host-binding.json').read_bytes())
 assert all(hashlib.sha256((ROOT/key).read_bytes()).hexdigest()==value for key,value in bound.items())
 assert not (HERE/'assert-watch').exists()
 command=[sys.executable,'-B','-X','utf8',str(ROOT/'.runtime/round-20261023/water-anchor-watcher-v7/watch_owned_disabled_skin_assert_r28_v7.py'),
  '--owner',OWNER,'--until','2026-10-23T07:25:00+08:00','--output',str(HERE/'assert-watch'),'--detach']
 result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8',check=True)
 receipt={'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'result':json.loads(result.stdout)}
 (HERE/'assert-watch-start.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8');print(result.stdout)
if __name__=='__main__':main()
