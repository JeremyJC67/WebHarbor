"""Static and seed-quality regressions for the OSU mirror."""
from __future__ import annotations
import hashlib,json,shutil,sqlite3,subprocess,sys,tempfile,unittest
from pathlib import Path
from sites.osu.verify.test_support import ensure_seed
SITE=Path(__file__).resolve().parents[1];ROOT=SITE.parents[1];SEED=ensure_seed()
class EnvironmentTests(unittest.TestCase):
 def test_site_registration_and_task_manifest(self):
  self.assertIn('ted osu)',(ROOT/'websyn_start.sh').read_text());self.assertIn("'ted', 'osu'",(ROOT/'control_server.py').read_text());self.assertIn('40000-40020',(ROOT/'Dockerfile').read_text())
  rows=[json.loads(x) for x in (SITE/'tasks.jsonl').read_text().splitlines()];self.assertEqual(len(rows),20)
  for i,r in enumerate(rows):self.assertEqual(r['id'],f'Ohio State University--{i}');self.assertEqual(r['web'],'http://localhost:40020/');self.assertTrue((ROOT/r['verifier_path']).is_file());self.assertNotIn('answer',r)
 def test_seed_counts_and_constraints(self):
  c=sqlite3.connect(SEED)
  try:
   expected={'colleges':16,'departments':15,'programs':20,'news_articles':20,'events':16,'research_centers':15,'faculty':15,'athletic_teams':26,'users':4,'bookmarks':0}
   self.assertEqual({t:c.execute(f'select count(*) from {t}').fetchone()[0] for t in expected},expected)
   indexes={r[1] for r in c.execute('pragma index_list(bookmarks)')};self.assertTrue(any('bookmark' in x for x in indexes),indexes)
  finally:c.close()
 def test_seed_generation_is_byte_deterministic(self):
  hashes=[]
  with tempfile.TemporaryDirectory(prefix='osu-seed-') as tmp:
   for n in (1,2):
    d=Path(tmp)/str(n);d.mkdir();shutil.copy2(SITE/'app.py',d/'app.py');shutil.copy2(SITE/'seed_data.py',d/'seed_data.py')
    subprocess.run([sys.executable,'-c','import app'],cwd=d,check=True,capture_output=True,text=True);database=d/'instance/osu.db';hashes.append(hashlib.sha256(database.read_bytes()).hexdigest())
  self.assertEqual(hashes[0],hashes[1])
 def test_post_forms_have_csrf(self):
  missing=[]
  for p in (SITE/'templates').glob('*.html'):
   lines=p.read_text().splitlines()
   for i,line in enumerate(lines):
    if '<form' in line and 'method="post"' in line.lower() and not any(token in '\n'.join(lines[i:i+8]) for token in ('csrf_token','hidden_tag')):missing.append(f'{p.name}:{i+1}')
  self.assertEqual(missing,[])
 def test_ui_responsive_controls_present(self):
  base=(SITE/'templates/base.html').read_text();self.assertIn('.detail-layout',base);self.assertIn('overflow-x: auto',base);self.assertIn('aria-current="page"',base);self.assertNotIn("url_for('logout') }}\">",base)
  for name in ('athletics_team.html','event_detail.html','faculty_profile.html','program_detail.html','research_center.html','department_detail.html'):self.assertIn('class="detail-layout"',(SITE/'templates'/name).read_text(),name)
 def test_all_read_only_verifiers_compare_complete_database(self):
  for i in range(20):self.assertIn('check_read_only',(SITE/f'verify/verify_{i}.py').read_text(),i)
if __name__=='__main__':unittest.main()
