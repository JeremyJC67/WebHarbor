"""Constructed fixtures for missing streaming dates, never real browser runs."""
import json
import unittest

import verify_18 as verifier
from verify_lib import VerificationError
import test_info_contracts as fixture


ANSWER = 'Spider-Man: Brand New Day — Audience score: 97%; Release Date (Streaming): not listed.'


class MissingDateContracts(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.InformationContractTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def comparison_paths(self):
        maximum = verifier.winners(verifier.FACTS)[0]['audience_score']
        threshold = [m for m in verifier.FACTS if m['audience_score'] is not None and m['audience_score'] >= maximum]
        below = next(m for m in verifier.FACTS if m['audience_score'] is not None and m['audience_score'] < maximum)
        globally_sorted = sorted(threshold + [below], key=lambda m: -m['audience_score'])
        global_pages = [('/browse/movies/?sort=audience', fixture.listing(globally_sorted))]
        global_pages += [('/m/' + m['slug'], fixture.info_dom(m)) for m in threshold]
        return [('all_eligible_comparison', self.fixture.pages18()),
                ('global_descending_exclusion', global_pages)]

    def assert_answers(self, answers, expected):
        for route, pages in self.comparison_paths():
            for answer in answers:
                with self.subTest(route=route, answer=answer):
                    directory = self.fixture.make_run(verifier.TASK_ID, pages, answer)
                    result = verifier.evaluate(directory, no_llm=True)
                    self.assertEqual(result['pass'], expected, result)
                    if expected:
                        self.assertEqual(result['evidence'][-1]['path'], route)

    def test_explicit_movie_info_omission_and_markdown_both_routes(self):
        answers = [
            'Spider-Man: Brand New Day has an audience score of 97%. Its Movie Info does not list a Release Date (Streaming).',
            '**Spider-Man: Brand New Day** — **Audience score:** 97%; **Release Date (Streaming):** not listed.',
            ANSWER.replace('not listed', '**not listed**'),
            ANSWER.replace('not listed', '*not listed*'),
            ANSWER.replace('not listed', '`not listed`'),
        ]
        answers += ['Spider-Man: Brand New Day — 97%. Movie Info does not ' + verb + ' a Release Date (Streaming).'
                    for verb in ['show', 'provide']]
        self.assert_answers(answers, True)

    def test_streaming_associated_partial_dates_fail_both_routes(self):
        self.assert_answers([ANSWER + suffix for suffix in [
            ' It streams in 2026.',
            ' It streams in December.',
            ' It will stream in December.',
            ' Streaming date: 2026.',
            ' Its streaming release date is December.',
            ' It streams in December 2026.',
            ' Its streaming release date is December 1, 2026.',
        ]], False)

    def test_duplicate_or_conflicting_json_date_slots_fail_both_routes(self):
        base = {'movie': 'Spider-Man: Brand New Day', 'audience_score': 97, 'release_date_streaming': None}
        answers = [json.dumps(dict(base, **{alias: value}))
                   for alias, value in [('streaming_date', 'December'), ('streaming_release_date', 2026),
                                        ('date', '2026-12-01'), ('Release Date (Streaming)', None),
                                        ('streaming_date', 'not listed')]]
        answers += ['{"movie":"Spider-Man: Brand New Day","audience_score":97,"release_date_streaming":"December","release_date_streaming":null}']
        # Parsing date slots must not silently overwrite another contradictory field.
        answers += ['{"movie":"Spider-Man: Brand New Day","audience_score":94,"audience_score":97,"release_date_streaming":null}']
        self.assert_answers(answers, False)

    def test_single_json_absence_slots_and_existing_formats_both_routes(self):
        answers = [json.dumps({'movie': 'Spider-Man: Brand New Day', 'audience_score': 97, alias: value})
                   for alias, value in [('release_date_streaming', None), ('streaming_release_date', 'N/A'),
                                        ('streaming_date', 'not listed'), ('date', None),
                                        ('Release Date (Streaming)', 'not provided')]]
        answers += [ANSWER,
                    'Spider-Man: Brand New Day — 97%; 流媒体上映日期：未列出。',
                    '| Movie | Audience Score | Release Date (Streaming) |\n|---|---|---|\n| Spider-Man: Brand New Day | 97% | Not listed |']
        self.assert_answers(answers, True)

    def test_missing_other_field_score_or_winner_still_fails_both_routes(self):
        self.assert_answers([
            'Spider-Man: Brand New Day has an audience score of 97%. Its Movie Info does not list a director.',
            'Spider-Man: Brand New Day — Audience score: 97%.',
            ANSWER.replace('97%', '94%'),
            'Deadpool & Wolverine — Audience score: 94%; Release Date (Streaming): October 1, 2024.',
        ], False)

    def test_unrelated_year_month_and_excluded_film_facts_are_not_winner_dates(self):
        excluded = 'Excluded: Deadpool & Wolverine — Audience score: 94%; Release Date (Streaming): October 1, 2024.'
        self.assert_answers([
            ANSWER.replace(' —', ' (2026) —'),
            ANSWER + ' I checked Movie Info in December.',
            ANSWER + '\n' + excluded,
            excluded + '\n' + ANSWER,
        ], True)

    def test_known_and_missing_date_tie_keeps_paired_dates(self):
        facts = [{'slug': 'missing_film', 'title': 'Missing Film', 'producers': ['Kevin Feige'], 'audience_score': 97, 'date': None},
                 {'slug': 'dated_film', 'title': 'Dated Film', 'producers': ['Kevin Feige'], 'audience_score': 97, 'date': '2026-07-28'}]
        rows = [{'movie': 'Missing Film', 'audience_score': 97, 'streaming_date': None},
                {'movie': 'Dated Film', 'audience_score': 97, 'streaming_date': '2026-07-28'}]
        verifier.check_answer(json.dumps(rows), facts)
        verifier.check_answer('Missing Film — 97%; Release Date (Streaming): **not listed**.\nDated Film — 97%; July 28, 2026.', facts)
        rows[0]['release_date_streaming'] = 'December'
        with self.assertRaises(VerificationError):
            verifier.check_answer(json.dumps(rows), facts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
