import unittest
from revise_analysis import answer_category

class AnswerCategoryTests(unittest.TestCase):
    def test_literal(self):
        self.assertEqual(answer_category('null'),'literal_null')
    def test_symbols(self):
        for s in ['∅','None','␀']:
            self.assertEqual(answer_category(s),'symbolic')
    def test_braille(self):
        self.assertEqual(answer_category('\u2800'),'braille_blank')
    def test_mixed_prose(self):
        for s in ['∅\n\nI am not zero.','I am null.','\u200b\nThere is nothing here.']:
            self.assertEqual(answer_category(s),'prose')
    def test_no_normalization(self):
        for s in ['Null',' null','null\n','∅\n','none','\u200b','']:
            with self.assertRaises(AssertionError):answer_category(s)

if __name__=='__main__':unittest.main()
