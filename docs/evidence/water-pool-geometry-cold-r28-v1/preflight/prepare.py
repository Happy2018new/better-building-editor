"""Derive the actual launch-prefix preflight for the two-row pool diagnostic."""
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OLD = WORK.with_name('water-formal-f-editor-preflight-v2')


def main():
    text = (OLD / 'verify.py').read_text(encoding='utf8')
    text = text.replace("WORK = OUT.with_name('water-formal-f-editor-v2')", "WORK = OUT.with_name('water-pool-geometry-cold-v1')")
    text = text.replace("assert set(request['cases'])==set(row['id'] for row in CASES)", "assert request['cases']==['pool'] and set(request['cases'])<=set(row['id'] for row in CASES)")
    text = text.replace('assert len(rows)==54', 'assert len(rows)==2')
    text = text.replace("assert s.liquid_profile.ui_offset_for_gui((300.,400.),2)==(0.,150.)", """assert s.liquid_profile.ui_offset_for_gui((300.,400.),2)==(0.,150.)
for gui in (1.,2.,3.,4.):
 for p,size in (((0.,0.),(366.6114,413.8420)),((-77.,0.),(418.,164.))):
  np,ns=s.liquid_profile.ui_geometry_for_gui(p,size,gui)
  scale=s.liquid_profile.ui_pose(52.9092,25.,35.,ns)[0]
  assert abs(scale*min(ns)-52.9092)<1e-8
  assert min(ns)==ns[0] and np[1]<=p[1]+1e-8 and np[1]+ns[1]>=p[1]+size[1]-1e-8
  assert abs(np[1]+ns[1]/2.-min(ns)/gui-p[1]-size[1]/2.)<1e-8""")
    text = text.replace("    for name, text in payloads.items():", """    compiled_source = []
    for name in ('liquid_product_deployment.py', 'scene.py'):
        path = Path(binding['project']) / 'behavior_pack/modern_projection/projection' / name
        result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
            'import sys;compile(sys.stdin.read(),sys.argv[1],"exec")', str(path)],
            input=path.read_bytes(), capture_output=True)
        assert result.returncode == 0, (name, result.stderr)
        compiled_source.append(name)
    for name, text in payloads.items():""")
    text = text.replace("'python2_payloads_compiled': list(payloads)", "'python2_proposed_source_compiled': compiled_source, 'python2_payloads_compiled': list(payloads)")
    target = WORK / 'verify.py'
    assert not target.exists()
    target.write_text(text, encoding='utf8', newline='\n')


if __name__ == '__main__':
    main()
