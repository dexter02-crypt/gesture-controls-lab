"""Trained gesture categories plus independent, session-calibrated pinch controls."""
from __future__ import annotations
import argparse,importlib.metadata,json,sys,time
from pathlib import Path
import cv2,numpy as np
from common import run_live,label,preview,read_image
from controls import Controls,pinch_measure,calibrate_thresholds
from effects import HandFX

__version__ = "0.2.0"

CHAINS=((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17))


def runtime_check():
    version=importlib.metadata.version('mediapipe')
    if version!='1.0.0':raise ValueError(f'This Mac candidate requires mediapipe==1.0.0; found {version}. Use the isolated setup, not a global upgrade.')
    if sys.version_info[:2]!=(3,12):raise ValueError('Use Python 3.12 for this candidate.')
    providers=[]
    for name in ('opencv-python','opencv-contrib-python','opencv-python-headless','opencv-contrib-python-headless'):
        try:importlib.metadata.version(name);providers.append(name)
        except importlib.metadata.PackageNotFoundError:pass
    if providers!=['opencv-contrib-python']:raise ValueError('Exactly one GUI OpenCV provider is required: opencv-contrib-python.')


class Engine:
    def __init__(self,max_hands=2,video=True):
        if not 1<=max_hands<=4:raise ValueError('Hand capacity is 1..4.')
        runtime_check()
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        from model_asset import verify
        self.mp=mp;self.video=video;self.last=-1
        options=vision.GestureRecognizerOptions(base_options=python.BaseOptions(model_asset_path=verify()),
                running_mode=vision.RunningMode.VIDEO if video else vision.RunningMode.IMAGE,
                num_hands=max_hands,min_hand_detection_confidence=.5,min_hand_presence_confidence=.5,min_tracking_confidence=.5)
        self.model=vision.GestureRecognizer.create_from_options(options)

    def process(self,frame,t):
        image=self.mp.Image(image_format=self.mp.ImageFormat.SRGB,data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
        stamp=max(self.last+1,round(t*1000));self.last=stamp
        result=self.model.recognize_for_video(image,stamp) if self.video else self.model.recognize(image)
        h,w=frame.shape[:2];rows=[];rejected=[]
        for i,landmarks in enumerate(result.hand_landmarks):
            points=np.array([(p.x,p.y,p.z) for p in landmarks])
            # Native inference is unmirrored; only the display coordinates are mirrored.
            points[:,0]=1-points[:,0]
            try:ratio,center,cursor=pinch_measure(points,w,h)
            except ValueError as e:rejected.append(str(e));continue
            cat=result.gestures[i][0] if i<len(result.gestures) and result.gestures[i] else None
            rows.append({'points':points.tolist(),'ratio':ratio,'center':center,'cursor':cursor,
                         'label':cat.category_name if cat else 'None','score':float(cat.score) if cat else 0.})
        return {'hands':rows,'rejected':rejected}

    def close(self):self.model.close()


class View:
    def __init__(self):
        self.controls=Controls();self.collect=None;self.samples={};self.message='O: sample open fingers | P: sample pinch | session calibration only'
        self.last_time=None;self.fx=HandFX();self.effects=True

    def key(self,k):
        if k in (ord('r'),ord('o'),ord('p'),ord('1'),ord('2'),ord('3')):self.fx.clear()
        if k==ord('e'):self.effects=not self.effects;self.fx.clear()
        if k in (ord('1'),ord('2'),ord('3')):self.controls.set_mode({ord('1'):'counter',ord('2'):'draw',ord('3'):'slider'}[k])
        if k==ord('r'):self.controls=Controls();self.samples={};self.collect=None;self.message='Session reset.'
        if k==ord('c'):self.controls.segments.clear()
        if k in (ord('o'),ord('p')):
            self.controls.cancel();self.collect=('open' if k==ord('o') else 'closed',None,[],None)
            self.message='Show exactly ONE hand; hold the requested posture for two seconds.'

    def __call__(self,result,new):
        if result is None:
            self.controls.cancel();self.fx.clear()
            # Do not count missing intervals as calibration observations.
            if self.collect is not None:self.collect=(self.collect[0],None,[],None)
            return None
        frame=preview(cv2.flip(result.frame,1));h,w=frame.shape[:2]
        data=result.data;rows=data['hands'];t=result.timestamp
        if new:
            if self.collect is not None:
                kind,start,values,last=self.collect
                if len(rows)!=1 or (last is not None and t-last>.6):start=None;values=[]
                elif start is None:start=t
                if len(rows)==1:
                    values.append(rows[0]['ratio'])
                    if start is not None and t-start>=2:
                        self.samples[kind]=values[:240];self.collect=None
                        self.message=f'{kind} samples captured. Collect the other posture with O or P.'
                        if 'open' in self.samples and 'closed' in self.samples:
                            try:
                                a,b=calibrate_thresholds(self.samples['open'],self.samples['closed'])
                                self.controls.set_thresholds(a,b);self.message=f'Calibrated: pinch <= {a:.2f}; release >= {b:.2f} (this session).'
                            except ValueError as e:self.message=str(e)
                if self.collect is not None:self.collect=(kind,start,values,t)
            else:self.controls.update(t,rows)
        if self.effects and self.collect is None:
            frame=self.fx.render(frame,self.controls.rows,t,new)
        else:self.fx.clear()
        for r in self.controls.rows:
            points=np.array(r['points']);color=(110,230,150) if r['active'] else (60,180,245)
            for chain in CHAINS:
                for a,b in zip(chain,chain[1:]):cv2.line(frame,tuple((points[a,:2]*[w,h]).astype(int)),tuple((points[b,:2]*[w,h]).astype(int)),color,2)
            x,y=(int(v*s) for v,s in zip(r['cursor'],(w,h)))
            cv2.circle(frame,(x,y),12,color,-1 if r['active'] else 2)
            label(frame,f'H{r["id"]}: {r["state"]} | candidate {r["label"]} {r["score"]:.2f} | gap {r["ratio"]:.2f} | {r["action"]}',3+(r['id']-1)%4)
        if self.controls.mode=='draw':
            for i,x1,y1,x2,y2 in self.controls.segments:cv2.line(frame,(round(x1*w),round(y1*h)),(round(x2*w),round(y2*h)),(80,230,250),4)
        if self.controls.mode=='slider':
            cv2.rectangle(frame,(int(.1*w),h-65),(int(.9*w),h-35),(230,230,230),2)
            cv2.rectangle(frame,(int(.1*w),h-65),(int((.1+.8*self.controls.slider)*w),h-35),(80,230,250),-1)
        label(frame,f'TRAINED GESTURES | 1 pinch counter  2 draw  3 slider | actions {self.controls.clicks}',1)
        label(frame,self.message,2)
        label(frame,'Q/Esc exits | E neon FX | R reset | C clear | no recording / no OS actions',8)
        if self.collect is not None:label(frame,f'CALIBRATING {self.collect[0].upper()} - actions disabled',7)
        if data['rejected']:label(frame,'Not actionable: '+', '.join(data['rejected']),9)
        return frame


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['model','check','camera','image']);p.add_argument('--camera',type=int,default=0);p.add_argument('--max-hands',type=int,choices=range(1,5),default=2);p.add_argument('--image',type=Path)
    args=p.parse_args()
    if args.command=='model':
        from model_asset import download
        download();return
    if args.command=='check':
        for video in (False,True):
            eng=Engine(args.max_hands,video)
            try:
                result=eng.process(np.full((480,640,3),127,np.uint8),1.)
                if result['hands']:raise RuntimeError('Unexpected hand result on blank input.')
            finally:eng.close()
            print(('VIDEO' if video else 'IMAGE')+' model loading and blank inference passed.')
        print('NATIVE STARTUP ONLY. Real hand/gesture accuracy is unmeasured.');return
    if args.command=='image':
        if args.image is None:raise ValueError('--image is required.')
        eng=Engine(args.max_hands,False)
        try:print(json.dumps(eng.process(read_image(args.image),1.),indent=2))
        finally:eng.close()
        return
    view=View();print('Open fingers, then pinch. O/P perform session-only calibration. Seven learned categories; pinch is a separate 2-D rule.',flush=True)
    run_live(lambda:Engine(args.max_hands),view,view.key,args.camera,title='KedByte Gesture Controls')

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,OSError,ImportError) as e:print('Stopped:',e,file=sys.stderr);sys.exit(2)
