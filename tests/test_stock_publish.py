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


class TitleOverride(unittest.TestCase):
    def manifest(self, title, qid="p0226-e1"):
        return {
            "destination_channel_id": CONFIG["channel_id"],
            "videos": [{"question_id": qid, "title": title, "description": "d", "file": "a.mp4", "sha256": "0" * 64, "duration": 27.4}],
        }

    def test_override_replaces_overlong_title(self):
        overrides = {"p0226-e1": "What Does the Song 'A War Without Bloodshed' Promote? | Tamil GK #Shorts"}
        v = sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"], overrides, "p0226-e1")
        self.assertEqual(v["title"], overrides["p0226-e1"])

    def test_override_matched_by_manifest_question_id(self):
        overrides = {"p0226-e1": "Short Title | Tamil GK #Shorts"}
        v = sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"], overrides)
        self.assertEqual(v["title"], "Short Title | Tamil GK #Shorts")

    def test_unrelated_override_leaves_bad_title_rejected(self):
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"], {"p9999-e1": "Other | Tamil GK #Shorts"}, "p0226-e1")

    def test_override_itself_validated(self):
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"], {"p0226-e1": "y" * 101}, "p0226-e1")
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"], {"p0226-e1": "யார்? | Tamil GK #Shorts"}, "p0226-e1")

    def test_no_overrides_unchanged_behaviour(self):
        with self.assertRaises(ValueError):
            sp.validate_manifest(self.manifest("x" * 120), CONFIG["channel_id"])
        v = sp.validate_manifest(self.manifest("Q? #Shorts"), CONFIG["channel_id"], None, "p0226-e1")
        self.assertEqual(v["title"], "Q? #Shorts")


class StockConfigData(unittest.TestCase):
    """The real stock_config.json: overrides and quarantine stay disjoint and
    every override passes the publisher's own title gate."""

    def test_real_config_overrides_valid_and_disjoint(self):
        cfg = json.loads((Path(sp.ROOT) / "data/stock_config.json").read_text())
        overrides = cfg.get("title_overrides", {})
        self.assertEqual(len(overrides), 46)
        self.assertFalse(set(overrides) & set(cfg.get("quarantined_ids", [])))
        for qid, title in overrides.items():
            sp.validate_title(title)
            self.assertRegex(qid, r"^p\d+-e\d+$")


class CandidateChoiceWithOverrides(unittest.TestCase):
    def test_reinstated_ids_pickable_again(self):
        cfg = dict(CONFIG, title_overrides={"p0226-e1": "Short | Tamil GK #Shorts"})
        stock = [{"id": "1", "name": "GK_TA_private_p0226-e1.zip"}, {"id": "2", "name": "GK_TA_private_p2412-e1.zip"}]
        out = sp.choose_candidates(stock, cfg, {"slots": {}})
        self.assertEqual([q for q, _ in out], ["p0226-e1"])


class _Resp:
    def __init__(self, status):
        self.status = status


class _HttpErr(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.resp = _Resp(status)


class _FlakyRequest:
    def __init__(self, failures, status):
        self.failures, self.status, self.calls = failures, status, 0

    def execute(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise _HttpErr(self.status)
        return {"items": []}


class ReadRetry(unittest.TestCase):
    def test_retries_transient_503_then_succeeds(self):
        req, waits = _FlakyRequest(2, 503), []
        self.assertEqual(sp.execute_read_with_retry(req, sleep=waits.append), {"items": []})
        self.assertEqual(req.calls, 3)
        self.assertEqual(waits, [2.0, 4.0])

    def test_gives_up_loudly_after_attempts(self):
        req = _FlakyRequest(99, 503)
        with self.assertRaises(_HttpErr):
            sp.execute_read_with_retry(req, attempts=3, sleep=lambda s: None)
        self.assertEqual(req.calls, 3)

    def test_non_transient_error_not_retried(self):
        req = _FlakyRequest(99, 403)
        with self.assertRaises(_HttpErr):
            sp.execute_read_with_retry(req, sleep=lambda s: None)
        self.assertEqual(req.calls, 1)


if __name__ == "__main__":
    unittest.main()
