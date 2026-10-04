import itertools
import json
import math
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.outline_preview import OUTLINE_BLOCK, OutlinePreview, outline_color
from projection.grid_preview import GridView
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS
from test_grid_preview import Control


def float32(value):
    return struct.unpack('f', struct.pack('f', value))[0]


class OutlinePreviewTests(unittest.TestCase):
    def test_packet_survives_native_float32_at_size_and_animation_boundaries(self):
        for size in itertools.product((1,2,64),(1,2,128),(1,2,64)):
            for distance,phase in itertools.product((-300.,-.015625,0.,.5,300.),(0,1,127,128,255)):
                red,green,blue=map(float32,outline_color(size,.65,distance,phase*6./256))
                packet=math.floor(float32(float32(green*524288)+.5))
                actual=(packet%64+1,packet//64%128+1,packet//8192+1)
                self.assertEqual(size,actual)
                state=math.floor(float32(blue*16777216))
                self.assertEqual(phase,state%256)
                self.assertEqual(distance,(state//256-32768)/64.)
                tag=round(float32(red*255))
                self.assertEqual(225,tag)
                self.assertAlmostEqual(.65,float32(float32(red*255)-tag)*8,places=3)
        self.assertEqual(224,round(outline_color((1,1,1),.3,-300)[0]*255))
        self.assertEqual(226,round(outline_color((1,1,1),.3,0,0,True)[0]*255))

    def test_target_animation_clipping_and_visibility_reuse_geometry(self):
        builds=[]
        session=SimpleNamespace(scene_origin=(16,32,16),
                                bridge=SimpleNamespace(geometry=lambda p:builds.append(p) or 'outline'))
        view=GridView(lambda p:(p[0]*10,p[1]*10),(0,0,1),10,
                      (1,-65,35),(400,300),(.25,.5),.65,'first')
        target=((17,35,17),(22,35,22))
        outline,doll,image=OutlinePreview(),Control(),Control()
        outline.update(session,doll,image,view,target,spectrum=0)
        self.assertTrue(doll.visible)
        original=image.color
        outline.update(session,doll,image,view,target,plane=((0,0,1),3),spectrum=1)
        self.assertNotEqual(original,image.color)
        self.assertEqual(1,len(doll.submissions))
        outline.update(session,doll,image,view,target,invalid=True,spectrum=1)
        self.assertEqual(226,round(image.color[0]*255))
        outline.update(session,doll,image,view,None)
        self.assertFalse(doll.visible)
        outline.update(session,doll,image,view,((16,32,16),(79,159,79)))
        self.assertTrue(doll.visible)
        self.assertEqual(1,len(builds))
        self.assertEqual(2,len(doll.submissions))
        self.assertEqual({(OUTLINE_BLOCK,0)},set(builds[0].common))

    def test_failed_native_submission_is_retried(self):
        session=SimpleNamespace(scene_origin=(0,0,0),bridge=SimpleNamespace(geometry=lambda p:'outline'))
        view=GridView(lambda p:(0,0),(0,0,1),1,(1,0,0),(400,300),(0,0),.3,'same')
        outline,doll,image=OutlinePreview(),Control(),Control()
        native=doll.RenderBlockGeometryModel
        doll.RenderBlockGeometryModel=lambda params:False
        target=((0,0,0),(0,0,0))
        outline.update(session,doll,image,view,target)
        self.assertIsNone(outline.signature)
        doll.RenderBlockGeometryModel=native
        outline.update(session,doll,image,view,target)
        self.assertEqual(1,len(doll.submissions))

    def test_internal_outline_resource_is_hidden_and_encodes_twelve_edges(self):
        self.assertIn(OUTLINE_BLOCK,INTERNAL_RENDER_BLOCKS)
        block=json.loads((ROOT/'behavior_pack/netease_blocks/preview_outline.json').read_text())
        self.assertFalse(block['minecraft:block']['description']['register_to_creative_menu'])
        model=json.loads((ROOT/'resource_pack/models/netease_block/preview_outline.json').read_text())
        cubes=model['netease:block_geometry']['bones'][0]['cubes']
        self.assertEqual(12,len(cubes))
        for index,cube in enumerate(cubes):
            self.assertEqual([-16-index*32,0,0],cube['origin'])
            self.assertEqual([16,0,16],cube['size'])
            self.assertEqual({'up','down'},set(cube['uv']))


if __name__=='__main__':
    unittest.main()
