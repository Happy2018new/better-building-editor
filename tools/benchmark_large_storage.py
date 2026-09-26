"""Standalone mixed-material maximum-volume codec benchmark; no engine/world IO."""
import json
import random
import sys
import time
from array import array
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.model import Document, MAX_AXES, MAX_VOLUME
from projection.codec import encode_chunk


def main():
    rng = random.Random(9826)
    values = array('H', (rng.randrange(1, 17) for unused in range(4096)))
    chunks = []
    for y in range((MAX_AXES[1]+15)//16):
        top = array('H', (v if (i//256+y*16)<MAX_AXES[1] else 0 for i,v in enumerate(values)))
        part = encode_chunk((0,0,0),top)[3]
        chunks.extend([x,y,z,part] for z in range((MAX_AXES[2]+15)//16) for x in range((MAX_AXES[0]+15)//16))
    source = {'version': 2, 'name': 'mixed material benchmark', 'size': list(MAX_AXES),
              'blockCount': MAX_VOLUME, 'palette': [['minecraft:air', 0]] + [['minecraft:wool', i] for i in range(16)],
              'chunks': chunks}
    started = time.perf_counter()
    document = Document.from_data(source)
    decoded = time.perf_counter() - started
    assert len(document.blocks) == MAX_VOLUME
    assert len(document.blocks.chunks) == 112
    assert all(len(chunk) == 4096 for chunk in document.blocks.chunks.values())
    corner = tuple(v-1 for v in MAX_AXES)
    expected = ('minecraft:wool', values[(corner[1]%16)*256+(corner[2]%16)*16+corner[0]%16]-1)
    assert document.get(corner) == expected
    started = time.perf_counter()
    encoded = document.to_data()
    encoding = time.perf_counter() - started
    assert encoded['chunks'] == sorted(source['chunks'])
    clone = document.blocks.copy()
    document.blocks[corner] = ('minecraft:stone', 0)
    assert clone.get(corner) == expected
    report = {'cells': len(document.blocks), 'mixedChunks': len(document.blocks.chunks),
              'voxelArrayBytes': len(chunks) * 8192, 'storeEstimateBytes': document.blocks.memory_bytes(),
              'hostDecodeSeconds': decoded, 'hostEncodeSeconds': encoding,
              'processRssBytes': psutil.Process().memory_info().rss,
              'hostPython': sys.version, 'scope': 'Host Python only; not engine timing or world writes'}
    output = ROOT / '.runtime/large_storage_benchmark.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
