"""Compile portal shader variants and verify installed resource ownership."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
NATIVE = Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data/shaders/glsl')


def run(args):
    contract=json.loads((args.project/args.contract).read_bytes())
    materials=json.loads((args.project/'resource_pack/materials/entity.material').read_bytes())['materials']
    models=json.loads((args.project/'resource_pack/models/netease_models.json').read_bytes())
    if (any(materials.get(key)!=value for key,value in contract['materials'].items()) or
            any(models.get(key)!=value for key,value in contract['models'].items())):
        raise ValueError('Installed portal registrations differ from the generated contract')
    for relative,expected in contract['output_sha256'].items():
        if relative in ('resource_pack/materials/entity.material','resource_pack/models/netease_models.json'):
            continue
        if hashlib.sha256((args.project/relative).read_bytes()).hexdigest()!=expected:
            raise ValueError('Installed portal resource differs: '+relative)
    args.output.mkdir(parents=True,exist_ok=False)
    compiler=ROOT/'.runtime/renderdoc/portable/RenderDoc_1.46_64/plugins/spirv/glslangValidator.exe'
    shaders=set(value[key] for value in contract['materials'].values() for key in ('vertexShader','fragmentShader'))
    receipts=[]
    for version in (100,300):
        for flags in ((),('USE_SKINNING','NETEASE_SKINNING'),('USE_SKINNING','NETEASE_SKINNING','USE_INSTANCE')):
            for relative in sorted(shaders):
                stage='vert' if relative.endswith('.vertex') else 'frag'
                path=args.output/('%s-%s-%s.%s' % (Path(relative).name,version,'-'.join(flags) or 'plain',stage))
                path.write_text(shader_source(args.project/'resource_pack'/relative,NATIVE,version,flags),encoding='ascii')
                result=subprocess.run([str(compiler),'-S',stage,str(path)],capture_output=True,text=True)
                receipt={'name':path.name,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
                if result.returncode and version==100 and stage=='vert' and 'USE_SKINNING' in flags:
                    baseline=args.output/('baseline-'+path.name)
                    baseline.write_text(shader_source(NATIVE/'netease_skeleton.vertex',NATIVE,version,flags),encoding='ascii')
                    original=subprocess.run([str(compiler),'-S',stage,str(baseline)],capture_output=True,text=True)
                    receipt.update(baseline_returncode=original.returncode,baseline_stdout=original.stdout,
                        inherited_unsupported_mat3x4=bool(original.returncode and
                            'unexpected IDENTIFIER' in original.stdout and 'unexpected IDENTIFIER' in result.stdout))
                receipts.append(receipt)
    (args.output/'compile.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='ascii')
    if any(row['returncode'] and not row.get('inherited_unsupported_mat3x4') for row in receipts):
        raise ValueError('Portal shader variant failed offline compilation')
    print(json.dumps({'compiled':len(receipts),'resources_verified':True}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=ROOT)
    parser.add_argument('--contract',default='tools/data/portal_resource_contract_nemc310_v1.json')
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':
    main()
