"""Archive immutable R27 anchor failure, reviewed reader repair and new diagnostic attempt."""
from datetime import datetime,timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
ROUND=Path(__file__).resolve().parent.parent
OUT=ROOT/'docs/evidence/water-size720-r27-v3'
LIMIT=240000
ALLOWED={'.json','.py','.patch','.txt','.png'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists(),'Preserve the original and every previous supplement'
    old_paths=[ROOT/'docs/evidence/water-size720-r27-v1/index.json',
               ROOT/'docs/evidence/water-size720-r27-v2/index.json']
    old_raws={str(path):path.read_bytes() for path in old_paths}
    old_entries=[]
    for path in old_paths:
        index=json.loads(path.read_bytes())
        old_entries.extend(index.get('entries',[]))
        for page in index.get('entry_pages',[]):
            old_entries.extend(json.loads((path.parent/page['path']).read_bytes())['entries'])
    included={(entry['original_raw_path'],entry['original_raw_sha256']) for entry in old_entries}
    files={}

    def add(label,path):
        assert path.is_file(),path
        if (str(path.resolve()),sha(path.read_bytes())) not in included:files[label]=path

    attempt=ROUND/'water-anchor-calibration-v6'
    group_path=attempt/'group-execution-v1.json'
    assert group_path.exists(),'Package only after the separate attempt actually finishes'
    group=json.loads(group_path.read_bytes())
    assert group.get('elapsed_seconds') is not None
    assert all(group.get('exact_identities_absent',{}).get(kind) for kind in ('game','mcdk'))
    gui_group=json.loads((ROUND/'water-gui-offset-lifecycle-v4/group-execution-v1.json').read_bytes())
    assert gui_group['completed'] and gui_group.get('elapsed_seconds') is not None
    assert all(gui_group['exact_identities_absent'][kind] for kind in ('game','mcdk'))
    labels=('water-anchor-calibration-v3','water-anchor-calibration-v4','water-anchor-calibration-v5','water-anchor-calibration-v6',
            'water-anchor-watcher-v4','water-anchor-watcher-v5','water-anchor-analysis-v1',
            'root-anchor-v3-review','root-watcher-v5-review','root-anchor-v4-review','root-anchor-v5-review-v5',
            'water-anchor-calibration-v6-static-review-v1','root-anchor-v6-static-review-v1',
            'water-ui-geometry-observer-v1','water-ui-geometry-observer-static-v1',
            'water-ui-geometry-observer-v2','water-ui-geometry-observer-static-v2',
            'water-ui-fixed-hold-controls-v2','root-ui-observer-controls-v1',
            'root-water-ui-observer-review-v1','root-ui-observer-static-v1','root-ui-observer-static-v2',
            'root-water-native-viewport-measurement-v1',
            'water-gui-offset-candidate-v1','water-gui-offset-lifecycle-v2',
            'water-gui-offset-lifecycle-v3','water-gui-offset-lifecycle-v4',
            'water-gui-offset-scene-controls-v2','water-gui-offset-static-v2',
            'water-gui-offset-static-v3','water-gui-offset-static-v4',
            'root-water-gui-offset-review-v4','root-water-gui-static-v4','root-water-gui-controls-v4',
            'root-water-gui-v4-static','root-water-gui-v4-controls',
            'water-gui-offset-scene-analysis-v1')
    for label in labels:
        directory=ROUND/label
        if not directory.exists():continue
        for path in directory.rglob('*'):
            if not path.is_file() or path.suffix not in ALLOWED:continue
            relative=path.relative_to(directory)
            if any('_burst' in part for part in relative.parts[:-1]) and path.name!='manifest.json':continue
            add(label+'/'+relative.as_posix(),path)
    for label in ('water-anchor-calibration-v3','water-anchor-calibration-v4','water-anchor-calibration-v6',
                  'water-ui-geometry-observer-v1','water-ui-geometry-observer-v2',
                  'water-gui-offset-lifecycle-v2','water-gui-offset-lifecycle-v3','water-gui-offset-lifecycle-v4'):
        launch_path=ROUND/label/'launch/launch.json'
        if not launch_path.exists():continue
        launch=json.loads(launch_path.read_bytes())
        if not launch.get('session_file'):continue
        registry=Path(launch['session_file']);session=json.loads(registry.read_bytes())
        assert session['state']=='stopped'
        add(label+'-registry/session.json',registry)
        log=Path(session['log'])
        if log.exists():add(label+'-registry/mcdk.log',log)
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
        'supplement_to':[{'path':str(path.resolve()),'sha256':sha(old_raws[str(path)])} for path in old_paths],
        'scope':['V3 neutral/matrix launch failure, watcher-health stop and exact cleanup',
                 'V4 reader draft real Windows lock-control failure retained',
                 'V5 native Win32 reader candidate and 15 controls, independent root review',
                 'V4 integer-tint payload error, exact cleanup and source audit',
                 'Separate V5 lifecycle, all-138 actual Python2 CONFIGURE controls, original LF core byte refusal and exact helper retirement',
                 'V6 full pre-Popen actual launcher controls, hidden zero-size contract failure and late final same-handle observer',
                 'Separate minimal SDK native geometry observer with explicit diagnostic Panel wrapper; only actual saved stages included',
                 'Predeclared neutral/matrix projection analysis, synthetic math controls and independent review material',
                 'Actual observer v2 twelve-state UI geometry, fixed root followup and 38 native pixel/matrix captures',
                 'Original global-mask debug-text contamination retained; separate SDK-parent-rectangle derived measurement scope',
                 'Narrow three-file private Product water GUI candidate and actual Python2 cache/resize/geometry controls',
                 'Only saved private normal Scene attempts and their exact cleanup, if actually performed'],
        'excluded_scope':['Full burst images','Source archives','Product qualification or manual acceptance'],
        'source_contract_sha256':'a564563ecf20f74b786565aaf0516575ab34c448b370a2bb2199319dc6b5c194',
        'diagnostic_source_contract_sha256':'334717aae34a1980dcb8c30a0fe50e596bbd4d027889a8315d5d9a67cb01c402',
        'private_gui_candidate_source_contract_sha256':'45985a50b720b72cd9dd55a68cdeb7064fffa7201c79084b1ec8953ca11d5424',
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
    assert all(path.read_bytes()==old_raws[str(path)] for path in old_paths)
    sizes=[path.stat().st_size for path in OUT.rglob('*') if path.is_file()]
    assert max(sizes)<=LIMIT
    print(json.dumps({'index_sha256':sha(indexraw),'entries':len(entries),'entry_pages':len(pages),
                      'largest_file_bytes':max(sizes),'total_bytes':sum(sizes),'secret_values_in_output':0,
                      'original_raws_preserved':True,'old_index_unchanged':True}))


if __name__=='__main__':main()
