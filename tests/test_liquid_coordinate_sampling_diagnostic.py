"""Nearest source texel selection uses independent explicit coordinate expectations."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from diagnose_liquid_coordinate_sampling import nearest_templates
from measure_native_liquid_side_uv import Hypothesis


class SamplingDiagnosticTests(unittest.TestCase):
    def test_quarter_edges_and_centers_have_distinct_nearest_texels(self):
        frame=np.zeros((32,32,4),dtype=np.uint8)
        frame[:,:,0]=np.arange(32)[None,:]
        frame[:,:,1]=np.arange(32)[:,None]
        grid={'u':[.12,.2,.88],'height':[.5,.5,.5],'top':[.8,.8,.8]}
        edge=Hypothesis('nw','bottom','identity',1.,False,0.,'edges')
        center=Hypothesis('nw','bottom','identity',1.,False,0.,'centers')
        np.testing.assert_array_equal(nearest_templates(frame,grid,edge)[:,0],[1,3,14])
        np.testing.assert_array_equal(nearest_templates(frame,grid,center)[:,0],[2,3,13])
        np.testing.assert_array_equal(nearest_templates(frame,grid,edge)[:,1],[8,8,8])

    def test_quadrant_offset_and_d4_are_applied_before_texel_selection(self):
        frame=np.zeros((32,32,4),dtype=np.uint8)
        frame[:,:,0]=np.arange(32)[None,:]
        frame[:,:,1]=np.arange(32)[:,None]
        grid={'u':[.25],'height':[.25],'top':[.5]}
        hypothesis=Hypothesis('se','stretch','rot90',1.,False,0.,'edges')
        np.testing.assert_array_equal(nearest_templates(frame,grid,hypothesis)[0,:2],[24,28])


if __name__=='__main__':unittest.main()
