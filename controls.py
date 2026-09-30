"""Independent pinch interaction; labels never arm an OS action."""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import math
import numpy as np

GESTURES={'Closed_Fist','Open_Palm','Pointing_Up','Thumb_Down','Thumb_Up','Victory','ILoveYou'}


def pinch_measure(points,width,height):
    p=np.asarray(points,dtype=float)
    if p.shape!=(21,3) or not np.isfinite(p).all() or width<16 or height<16:raise ValueError('Invalid landmarks.')
    # Only x/y measure visible separation. Estimated depth is not physical contact.
    xy=p[:,:2]*[width,height]
    if ((p[[0,4,8,9],:2]<0)|(p[[0,4,8,9],:2]>1)).any():raise ValueError('Required points clipped.')
    palm=float(np.linalg.norm(xy[0]-xy[9]))
    if palm<20:raise ValueError('Palm too small for an actionable pinch.')
    ratio=float(np.linalg.norm(xy[4]-xy[8])/palm)
    center=tuple(np.mean(p[[0,5,9,13,17],:2],axis=0))
    cursor=tuple(np.mean(p[[4,8],:2],axis=0))
    if not 0<=ratio<=5:raise ValueError('Implausible visible pinch separation.')
    return ratio,center,cursor


def calibrate_thresholds(open_samples,closed_samples):
    if len(open_samples)<12 or len(closed_samples)<12:raise ValueError('At least 12 valid samples in each posture are required.')
    a=np.array(open_samples,dtype=float);b=np.array(closed_samples,dtype=float)
    if not np.isfinite(a).all() or not np.isfinite(b).all() or min(a.min(),b.min())<0 or max(a.max(),b.max())>5:
        raise ValueError('Invalid calibration values.')
    upper_closed=float(np.quantile(b,.9));lower_open=float(np.quantile(a,.1))
    gap=lower_open-upper_closed
    if gap<.12:raise ValueError('Open and pinch samples overlap. Keep one hand steady, increase visible separation, and retry.')
    return upper_closed+.25*gap,upper_closed+.65*gap


@dataclass
class PinchGate:
    close:float=.23
    release:float=.38
    armed:bool=False
    active:bool=False
    since:float|None=None
    phase:str='NEED_RELEASE'
    last:float|None=None

    def __post_init__(self):
        if not (math.isfinite(self.close) and math.isfinite(self.release) and 0<self.close<self.release<=5):
            raise ValueError('Invalid pinch thresholds.')

    def reset(self):
        self.armed=self.active=False;self.since=None;self.phase='NEED_RELEASE';self.last=None

    def update(self,t,ratio):
        if not math.isfinite(t) or t<0 or (self.last is not None and t<=self.last):raise ValueError('Time must increase.')
        if self.last is not None and t-self.last>.6:self.reset()
        self.last=t
        if ratio is None or not math.isfinite(ratio) or not 0<=ratio<=5:
            self.reset();return 'CANCEL'
        if ratio>=self.release:
            event='RELEASE' if self.active else None
            self.active=False
            if self.phase!='OPEN':self.since=t
            self.phase='OPEN'
            if t-self.since>=.10:self.armed=True
            return event
        if ratio<=self.close:
            if self.active:return None
            if not self.armed:self.phase='NEED_RELEASE';self.since=None;return None
            if self.phase!='CLOSING':self.since=t
            self.phase='CLOSING'
            if t-self.since>=.07:
                self.active=True;self.armed=False;self.phase='PINCH';self.since=None;return 'PRESS'
            return None
        if not self.active:
            self.since=None;self.phase='READY' if self.armed else 'NEED_RELEASE'
        return None


@dataclass
class Track:
    ident:int
    center:tuple
    gate:PinchGate
    label:str='None'
    since:float=0
    samples:int=0
    stable:str='UNKNOWN'
    previous:tuple|None=None


class Controls:
    """Small spatial association with explicit reset on crossings, loss or stale input."""
    def __init__(self):
        self.tracks={};self.next_id=1;self.last=None
        self.close=.23;self.release=.38;self.mode='counter';self.clicks=0;self.slider=.5
        self.segments=deque(maxlen=2000);self.rows=[]

    def cancel(self):
        self.tracks={};self.rows=[];self.last=None

    def set_mode(self,mode):
        if mode not in ('counter','draw','slider'):raise ValueError('Unknown mode.')
        self.cancel();self.mode=mode

    def set_thresholds(self,close,release):
        PinchGate(close,release)
        self.close,self.release=close,release;self.cancel()

    def update(self,t,observations):
        if len(observations)>4:raise ValueError('Maximum four hands.')
        if not math.isfinite(t) or t<0 or (self.last is not None and t<=self.last):raise ValueError('Time must increase.')
        if self.last is not None and t-self.last>.6:self.cancel()
        self.last=t
        # Cost in normalized screen space. Do not carry an ID across a close tie.
        candidates=[]
        for j,o in enumerate(observations):
            values=sorted((math.dist(o['center'],r.center),i) for i,r in self.tracks.items())
            if values and values[0][0]<.18 and (len(values)==1 or values[1][0]-values[0][0]>.04):
                candidates.append((values[0][0],j,values[0][1]))
        counts={i:sum(k==i for _,_,k in candidates) for _,_,i in candidates}
        mapping={j:i for _,j,i in candidates if counts[i]==1}
        current={};rows=[]
        for j,o in enumerate(observations):
            ident=mapping.get(j)
            if ident is None:
                ident=self.next_id;self.next_id+=1
                tr=Track(ident,o['center'],PinchGate(self.close,self.release))
            else:tr=self.tracks[ident]
            tr.center=o['center'];event=tr.gate.update(t,o['ratio'])
            label=o.get('label','None');score=o.get('score',0.)
            if label not in GESTURES or not math.isfinite(score) or score<.6:
                tr.label='None';tr.samples=0;tr.stable='UNKNOWN'
            elif label!=tr.label:
                tr.label=label;tr.since=t;tr.samples=1;tr.stable='PENDING'
            else:
                tr.samples+=1
                tr.stable=label if tr.samples>=2 and t-tr.since>=.10 else 'PENDING'
            x,y=o['cursor']
            if event=='PRESS':self.clicks+=1
            if tr.gate.active:
                if self.mode=='slider':self.slider=min(1.,max(0.,(x-.10)/.80))
                if self.mode=='draw':
                    if tr.previous is not None and math.dist((x,y),tr.previous)<.15:self.segments.append((ident,*tr.previous,x,y))
                    tr.previous=(x,y)
            else:tr.previous=None
            current[ident]=tr
            rows.append({**o,'id':ident,'state':tr.stable,'action':tr.gate.phase,'active':tr.gate.active,'event':event})
        self.tracks=current;self.rows=rows
        return rows
