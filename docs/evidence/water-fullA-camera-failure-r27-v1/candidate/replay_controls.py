"""Execute the original control body with only its output directory redirected."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy
import sys

WORK=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    output=args.output_root.resolve()
    assert not output.exists()
    source=WORK/'run_controls.py'
    raw=source.read_bytes()
    namespace=runpy.run_path(str(source),run_name='controls_import_only')
    function=next(node for node in ast.parse(raw).body if isinstance(node,ast.FunctionDef) and node.name=='main')
    assert isinstance(function.body[0],ast.Assign) and isinstance(function.body[0].targets[0],ast.Name)
    assert function.body[0].targets[0].id=='out'
    function.body[0].value=ast.Name(id='INDEPENDENT_OUTPUT_ROOT',ctx=ast.Load())
    namespace['INDEPENDENT_OUTPUT_ROOT']=output
    module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    exec(compile(module,str(source)+':output-only-redirect','exec'),namespace)
    namespace['main']()
    controls=json.loads((output/'report.json').read_bytes())
    receipt={'schema':1,'passed':controls['passed'],'original_control_source_sha256':hashlib.sha256(raw).hexdigest(),
        'only_AST_assignment_replaced':'main.out = independent output directory',
        'control_logic_or_inputs_changed':False,'MC_started':False,'RPC_dispatched':False}
    with (output/'replay-host-receipt-v1.json').open('x',encoding='ascii') as stream:json.dump(receipt,stream,indent=2)


if __name__=='__main__':
    main()
