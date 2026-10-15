"""Evaluation only: existing v2 chunks -> compact JSON -> zlib -> Base64.

No product clipboard/import UI is installed. The core also runs under the
embedded Python 2.7 for real codec timings, without building native geometry.
"""
from __future__ import print_function
import base64
import json
import random
import sys
import time
import zlib
from array import array
from collections import Counter


def dependencies():
    try:
        from modern_projection.projection.model import Document
        from modern_projection.projection.codec import to_data
    except ImportError:
        import os
        sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'behavior_pack'))
        from modern_projection.projection.model import Document
        from modern_projection.projection.codec import to_data
    return Document,to_data


def fixture(kind):
    Document,unused=dependencies()
    doc=Document((64,128,64),name='Clipboard benchmark')
    palette_size=256 if kind=='random256' else (65535 if kind=='random65535' else 16)
    values=[('assessment:block_%d'%i,0) for i in range(palette_size)]
    for value in values: doc.blocks.palette_id(value)
    rng=random.Random(500)
    for cy in range(8):
        for cz in range(4):
            for cx in range(4):
                key=(cx,cy,cz)
                if kind=='empty': continue
                if kind=='solid':
                    doc.blocks.fill_chunk(key,values[0]);continue
                cells=array('H')
                for y in range(16):
                    for z in range(16):
                        for x in range(16):
                            gx,gy,gz=cx*16+x,cy*16+y,cz*16+z
                            if kind=='shell':
                                identity=1 if gx in (0,63) or gy in (0,127) or gz in (0,63) else 0
                            elif kind=='building':
                                # Repeated floors, external walls/windows and pillars.
                                solid=(gy%8==0 or gx in (0,63) or gz in (0,63) or (gx%12==0 and gz%12==0))
                                identity=1+(gy//8)%4 if solid else 0
                                if solid and gx in (0,63) and 2<=gy%8<=5 and 2<=gz%8<=5:identity=5
                            else: identity=rng.randrange(1,palette_size+1)
                            cells.append(identity)
                counts=Counter(cells)
                if counts.get(0)==4096:continue
                doc.blocks.chunks[key]=cells
                doc.blocks.owned.add(key)
                doc.blocks.count+=4096-counts.get(0,0)
                for identity,count in counts.items():
                    if identity:doc.blocks.counts[doc.blocks.palette[identity]]+=count
                for y in range(16): doc.blocks.layers[cy*16+y]+=sum(bool(v) for v in cells[y*256:(y+1)*256])
                doc.blocks.compact(key)
    # Exclude never-used palette entries, as a share exporter should do.
    if kind in ('empty','solid','shell','building'):
        used=1 if kind!='building' else 5
        doc.blocks.palette=doc.blocks.palette[:used+1] if kind!='empty' else doc.blocks.palette[:1]
        doc.blocks.palette_ids=dict((v,i) for i,v in enumerate(doc.blocks.palette))
    return doc


def measure(kind, retain=False):
    Document,to_data=dependencies()
    doc=fixture(kind)
    started=time.time()
    payload=json.dumps(to_data(doc),ensure_ascii=True,separators=(',',':')).encode('ascii')
    json_time=time.time()-started
    started=time.time()
    packed=zlib.compress(payload,6)
    text='MP1:'+base64.b64encode(packed).decode('ascii')+':%08x'%(zlib.crc32(payload)&0xffffffff)
    encode_time=json_time+time.time()-started
    started=time.time()
    restored=zlib.decompress(base64.b64decode(text.split(':')[1]))
    assert '%08x'%(zlib.crc32(restored)&0xffffffff)==text.split(':')[2]
    result=Document.from_data(json.loads(restored.decode('ascii')))
    decode_time=time.time()-started
    assert result.size==doc.size and result.blocks==doc.blocks
    row=dict(case=kind,blocks=len(doc.blocks),palette=len(doc.blocks.palette),json_bytes=len(payload),
             compressed_bytes=len(packed),characters=len(text),encode_ms=round(encode_time*1000,2),
             decode_ms=round(decode_time*1000,2))
    if retain:return row,text
    return row


def assess():
    return [measure(kind) for kind in ('empty','solid','shell','building','random16','random256','random65535')]


if __name__=='__main__':
    from pathlib import Path
    result={'runtime':sys.version,'cases':assess()}
    target=Path(__file__).resolve().parents[1]/'.runtime/stage50_share_host.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
