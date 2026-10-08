import unittest
from analyze import classify, canonical, sha

def response(text='', stop='stop', **fields):
    return {'choices':[{'finish_reason':stop,'message':dict(content=text,**fields)}]}

class ClassifierTests(unittest.TestCase):
    def test_empty_present(self): self.assertEqual(classify(200,response()),'V0')
    def test_missing(self): self.assertEqual(classify(200,response(None)),'V2')
    def test_budget(self): self.assertEqual(classify(200,response('', 'length')),'V1')
    def test_zero_width(self): self.assertEqual(classify(200,response('\u200b')),'NV');self.assertEqual(len('\u200b'.encode()),3)
    def test_symbol(self): self.assertEqual(classify(200,response('∅')),'R');self.assertEqual(len('∅'.encode()),3)
    def test_whitespace(self): self.assertEqual(classify(200,response('\n')),'NV')
    def test_ellipsis(self): self.assertEqual(classify(200,response('…')),'NV')
    def test_error(self): self.assertEqual(classify(520,None),'E')
    def test_refusal(self): self.assertEqual(classify(200,response(refusal='blocked')),'RF')
    def test_tool(self): self.assertEqual(classify(200,response(tool_calls=[{}])),'TC')
    def test_length_visible(self): self.assertEqual(classify(200,response('hello','length')),'R')
    def test_key_order(self): self.assertEqual(sha(canonical({'b':1,'a':2})),sha(canonical({'a':2,'b':1})))
if __name__=='__main__':unittest.main()
