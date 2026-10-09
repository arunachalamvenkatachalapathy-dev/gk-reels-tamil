import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("pipeline", Path(__file__).resolve().parents[1] / "scripts" / "run_pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)

class PipelinePauseTests(unittest.TestCase):
    def test_default_is_paused(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(pipeline, "json") as data:
            pipeline.main()
            data.loads.assert_not_called()

    def test_enabled_still_rejects_empty_bank(self):
        with patch.dict(os.environ, {"PUBLISHING_ENABLED": "true"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "question bank is empty"):
                pipeline.main()

if __name__ == "__main__":
    unittest.main()
