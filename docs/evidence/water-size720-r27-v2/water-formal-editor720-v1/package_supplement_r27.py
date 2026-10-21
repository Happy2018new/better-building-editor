"""Add immutable R27 formal-failure/camera/anchor evidence beside the older pack."""
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
ROUND=Path(__file__).resolve().parent.parent
OUT=ROOT/'docs/evidence/water-size720-r27-v2'
LIMIT=240000
ALLOWED={'.json','.py','.patch','.txt','.png'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists(),'Preserve the original and every previous supplement'
    original=ROOT/'docs/evidence/water-size720-r27-v1/index.json'
    original_raw=original.read_bytes()
    old=json.loads(original_raw)
    included={(entry['original_raw_path'],entry['original_raw_sha256']) for entry in old['entries']}
    files={}

    def add(label,path):
        assert path.is_file(),path
        if (str(path.resolve()),sha(path.read_bytes())) not in included:files[label]=path

    for label in ('water-formal-editor720-v1','water-camera-signal-v1','water-camera-signal-v2',
                  'water-anchor-calibration-v1','water-anchor-calibration-v2'):
        directory=ROUND/label
        for path in directory.rglob('*'):
            if not path.is_file() or path.suffix not in ALLOWED:continue
            relative=path.relative_to(directory)
            if any('_burst' in part for part in relative.parts[:-1]) and path.name!='manifest.json':continue
            # A later native run gets its own capture supplement. This package freezes preparation only.
            if relative.parts[0]=='captures':continue
            add(label+'/'+relative.as_posix(),path)
    directory=ROUND/'water-size720-v3'
    for path in directory.iterdir():
        if path.is_file() and path.suffix in ALLOWED:add('water-size720-v3/'+path.name,path)
    books=ROUND/'books-editor-v1/camera-signal-review-v1'
    for path in books.iterdir():
        if path.is_file() and path.suffix in ALLOWED:add('independent-camera-review/'+path.name,path)
    launch=json.loads((ROUND/'water-formal-editor720-v1/launch/launch.json').read_bytes())
    registry=Path(launch['session_file'])
    session=json.loads(registry.read_bytes())
    assert session['state']=='stopped'
    add('formal-registry/session.json',registry)
    add('formal-registry/mcdk.log',Path(session['log']))
    burst=next((ROUND/'water-formal-editor720-v1').glob('*_burst'))
    pngs=sorted(burst.glob('frame_*.png'))
    if pngs:
        for path in (pngs[0],pngs[len(pngs)//2],pngs[-1]):add('formal-selected-burst/'+path.name,path)
    secrets=set()
    redactions={}

    def discover(value,location,found):
        if isinstance(value,dict):
            for key,item in value.items():
                child=location+'.'+key
                if isinstance(item,str) and len(item)>=8 and ('token' in key.lower() or key.lower() in
                    ('authorization','api_key','apikey','secret')) and not key.lower().endswith('sha256'):
                    secrets.add(item);found.append(child)
                else:discover(item,child,found)
        elif isinstance(value,list):
            for index,item in enumerate(value):discover(item,location+'[%d]'%index,found)
        elif isinstance(value,str) and value.lstrip().startswith(('{','[')):
            try:nested=json.loads(value)
            except ValueError:return
            discover(nested,location+':decoded_json',found)

    for label,path in files.items():
        if path.suffix=='.json':
            found=[]
            discover(json.loads(path.read_bytes()),'$',found)
            redactions[label]=found
    OUT.mkdir(parents=True)
    entries=[]
    for label,path in sorted(files.items()):
        raw=path.read_bytes()
        entry={'logical_name':label,'original_raw_path':str(path.resolve()),'original_raw_sha256':sha(raw),
               'original_raw_bytes':len(raw),'redacted_fields':redactions.get(label,[])}
        target=OUT/label
        target.parent.mkdir(parents=True,exist_ok=True)
        if path.suffix=='.png':
            encoded=raw;encoding='png';reconstructable=True
            if len(raw)>LIMIT:
                image=Image.open(io.BytesIO(raw)).convert('RGB')
                for quality in range(95,44,-5):
                    memory=io.BytesIO();image.save(memory,'JPEG',quality=quality,optimize=True,subsampling=0)
                    encoded=memory.getvalue()
                    if len(encoded)<LIMIT:break
                assert len(encoded)<LIMIT
                target=target.with_suffix('.jpg');encoding='jpeg';reconstructable=False
                entry.update(lossy_visual_reference=True,jpeg_quality=quality,full_resolution=list(image.size))
            target.write_bytes(encoded)
            entry.update(encoding=encoding,original_bytes_reconstructable=reconstructable,
                derived_parts=[{'path':target.relative_to(OUT).as_posix(),'sha256':sha(encoded),'bytes':len(encoded)}])
        else:
            text=raw.decode('utf-8-sig');occurrences=0
            for secret in sorted(secrets,key=len,reverse=True):
                occurrences+=text.count(secret);text=text.replace(secret,'[REDACTED_SESSION_TOKEN]')
            sanitized=text.encode('utf-8');zipped=len(sanitized)>100000
            encoded=gzip.compress(sanitized,mtime=0) if zipped else sanitized
            if zipped:target=Path(str(target)+'.gz')
            parts=[]
            chunks=[encoded[index:index+LIMIT] for index in range(0,len(encoded),LIMIT)] or [b'']
            for index,chunk in enumerate(chunks):
                destination=Path(str(target)+('.%03d'%(index+1) if len(chunks)>1 else ''))
                destination.write_bytes(chunk)
                parts.append({'path':destination.relative_to(OUT).as_posix(),'sha256':sha(chunk),'bytes':len(chunk)})
            entry.update(encoding='gzip' if zipped else 'utf8',decoded_sanitized_sha256=sha(sanitized),
                         decoded_sanitized_bytes=len(sanitized),redaction_occurrences=occurrences,
                         original_bytes_reconstructable=sanitized==raw,derived_parts=parts)
        entries.append(entry)
    pages=[]
    for number,start in enumerate(range(0,len(entries),75),1):
        rows=entries[start:start+75]
        data=(json.dumps({'schema':1,'entries':rows},indent=2)+'\n').encode('utf-8')
        assert len(data)<LIMIT
        path=OUT/('entries-%03d.json'%number)
        path.write_bytes(data)
        pages.append({'path':path.name,'sha256':sha(data),'bytes':len(data),'entries':len(rows)})
    index={'schema':2,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'supplement_to':{'path':str(original.resolve()),'sha256':sha(original_raw),'entries':len(old['entries'])},
        'scope':['Nontrace formal editor720 failed attempt, guard/restoration/actual exit',
                 'Gap v1/v2 mistakes retained, corrected v3 and static RPC boundary',
                 'Camera signal v1 rejection, actual v2 repair and independent counterexamples',
                 'Original failed flow ROI, GUI anchor hypothesis and actual image references',
                 'Independent neutral/matrix source and v1/v2 host preparation only'],
        'excluded_scope':['Full burst images','Source archives','Future native anchor run results'],
        'source_contract_sha256':'a564563ecf20f74b786565aaf0516575ab34c448b370a2bb2199319dc6b5c194',
        'diagnostic_source_contract_sha256':'334717aae34a1980dcb8c30a0fe50e596bbd4d027889a8315d5d9a67cb01c402',
        'formal_A_accepted':False,'world_qualification_granted':False,'production_admission_performed':False,
        'manual_closures_added':0,'original_raws_modified':False,'secret_values_discovered':len(secrets),
        'entry_count':len(entries),'entry_pages':pages,'single_file_limit_bytes':LIMIT}
    indexraw=(json.dumps(index,indent=2)+'\n').encode('utf-8')
    (OUT/'index.json').write_bytes(indexraw)
    for entry in entries:
        data=b''.join((OUT/part['path']).read_bytes() for part in entry['derived_parts'])
        assert all(sha((OUT/part['path']).read_bytes())==part['sha256'] for part in entry['derived_parts'])
        if 'decoded_sanitized_sha256' in entry:
            decoded=gzip.decompress(data) if entry['encoding']=='gzip' else data
            assert sha(decoded)==entry['decoded_sanitized_sha256']
            assert not any(secret.encode('utf-8') in decoded for secret in secrets)
        assert sha(Path(entry['original_raw_path']).read_bytes())==entry['original_raw_sha256']
    assert original.read_bytes()==original_raw
    sizes=[path.stat().st_size for path in OUT.rglob('*') if path.is_file()]
    assert max(sizes)<=LIMIT
    print(json.dumps({'index_sha256':sha(indexraw),'entries':len(entries),'entry_pages':len(pages),
                      'largest_file_bytes':max(sizes),'total_bytes':sum(sizes),'secret_values_in_output':0,
                      'original_raws_preserved':True,'old_index_unchanged':True}))


if __name__=='__main__':main()
