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
 def test_exact_approval(self):
  md={'channel_id':C['channel_id'],'title':'Quiz #Shorts','description':'Exact description #Shorts'}
  a={'channel_id':C['channel_id'],'question_id':'q','sha256':'a'*64,'metadata':md,'download_url':'https://example.test/video.mp4','approval':{'user_message_id':'original','approved_at':'2026-10-13','question_id':'q','video_sha256':'a'*64,'metadata':md.copy(),'channel_id':C['channel_id']}}
  self.assertEqual(s.verify_asset(a,C),md)
  a['metadata']['description']='Changed'
  with self.assertRaises(ValueError):s.verify_asset(a,C)
if __name__=='__main__':unittest.main()
