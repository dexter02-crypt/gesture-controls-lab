import unittest,time
from threading import Event
import numpy as np
from common import LatestWorker,validate_frame,open_camera
from unittest.mock import patch
class WorkerTests(unittest.TestCase):
 def test_one_inflight_no_backlog(self):
  entered=Event();release=Event()
  class Engine:
   def process(self,im,t):entered.set();release.wait(3);return {'t':t,'pixel':int(im[0,0,0])}
  w=LatestWorker(Engine)
  try:
   self.assertTrue(w.ready.wait(1));im=np.zeros((20,20,3),np.uint8)
   self.assertTrue(w.submit(1,im));self.assertTrue(entered.wait(1));im[:]=255
   self.assertFalse(w.submit(2,im));release.set()
   deadline=time.monotonic()+2;r=None
   while r is None and time.monotonic()<deadline:r=w.take();time.sleep(.005)
   self.assertIsNotNone(r);self.assertEqual(r.data['pixel'],0);self.assertEqual(r.timestamp,1)
  finally:release.set();w.close()
 def test_worker_error_surfaces(self):
  def factory():raise ValueError('bad model')
  w=LatestWorker(factory)
  try:
   self.assertTrue(w.ready.wait(1))
   with self.assertRaises(RuntimeError):w.check()
  finally:w.close()
 def test_cleanup_called(self):
  closed=Event()
  class Engine:
   def close(self):closed.set()
  w=LatestWorker(Engine);w.ready.wait(1);w.close();self.assertTrue(closed.is_set())
 def test_network_camera_refused(self):
  with patch('common.cv2.VideoCapture') as native:
   with self.assertRaises(ValueError):open_camera('https://example.invalid/video')
   native.assert_not_called()
 def test_missing_camera_released(self):
  with patch('common.cv2.VideoCapture') as native:
   native.return_value.isOpened.return_value=False
   with self.assertRaises(ValueError):open_camera(0)
   native.return_value.release.assert_called_once()
