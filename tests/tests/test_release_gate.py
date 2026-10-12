import hashlib, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from run_pipeline import verify_release, CHANNEL

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.video=Path(self.temp.name)/'draft.mp4'
        self.video.write_bytes(b'fixture')
        self.meta={'channel_id':CHANNEL,'title':'Tamil quiz #Shorts','description':'Verified sample'}
        self.approval={'channel_id':CHANNEL,'question_id':'ta-test','video_sha256':hashlib.sha256(b'fixture').hexdigest(),'metadata':self.meta.copy(),'user_message_id':'fixture-user','approved_at':'fixture-date'}
    def tearDown(self):self.temp.cleanup()
    def test_exact_match(self):verify_release(self.approval,self.video,self.meta,'ta-test')
    def test_changed_video(self):
        self.video.write_bytes(b'changed')
        with self.assertRaises(ValueError):verify_release(self.approval,self.video,self.meta,'ta-test')
    def test_changed_copy(self):
        self.meta['title']='Unreviewed'
        with self.assertRaises(ValueError):verify_release(self.approval,self.video,self.meta,'ta-test')
    def test_wrong_channel(self):
        self.approval['channel_id']='wrong'
        with self.assertRaises(ValueError):verify_release(self.approval,self.video,self.meta,'ta-test')
    def test_missing_owner_evidence(self):
        self.approval.pop('user_message_id')
        with self.assertRaises(ValueError):verify_release(self.approval,self.video,self.meta,'ta-test')
