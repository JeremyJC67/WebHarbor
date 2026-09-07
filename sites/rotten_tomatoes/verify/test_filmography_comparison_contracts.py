"""R18 false-negative regression fixtures; no real browser runs are created."""
import json
import unittest
from unittest.mock import patch

import verify_18 as v
import verify_lib
from verify_lib import VerificationError
import test_info_contracts as fixture

ANSWER = fixture.ANSWER18
RATIONALE = ('Other candidates: Deadpool & Wolverine 94%, '
             'The Fantastic Four: First Steps 90%, Avengers: Endgame 90%.')
OBSERVED_ANSWER = ('Spider-Man: Brand New Day 的观众分数最高，为 97%；Release Date (Streaming)：未列出。没有并列电影。'
                   'Kevin Feige 人物页的完整 Filmography 显示其余三部为：Deadpool & Wolverine 94%、'
                   'The Fantastic Four: First Steps 90%、Avengers: Endgame 90%。'
                   '获选电影的完整 Movie Info 确认 Producer 包含 Kevin Feige，且未列 Streaming 日期。')


def filmography(movies, person='Kevin Feige', roles=None, scores=None):
    roles, scores = roles or {}, scores or {}
    text = ('- main:\n  - heading "' + person + '" [level=1]\n'
            '  - text: "Highest Rated:"\n  - link "Avengers: Endgame (94%)":\n'
            '    - /url: /m/avengers_endgame\n  - heading "Filmography" [level=2]\n')
    for m in movies:
        score = scores.get(m['slug'], m['audience_score'])
        role = roles.get(m['slug'], 'producer')
        text += (f'  - link "{m["title"]}":\n    - /url: /m/{m["slug"]}\n'
                 '    - img "Certified Fresh"\n    - text: 89%\n'
                 '    - img "Audience score"\n    - text: ' + ('--' if score is None else str(score)+'%') + '\n'
                 f'    - generic: "{m["title"]}"\n    - generic: ({role})\n')
    return text + '- contentinfo:\n'


