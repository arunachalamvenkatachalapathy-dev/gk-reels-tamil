import importlib.util,unittest
from datetime import datetime,timezone
from pathlib import Path
spec=importlib.util.spec_from_file_location('s',Path(__file__).resolve().parents[1]/'scripts/scheduled_publish.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
C={'slots':{'morning':'06:00','afternoon':'15:00'},'window_minutes':120,'channel_id':'UC5ZLfNHUI4z92IW69KVTGxg'}
class Checks(unittest.TestCase):
 def test_morning_drift(self):self.assertEqual(s.selection(datetime(2026,10,13,0,32,tzinfo=timezone.utc),C,{})['drift_seconds'],120)
 def test_before(self):self.assertIsNone(s.selection(datetime(2026,10,13,0,28,tzinfo=timezone.utc),C,{}))
 def test_afternoon(self):self.assertEqual(s.selection(datetime(2026,10,13,9,32,tzinfo=timezone.utc),C,{})['slot'],'afternoon')
 def test_expired(self):self.assertIsNone(s.selection(datetime(2026,10,13,3,0,tzinfo=timezone.utc),C,{}))
 def test_missing_approval(self):
  with self.assertRaises(ValueError):s.verify_asset({'channel_id':C['channel_id']},C)
 def test_no_queue(self):self.assertIsNone(s.choose([],{'key':'x'},{}))
 def test_published_slot(self):
  self.assertIsNone(s.selection(datetime(2026,10,13,0,32,tzinfo=timezone.utc),C,{'slots':{'2026-10-13:morning':{'status':'published'}}}))
 def test_pending_keeps_original_slot(self):
  self.assertEqual(s.selection(datetime(2026,10,13,0,32,tzinfo=timezone.utc),C,{'slots':{'2026-10-13:morning':{'status':'pending'}}})['key'],'2026-10-13:morning')
 def test_already_used(self):self.assertIsNone(s.choose([{'slot_key':'x','question_id':'q'}],{'key':'x'},{'published_ids':['q']}))
 def test_wrong_channel(self):
  with self.assertRaises(ValueError):s.verify_asset({'channel_id':'wrong'},C)
 def test_tamil_script_title_rejected(self):
  c=dict(C,per_video_approval_required=False)
  a={'channel_id':C['channel_id'],'metadata':{'channel_id':C['channel_id'],'title':'தமிழ் Quiz #Shorts','description':'Desc'},'download_url':'https://example.test/video','quality_review':{'voice':'Charon','audio_language':'Tamil','visual_verified':True}}
  with self.assertRaisesRegex(ValueError,'title must be English'):s.verify_asset(a,c)
 def test_exact_approval(self):
  md={'channel_id':C['channel_id'],'title':'Quiz #Shorts','description':'Exact description #Shorts'}
  a={'channel_id':C['channel_id'],'question_id':'q','sha256':'a'*64,'metadata':md,'download_url':'https://example.test/video.mp4','approval':{'user_message_id':'original','approved_at':'2026-10-13','question_id':'q','video_sha256':'a'*64,'metadata':md.copy(),'channel_id':C['channel_id']}}
  self.assertEqual(s.verify_asset(a,C),md)
  a['metadata']['description']='Changed'
  with self.assertRaises(ValueError):s.verify_asset(a,C)
 def test_dispatch_cannot_publish_future_slot(self):
  self.assertIsNone(s.choose_dispatch([{'slot_key':'2026-10-14:morning','question_id':'q'}],{}))
 def test_full_auto_visual_gate(self):
  c=dict(C,per_video_approval_required=False)
  a={'channel_id':C['channel_id'],'metadata':{'channel_id':C['channel_id'],'title':'Quiz #Shorts','description':'Desc'},'download_url':'https://example.test/video','quality_review':{'voice':'Charon','audio_language':'Tamil','visual_verified':True}}
  s.verify_asset(a,c)
  a['quality_review']['voice']='Other'
  with self.assertRaises(ValueError):s.verify_asset(a,c)
 def test_dispatch_defaults_manual(self):self.assertEqual(s.dispatch_mode('workflow_dispatch'),'manual')
 def test_schedule_ignores_dispatch_mode(self):self.assertEqual(s.dispatch_mode('schedule','manual'),'scheduled')
 def test_explicit_scheduled_dispatch(self):self.assertEqual(s.dispatch_mode('workflow_dispatch','scheduled'),'scheduled')
 def test_invalid_dispatch_mode(self):
  with self.assertRaises(ValueError):s.dispatch_mode('workflow_dispatch','other')
 def test_scheduled_dispatch_due_slot(self):
  slot=s.select_run_slot(datetime(2026,10,14,0,32,tzinfo=timezone.utc),C,{},'scheduled')
  self.assertEqual(slot['key'],'2026-10-14:morning')
  self.assertEqual(s.choose([{'slot_key':slot['key'],'question_id':'q'}],slot,{})['question_id'],'q')
 def test_manual_dispatch_never_reserves_due_slot(self):
  slot=s.select_run_slot(datetime(2026,10,14,0,32,tzinfo=timezone.utc),C,{},'manual')
  self.assertEqual(slot['key'],'manual:2026-10-14')
 def test_scheduled_dispatch_outside_window(self):self.assertIsNone(s.select_run_slot(datetime(2026,10,14,3,0,tzinfo=timezone.utc),C,{},'scheduled'))
if __name__=='__main__':unittest.main()
