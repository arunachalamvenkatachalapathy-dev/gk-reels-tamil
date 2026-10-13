import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('pipeline',Path(__file__).resolve().parents[1]/'scripts/run_pipeline.py')
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)
class PipelineContractTests(unittest.TestCase):
 def test_requires_question(self):
  with patch('sys.argv',['run_pipeline.py']):
   with self.assertRaises(SystemExit):pipeline.main()
 def test_empty_bank_rejected(self):
  with patch.object(pipeline,'load',return_value=[]):
   with self.assertRaisesRegex(ValueError,'One unique source-reviewed'):
    pipeline.checked_question('missing')
 def test_explicit_source_rebuild_allowed(self):
  q={'id':'rebuilt'};r={'rebuilt':{'release_verdict':'verified','source_url':'https://example.test','scan_verified':False,'source_rebuild_verified':True,'semantic_dedup_verified':True}}
  with patch.object(pipeline,'load',side_effect=[[q],r]):self.assertEqual(pipeline.checked_question('rebuilt'),q)
if __name__=='__main__':unittest.main()
