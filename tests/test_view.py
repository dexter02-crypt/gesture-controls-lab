"""Rendering checks with fabricated landmark results; not native ML tests."""
import unittest
import numpy as np
from app import View, __version__
from common import Result

class ViewTests(unittest.TestCase):
    def test_release_version(self):
        self.assertEqual(__version__, "0.2.0")
    def fixture(self,ratio=.6):
        p=np.tile([.5,.5,0.],(21,1));p[:,1]=np.linspace(.3,.7,21)
        return {'hands':[{'points':p.tolist(),'ratio':ratio,'center':(.5,.5),'cursor':(.5,.5),'label':'None','score':.1}],'rejected':[]}
    def test_render_unknown_does_not_hide_pinch_control(self):
        v=View();frame=np.zeros((480,640,3),np.uint8)
        for t,r in [(0,.6),(.12,.6),(.2,.1),(.29,.1)]:
            output=v(Result(t,frame,self.fixture(r),.01),True)
        self.assertEqual(v.controls.clicks,1);self.assertEqual(output.shape,frame.shape)
        self.assertEqual(int(frame.sum()),0)
    def test_stale_result_cancels_without_erasing_session_counter(self):
        v=View();v.controls.clicks=3;self.assertIsNone(v(None,False));self.assertEqual(v.controls.clicks,3);self.assertEqual(v.controls.rows,[])
    def test_mode_keyboard_disables_held_state(self):
        v=View();v.key(ord('2'));self.assertEqual(v.controls.mode,'draw');v.key(ord('3'));self.assertEqual(v.controls.mode,'slider');v.key(ord('r'));self.assertEqual(v.controls.mode,'counter')
    def test_calibration_suppresses_actions(self):
        v=View();v.key(ord('o'));frame=np.zeros((480,640,3),np.uint8)
        for t,r in [(0,.6),(.12,.6),(.2,.1),(.29,.1)]:v(Result(t,frame,self.fixture(r),.01),True)
        self.assertEqual(v.controls.clicks,0);self.assertIsNotNone(v.collect)
    def test_missing_interval_resets_calibration_samples(self):
        v=View();v.key(ord('p'));frame=np.zeros((480,640,3),np.uint8)
        v(Result(0,frame,self.fixture(.1),.01),True);v(None,False)
        self.assertEqual(v.collect[2],[])
