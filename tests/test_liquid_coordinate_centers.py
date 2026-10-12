"""Absolute texture-center locations are selected only from independent geometry."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from diagnose_liquid_coordinate_centers import center_grid
from diagnose_liquid_coordinate_sampling import nearest_templates
from liquid_coordinate_markers import marker_frame
from measure_native_liquid_side_uv import Hypothesis


class CenterGridTests(unittest.TestCase):
    def test_centers_follow_absolute_height_and_preserve_insets(self):
        surface={'cell_origin':[6,96,6],'corner_heights':[.2,.4,.8,.4],'side':'north'}
        grid=center_grid(surface);u,height,top=(np.asarray(grid[key]) for key in ('u','height','top'))
        np.testing.assert_allclose(u*16-.5,np.asarray(grid['source_texels'])[:,0])
        np.testing.assert_allclose((1-height)*16-.5,np.asarray(grid['source_texels'])[:,1])
        self.assertTrue(np.all((u>=.12)&(u<=.88)))
        self.assertTrue(np.all((height/top>=.12)&(height/top<=.88)))
        world=np.asarray(grid['world_points'])
        np.testing.assert_allclose(world[:,0],6+u);np.testing.assert_allclose(world[:,1],96+height)
        np.testing.assert_array_equal(world[:,2],np.full(len(u),6.))

    def test_west_winding_and_too_thin_geometry(self):
        surface={'cell_origin':[6,96,7],'corner_heights':[.2,.4,.8,.4],'side':'west'}
        grid=center_grid(surface);world=np.asarray(grid['world_points'])
        np.testing.assert_allclose(world[:,2],8-np.asarray(grid['u']))
        with self.assertRaises(ValueError):center_grid(dict(surface,corner_heights=[.01]*4))

    def test_nearest_center_probe_cannot_identify_pixel_mapping(self):
        surface={'cell_origin':[6,96,6],'corner_heights':[.2,.4,.8,.4],'side':'north'}
        grid=center_grid(surface);frame=marker_frame(32,271)
        edge=Hypothesis('nw','bottom','identity',1.,False,0.,'edges')
        center=Hypothesis('nw','bottom','identity',1.,False,0.,'centers')
        np.testing.assert_array_equal(nearest_templates(frame,grid,edge),nearest_templates(frame,grid,center))


if __name__=='__main__':unittest.main()