class FilmographyComparisonContracts(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.InformationContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.eligible = v.eligible_movies(v.FACTS)

    def pages(self, dom=None, facts=None):
        facts = v.FACTS if facts is None else facts
        return [('/celebrity/kevin_feige?sort=oldest', dom or filmography(v.eligible_movies(facts)))] + [
            ('/m/'+m['slug'],fixture.info_dom(m)) for m in v.winners(facts)]

    def check(self, expected, pages=None, answer=ANSWER, facts=None):
        directory = self.fixture.make_run(v.TASK_ID, self.pages() if pages is None else pages, answer, facts=facts)
        result = v.evaluate(directory, no_llm=True)
        self.assertEqual(result['pass'], expected, result)
        return result

    def test_explicit_other_candidate_rationale_is_not_an_extra_result(self):
        for answer in [ANSWER+' '+RATIONALE, OBSERVED_ANSWER,
                       ANSWER+' Remaining films: Deadpool & Wolverine 94%.',
                       ANSWER+' 其他候选电影：Deadpool & Wolverine 94%、Avengers: Endgame 90%。',
                       RATIONALE+'\n'+ANSWER]:
            with self.subTest(answer=answer):
                v.check_answer(answer)

    def test_comparison_rationale_cannot_hide_wrong_facts_or_extra_winners(self):
        for suffix in [RATIONALE.replace('94%', '95%'),
                       'Other candidates: Deadpool & Wolverine 94%; Release Date (Streaming): January 1, 2000.',
                       'Other candidates: Deadpool & Wolverine 94%; Release Date (Streaming): not listed.',
                       'Other candidates: Deadpool & Wolverine 94%; streaming date: December.',
                       'Other candidates: Deadpool & Wolverine 94%, also a winner.',
                       'Other candidates: Deadpool & Wolverine 94%，也是并列赢家。',
                       'Other candidates: Madeup Movie 90%, Deadpool & Wolverine 94%.',
                       'Other candidates: Deadpool & Wolverine 94%, Madeup Movie 90%.',
                       'Other candidates: Oppenheimer 91%.',
                       'Other candidates: Deadpool & Wolverine 94%, Spider-Man: Brand New Day 97%.',
                       RATIONALE+' It streams in December.',
                       'Also Deadpool & Wolverine — 94%; October 1, 2024.']:
            with self.subTest(suffix=suffix), self.assertRaises(VerificationError):
                v.check_answer(ANSWER+' '+suffix)

    def test_filmography_complete_role_score_comparison_and_winner_info(self):
        for movies in [self.eligible, list(reversed(self.eligible))]:
            result = self.check(True, self.pages(filmography(movies)), OBSERVED_ANSWER)
            self.assertEqual(result['evidence'][-1]['path'], 'producer_filmography_comparison')

    def test_filmography_missing_each_candidate_fails(self):
        for missing in self.eligible:
            with self.subTest(missing=missing['slug']):
                self.check(False,self.pages(filmography([m for m in self.eligible if m!=missing])))

    def test_multiple_person_page_observations_can_cover_the_candidates(self):
        pages=[('/celebrity/kevin_feige?sort=newest',filmography(self.eligible[:2])),
               ('/celebrity/kevin_feige?sort=oldest',filmography(self.eligible[2:]))]
        self.check(True,pages+self.pages()[1:])

    def test_unknown_audience_score_is_observed_as_missing_not_zero(self):
        facts=[dict(m) for m in v.FACTS]
        unknown=next(m for m in facts if m['slug']=='avengers_endgame')
        unknown['audience_score']=None
        for score,expected in [(None,True),(0,False)]:
            pages=self.pages(filmography(v.eligible_movies(facts),scores={unknown['slug']:score}),facts=facts)
            directory=self.fixture.make_run(v.TASK_ID,pages,ANSWER,facts=facts)
            run=v.Run(directory,v.CONTRACTS[v.TASK_ID],no_llm=True)
            if expected:
                self.assertEqual(v.check_ui(run,facts),'producer_filmography_comparison')
            else:
                with self.assertRaises(VerificationError):
                    v.check_ui(run,facts)

    def test_exact_person_identity_is_required(self):
        for person in ['Kevin Etten','Kevin Feige Jr','Kevin','Kevin Feige (unrelated person)']:
            with self.subTest(person=person):
                self.check(False,self.pages(filmography(self.eligible,person=person)))
        self.check(False,[('/celebrity/kevin_etten',filmography(self.eligible))]+self.pages()[1:])

    def test_every_candidate_needs_its_own_exact_producer_role_and_audience_score(self):
        for movie in self.eligible:
            for role in ['actor','executive producer','producer assistant','']:
                with self.subTest(movie=movie['slug'],role=role):
                    self.check(False,self.pages(filmography(self.eligible,roles={movie['slug']:role})))
            with self.subTest(movie=movie['slug'],score='wrong'):
                self.check(False,self.pages(filmography(self.eligible,scores={movie['slug']:89})))

    def test_filmography_scores_cannot_use_summary_or_critic_labels(self):
        dom=filmography(self.eligible)
        for altered in [dom.replace('img "Audience score"','img "Tomatometer"'),
                        dom.split('  - heading "Filmography"')[0]+'- contentinfo:\n',
                        dom.replace('    - generic: (producer)\n','')]:
            self.check(False,self.pages(altered))

    def test_filmography_title_slug_pair_and_candidate_scope_are_exact(self):
        dom=filmography(self.eligible)
        self.check(False,self.pages(dom.replace('generic: "Avengers: Endgame"','generic: "Avengers: Endgame Part II"')))
        outsider=next(m for m in v.FACTS if m['slug']=='oppenheimer_2023')
        self.check(False,self.pages(filmography(self.eligible+[outsider])))
        self.check(True,self.pages(filmography(self.eligible+[outsider],roles={outsider['slug']:'actor'})))
        self.check(True,self.pages(filmography(self.eligible,roles={self.eligible[0]['slug']:'director, producer'})))

    def test_winner_movie_info_must_still_prove_role_and_missing_date(self):
        self.check(False,self.pages()[:1])
        winner=v.winners(v.FACTS)[0]
        for dom in [fixture.info_dom(winner,producer_role='Director'),
                    fixture.info_dom(winner,producer_override=['Kevin Etten']),
                    fixture.info_dom(winner).split('  - heading "More Like This"')[0]]:
            self.check(False,self.pages()[:1]+[('/m/'+winner['slug'],dom)])

    def test_comparison_group_may_not_replace_a_tied_winner(self):
        facts=[dict(m) for m in v.FACTS]
        tied=next(m for m in facts if m['slug']=='deadpool_and_wolverine')
        tied['audience_score']=97
        with self.assertRaises(VerificationError):
            v.check_answer(ANSWER+' Other candidates: Deadpool & Wolverine 97%.',facts)
        answer=ANSWER+'\nDeadpool & Wolverine — Audience score: 97%; Release Date (Streaming): October 1, 2024.'
        with patch.object(v,'FACTS',facts):
            # Default facts arguments are bound at definition time; call the
            # exposed contract methods directly for this synthetic tied catalog.
            directory=self.fixture.make_run(v.TASK_ID,self.pages(facts=facts),answer,facts=facts)
            run=v.Run(directory,v.CONTRACTS[v.TASK_ID],no_llm=True)
            v.check_answer(answer,facts)
            self.assertEqual(v.check_ui(run,facts),'producer_filmography_comparison')


class FilmographyScreenshotContracts(unittest.TestCase):
    """Mock only screenshot routing. No vision model or image accuracy is tested."""

    setUp = FilmographyComparisonContracts.setUp
    pages = FilmographyComparisonContracts.pages

    def screenshot_run(self, pages=None, remove_all=False):
        directory=self.fixture.make_run(v.TASK_ID,self.pages() if pages is None else pages,ANSWER)
        for observation in (directory/'observations').glob('*.txt'):
            if remove_all or 'heading "Filmography"' in observation.read_text():
                observation.unlink()
        return directory

    def candidate_claim(self, claim, movie):
        return ('full movie title "'+movie['title']+'"') in claim

    def test_screenshot_only_dispatch_binds_each_candidate_and_winner(self):
        directory=self.screenshot_run(remove_all=True)
        calls=[]
        winner=v.winners(v.FACTS)[0]
        def visual(run,frame,claim):
            calls.append((frame.path,claim))
            if frame.path=='/celebrity/kevin_feige' and claim.startswith('Within Filmography'):
                matches=[m for m in self.eligible if self.candidate_claim(claim,m)]
                self.assertEqual(len(matches),1)
                self.assertIn('heading is exactly "Kevin Feige"',claim)
                self.assertIn('exact "producer" role',claim)
                self.assertIn('own labelled Audience Score as '+str(matches[0]['audience_score'])+'%',claim)
                self.assertIn('same row',claim)
                return True
            return frame.path=='/m/'+winner['slug'] and (
                claim.startswith('The Movie Info Producer field lists exactly:') or
                claim.startswith('This movie page visibly labels its Audience Score') or
                claim.startswith('The complete Movie Info section'))
        with patch.object(v.Run,'visual',autospec=True,side_effect=visual), \
             patch.object(verify_lib,'urlopen',side_effect=AssertionError('real vision must not run')):
            result=v.evaluate(directory,no_llm=False)
        self.assertTrue(result['pass'],result)
        claimed={m['slug'] for _,claim in calls for m in self.eligible if self.candidate_claim(claim,m)}
        self.assertEqual(claimed,{m['slug'] for m in self.eligible})
        self.assertTrue(any(e.get('check')=='Kevin_Feige_producer_filmography' and e['source']=='anchored_screenshot' for e in result['evidence']))

    def test_screenshot_comparison_requires_every_candidate(self):
        for missing in self.eligible:
            with self.subTest(missing=missing['slug']):
                directory=self.screenshot_run()
                def visual(run,frame,claim):
                    return frame.path=='/celebrity/kevin_feige' and claim.startswith('Within Filmography') and not self.candidate_claim(claim,missing)
                with patch.object(v.Run,'visual',autospec=True,side_effect=visual):
                    self.assertFalse(v.evaluate(directory,no_llm=False)['pass'])

    def test_no_visual_evidence_disabled_vision_or_missing_image_fails(self):
        directory=self.screenshot_run()
        with patch.object(v.Run,'visual',return_value=False):
            self.assertFalse(v.evaluate(directory,no_llm=False)['pass'])
        with patch.object(verify_lib,'urlopen',side_effect=AssertionError('disabled vision must not run')):
            self.assertFalse(v.evaluate(directory,no_llm=True)['pass'])
        next((directory/'screenshots').glob('*.png')).unlink()
        with patch.object(v.Run,'visual',return_value=True) as visual:
            self.assertFalse(v.evaluate(directory,no_llm=False)['pass'])
            visual.assert_not_called()

    def test_wrong_person_path_cannot_dispatch_filmography_vision(self):
        pages=[('/celebrity/kevin_etten',filmography(self.eligible))]+self.pages()[1:]
        directory=self.screenshot_run(pages=pages)
        run=v.Run(directory,v.CONTRACTS[v.TASK_ID],no_llm=False)
        with patch.object(v.Run,'visual',return_value=True) as visual:
            with self.assertRaises(VerificationError):
                v.filmography_comparison(run,v.FACTS)
            visual.assert_not_called()

    def test_present_dom_is_authoritative_and_cannot_be_rescued(self):
        good=filmography(self.eligible)
        for dom,expected in [(good,True),(good.replace('heading "Kevin Feige"','heading "Kevin Feige Jr"'),False),
                             (good.replace('(producer)','(actor)'),False),
                             (good.replace('img "Audience score"','img "Tomatometer"'),False),
                             (good.replace('text: 94%','text: 95%'),False)]:
            with self.subTest(dom=dom,expected=expected):
                directory=self.fixture.make_run(v.TASK_ID,self.pages(dom),ANSWER)
                with patch.object(v.Run,'visual',return_value=True) as visual:
                    result=v.evaluate(directory,no_llm=False)
                    self.assertEqual(result['pass'],expected,result)
                    visual.assert_not_called()

    def test_mixed_dom_and_screenshot_observations_cover_the_same_set(self):
        pages=[('/celebrity/kevin_feige',filmography(self.eligible[:2])),
               ('/celebrity/kevin_feige?sort=oldest',filmography(self.eligible[2:]))]+self.pages()[1:]
        directory=self.fixture.make_run(v.TASK_ID,pages,ANSWER)
        (directory/'observations/step_002.txt').unlink()
        calls=[]
        def visual(run,frame,claim):
            calls.append(claim)
            return frame.path=='/celebrity/kevin_feige' and claim.startswith('Within Filmography')
        with patch.object(v.Run,'visual',autospec=True,side_effect=visual):
            result=v.evaluate(directory,no_llm=False)
        self.assertTrue(result['pass'],result)
        claimed={m['slug'] for claim in calls for m in self.eligible if self.candidate_claim(claim,m)}
        self.assertEqual(claimed,{m['slug'] for m in self.eligible[2:]})
        sources={e['source'] for e in result['evidence'] if e.get('check')=='Kevin_Feige_producer_filmography'}
        self.assertEqual(sources,{'synchronous_dom','anchored_screenshot'})


if __name__=='__main__':
    unittest.main(verbosity=2)
