import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
from loop.runner import run
class T(unittest.TestCase):
 def test_tool(self):self.assertEqual(run([{'type':'tool_call','name':'x','arguments':{}}],{'x':lambda x:'ok'})[1]['result'],'ok')
 def test_unknown(self):
  with self.assertRaises(ValueError):run([{'type':'tool_call','name':'bad'}],{})
if __name__=='__main__':unittest.main()
