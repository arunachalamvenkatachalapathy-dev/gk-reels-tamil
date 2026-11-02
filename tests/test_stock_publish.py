"""Gate tests for the Tamil Drive-stock publisher. No network, no credentials."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stock_publish as sp


CONFIG = {
    "drive_folder_id": "folder",
    "channel_id": "UC5ZLfNHUI4z92IW69KVTGxg",
    "slots": {"morning": "07:30", "afternoon": "19:30"},
    "window_minutes": 120,
    "quarantined_ids": ["p2412-e1", "p3003-e1", "p3310-e1", "p3580-e1", "p0886-e1"],
    "studio_evening_until": "2026-11-05",
    "state_branch": "tamil-publication-state",
    "state_file": "stock_state.json",
}


def ist(y, m, d, hh, mm):
    from datetime import timedelta
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)


class NameParsing(unittest.TestCase):
    def test_stock_zip(self):
        self.assertEqual(sp.parse_stock_name("GK_TA_private_p0464-e1.zip"), "p0464-e1")

    def test_pilot_and_records_rejected(self):
        self.assertIsNone(sp.parse_stock_name("GK_TA_private_p0217-e1_4seg.zip"))
        self.assertIsNone(sp.parse_stock_name("TA-STOCK-INDEX.txt"))
        self.assertIsNone(sp.parse_stock_name("TA-B27-held-p4402-e1-evidence.tar.gz"))


class TitleGate(unittest.TestCase):
    def test_english_title_ok(self):
        sp.validate_title("Which Article Empowers Parliament? | Tamil GK #Shorts")

    def test_tamil_script_title_rejected(self):
        with self.assertRaises(ValueError):
            sp.validate_title("யார் நிறுவனர் அல்ல? | Tamil GK #Shorts")

    def test_length(self):
        with self.assertRaises(ValueError):
            sp.validate_title("x" * 101)
        with self.assertRaises(ValueError):
            sp.validate_title("")


class ManifestGate(unittest.TestCase):
    def manifest(self, **kw):
        base = {
            "destination_channel_id": CONFIG["channel_id"],
            "videos": [{"question_id": "p1-e1", "title": "Q? #Shorts", "description": "d", "file": "a.mp4", "sha256": "0" * 64, "duration": 27.4}],
        }
        base.update(kw)
        return base

    def test_valid(self):
        v = sp.validate_manifest(self.manifest(), CONFIG["channel_id"])
        self.assertEqual(v["file"], "a.mp4")

    def test_wrong_channel(self):
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest(destination_channel_id="UC_other"), CONFIG["channel_id"])

    def test_duration_cap(self):
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest(videos=[{"title": "Q #Shorts", "description": "d", "file": "a.mp4", "sha256": "0" * 64, "duration": 36.0}]), CONFIG["channel_id"])


class CandidateChoice(unittest.TestCase):
    def stock(self, *qids):
        return [{"id": q, "name": f"GK_TA_private_{q}.zip"} for q in qids]

    def test_quarantine_and_published_excluded(self):
        state = {"published_ids": ["p0464-e1"], "slots": {}}
        out = sp.choose_candidates(self.stock("p0464-e1", "p2412-e1", "p0465-e1"), CONFIG, state)
        self.assertEqual([q for q, _ in out], ["p0465-e1"])

    def test_deterministic_order(self):
        out = sp.choose_candidates(self.stock("p2000-e1", "p0100-e1", "p1500-e2"), CONFIG, {"slots": {}})
        self.assertEqual([q for q, _ in out], ["p0100-e1", "p1500-e2", "p2000-e1"])


class SlotGate(unittest.TestCase):
    def test_morning_open(self):
        slot = sp.select_slot(ist(2026, 11, 2, 7, 45), CONFIG, {"slots": {}})
        self.assertEqual(slot["key"], "2026-11-02:morning")

    def test_evening_suppressed_while_studio_queue_active(self):
        self.assertIsNone(sp.select_slot(ist(2026, 11, 2, 19, 45), CONFIG, {"slots": {}}))
        self.assertIsNone(sp.select_slot(ist(2026, 11, 5, 19, 45), CONFIG, {"slots": {}}))

    def test_evening_open_after_studio_queue(self):
        slot = sp.select_slot(ist(2026, 11, 6, 19, 45), CONFIG, {"slots": {}})
        self.assertEqual(slot["key"], "2026-11-06:afternoon")

    def test_published_slot_not_repicked(self):
        state = {"slots": {"2026-11-02:morning": {"status": "published"}}}
        self.assertIsNone(sp.select_slot(ist(2026, 11, 2, 7, 45), CONFIG, state))

    def test_outside_window(self):
        self.assertIsNone(sp.select_slot(ist(2026, 11, 2, 12, 0), CONFIG, {"slots": {}}))


if __name__ == "__main__":
    unittest.main()
