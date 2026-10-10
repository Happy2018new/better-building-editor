"""Chunk initialization matches exact cell semantics without per-cell world FFI."""
import unittest
from types import SimpleNamespace
from test_occupancy_review import Runtime,STONE
from modern_projection.projection.model import Document
from modern_projection.projection.occupancy import ProjectionOccupancy
from modern_projection.projection.occupancy_initial import prepare_chunk
from modern_projection.projection.large_preview import SurfacePalette
from modern_projection.projection.cell import AIR, make_cell

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
        expected={p for p in document.blocks if p[1] not in hidden and (layer is None or p[1]==layer)}
        self.assertEqual(expected,set(o.targets))
        expected_data = document.palette_data(lambda p: p in expected and state != 2)
        for key in ('common', 'extra'):
            self.assertEqual(dict((value, sorted(indices)) for value, indices in expected_data[key].items()),
                             dict((value, sorted(indices)) for value, indices in getattr(output, key).items()))
        self.assertEqual(expected_data['actor'], output.actor)
        self.assertEqual(sum(len(indices) for key in ('common', 'extra')
                             for indices in expected_data[key].values()), output.count)
        for data in (output.common, output.extra):
            actual=[i for group in data.values() for i in group]
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

    def test_initial_chunk_keeps_background_only_cells_and_client_actors(self):
        water = ('minecraft:water', 0)
        chest = ('minecraft:chest', 2)
        snow = ('minecraft:snow_layer', 2)
        actor = {'id': 'Chest', 'x': 16, 'y': 0, 'z': 0}
        document = Document((32, 16, 16), {
            (15, 0, 0): make_cell(AIR, water),
            (16, 0, 0): make_cell(chest, water, actor),
            (16, 1, 0): make_cell(('minecraft:short_grass', 0), snow),
        })
        self.build(document)
        self.build(document, state=2)
        self.build(document, hidden=(1,))

    def test_uniform_complete_chunk_expands_both_layers_without_world_reads(self):
        document = Document((32, 16, 16))
        document.blocks.fill_chunk((0, 0, 0), make_cell(STONE, ('minecraft:water', 0)))
        document.blocks.fill_chunk((1, 0, 0), make_cell(AIR, ('minecraft:water', 0)))
        self.build(document)
        self.build(document, state=2)

if __name__=='__main__':unittest.main()
