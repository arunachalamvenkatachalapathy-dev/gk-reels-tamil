import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('validate_bank', Path(__file__).resolve().parents[1] / 'scripts/validate_bank.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class BankValidation(unittest.TestCase):
    def row(self):
        return {'id':'p0014-e1','question':'வினா','question_en':'Question','options':['அ','ஆ','இ','ஈ'],'options_en':['A','B','C','D'],'correct_index':0,'answer':'அ','answer_en':'A'}
    def test_valid(self):
        self.assertEqual(module.validate([self.row()], 1), 1)
    def test_duplicate(self):
        with self.assertRaises(ValueError): module.validate([self.row(), self.row()])
    def test_bad_answer(self):
        q=self.row();q['answer_en']='B'
        with self.assertRaises(ValueError): module.validate([q])
    def test_missing_tamil(self):
        q=self.row();q['question']=''
        with self.assertRaises(ValueError): module.validate([q])
    def test_missing_choice(self):
        q=self.row();q['options'].pop()
        with self.assertRaises(ValueError): module.validate([q])
    def test_count(self):
        with self.assertRaises(ValueError): module.validate([self.row()], 730)
    def test_boolean_key_rejected(self):
        q=self.row();q['correct_index']=True
        with self.assertRaises(ValueError): module.validate([q])

if __name__ == '__main__': unittest.main()
