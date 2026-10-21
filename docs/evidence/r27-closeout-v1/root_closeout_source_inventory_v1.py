"""Rehash the exact tested scopes without running tests or changing original receipts."""
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'.runtime/round-20261022'
driver=RUN/'integration-v1/run_integration.py'
baseline=RUN/'integration-v1/source-after.json'
assert hashlib.sha256(driver.read_bytes()).hexdigest()=='ffe3fd02419a766f03f93dd52c95e2cccf32dca343d32c9a155ddb63b08aaa28'
assert hashlib.sha256(baseline.read_bytes()).hexdigest()=='1db2a50b4718da1d39612db08e6f5a780390afd30364a07f541c36258a0280e1'
tree=ast.parse(driver.read_bytes(),filename=str(driver))
nodes=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='before' for target in node.targets):break
    nodes.append(node)
scope={'__file__':str(driver),'__name__':'_root_source_identity_only'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(driver)+':source-identity-only','exec'),scope)
after=scope['source_identity']()
before=json.loads(baseline.read_bytes())
changed=sorted(path for path in before['files'].keys()|after['files'].keys() if before['files'].get(path)!=after['files'].get(path))
assert not changed,changed
report=dict(schema=1,read_at=datetime.now().astimezone().isoformat(),passed=True,
    reference_inventory_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
    source_inventory_driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),
    current_head=after['head'],scopes=after['source_scope'],files_rehashed=len(after['files']),
    bytes_rehashed=sum(row['bytes'] for row in after['files'].values()),changed_files=changed,
    additional_tests_run=0,clean_HEAD_only=False,CPU_regression_still_applies_to_unchanged_worktree_sources=True,
    new_GPU_or_manual_qualification=False)
target=RUN/'root-closeout-source-inventory-v1.json'
assert not target.exists()
target.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
print(json.dumps(report))
