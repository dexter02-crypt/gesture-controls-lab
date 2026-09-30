"""Display-only pinch bursts, neon trails and a two-hand energy bridge."""
from collections import deque
import math
import cv2
import numpy as np


class HandFX:
    def __init__(self, seed=17):
        self.random=np.random.default_rng(seed)
        self.particles=[];self.trails={};self.last=None

    def clear(self):
        self.particles=[];self.trails={};self.last=None

    def advance(self,t,rows):
        if not math.isfinite(t) or t<0:raise ValueError('Invalid effect time.')
        if self.last is not None and t<=self.last:return
        dt=0 if self.last is None else min(.1,t-self.last)
        if self.last is not None and t-self.last>.6:self.clear()
        self.last=t
        visible={r['id'] for r in rows}
        self.trails={i:q for i,q in self.trails.items() if i in visible}
        for row in rows:
            x,y=row['cursor']
            if not math.isfinite(x+y) or not (0<=x<=1 and 0<=y<=1):continue
            trail=self.trails.setdefault(row['id'],deque(maxlen=24))
            if trail and math.dist((x,y),trail[-1])>.18:trail.clear()
            trail.append((x,y))
            if row.get('event')=='PRESS':
                for angle,speed in zip(self.random.uniform(0,2*math.pi,36),self.random.uniform(.08,.30,36)):
                    self.particles.append([x,y,math.cos(angle)*speed,math.sin(angle)*speed,.7,row['id']])
        self.particles=self.particles[-720:]
        alive=[]
        for p in self.particles:
            p[4]-=dt;p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=.12*dt
            if p[4]>0 and 0<=p[0]<=1 and 0<=p[1]<=1:alive.append(p)
        self.particles=alive

    @staticmethod
    def color(ident):
        palette=((255,180,50),(80,240,255),(240,80,220),(100,255,160))
        return palette[(ident-1)%len(palette)]

    def render(self,frame,rows,t,new=True):
        if new:self.advance(t,rows)
        out=frame.copy();layer=np.zeros_like(out);h,w=out.shape[:2]
        for ident,trail in self.trails.items():
            p=[(round(x*w),round(y*h)) for x,y in trail]
            for k,(a,b) in enumerate(zip(p,p[1:])):
                col=tuple(round(v*(k+1)/max(1,len(p))) for v in self.color(ident))
                cv2.line(layer,a,b,col,2,cv2.LINE_AA)
        active=[]
        for row in rows:
            x,y=row['cursor'];pt=round(x*w),round(y*h);col=self.color(row['id'])
            if row.get('active'):
                active.append(pt)
                radius=22+round(3*math.sin(t*6))
                cv2.circle(layer,pt,radius,col,2,cv2.LINE_AA)
                cv2.ellipse(layer,pt,(radius+9,radius+9),t*90%360,0,240,col,2,cv2.LINE_AA)
        if len(active)==2:
            a,b=np.array(active[0],float),np.array(active[1],float)
            d=b-a;n=np.array([-d[1],d[0]])/max(1,float(np.linalg.norm(d)))
            pts=np.array([a+d*s+n*math.sin(s*math.pi*6+t*9)*8*math.sin(s*math.pi)
                          for s in np.linspace(0,1,40)],np.int32)
            cv2.polylines(layer,[pts.reshape(-1,1,2)],False,(235,200,120),2,cv2.LINE_AA)
        for x,y,vx,vy,life,ident in self.particles:
            col=tuple(round(v*life/.7) for v in self.color(ident))
            cv2.circle(layer,(round(x*w),round(y*h)),2,col,-1,cv2.LINE_AA)
        return cv2.add(cv2.add(out,cv2.GaussianBlur(layer,(0,0),3)),layer)
