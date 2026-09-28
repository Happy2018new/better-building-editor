"""Chunk initialization matches exact cell semantics without per-cell world FFI."""
import unittest
from types import SimpleNamespace
from test_occupancy_review import Runtime,STONE
from modern_projection.projection.model import Document
from modern_projection.projection.occupancy import ProjectionOccupancy
from modern_projection.projection.occupancy_initial import prepare_chunk
from modern_projection.projection.large_preview import SurfacePalette

class InitialChunkTests(unittest.TestCase):
    def build(self, document, state=1, hidden=(), layer=None):
        r=Runtime()
        session=SimpleNamespace(editor=SimpleNamespace(document=document,layer=layer),
             preview_hidden=lambda:hidden,solo_layer=layer is not None)
        b=SimpleNamespace(session=session,projection_serial=1,projection_occupancy=None,
                          factory=r,system=r,level='level')
        o=ProjectionOccupancy(b,(10,64,20))
        def begin(key):
            size=tuple(min(16,document.size[i]-key[i]*16) for i in range(3))
            o.bulk.initial=(key,(bytearray([state])*(size[0]*size[1]*size[2]),size))
        o.bulk.begin=begin
        output=SurfacePalette(document.size)
        for key in sorted(document.blocks.chunks):
            size=tuple(min(16,document.size[i]-key[i]*16) for i in range(3))
            for unused in prepare_chunk(o,document.blocks,key,size,output):pass
        expected=[p for p in document.blocks if p[1] not in hidden and (layer is None or p[1]==layer)]
        self.assertEqual(set(expected),set(o.targets))
        expected_indices={o.index(p) for p in expected} if state!=2 else set()
        actual=[i for group in output.common.values() for i in group]
        self.assertEqual(expected_indices,set(actual))
        self.assertEqual(len(expected_indices),output.count)
        self.assertEqual(len(actual),len(set(actual)))
        for key,common in o.cached.items():
            for value,indices in common.items():
                for slot,index in enumerate(indices):self.assertEqual(slot,o.slots[index])
        self.assertEqual(0,o.reads)
        return o

    def test_uniform_full_volume_air_and_occupied(self):
        document=Document((32,32,32))
        for x in range(2):
            for y in range(2):
                for z in range(2):document.blocks.fill_chunk((x,y,z),STONE)
        self.build(document)
        self.build(document,2)
        self.build(document,hidden=(0,7,16,31),layer=15)

    def test_mixed_partial_chunks_and_layers(self):
        document=Document((19,21,23),{(x,y,z):STONE for x in range(19)
            for y in range(21) for z in range(23) if (x+y+z)%5==0})
        self.build(document,hidden=(3,17))
        self.build(document,layer=20)

if __name__=='__main__':unittest.main()
