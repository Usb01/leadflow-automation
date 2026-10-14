import tempfile,unittest,sqlite3
from pathlib import Path
from app import normalize,process
from report import report

import uuid
class Scratch:
 def __init__(self):
  self.path=Path(__file__).parent/'.test-tmp'/uuid.uuid4().hex
  self.path.mkdir(parents=True)
  self.name=str(self.path)
 def cleanup(self):
  for file in self.path.iterdir():
   if file.is_file():file.unlink()
  self.path.rmdir()

class LeadTests(unittest.TestCase):
 def setUp(self):self.tmp=Scratch();self.db=Path(self.tmp.name)/'test.sqlite';self.lead={'name':' Alex ','email':'A@EXAMPLE.COM','budget':'2000','interest':'API'}
 def tearDown(self):self.tmp.cleanup()
 def test_normalization(self):self.assertEqual(normalize(self.lead)['email'],'a@example.com')
 def test_priority_boundary(self):self.assertEqual(normalize(self.lead)['route'],'priority_review');self.assertEqual(normalize({**self.lead,'budget':'1999'})['route'],'standard_review')
 def test_invalid_fields(self):
  for change in [{'email':'invalid'},{'name':' '},{'budget':'-1'},{'budget':'nan'}]:
   with self.subTest(change=change),self.assertRaises(ValueError):normalize({**self.lead,**change})
 def test_duplicate_in_same_batch(self):self.assertEqual([x['status'] for x in process([self.lead,self.lead],self.db)],['accepted','duplicate'])
 def test_replay_across_runs(self):process([self.lead],self.db);self.assertEqual(process([self.lead],self.db)[0]['status'],'duplicate')
 def test_invalid_record_does_not_stop_batch(self):self.assertEqual([x['status'] for x in process([{'email':'bad'},self.lead],self.db)],['rejected','accepted'])
 def test_html_escapes_input(self):
  path=Path(self.tmp.name)/'report.html';report(path,'Test','demo',[{'data':'<script>alert(1)</script>'}],{});self.assertNotIn('<script>',path.read_text())
if __name__=='__main__':unittest.main()
