import sys,unittest
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from slot_gate import due_slot, reserve, confirm_published

class SlotGateTests(unittest.TestCase):
    times={'morning':'06:00','afternoon':'15:00'} # Test data only, not deployment defaults.
    def at(self,t):return datetime.fromisoformat('2026-10-12T'+t+'+05:30')
    def test_preopen(self):self.assertIsNone(due_slot(self.at('05:59'),{},self.times))
    def test_earliest_at_afternoon(self):self.assertEqual(due_slot(self.at('16:00'),{},self.times)['slot'],'morning')
    def test_afternoon_after_morning(self):
        state={'slots':{'2026-10-12:morning':{'status':'published'}}}
        self.assertEqual(due_slot(self.at('16:00'),state,self.times)['slot'],'afternoon')
    def test_future_slot_skips(self):
        state={'slots':{'2026-10-12:morning':{'status':'published'}}}
        self.assertIsNone(due_slot(self.at('14:59'),state,self.times))
    def test_complete_day(self):
        s={'slots':{f'2026-10-12:{x}':{'status':'published'} for x in self.times}}
        self.assertIsNone(due_slot(self.at('23:59'),s,self.times))
    def test_ist_date_not_utc(self):
        s=due_slot(datetime.fromisoformat('2026-10-12T00:31:00+00:00'),{},self.times)
        self.assertEqual(s['key'],'2026-10-12:morning')
    def test_pending_blocks_duplicate(self):
        s={'slots':{'2026-10-12:morning':{'status':'pending'}}}
        with self.assertRaisesRegex(RuntimeError,'Reconcile'):due_slot(self.at('16:00'),s,self.times)
    def test_no_previous_date_backfill(self):
        s={'slots':{'2026-10-11:morning':{'status':'failed'}}}
        self.assertEqual(due_slot(self.at('06:00'),s,self.times)['key'],'2026-10-12:morning')
    def test_unconfirmed_times_rejected(self):
        with self.assertRaises(ValueError):due_slot(self.at('16:00'),{}, {})
    def test_reservation_not_consumed_and_receipts_required(self):
        s={};select=due_slot(self.at('16:00'),s,self.times);reserve(s,select,'ta-1')
        self.assertNotIn('published_ids',s)
        with self.assertRaises(RuntimeError):confirm_published(s,select['key'],['youtube'])
        s['slots'][select['key']]['destinations']['youtube']={'id':'receipt'}
        confirm_published(s,select['key'],['youtube'])
        self.assertEqual(s['published_ids'],['ta-1'])
