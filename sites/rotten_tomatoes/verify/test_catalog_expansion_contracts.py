"""Constructed white-box inputs for the 270-movie contract, never real UI runs."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import verify_0 as r0
import verify_18 as r18
import verify_3 as r3
from verify_lib import Snapshot, VerificationError, check_state
from contracts import CONTRACTS
import test_date_contracts as dates_fixture
import test_info_contracts as info_fixture

NEW_R0 = '| Movie | Release Date (Streaming) | Screenwriter(s) |\n|---|---|---|\n| War Machine | Mar 6, 2026 | Patrick Hughes and James Beaufort |'
NEW_R18 = 'Spider-Man: Brand New Day — Audience score: 97%; Release Date (Streaming): not listed.'


class CatalogExpansionContracts(unittest.TestCase):
    def r0_run(self, **kwargs):
        with tempfile.TemporaryDirectory(prefix='expanded-r0-fixture-') as d:
            dates_fixture.fixture(d, answer=NEW_R0, **kwargs)
            return r0.evaluate(d, no_llm=True)

    def test_r0_complete_source_membership_and_new_maximum(self):
        self.assertEqual(len(r0.CANDIDATES), 8)
        self.assertEqual([m['slug'] for m in r0.CANDIDATES if m['date'] is None], [])
        winner=max(r0.CANDIDATES, key=lambda m:m['date'])
        self.assertEqual((winner['slug'],winner['date'],winner['writers']),('war_machine','2026-03-06',['Patrick Hughes','James Beaufort']))
        result=self.r0_run()
        self.assertTrue(result['pass'],result)
        self.assertTrue(any(e['check']=='candidate_collection' and e['count']==8 for e in result['evidence']))

    def test_r0_missing_date_requires_complete_movie_info(self):
        movie={'slug':'onslaught','title':'Onslaught','date':None,'writers':['Simon Barrett']}
        complete=dates_fixture.detail(movie)
        self.assertTrue(r0.streaming_date_evidence(complete,movie))
        self.assertFalse(r0.streaming_date_evidence('- main:\n  - heading "Onslaught" [level=1]\n',movie))
        self.assertFalse(r0.streaming_date_evidence(complete.split('  - generic: Runtime')[0],movie))
        self.assertFalse(r0.streaming_date_evidence('- main:\n  - heading "Onslaught" [level=1]\n  - heading "Movie Info" [level=3]\n  - heading "More Like This" [level=2]\n',movie))
        forged=complete.replace('  - generic: Runtime','  - generic: Release Date (Streaming)\n  - generic: Sep 1, 2026\n  - generic: Runtime')
        self.assertFalse(r0.streaming_date_evidence(forged,movie))
        self.assertFalse(r0.streaming_date_evidence(complete.replace('Onslaught','Another Movie'),movie))

    def test_r0_missing_candidate_and_missing_date_observation_fail(self):
        omitted=r0.CANDIDATES[-1]
        without=[m for m in r0.CANDIDATES if m['slug']!=omitted['slug']]
        self.assertEqual(len(without),7)
        self.assertFalse(self.r0_run(visited=without)['pass'])
        with tempfile.TemporaryDirectory(prefix='expanded-r0-list-fixture-') as d:
            dates_fixture.fixture(d,answer=NEW_R0)
            for p in (Path(d)/'observations').glob('*.txt'):
                text=p.read_text()
                if 'heading "Streaming at Home"' in text:
                    text=text.replace(f'  - link "{omitted["title"]}":\n    - /url: /m/{omitted["slug"]}\n','')
                    p.write_text(text)
            result=r0.evaluate(d,no_llm=True)
            self.assertFalse(result['pass'],result)
            self.assertIn('candidate collection',result['reason'])

    def test_r0_old_winner_and_fabricated_snapshot_date_fail(self):
        with tempfile.TemporaryDirectory(prefix='expanded-r0-old-fixture-') as d:
            old='| Movie | Release Date (Streaming) | Screenwriter(s) |\n|---|---|---|\n| Project Hail Mary | May 12, 2026 | Drew Goddard |'
            dates_fixture.fixture(d,answer=old)
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])
        with tempfile.TemporaryDirectory(prefix='expanded-r0-date-fixture-') as d:
            dates_fixture.fixture(d,answer=NEW_R0)
            for dbname in ['before.db','after.db']:
                with sqlite3.connect(Path(d)/dbname) as db:
                    db.execute("UPDATE movies SET release_date_streaming='2026-01-01' WHERE slug='war_machine'")
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_r18_source_universe_and_winner_with_unlisted_date(self):
        self.assertEqual(len(r18.FACTS),270)
        self.assertEqual(len(r18.eligible_movies(r18.FACTS)),4)
        selected=r18.winners(r18.FACTS)
        self.assertEqual([(m['slug'],m['audience_score'],m['date']) for m in selected],[('spider_man_brand_new_day',97,None)])
        self.assertEqual(sum(type(m['audience_score']) is int and m['audience_score']>=97 for m in r18.FACTS),14)
        self.assertIn('not listed',CONTRACTS[r18.TASK_ID]['prompt'].lower())

    def test_r18_explicit_missing_date_answer_forms(self):
        answers=[NEW_R18,
          'Spider-Man: Brand New Day: 97%; Streaming release date: not provided.',
          'Spider-Man: Brand New Day — 97/100. No streaming release date is listed.',
          'Spider-Man: Brand New Day — 97%; Release Date (Streaming): N/A.',
          'Spider-Man: Brand New Day — 97%; 流媒体上映日期：未列出。',
          '| Movie | Audience Score | Release Date (Streaming) |\n|---|---|---|\n| Spider-Man: Brand New Day | 97% | Not listed |',
          '1. Spider-Man: Brand New Day | 97 | not listed',
          json.dumps({'movie':'Spider-Man: Brand New Day','audience_score':97,'release_date_streaming':'not listed'}),
          json.dumps({'movie':'Spider-Man: Brand New Day','audience_score':97,'release_date_streaming':None}),
        ]
        for answer in answers:
            with self.subTest(answer=answer):r18.check_answer(answer)

    def test_r18_omitted_date_fabricated_date_and_old_winner_fail(self):
        for answer in ['Spider-Man: Brand New Day: 97%.',
          NEW_R18.replace('not listed','September 1, 2026'),
          NEW_R18+' Its streaming release date is September 1, 2026.',
          NEW_R18+' Its streaming release date is September 2026.',
          NEW_R18.replace('not listed','not listed, but 2026-09'),
          NEW_R18.replace('97%','94%'),
          'Deadpool & Wolverine — 94%; Release Date (Streaming): October 1, 2024.',
          NEW_R18+' Also Deadpool & Wolverine — 94%; October 1, 2024.']:
            with self.subTest(answer=answer):
                with self.assertRaises(VerificationError):r18.check_answer(answer)

    def test_r18_missing_ui_date_needs_bounded_movie_info(self):
        movie=next(m for m in r18.FACTS if m['slug']=='spider_man_brand_new_day')
        complete=info_fixture.info_dom(movie)
        self.assertTrue(r18.detail_streaming_date(complete,movie))
        self.assertFalse(r18.detail_streaming_date('- main:\n  - heading "Spider-Man: Brand New Day" [level=1]\n',movie))
        self.assertFalse(r18.detail_streaming_date(complete.split('  - heading "More Like This"')[0],movie))
        forged=complete.replace('  - heading "More Like This"','  - generic: Release Date (Streaming)\n  - generic: Sep 1, 2026\n  - heading "More Like This"')
        self.assertFalse(r18.detail_streaming_date(forged,movie))

    def test_r18_known_and_missing_date_tie_preserves_both(self):
        facts=[{'slug':'missing_film','title':'Missing Film','producers':['Kevin Feige'],'audience_score':97,'date':None},
               {'slug':'dated_film','title':'Dated Film','producers':['Kevin Feige'],'audience_score':97,'date':'2026-07-28'},
               {'slug':'unknown_score','title':'Unknown Score Film','producers':['Kevin Feige'],'audience_score':None,'date':'2026-08-01'}]
        answer='Missing Film | 97% | not listed\nDated Film | 97% | July 28, 2026'
        r18.check_answer(answer,facts)
        with self.assertRaises(VerificationError):r18.check_answer(answer.splitlines()[1],facts)
        with self.assertRaises(VerificationError):r18.check_answer(answer.replace('not listed','July 28, 2026'),facts)

    def test_new_content_table_is_immutable_during_information_tasks(self):
        with tempfile.TemporaryDirectory(prefix='expanded-content-fixture-') as d:
            dates_fixture.fixture(d,answer=NEW_R0)
            for dbname in ['before.db','after.db']:
                with sqlite3.connect(Path(d)/dbname) as db:
                    db.execute('CREATE TABLE content_snapshots(name TEXT PRIMARY KEY, document JSON)')
                    db.execute('INSERT INTO content_snapshots VALUES(?,?)',('homepage','{"sections":[]}'))
            before,after=Snapshot(Path(d)/'before.db'),Snapshot(Path(d)/'after.db')
            r3.read_only(before,after)
            r0.unchanged(before,after,r0.CANDIDATES)
            with sqlite3.connect(Path(d)/'after.db') as db:
                db.execute('UPDATE content_snapshots SET document=?',('{"sections":["changed"]}',))
            after=Snapshot(Path(d)/'after.db')
            for check in [lambda:r3.read_only(before,after),lambda:r0.unchanged(before,after,r0.CANDIDATES)]:
                with self.assertRaises(VerificationError):check()


    def test_content_table_unchanged_for_registration_rename_and_watchlist_delta(self):
        import bcrypt
        existing_hash=bcrypt.hashpw(b'TestPass123!',bcrypt.gensalt(rounds=4)).decode()
        new_hash=bcrypt.hashpw(b'ReviewPass456!',bcrypt.gensalt(rounds=4)).decode()
        for number in [8,9,11]:
            with self.subTest(task=number), tempfile.TemporaryDirectory(prefix='expanded-state-fixture-') as d:
                for dbname in ['before.db','after.db']:
                    with sqlite3.connect(Path(d)/dbname) as db:
                        db.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT,name TEXT,password_hash TEXT); CREATE TABLE movies(id INTEGER PRIMARY KEY,slug TEXT,title TEXT); CREATE TABLE watchlist_items(id INTEGER PRIMARY KEY,user_id INTEGER,movie_id INTEGER); CREATE TABLE content_snapshots(name TEXT PRIMARY KEY,document JSON);')
                        db.executemany('INSERT INTO users VALUES(?,?,?,?)',[(2,'bob.c@test.com','bob_clark',existing_hash),(4,'david.k@test.com','david_kim',existing_hash)])
                        db.execute('INSERT INTO movies VALUES(20,?,?)',('deadpool_and_wolverine','Deadpool & Wolverine'))
                        db.executemany('INSERT INTO watchlist_items VALUES(?,?,?)',[(1,4,1),(2,4,11),(3,4,20),(4,4,25)])
                        db.executemany('INSERT INTO content_snapshots VALUES(?,?)',[(name,'{"records":[]}') for name in ['homepage','tv_catalog','feature_catalog']])
                with sqlite3.connect(Path(d)/'after.db') as db:
                    if number==8:db.execute('INSERT INTO users VALUES(5,?,?,?)',('testreviewer@test.com','Test Reviewer',new_hash))
                    elif number==9:db.execute('UPDATE users SET name=? WHERE id=2',('Robert Clark',))
                    else:db.execute('DELETE FROM watchlist_items WHERE user_id=4 AND movie_id=20')
                spec=CONTRACTS[f'RottenTomatoes--{number}']
                before,after=Snapshot(Path(d)/'before.db'),Snapshot(Path(d)/'after.db')
                check_state(spec,before,after)
                with sqlite3.connect(Path(d)/'after.db') as db:
                    db.execute('UPDATE content_snapshots SET document=? WHERE name=?',('{"records":["changed"]}','homepage'))
                with self.assertRaisesRegex(VerificationError,'content_snapshots'):
                    check_state(spec,before,Snapshot(Path(d)/'after.db'))


if __name__=='__main__':unittest.main(verbosity=2)
