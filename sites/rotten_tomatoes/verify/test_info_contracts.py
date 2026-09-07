"""Offline R3/R18 grading-contract regressions using constructed evidence.

Run from the repository root:
    python -m unittest discover -s sites/rotten_tomatoes/verify -p test_info_contracts.py -v

The temporary DOM records, placeholder pixels, trajectories, and minimal SQLite
snapshots below are deliberately constructed unit-test inputs, not browser runs.
They test the production Run/Snapshot adapters with no_llm=True; no network,
application startup, downloaded assets, or production database is required.
Answer-bearing fixtures stay beside the verifiers, outside the agent task file.
"""
import base64
import copy
from datetime import date
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

import verify_3 as v3
import verify_18 as v18
from verify_lib import Run, VerificationError
from contracts import CONTRACTS

ANSWER3 = 'Shared producers: Emma Thomas and Charles Roven.\nOppenheimer: November 21, 2023.\nThe Dark Knight: June 14, 2010.'
ANSWER18 = 'Spider-Man: Brand New Day — audience score 97%; Release Date (Streaming): not listed.'
HOME = '- main:\n  - heading "Rotten Tomatoes" [level=1]\n- contentinfo:\n'
SEARCH = '- main:\n  - heading "Search Results for \\"Christopher Nolan\\"" [level=1]\n  - link "Christopher Nolan":\n    - /url: /celebrity/christopher_nolan\n- contentinfo:\n'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jM1sAAAAASUVORK5CYII=')


def info_dom(movie, *, producer_role='Producer', producer_override=None, score_override='default'):
    score = movie.get('audience_score', 94) if score_override == 'default' else score_override
    producers = movie['producers'] if producer_override is None else producer_override
    display_date = date.fromisoformat(movie['date']).strftime('%b %d, %Y') if movie.get('date') else '--'
    date_field = ('  - generic: Release Date (Streaming)\n  - generic: ' + display_date + '\n') if movie.get('date') else ''
    return ('- main:\n  - heading "' + movie['title'] + '" [level=1]\n'
            '  - generic: 77%\n  - generic: Tomatometer\n  - img "Audience score"\n'
            '  - generic: ' + ('--' if score is None else str(score) + '%') + '\n'
            '  - generic: Audience Score\n  - heading "Movie Info" [level=3]\n'
            '  - generic: ' + producer_role + '\n  - generic: ' + ', '.join(producers) + '\n'
            '  - generic: Screenwriter\n  - generic: Someone Else\n'
            + date_field +
            '  - heading "More Like This" [level=2]\n- contentinfo:\n')


def listing(movies, sort='Audience Score'):
    text = '- main:\n  - heading "All Movies" [level=1]\n  - combobox "Sort:":\n    - option "' + sort + '" [selected]\n'
    for movie in movies:
        text += ('  - link "' + movie['title'] + '":\n    - /url: /m/' + movie['slug'] + '\n'
                 '    - img "Audience score"\n    - text: ' + ('--' if movie['audience_score'] is None else str(movie['audience_score']) + '%') + '\n')
    return text + '- contentinfo:\n'


class InformationContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rotten-info-contract-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.counter = 0

    def make_run(self, task, pages, answer, facts=None):
        self.counter += 1
        directory = self.root / str(self.counter)
        (directory / 'screenshots').mkdir(parents=True)
        (directory / 'observations').mkdir()
        pages = [('/', HOME)] + pages
        origin = 'http://localhost:40019'
        steps = []
        for index, (path, dom) in enumerate(pages):
            name = 'step_' + str(index).zfill(3)
            (directory / 'screenshots' / (name + '.png')).write_bytes(PNG)
            (directory / 'observations' / (name + '.txt')).write_text(dom)
            next_path = pages[index + 1][0] if index + 1 < len(pages) else path
            steps.append({'step': index, 'url': origin + path, 'url_after': origin + next_path,
                          'action': 'goto' if index + 1 < len(pages) else 'done',
                          'params': {'url': origin + next_path} if index + 1 < len(pages) else {'text': answer},
                          'action_result': {'success': True}, 'screenshot_before': name + '.png',
                          'screenshot_after': 'step_' + str(min(index + 1, len(pages) - 1)).zfill(3) + '.png'})
        document = {'task_id': task, 'task': CONTRACTS[task]['prompt'], 'start_url': origin + '/',
                    'final_answer': answer, 'steps': steps, 'fixture_notice': 'CONSTRUCTED INFORMED TEST; NOT A REAL RUN'}
        (directory / 'trajectory.json').write_text(json.dumps(document))
        with sqlite3.connect(directory / 'before.db') as db:
            db.execute('CREATE TABLE movies (id INTEGER PRIMARY KEY, slug TEXT, title TEXT)')
            db.executemany('INSERT INTO movies VALUES (?,?,?)', [(i, movie['slug'], movie['title']) for i, movie in enumerate((v18.FACTS if facts is None else facts), 1)])
            db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)')
            db.execute("INSERT INTO users VALUES (1,'Unchanged User')")
            db.execute('CREATE TABLE watchlist_items (id INTEGER PRIMARY KEY, user_id INTEGER, movie_id INTEGER)')
            db.execute('INSERT INTO watchlist_items VALUES (1,1,1)')
        shutil.copyfile(directory / 'before.db', directory / 'after.db')
        return directory

    def pages3(self):
        return [('/search?q=Christopher+Nolan', SEARCH)] + [('/m/' + movie['slug'], info_dom(movie)) for movie in v3.MOVIES]

    def pages18(self, facts=None):
        eligible = v18.eligible_movies((v18.FACTS if facts is None else facts))
        return [('/browse/movies/?sort=audience', listing(eligible))] + [('/m/' + movie['slug'], info_dom(movie)) for movie in eligible]

    def assert_rejected(self, function, *args):
        with self.assertRaises(VerificationError):
            function(*args)

    def test_r3_natural_producer_assertions_with_intro(self):
        # Labels derive from the public request and frozen source facts, not
        # from the parser's previous rejection of ordinary introductory words.
        dates = '\nOppenheimer: November 21, 2023.\nThe Dark Knight: June 14, 2010.'
        for statement in (
            'After comparing both Movie Info sections, Emma Thomas and Charles Roven are the producers credited on both pages.',
            'After comparing both Movie Info sections, the shared producers are Emma Thomas and Charles Roven.',
            'The producers credited on both pages are Charles Roven and Emma Thomas.',
            'I found that Emma Thomas and Charles Roven are the common producers.',
        ):
            with self.subTest(statement=statement):
                v3.check_answer(statement + dates)

    def test_r3_markdown_producer_records(self):
        for producers in (
            '| Shared producers |\n| --- |\n| Emma Thomas |\n| Charles Roven |',
            '| Field | Value |\n| --- | --- |\n| Shared producers | Emma Thomas and Charles Roven |',
        ):
            answer = producers + '\n\n| Movie | Release Date (Streaming) |\n| --- | --- |\n| Oppenheimer | November 21, 2023 |\n| The Dark Knight | June 14, 2010 |'
            with self.subTest(producers=producers):
                v3.check_answer(answer)

    def test_r3_json_producer_records(self):
        for producers in (['Emma Thomas', 'Charles Roven'], 'Charles Roven and Emma Thomas'):
            answer = json.dumps({'shared_producers': producers,
                'streaming_dates': {'Oppenheimer': '2023-11-21', 'The Dark Knight': '2010-06-14'}})
            v3.check_answer(answer)

    def test_r3_structured_and_natural_extra_producers_fail(self):
        dates = '\nOppenheimer: November 21, 2023.\nThe Dark Knight: June 14, 2010.'
        for name in ('Christopher Nolan', 'Madeup Person'):
            answers = (
                'After comparing both Movie Info sections, Emma Thomas, Charles Roven and ' + name + ' are the producers credited on both pages.' + dates,
                '| Shared producers |\n| --- |\n| Emma Thomas |\n| Charles Roven |\n| ' + name + ' |' + dates,
                json.dumps({'shared_producers': ['Emma Thomas', 'Charles Roven', name],
                    'streaming_dates': {'Oppenheimer': '2023-11-21', 'The Dark Knight': '2010-06-14'}}),
            )
            for answer in answers:
                with self.subTest(answer=answer):
                    self.assert_rejected(v3.check_answer, answer)

    def test_r3_negated_required_producer_and_additional_assertion_fail(self):
        for answer in (
            ANSWER3.replace('Emma Thomas and Charles Roven.', 'Emma Thomas, not Charles Roven.'),
            ANSWER3 + '\nThe shared producers also include Christopher Nolan.',
            ANSWER3 + '\nChristopher Nolan is also a shared producer.',
            ANSWER3 + '\nMadeup Person is another producer.',
            ANSWER3 + '\nEmma Thomas and Charles Roven are not the shared producers.',
            '{"shared_producers":["Christopher Nolan"],"shared_producers":["Emma Thomas","Charles Roven"],"dates":{"Oppenheimer":"2023-11-21","The Dark Knight":"2010-06-14"}}',
            '{"shared_producers":["Emma Thomas","Charles Roven"],"extra_producers":["Madeup Person"],"dates":{"Oppenheimer":"2023-11-21","The Dark Knight":"2010-06-14"}}',
        ):
            with self.subTest(answer=answer):
                self.assert_rejected(v3.check_answer, answer)

    def test_r3_common_answer_formats(self):
        for answer in (ANSWER3,
                       'Common producers: Charles Roven, Emma Thomas; Oppenheimer — 2023-11-21; The Dark Knight — 2010-06-14',
                       'Emma Thomas and Charles Roven\nOppenheimer: 21 November 2023\nThe Dark Knight: 14 June 2010',
                       'Shared producers: Emma Thomas and Charles Roven, not Christopher Nolan\nNovember 21, 2023 for Oppenheimer; June 14, 2010 for The Dark Knight',
                       'Shared producers: Emma Thomas and Charles Roven\nOppenheimer: 21/11/2023\nThe Dark Knight: 14/6/2010',
                       'Shared producers:\n1. Emma Thomas\n2. Charles Roven\nOppenheimer: November 21, 2023\nThe Dark Knight: June 14, 2010',
                       '共同制片人：Emma Thomas 和 Charles Roven\nOppenheimer：2023年11月21日\nThe Dark Knight：2010年6月14日'):
            with self.subTest(answer=answer):
                v3.check_answer(answer)

    def test_r3_wrong_paired_dates(self):
        self.assert_rejected(v3.check_answer, ANSWER3.replace('November 21, 2023', 'SWAP').replace('June 14, 2010', 'November 21, 2023').replace('SWAP', 'June 14, 2010'))

    def test_r3_extra_producer_known_or_unknown(self):
        for name in ('Christopher Nolan', 'Madeup Person'):
            self.assert_rejected(v3.check_answer, ANSWER3.replace('Charles Roven.', 'Charles Roven and ' + name + '.'))
            self.assert_rejected(v3.check_answer, ANSWER3 + '\nAdditional producer: ' + name)

    def test_r3_incomplete_or_empty(self):
        for answer in ('', ANSWER3.replace('Emma Thomas and ', ''), ANSWER3.replace('The Dark Knight: June 14, 2010.', '')):
            self.assert_rejected(v3.check_answer, answer)

    def test_r3_production_adapter_on_constructed_fixture_passes(self):
        result = v3.evaluate(self.make_run(v3.TASK_ID, self.pages3(), ANSWER3), no_llm=True)
        self.assertTrue(result['pass'], result)

    def test_r3_correct_answer_without_ui_fails(self):
        result = v3.evaluate(self.make_run(v3.TASK_ID, [], ANSWER3), no_llm=True)
        self.assertFalse(result['pass'])

    def test_r3_missing_search_or_detail_fails(self):
        for pages in (self.pages3()[1:], self.pages3()[:-1]):
            result = v3.evaluate(self.make_run(v3.TASK_ID, pages, ANSWER3), no_llm=True)
            self.assertFalse(result['pass'], result)

    def test_r3_wrong_role_and_wrong_search_fail(self):
        pages = self.pages3()
        pages[-1] = (pages[-1][0], info_dom(v3.MOVIES[-1], producer_role='Director'))
        self.assertFalse(v3.evaluate(self.make_run(v3.TASK_ID, pages, ANSWER3), no_llm=True)['pass'])
        pages = self.pages3()
        pages[0] = ('/search?q=Jonathan+Nolan', SEARCH.replace('Christopher', 'Jonathan'))
        self.assertFalse(v3.evaluate(self.make_run(v3.TASK_ID, pages, ANSWER3), no_llm=True)['pass'])

    def test_r3_extra_movie_visit_is_allowed(self):
        pages = self.pages3() + [('/m/not-required-third-film', HOME)]
        result = v3.evaluate(self.make_run(v3.TASK_ID, pages, ANSWER3), no_llm=True)
        self.assertTrue(result['pass'], result)

    def test_r3_search_does_not_require_a_person_result_or_visit(self):
        pages = self.pages3()
        pages[0] = (pages[0][0], '- main:\n  - heading "Search Results for Christopher Nolan" [level=1]\n- contentinfo:\n')
        result = v3.evaluate(self.make_run(v3.TASK_ID, pages, ANSWER3), no_llm=True)
        self.assertTrue(result['pass'], result)

    def test_read_only_delta_enforced(self):
        for module, pages, answer in ((v3, self.pages3(), ANSWER3), (v18, self.pages18(), ANSWER18)):
            directory = self.make_run(module.TASK_ID, pages, answer)
            with sqlite3.connect(directory / 'after.db') as db:
                db.execute('DELETE FROM watchlist_items')
            self.assertFalse(module.evaluate(directory, no_llm=True)['pass'])

    def test_r18_eligible_comparison_passes(self):
        result = v18.evaluate(self.make_run(v18.TASK_ID, self.pages18(), ANSWER18), no_llm=True)
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['evidence'][-1]['path'], 'all_eligible_comparison')

    def test_r18_answer_formats(self):
        dated_facts = [{'slug':'deadpool_and_wolverine','title':'Deadpool & Wolverine', 'producers':['Kevin Feige'],'audience_score':94,'date':'2024-10-01'}]
        old_answer = 'Deadpool & Wolverine — audience score 94%; Release Date (Streaming): October 1, 2024.'
        for answer in (old_answer, 'Deadpool and Wolverine: 94%; streaming 2024-10-01', 'Deadpool & Wolverine | 94/100 | 1 October 2024',
                       'With 94% audience score, the highest movie is Deadpool & Wolverine. Streaming date: October 1, 2024.',
                       'Deadpool & Wolverine | 94 | 2024-10-01', '1. Deadpool & Wolverine | 94 | 2024-10-01'):
            v18.check_answer(answer, dated_facts)

    def test_r18_wrong_score_date_and_extra_answer(self):
        for answer in ('', ANSWER18.replace('97%', '77%'), ANSWER18.replace('not listed', 'October 1, 2025'),
                       ANSWER18 + '\nAvengers: Endgame — 90%; July 30, 2019.',
                       ANSWER18 + '\nImaginary Film — 94%; October 1, 2024.', ANSWER18 + '\nAlso Imaginary Film.'):
            self.assert_rejected(v18.check_answer, answer)

    def test_r18_correct_answer_only_detail_is_insufficient(self):
        winner = v18.winners(v18.FACTS)[0]
        pages = [('/m/' + winner['slug'], info_dom(winner))]
        self.assertFalse(v18.evaluate(self.make_run(v18.TASK_ID, pages, ANSWER18), no_llm=True)['pass'])

    def test_r18_wrong_kevin_or_role_cannot_prove_eligibility(self):
        for kwargs in ({'producer_override': ['Kevin Krikst']}, {'producer_role': 'Screenwriter'}):
            pages = self.pages18()
            movie = v18.eligible_movies(v18.FACTS)[-1]
            pages[-1] = ('/m/' + movie['slug'], info_dom(movie, **kwargs))
            self.assertFalse(v18.evaluate(self.make_run(v18.TASK_ID, pages, ANSWER18), no_llm=True)['pass'])

    def test_r18_global_descending_exclusion_without_old_anchor(self):
        maximum = v18.winners(v18.FACTS)[0]['audience_score']
        threshold = [movie for movie in v18.FACTS if movie['audience_score'] is not None and movie['audience_score'] >= maximum]
        below = next(movie for movie in v18.FACTS if movie['audience_score'] is not None and movie['audience_score'] < maximum)
        # The old Endgame anchor may appear as a lower boundary card but its
        # detail page is never visited. No lower eligible producer proof needed.
        pages = [('/browse/movies/?sort=audience', listing(sorted(threshold + [below], key=lambda m: -m['audience_score'])))]
        pages += [('/m/' + movie['slug'], info_dom(movie)) for movie in threshold]
        self.assertNotIn('/m/avengers_endgame', [page[0] for page in pages])
        result = v18.evaluate(self.make_run(v18.TASK_ID, pages, ANSWER18), no_llm=True)
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['evidence'][-1]['path'], 'global_descending_exclusion')

    def test_r18_global_missing_higher_competitor_or_filtered_catalog_fails(self):
        maximum = v18.winners(v18.FACTS)[0]['audience_score']
        threshold = [movie for movie in v18.FACTS if movie['audience_score'] is not None and movie['audience_score'] >= maximum]
        below = next(movie for movie in v18.FACTS if movie['audience_score'] is not None and movie['audience_score'] < maximum)
        for filtered, omit in ((True, False), (False, True)):
            pages = [('/browse/movies/?sort=audience' + ('&genre=action' if filtered else ''), listing(threshold + [below]))]
            pages += [('/m/' + movie['slug'], info_dom(movie)) for movie in threshold if not omit or movie != threshold[-1]]
            self.assertFalse(v18.evaluate(self.make_run(v18.TASK_ID, pages, ANSWER18), no_llm=True)['pass'])

    def test_r18_tied_maximum_and_unknown_scores(self):
        facts = copy.deepcopy(v18.eligible_movies(v18.FACTS)[:3])
        facts[0]['audience_score'] = None
        facts[1]['audience_score'] = 94
        facts[2]['audience_score'] = 94
        expected = [facts[1], facts[2]]  # Raw constructed facts: exactly these two equal 94; first is NULL.
        self.assertEqual([m['slug'] for m in v18.winners(facts)], [m['slug'] for m in expected])
        answer = '\n'.join(movie['title'] + ': 94%; ' + movie['date'] for movie in expected)
        v18.check_answer(answer, facts)
        self.assert_rejected(v18.check_answer, answer.splitlines()[0], facts)
        directory = self.make_run(v18.TASK_ID, self.pages18(facts), answer, facts)
        run = Run(directory, CONTRACTS[v18.TASK_ID], no_llm=True)
        self.assertEqual(v18.check_ui(run, facts), 'all_eligible_comparison')
        global_pages = [('/browse/movies/?sort=audience', listing(expected))]
        global_pages += [('/m/' + m['slug'], info_dom(m)) for m in expected]
        directory = self.make_run(v18.TASK_ID, global_pages, answer, facts)
        self.assertEqual(v18.check_ui(Run(directory, CONTRACTS[v18.TASK_ID], no_llm=True), facts), 'global_descending_exclusion')

    def test_r18_all_unknown_scores_have_no_numeric_maximum(self):
        facts = copy.deepcopy(v18.eligible_movies(v18.FACTS))
        for movie in facts:
            movie['audience_score'] = None
        self.assert_rejected(v18.winners, facts)

    def test_r18_descending_evidence_rejects_scrambled_scores(self):
        high = next(m for m in v18.FACTS if m['audience_score'] == 99)
        low = next(m for m in v18.FACTS if m['audience_score'] == 94)
        self.assertFalse(v18.descending_dom(listing([low, high]), 'Audience Score', v18.FACTS))

    def test_r18_wrong_kevin_name_or_other_role_is_not_eligible(self):
        facts = copy.deepcopy(v18.eligible_movies(v18.FACTS)[:3])
        facts[0]['producers'] = ['Kevin Feige Jr.']
        facts[0]['audience_score'] = 100
        facts[1]['producers'] = ['Kevin Krikst']
        facts[1]['directors'] = ['Kevin Feige']
        facts[1]['audience_score'] = 99
        self.assertEqual([movie['slug'] for movie in v18.winners(facts)], [facts[2]['slug']])

    def test_missing_dom_cannot_be_rescued_with_no_llm(self):
        directory = self.make_run(v18.TASK_ID, self.pages18(), ANSWER18)
        shutil.rmtree(directory / 'observations')
        self.assertFalse(v18.evaluate(directory, no_llm=True)['pass'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
