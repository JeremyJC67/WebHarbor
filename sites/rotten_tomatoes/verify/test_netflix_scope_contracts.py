"""Bounded R0 scope regression fixtures. No browser runs or live databases."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import verify_0 as r0
from contracts import CONTRACTS
import test_date_contracts as fixture

EXPECTED = {'godzilla_minus_one', 'bugonia', 'war_machine', 'frankenstein_2025',
            'the_hunger_games_the_ballad_of_songbirds_and_snakes', 'jurassic_world_rebirth',
            'the_hunger_games', 'the_hunger_games_catching_fire'}


def rewrite_scope(directory, url_change=lambda x:x, dom_change=lambda x:x):
    p=Path(directory)/'trajectory.json';data=json.loads(p.read_text())
    for step in data['steps']:
        for key in ['url','url_after']:
            if '/browse/movies_at_home/' in step[key]:step[key]=url_change(step[key])
    p.write_text(json.dumps(data))
    for p in (Path(directory)/'observations').glob('*.txt'):
        text=p.read_text()
        if 'heading "Streaming at Home"' in text:p.write_text(dom_change(text))


class NetflixScopeContracts(unittest.TestCase):
    def test_public_contract_and_source_scope(self):
        self.assertEqual({m['slug'] for m in r0.CANDIDATES}, EXPECTED)
        self.assertIn('Subscription Platform set to Netflix', CONTRACTS[r0.TASK_ID]['prompt'])
        self.assertIn('Netflix', CONTRACTS[r0.TASK_ID]['judge_rubric'])

    def test_full_eight_candidates_and_all_writers(self):
        for answer in [fixture.ANSWER,fixture.table(writers='James Beaufort; Patrick Hughes')]:
            with self.subTest(answer=answer),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d,answer=answer)
                result=r0.evaluate(d,no_llm=True);self.assertTrue(result['pass'],result)
                self.assertIn({'check':'candidate_collection','count':8},result['evidence'])
        for writers in ['Patrick Hughes','James Beaufort','Patrick Hughes; James Beaufort; Jane Doe']:
            with self.subTest(writers=writers),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d,answer=fixture.table(writers=writers))
                self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_missing_or_wrong_platform_scope_fails(self):
        for platform in ['', 'Hulu']:
            with self.subTest(platform=platform),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d)
                rewrite_scope(d,lambda u:u.replace('&platform=Netflix','&platform='+platform),
                              lambda text:text.replace('option "Netflix" [selected]',f'option "{platform or "All Subscription Platforms"}" [selected]'))
                self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_url_and_visible_selection_must_agree(self):
        for wrong_side in ['url','dom']:
            with self.subTest(side=wrong_side),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d)
                if wrong_side=='url':rewrite_scope(d,lambda u:u.replace('&platform=Netflix','&platform=Hulu'))
                else:rewrite_scope(d,dom_change=lambda text:text.replace('option "Netflix" [selected]','option "Netflix"'))
                self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_conflicting_platform_query_is_not_a_proven_scope(self):
        with tempfile.TemporaryDirectory() as d:
            fixture.fixture(d)
            rewrite_scope(d,lambda u:u.replace('&platform=Netflix','&platform=Netflix&platform=Hulu'))
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_extra_filters_cannot_silently_reduce_candidates(self):
        for parameter in ['rating=R','certified_fresh=true']:
            with self.subTest(parameter=parameter),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d)
                rewrite_scope(d,lambda u:u+'&'+parameter)
                self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_same_origin_routes_and_sort_order_are_not_fixed(self):
        for method in ['goto','navigate','press','keypress']:
            with self.subTest(method=method),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d,entry_method=method,reverse=True)
                rewrite_scope(d,lambda u:u+'&sort=a_z')
                result=r0.evaluate(d,no_llm=True);self.assertTrue(result['pass'],result)

    def test_scope_uses_exact_subscription_membership(self):
        for platforms,expected in [('Hulu, Netflix',True),('Netflix Premium',False),('Hulu',False)]:
            with self.subTest(platforms=platforms),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d)
                for dbname in ['before.db','after.db']:
                    with sqlite3.connect(Path(d)/dbname) as db:
                        db.execute('UPDATE movies SET streaming_platform=? WHERE slug=?',(platforms,'war_machine'))
                result=r0.evaluate(d,no_llm=True);self.assertEqual(result['pass'],expected,result)

    def test_outside_platform_movie_is_preserved_but_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            fixture.fixture(d)
            for dbname in ['before.db','after.db']:
                with sqlite3.connect(Path(d)/dbname) as db:
                    db.execute('INSERT INTO movies VALUES(?,?,?,?,?,?,?)',(999,'outside_netflix','Outside Netflix','2027-01-01','Other Writer',1,'Hulu'))
                    db.execute('INSERT INTO movie_genres VALUES(999,1)')
            result=r0.evaluate(d,no_llm=True);self.assertTrue(result['pass'],result)
            with sqlite3.connect(Path(d)/'after.db') as db:db.execute('DELETE FROM movies WHERE id=999')
            self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_previous_scope_winners_and_missing_candidate_fail(self):
        for answer in [fixture.table('Supergirl','Jul 28, 2026','Ana Nogueira'),
                       fixture.table('Project Hail Mary','May 12, 2026','Drew Goddard')]:
            with self.subTest(answer=answer),tempfile.TemporaryDirectory() as d:
                fixture.fixture(d,answer=answer);self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])
        with tempfile.TemporaryDirectory() as d:
            fixture.fixture(d,visited=r0.CANDIDATES[:-1]);self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])

    def test_unknown_date_rule_remains_without_inventing_a_current_unknown(self):
        unknown={'slug':'unknown_date','title':'Unknown Date Film','date':None,'writers':['Unknown Writer']}
        facts=[dict(next(m for m in r0.CANDIDATES if m['slug']=='war_machine')),unknown]
        with patch.object(r0,'CANDIDATES',facts):
            with tempfile.TemporaryDirectory() as d:
                fixture.fixture(d);result=r0.evaluate(d,no_llm=True);self.assertTrue(result['pass'],result)
                self.assertTrue(any(e['check']=='streaming_date_absent:unknown_date' for e in result['evidence']))
            with tempfile.TemporaryDirectory() as d:
                fixture.fixture(d,visited=facts[:1]);self.assertFalse(r0.evaluate(d,no_llm=True)['pass'])


if __name__=='__main__':unittest.main(verbosity=2)
