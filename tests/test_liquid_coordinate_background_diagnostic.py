"""An independent transmission removes a varying background without fitting UVs."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from diagnose_liquid_coordinate_background import subtract_background
from liquid_coordinate_markers import score


class BackgroundDiagnosticTests(unittest.TestCase):
    def test_independent_transmission_recovers_texture_rank_from_varying_background(self):
        texture=np.array([[5,10,20],[10,20,25],[15,30,40]],float)
        background=np.array([[240,240,220],[120,120,130],[0,0,0]],float)
        observed=texture+.33*background
        self.assertGreater(score(texture,observed)['rank_rmse'],.2)
        recovered=subtract_background(observed,background,.33)
        np.testing.assert_allclose(recovered,texture)
        self.assertEqual(0.,score(texture,recovered)['rank_rmse'])

    def test_shape_and_scalar_transmission_are_required(self):
        values=np.zeros((3,3))
        for transmission in (0.,1.,float('nan'),[.3,.3,.3]):
            with self.assertRaises(ValueError):subtract_background(values,values,transmission)
        with self.assertRaises(ValueError):subtract_background(values,values[:2],.33)


if __name__=='__main__':unittest.main()
