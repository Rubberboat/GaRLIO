import unittest
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from interpolate_trajectory import resample

class InterpolationTests(unittest.TestCase):
    def test_constant_translation_and_half_rotation(self):
        poses=np.array([[10,0,0,0,0,0,0,1],[10.1,1,2,3,0,0,1,0]])
        out,valid=resample(poses,[10.05])
        self.assertTrue(valid[0])
        np.testing.assert_allclose(out[0,1:4],[.5,1,1.5])
        np.testing.assert_allclose(out[0,4:],[0,0,2**-.5,2**-.5])
    def test_quaternion_sign_and_no_outage_bridge_or_extrapolation(self):
        poses=np.array([[10,0,0,0,0,0,0,1],[10.1,1,0,0,0,0,0,-1],[11,2,0,0,0,0,0,1]])
        out,valid=resample(poses,[9.9,10,10.05,10.5,11,11.1])
        self.assertEqual(valid.tolist(),[False,True,True,False,True,False])
        np.testing.assert_allclose(out[2,4:],[0,0,0,1])
        self.assertTrue(np.isnan(out[3]).all())
