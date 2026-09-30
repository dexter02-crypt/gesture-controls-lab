import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import model_asset
class Assets(unittest.TestCase):
 def test_missing_model_explicit(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   with patch.object(model_asset,'ROOT',root),patch.object(model_asset,'MODEL',root/'m.task'),patch.object(model_asset,'RECEIPT',root/'r.json'):
    with self.assertRaises(ValueError):model_asset.verify()
 def test_receipt_detects_tampering(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);model=root/'m.task';r=root/'r.json';model.write_bytes(b'original')
   r.write_text(json.dumps({'url':model_asset.MODEL_URL,'sha256':hashlib.sha256(b'original').hexdigest(),'bytes':8}))
   with patch.object(model_asset,'ROOT',root),patch.object(model_asset,'MODEL',model),patch.object(model_asset,'RECEIPT',r):
    self.assertEqual(model_asset.verify(),str(model));model.write_bytes(b'changed!')
    with self.assertRaises(ValueError):model_asset.verify()
 def test_redirect_restriction(self):
  redirect=model_asset.RestrictedRedirect()
  with self.assertRaises(ValueError):redirect.redirect_request(None,None,302,'',{},'http://storage.googleapis.com/x')
  with self.assertRaises(ValueError):redirect.redirect_request(None,None,302,'',{},'https://untrusted.invalid/x')
