import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import meta_publish as m
import scheduled_publish as s
ENV={'IG_ACCESS_TOKEN':'test-not-a-secret','FB_PAGE_ID':m.PAGE_ID,'IG_USER_ID':'123',
     'YT_CLIENT_ID':'test','YT_CLIENT_SECRET':'test','YT_REFRESH_TOKEN':'test'}
DEBUG={'data':{'is_valid':True,'app_id':m.APP_ID,'type':'PAGE','profile_id':m.PAGE_ID,
    'expires_at':0,'data_access_expires_at':9999999999,'scopes':['pages_show_list',
    'pages_read_engagement','pages_manage_posts','instagram_basic','instagram_content_publish']}}
class MetaChecks(unittest.TestCase):
 def test_valid_preflight(self):
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=[DEBUG,{'id':m.PAGE_ID,'instagram_business_account':{'id':'123'}},{'id':'123','username':m.IG_USERNAME},{'data':[{'quota_usage':0}]}]):
   self.assertEqual(m.preflight()['page_id'],m.PAGE_ID)
 def test_missing_ig_before_api(self):
  with patch.dict(os.environ,{'IG_ACCESS_TOKEN':'test','FB_PAGE_ID':m.PAGE_ID},clear=True),patch.object(m,'graph') as api:
   with self.assertRaises(RuntimeError):m.preflight()
   api.assert_not_called()
 def test_wrong_page_before_api(self):
  with patch.dict(os.environ,dict(ENV,FB_PAGE_ID='wrong'),clear=True),patch.object(m,'graph') as api:
   with self.assertRaises(RuntimeError):m.preflight()
   api.assert_not_called()
 def test_scope_gate(self):
  d=json.loads(json.dumps(DEBUG));d['data']['scopes'].remove('instagram_content_publish')
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',return_value=d):
   with self.assertRaises(RuntimeError):m.preflight()
 def test_wrong_ig_account(self):
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=[DEBUG,{'id':m.PAGE_ID,'instagram_business_account':{'id':'123'}},{'id':'123','username':'wrong'}]):
   with self.assertRaises(RuntimeError):m.preflight()
 def test_expired_token(self):
  d=json.loads(json.dumps(DEBUG));d['data']['data_access_expires_at']=1
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',return_value=d):
   with self.assertRaises(RuntimeError):m.preflight()
 def test_ig_checkpoint_before_publish_and_optional_link_failure(self):
  checkpoints=[]
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=[{'id':'container'},{'status_code':'FINISHED'},{'id':'media'},RuntimeError('offline')]):
   r=m.publish_reel('https://example.test/video','caption',checkpoints.append)
  self.assertEqual(r['id'],'media');self.assertEqual(checkpoints[-1]['status'],'published')
  self.assertEqual(checkpoints[0]['container_id'],'container')
 def test_ig_failed_processing_never_publishes(self):
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=[{'id':'container'},{'status_code':'ERROR'}]) as api:
   with self.assertRaises(RuntimeError):m.publish_reel('https://example.test/video','caption',lambda x:None)
   self.assertEqual(api.call_count,2)
 def test_public_hash_mismatch(self):
  response=types.SimpleNamespace(geturl=lambda:'https://example.test/video',read=lambda:b'html')
  with patch.object(m.urllib.request,'urlopen') as open_url:
   open_url.return_value.__enter__.return_value=response
   with self.assertRaises(ValueError):m.public_video('https://example.test/video','a'*64)
 def test_fb_upload_host_gate(self):
  saved=[]
  with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',return_value={'video_id':'v','upload_url':'https://attacker.test/upload'}),patch.object(m.urllib.request,'urlopen') as upload:
   with self.assertRaises(RuntimeError):m.publish_facebook_reel('unused','title','description',saved.append)
   upload.assert_not_called();self.assertEqual(saved[0]['id'],'v')
 def test_fb_requires_confirmed_publishing_status(self):
  with tempfile.NamedTemporaryFile() as video:
   video.write(b'video');video.flush();checkpoints=[]
   replies=[{'video_id':'fb-id','upload_url':'https://rupload.facebook.com/video-upload/id'},
            {'success':True},{'status':{'publishing_phase':{'status':'complete'}}},RuntimeError('offline')]
   with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=replies),patch.object(m.AUTH_HTTP,'open') as upload:
    upload.return_value.__enter__.return_value.read.return_value=b'{"success":true}'
    receipt=m.publish_facebook_reel(video.name,'title','description',checkpoints.append)
   self.assertEqual(receipt['status'],'published');self.assertEqual(checkpoints[-1]['id'],'fb-id')
 def test_fb_acceptance_is_not_a_published_receipt(self):
  with tempfile.NamedTemporaryFile() as video:
   video.write(b'video');video.flush();checkpoints=[]
   replies=[{'video_id':'fb-id','upload_url':'https://rupload.facebook.com/video-upload/id'},
            {'success':True}]+[{'status':{'publishing_phase':{'status':'in_progress'}}}]*5
   with patch.dict(os.environ,ENV,clear=True),patch.object(m,'graph',side_effect=replies),patch.object(m.AUTH_HTTP,'open') as upload,patch.object(m.time,'sleep'):
    upload.return_value.__enter__.return_value.read.return_value=b'{"success":true}'
    with self.assertRaises(TimeoutError):m.publish_facebook_reel(video.name,'title','description',checkpoints.append)
   self.assertFalse(any(x.get('status')=='published' for x in checkpoints))
 def test_full_publisher_partial_receipts_block_retry(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'data').mkdir();(root/'state').mkdir()
   config={'publish_enabled':True,'channel_id':'UC5ZLfNHUI4z92IW69KVTGxg','ready_queue':'data/queue.json','per_video_approval_required':False}
   asset={'slot_key':'manual:q','question_id':'q','channel_id':config['channel_id'],'sha256':m.hashlib.sha256(b'video').hexdigest(),'download_url':'https://example.test/video','metadata':{'channel_id':config['channel_id'],'title':'quiz','description':'caption'},'quality_review':{'voice':'Charon','audio_language':'Tamil','visual_verified':True}}
   (root/'data/automation_config.json').write_text(json.dumps(config));(root/'data/queue.json').write_text(json.dumps([asset]));(root/'state/state.json').write_text('{}')
   yt=types.SimpleNamespace(get_youtube_client=lambda:None,upload_short=lambda *args:'yt-id')
   pipeline=types.SimpleNamespace(checked_question=lambda q:None)
   saved=[]
   def persist(sd,state,note):s.save(sd/'state.json',state);saved.append(json.loads(json.dumps(state)))
   with patch.dict(os.environ,dict(ENV,PUBLICATION_STATE_DIR=str(root/'state'),GITHUB_EVENT_NAME='workflow_dispatch'),clear=True),patch.object(s,'ROOT',root),patch.object(s,'persist',side_effect=persist),patch.dict(sys.modules,{'upload_youtube':yt,'run_pipeline':pipeline}),patch.object(m,'preflight',return_value={'page_id':m.PAGE_ID}),patch.object(m,'public_video',return_value=b'video'),patch.object(m,'publish_reel',side_effect=RuntimeError('uncertain')),patch.object(m,'publish_facebook_reel') as fb:
    with self.assertRaises(RuntimeError):s.main()
    fb.assert_not_called()
    state=json.loads((root/'state/state.json').read_text());entry=next(iter(state['slots'].values()))
    self.assertEqual(entry['status'],'ambiguous');self.assertEqual(entry['receipts']['youtube']['id'],'yt-id')
    self.assertEqual(entry['receipts']['instagram']['status'],'ambiguous');self.assertNotIn('q',state.get('published_ids',[]))
    self.assertEqual(next(iter(saved[0]['slots'].values()))['receipts'],{})
    with self.assertRaises(RuntimeError):s.main()
if __name__=='__main__':unittest.main()
