"""Compare only exported actual native inputs across the diagnostic phases."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'behavior_pack/modern_projection')]
from projection.cell import thaw,AIR
import trial_fixtures_v1 as fixtures
import trial_capture_v2 as host


def decode(wire):
    raw=base64.b64decode(wire['base64'],validate=True)
    assert wire['codec']=='cell.freeze-repr-utf8-base64' and len(raw)==wire['bytes']
    assert hashlib.sha256(raw).hexdigest()==wire['host_sha256']
    return thaw(ast.literal_eval(raw.decode('utf8')))


def text(value):
    if isinstance(value,bytes):return value.decode('utf8')
    if isinstance(value,dict):return {text(key):text(child) for key,child in value.items()}
    if isinstance(value,list):return [text(child) for child in value]
    if isinstance(value,tuple):return tuple(text(child) for child in value)
    return value


def structural(value):
    value=text(value)
    # Native cell-list order does not change the submitted geometry.
    for key in ('common','extra'):
        value[key]={tuple(material):tuple(sorted(indices)) for material,indices in value[key].items()}
    return value


def phase_maps(snapshot):
    out={}
    records=snapshot['records']
    assert records and len(records)%3==0
    for index in range(0,len(records),3):
        create,load,combine=records[index:index+3]
        assert [row['phase'] for row in (create,load,combine)]==['CreatePalette','Deserialize','Combine']
        assert all(row['result'] for row in (create,load,combine))
        assert create['palette_id']==load['palette_id']==combine['palette_id']
        assert load['native_serialized_after']==combine['native_serialized']
        match=re.fullmatch(r'modern_projection_buffer_\d_\d_([co])_(-?\d+)_(-?\d+)_(-?\d+)',combine['name'])
        assert match,'Unexpected current native part name'
        key=(combine['source_kind'],match.group(1),tuple(int(match.group(i)) for i in (2,3,4)))
        assert key not in out,'Duplicate actual native part in one phase'
        out[key]={'input':structural(decode(load['native_input'])),
          'serialized':structural(decode(combine['native_serialized'])),
          'logical_document':load['logical_document']}
    return out


def native_rows(palette):
    result=set()
    for layer in ('common','extra'):
        for material,indices in palette[layer].items():
            for index in indices:result.add((layer,material,index))
    assert not palette['actor'],'These eight fixtures contain no actor payload'
    return result


def compare_actual(old,new,item):
    assert old.keys()==new.keys(),'Actual native batches changed'
    cells={tuple(pos):(tuple(front),tuple(back)) for pos,front,back in item['cells']}
    changes=[]
    for key,prior in old.items():
        after=new[key]
        assert prior['logical_document']==after['logical_document']
        for boundary in ('input','serialized'):
            a,b=prior[boundary],after[boundary]
            assert {k:v for k,v in a.items() if k not in ('common','extra')}=={k:v for k,v in b.items() if k not in ('common','extra')},'Actual native metadata changed'
            added=native_rows(b)-native_rows(a)
            removed=native_rows(a)-native_rows(b)
            assert not added,'Unexpected actual native additions'
            for layer,material,index in sorted(removed):
                assert key[1]=='c' and layer=='common' and material==fixtures.WHITE
                volume=a['volume']
                packed=(index//volume[0]%volume[1],index//(volume[0]*volume[1]),index%volume[0])
                target=tuple(key[2][axis]+packed[axis]//4 for axis in range(3))
                neighbor=tuple(packed[axis]%4-1 for axis in range(3))
                assert neighbor==(0,-1,0),'Removed actual copied cell is not direct lower support'
                own=cells[target]
                below=cells[(target[0],target[1]-1,target[2])]
                assert own==(fixtures.WIRE,AIR) and below==(fixtures.WHITE,AIR),'Removed actual cell lacks complete dry logical admission'
                center=((target[1]%16*4+1)*64+(target[0]%16*4+1))*64+(target[2]%16*4+1)
                assert ('common',fixtures.WIRE,center) in native_rows(b),'Own wire target was removed'
                changes.append({'source_kind':key[0],'origin':key[2],'boundary':boundary,
                  'target':target,'removed_neighbor':neighbor,'material':material})
            if item['negative']:assert not removed,'Negative actual native boundary changed'
    if not item['negative']:assert changes,'Positive candidate actual native input never changed'
    return changes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=json.loads(args.report.read_bytes())
    assert report['completed'] and report['restored'] and not report['cleanup_errors']
    item=fixtures.fixture(report['fixture'])
    samples=report['samples']
    assert len(samples)==12
    results=[]
    for start in range(0,len(samples),4):
        group=samples[start:start+4]
        assert [row['mode'] for row in group]==['base','repeat','candidate','restored']
        maps=[]
        for number,sample in enumerate(group,start+1):
            assert sample['completed'] and sample['native_creation']['verified']
            snapshot=json.loads(args.report.with_name('phase-%02d-native.json'%number).read_bytes())
            maps.append(phase_maps(snapshot))
        assert maps[0]==maps[1]==maps[3],'Actual native base/repeat/restored changed'
        results.append({'group':[row['label'] for row in group],
          'actual_boundary_changes':compare_actual(maps[0],maps[2],item),
          'actual_base_repeat_restored_equal':True})
    result={'schema':'wire-r27-actual-native-delta-review-v2','passed':True,
      'report_sha256':host.sha(args.report),'groups':results,'runtime_calls':0,
      'uses_actual_exported_native_inputs':True,'uses_CPU_expected_palette_prediction':False,
      'GPU_qualified':False,'manual_closures':0}
    target=host.within_here(args.output)
    with target.open('xb') as stream:stream.write((json.dumps(result,indent=2)+'\n').encode('ascii'))
    print(json.dumps({'passed':True,'groups':len(results),'output':str(target),'GPU_qualified':False}))


if __name__=='__main__':main()
