"""Small local-camera utilities. No network capture, recording, or OS controls."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from threading import Thread, Lock, Event
import json
import math
import time
import cv2
import numpy as np


def validate_frame(frame):
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError('Expected a uint8 BGR image with three channels.')
    h,w=frame.shape[:2]
    if h<16 or w<16 or h*w>24_000_000:
        raise ValueError('Image dimensions must be at least 16 pixels and at most 24 megapixels.')
    return frame


def read_image(path):
    p=Path(path).expanduser()
    if p.is_symlink() or not p.is_file() or p.stat().st_size>40_000_000:
        raise ValueError('Use a regular local image, at most 40 MB.')
    return validate_frame(cv2.imread(str(p),cv2.IMREAD_COLOR))


def safe_text(text, limit=120):
    # JSON escaping prevents terminal controls and bidi escapes from becoming actions.
    s=json.dumps(str(text),ensure_ascii=True)[1:-1]
    return s if len(s)<=limit else s[:limit]+' [truncated]'


def label(frame, text, line=0):
    y=24+line*24
    cv2.putText(frame,safe_text(text,170),(12,y),cv2.FONT_HERSHEY_SIMPLEX,.52,(0,0,0),3,cv2.LINE_AA)
    cv2.putText(frame,safe_text(text,170),(12,y),cv2.FONT_HERSHEY_SIMPLEX,.52,(245,245,245),1,cv2.LINE_AA)


def preview(frame,width=1100):
    h,w=frame.shape[:2]
    return cv2.resize(frame,(width,round(h*width/w)),interpolation=cv2.INTER_AREA) if w>width else frame.copy()


@dataclass
class Result:
    timestamp: float
    frame: np.ndarray
    data: object
    duration: float


class LatestWorker:
    """One in-flight inference and one completed result, never an input queue.

    Factory, processing, and native cleanup belong to the same worker thread.
    Dropping an offered frame is deliberate; old coordinates are never drawn on
    a new image. Main thread owns camera and GUI.
    """
    def __init__(self, factory):
        self.factory=factory
        self.lock=Lock(); self.wake=Event(); self.ready=Event()
        self.job=None; self.result=None; self.error=None; self.busy=False; self.stopping=False
        self.thread=Thread(target=self._run,daemon=True,name='one-inference-worker')
        self.thread.start()

    def _run(self):
        engine=None
        try:
            engine=self.factory(); self.ready.set()
            while True:
                self.wake.wait(); self.wake.clear()
                with self.lock:
                    if self.stopping:break
                    job=self.job; self.job=None
                if job is None:continue
                t,frame=job; start=time.monotonic()
                data=engine.process(frame,t)
                with self.lock:
                    self.result=Result(t,frame,data,time.monotonic()-start); self.busy=False
        except Exception as exc:
            with self.lock:self.error=exc;self.busy=False
            self.ready.set()
        finally:
            if engine is not None and hasattr(engine,'close'):
                try:engine.close()
                except Exception as exc:
                    with self.lock:
                        if self.error is None:self.error=exc

    def check(self):
        with self.lock:
            if self.error is not None:raise RuntimeError(f'Inference worker failed: {self.error}') from self.error

    def submit(self,t,frame):
        self.check()
        with self.lock:
            if self.busy or self.stopping or not self.ready.is_set():return False
            self.busy=True;self.job=(t,frame.copy());self.wake.set();return True

    def take(self):
        self.check()
        with self.lock:
            result,self.result=self.result,None
            return result

    def close(self):
        with self.lock:self.stopping=True
        self.wake.set();self.thread.join(timeout=3)
        # Native calls are not forcibly killed; a blocked daemon cannot hold exit.


def open_camera(index=0,width=1280,height=720):
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<=8:
        raise ValueError('Camera must be a local integer index 0..8, not a network URL.')
    cap=cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release();raise ValueError('Cannot open camera. Check Terminal camera permission or select another --camera index.')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,width);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,height)
    cap.set(cv2.CAP_PROP_FPS,30)
    return cap


def run_live(factory,renderer,key_handler=None,camera=0,width=1280,height=720,title='KedByte Camera Lab',stale_s=.6):
    if not .1<=stale_s<=10:raise ValueError('Invalid stale-result duration.')
    worker=LatestWorker(factory);cap=None
    try:
        if not worker.ready.wait(120):raise RuntimeError('Model initialization exceeded 120 seconds.')
        worker.check();cap=open_camera(camera,width,height)
        last=None;first=True
        while True:
            ok,frame=cap.read()
            if not ok:raise ValueError('Camera stopped returning frames.')
            validate_frame(frame)
            if first:
                print(f'Actual capture: {frame.shape[1]}x{frame.shape[0]}; no recording; Q/Esc exits.',flush=True);first=False
            now=time.monotonic()
            new=worker.take()
            if new is not None:last=new
            fresh=last is not None and now-last.timestamp<=stale_s
            if fresh:
                show=renderer(last,new is not None)
                label(show,f'Inference {last.duration*1000:.0f} ms | result age {(now-last.timestamp)*1000:.0f} ms',0)
            else:
                show=renderer(None,False)
                if show is None:show=preview(frame)
                label(show,'WAITING FOR FRESH RESULT - no active prediction',0)
            worker.submit(now,frame)
            cv2.imshow(title,show)
            key=cv2.waitKey(1)&0xFF
            if key in (ord('q'),27):break
            if key_handler is not None:key_handler(key)
            if cv2.getWindowProperty(title,cv2.WND_PROP_VISIBLE)<1:break
    finally:
        if cap is not None:cap.release()
        worker.close();cv2.destroyAllWindows()
