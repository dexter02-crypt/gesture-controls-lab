"""Deterministic display effects driven by fabricated interaction results."""
import copy
import unittest
import numpy as np
from effects import HandFX
from app import View

class EffectsTests(unittest.TestCase):
    def row(self,i=1,event='PRESS',x=.5):return {'id':i,'cursor':(x,.5),'active':True,'event':event}
    def test_press_emits_particles(self):
        f=HandFX();f.advance(0,[self.row()]);self.assertEqual(len(f.particles),36)
    def test_same_result_not_retriggered(self):
        f=HandFX();f.advance(0,[self.row()]);f.advance(0,[self.row()]);self.assertEqual(len(f.particles),36)
    def test_no_event_no_burst(self):
        f=HandFX();f.advance(0,[self.row(event=None)]);self.assertEqual(f.particles,[])
    def test_lost_hand_clears_trail(self):
        f=HandFX();f.advance(0,[self.row()]);f.advance(.1,[]);self.assertEqual(f.trails,{})
    def test_stale_clears_particles(self):
        f=HandFX();f.advance(0,[self.row()]);f.advance(2,[]);self.assertEqual(f.particles,[])
    def test_particle_capacity(self):
        f=HandFX()
        for i in range(40):f.advance(i*.01,[self.row(x=.3),self.row(2,x=.7)])
        self.assertLessEqual(len(f.particles),720)
    def test_draw_preserves_inputs(self):
        f=HandFX();frame=np.zeros((360,640,3),np.uint8);rows=[self.row(),self.row(2,x=.7)];before=copy.deepcopy(rows)
        out=f.render(frame,rows,0)
        self.assertGreater(int(out.sum()),0);self.assertEqual(int(frame.sum()),0);self.assertEqual(rows,before)
    def test_toggle_clears_effect(self):
        v=View();v.fx.advance(0,[self.row()]);v.key(ord('e'));self.assertFalse(v.effects);self.assertEqual(v.fx.particles,[])
    def test_stale_view_cancels_visuals(self):
        v=View();v.fx.advance(0,[self.row()]);v(None,False);self.assertEqual(v.fx.particles,[])
    def test_bad_time(self):
        with self.assertRaises(ValueError):HandFX().advance(float('nan'),[])
