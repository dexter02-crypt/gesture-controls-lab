"""Explicit Google-hosted model acquisition and local integrity receipt."""
from pathlib import Path
import hashlib,json,urllib.request,urllib.parse,zipfile,io,os
MODEL_URL='https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task'
ROOT=Path(__file__).resolve().parent/'models'
MODEL=ROOT/'gesture_recognizer.task'
RECEIPT=ROOT/'gesture_recognizer.receipt.json'

class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        u=urllib.parse.urlparse(newurl)
        if u.scheme!='https' or u.hostname!='storage.googleapis.com':raise ValueError('Unexpected model redirect.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def verify():
    if ROOT.is_symlink() or MODEL.is_symlink() or RECEIPT.is_symlink():raise ValueError('Model paths must not be symlinks.')
    if not MODEL.is_file() or not RECEIPT.is_file():raise ValueError('Run app.py model first; the old hand_landmarker.task is not a gesture classifier.')
    if MODEL.stat().st_size>50_000_000 or RECEIPT.stat().st_size>10000:raise ValueError('Oversized model or receipt.')
    r=json.loads(RECEIPT.read_text());data=MODEL.read_bytes()
    if r.get('url')!=MODEL_URL or r.get('sha256')!=hashlib.sha256(data).hexdigest() or r.get('bytes')!=len(data):raise ValueError('Model receipt mismatch.')
    return str(MODEL)

def download():
    if MODEL.exists() and RECEIPT.exists():return verify()
    if ROOT.is_symlink() or MODEL.exists() or RECEIPT.exists():raise ValueError('Incomplete model state. Preserve and inspect it instead of overwriting.')
    ROOT.mkdir(exist_ok=True)
    print('Downloading the Google gesture-recognizer model. Local SHA-256 is integrity evidence, not an upstream signature.',flush=True)
    with urllib.request.build_opener(RestrictedRedirect()).open(MODEL_URL,timeout=60) as response:
        data=response.read(50_000_001)
    if len(data)>50_000_000 or len(data)<100000:raise ValueError('Unexpected model size.')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if not any('gesture' in n for n in z.namelist()):raise ValueError('Not a gesture model bundle.')
    except zipfile.BadZipFile as exc:
        raise ValueError('Downloaded bytes are not a model bundle.') from exc
    r={'url':MODEL_URL,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    made=[]
    try:
        with MODEL.open('xb') as f:made.append(MODEL);f.write(data)
        with RECEIPT.open('x') as f:made.append(RECEIPT);json.dump(r,f,indent=2)
    except Exception:
        for p in made:p.unlink(missing_ok=True)
        raise
    print(json.dumps(r,indent=2));return verify()
