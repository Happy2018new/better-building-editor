"""Standalone mixed-material maximum-volume codec benchmark; no engine/world IO."""
import json
import random
import sys
import time
from array import array
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/HelloScript'))
from projection.model import Document
from projection.codec import encode_chunk


def main():
    rng = random.Random(9826)
    values = array('H', (rng.randrange(1, 17) for unused in range(4096)))
    payload = encode_chunk((0, 0, 0), values)[3]
    source = {'version': 2, 'name': 'mixed material benchmark', 'size': [256, 384, 256],
              'blockCount': 25165824, 'palette': [['minecraft:air', 0]] + [['minecraft:wool', i] for i in range(16)],
              'chunks': [[x, y, z, payload] for y in range(24) for z in range(16) for x in range(16)]}
    started = time.perf_counter()
    document = Document.from_data(source)
    decoded = time.perf_counter() - started
    assert len(document.blocks) == 25165824
    assert len(document.blocks.chunks) == 6144
    assert all(len(chunk) == 4096 for chunk in document.blocks.chunks.values())
    assert document.get((255, 383, 255)) == ('minecraft:wool', values[-1] - 1)
    started = time.perf_counter()
    encoded = document.to_data()
    encoding = time.perf_counter() - started
    assert encoded['chunks'] == sorted(source['chunks'])
    clone = document.blocks.copy()
    document.blocks[(255, 383, 255)] = ('minecraft:stone', 0)
    assert clone.get((255, 383, 255)) == ('minecraft:wool', values[-1] - 1)
    report = {'cells': len(document.blocks), 'mixedChunks': len(document.blocks.chunks),
              'voxelArrayBytes': 6144 * 8192, 'storeEstimateBytes': document.blocks.memory_bytes(),
              'hostDecodeSeconds': decoded, 'hostEncodeSeconds': encoding,
              'processRssBytes': psutil.Process().memory_info().rss,
              'hostPython': sys.version, 'scope': 'Host Python only; not engine timing or world writes'}
    output = ROOT / '.runtime/large_storage_benchmark.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
