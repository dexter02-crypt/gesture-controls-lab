import unittest,math
import numpy as np
from controls import PinchGate,Controls,pinch_measure,calibrate_thresholds

def obs(ratio=.6,center=(.5,.5),cursor=(.5,.5),label='Open_Palm',score=.9):
 return dict(ratio=ratio,center=center,cursor=cursor,label=label,score=score,points=np.zeros((21,3)).tolist())

class Gates(unittest.TestCase):
 def test_entry_pinched_does_not_click(self):
  g=PinchGate();self.assertIsNone(g.update(0,.1));self.assertIsNone(g.update(.3,.1));self.assertFalse(g.active)
 def test_release_then_single_click(self):
  g=PinchGate();g.update(0,.6);g.update(.15,.6);g.update(.2,.1)
  self.assertEqual(g.update(.3,.1),'PRESS');self.assertIsNone(g.update(.4,.1));self.assertEqual(g.update(.5,.6),'RELEASE')
 def test_gray_zone_holds_active(self):
  g=PinchGate();g.update(0,.6);g.update(.15,.6);g.update(.2,.1);g.update(.3,.1);g.update(.4,.3);self.assertTrue(g.active)
 def test_gap_cancels(self):
  g=PinchGate();g.update(0,.6);g.update(.15,.6);g.update(.2,.1);g.update(.3,.1);g.update(2,.1);self.assertFalse(g.active)
 def test_invalid_cancels(self):
  g=PinchGate();self.assertEqual(g.update(0,float('nan')),'CANCEL');self.assertFalse(g.armed)
 def test_time_reversal(self):
  g=PinchGate();g.update(1,.6)
  with self.assertRaises(ValueError):g.update(.9,.6)
 def test_invalid_threshold(self):
  with self.assertRaises(ValueError):PinchGate(.5,.2)
 def test_calibration_separates(self):
  a,b=calibrate_thresholds([.7]*15,[.12]*15);self.assertLess(.12,a);self.assertLess(a,b);self.assertLess(b,.7)
 def test_calibration_rejects_overlap(self):
  with self.assertRaises(ValueError):calibrate_thresholds([.3]*15,[.3]*15)
 def test_calibration_min_samples(self):
  with self.assertRaises(ValueError):calibrate_thresholds([.7]*2,[.1]*15)
 def test_2d_measure_ignores_estimated_depth(self):
  p=np.full((21,3),.5);p[0,:2]=(.5,.7);p[9,:2]=(.5,.5);p[4,:2]=(.49,.3);p[8,:2]=(.51,.3)
  original=pinch_measure(p,1280,720)[0];p[4,2]=10
  self.assertEqual(pinch_measure(p,1280,720)[0],original)
 def test_minimum_palm(self):
  with self.assertRaises(ValueError):pinch_measure(np.zeros((21,3)),1280,720)

class Sessions(unittest.TestCase):
 def test_two_hands_independent(self):
  c=Controls();r=c.update(0,[obs(center=(.2,.5)),obs(center=(.8,.5))]);self.assertEqual(len(r),2);self.assertNotEqual(r[0]['id'],r[1]['id'])
 def test_reordered_ids(self):
  c=Controls();r=c.update(0,[obs(center=(.2,.5)),obs(center=(.8,.5))]);r2=c.update(.2,[obs(center=(.8,.5)),obs(center=(.2,.5))]);self.assertEqual([r2[0]['id'],r2[1]['id']],[r[1]['id'],r[0]['id']])
 def test_unknown_label_does_not_block_pinch(self):
  c=Controls();c.update(0,[obs(label='None')]);c.update(.15,[obs(label='None')]);c.update(.2,[obs(.1,label='None')]);c.update(.3,[obs(.1,label='None')]);self.assertEqual(c.clicks,1);self.assertEqual(c.rows[0]['state'],'UNKNOWN')
 def test_release_needed_after_loss(self):
  c=Controls();c.update(0,[obs()]);c.update(.15,[obs()]);c.update(.2,[]);c.update(.3,[obs(.1)]);c.update(.5,[obs(.1)]);self.assertEqual(c.clicks,0)
 def test_label_dwell(self):
  c=Controls();c.update(0,[obs()]);c.update(.05,[obs()]);self.assertEqual(c.rows[0]['state'],'PENDING');c.update(.15,[obs()]);self.assertEqual(c.rows[0]['state'],'Open_Palm')
 def test_low_score_not_accepted(self):
  c=Controls();c.update(0,[obs(score=.1)]);self.assertEqual(c.rows[0]['state'],'UNKNOWN')
 def test_mode_change_cancels(self):
  c=Controls();c.update(0,[obs()]);c.set_mode('draw');self.assertEqual(c.tracks,{})
 def test_slider_in_app_only(self):
  c=Controls();c.set_mode('slider');c.update(0,[obs()]);c.update(.15,[obs()]);c.update(.2,[obs(.1,cursor=(.9,.5))]);c.update(.3,[obs(.1,cursor=(.9,.5))]);self.assertAlmostEqual(c.slider,1.)
 def test_crossing_ambiguity_new_identity(self):
  c=Controls();old=c.update(0,[obs(center=(.4,.5)),obs(center=(.6,.5))]);new=c.update(.2,[obs(center=(.5,.5))]);self.assertNotIn(new[0]['id'],[r['id'] for r in old])
 def test_persistent_sequences_no_repeated_press(self):
  c=Controls();c.update(0,[obs()]);c.update(.15,[obs()]);
  for t in np.arange(.2,3,.1):c.update(float(t),[obs(.1)])
  self.assertEqual(c.clicks,1)
