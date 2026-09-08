"""Personal-score clauses retain their preceding movie without accepting other metrics."""
import unittest

from verify_14 import answer_pairs
from verify_lib import VerificationError


class PersonalScoreProseContracts(unittest.TestCase):
    movies = [{'title': 'Oddity'}, {'title': 'Nosferatu'}, {'title': 'The Substance'}]
    expected = {'Oddity': 5}

    def accepts(self, answer):
        self.assertEqual(answer_pairs(answer, self.movies, self.expected), self.expected)

    def rejects(self, answer):
        with self.assertRaises(VerificationError):
            answer_pairs(answer, self.movies, self.expected)

    def test_recorded_chinese_answer(self):
        self.accepts('Carol 已评分但不在收藏列表中的电影只有 Oddity，她给的评分是 5.0/5。')

    def test_equivalent_personal_rating_clauses(self):
        for clause in ('她给的评分为 5/5', '她的评分是 5 分', '个人评分：5/5'):
            with self.subTest(clause=clause):
                self.accepts('Oddity；' + clause)

    def test_existing_title_references_and_inline_score(self):
        for answer in ('Oddity: 5/5', 'Oddity; it received five out of five', 'Oddity；该片获得五颗星'):
            with self.subTest(answer=answer):
                self.accepts(answer)

    def test_wrong_contradictory_and_wrong_scale_scores(self):
        for answer in ('Oddity；她给的评分是 4/5', 'Oddity；她给的评分是 5/10',
                       'Oddity: 4/5；她给的评分是 5/5'):
            with self.subTest(answer=answer):
                self.rejects(answer)

    def test_unpaired_or_unrelated_metrics(self):
        for answer in ('她给的评分是 5/5', 'Oddity；电影数量为 5',
                       'Oddity；全站平均评分为 5/5', 'Oddity；Bob 给的评分是 5/5',
                       'Oddity；她给另一部电影的评分是 5/5'):
            with self.subTest(answer=answer):
                self.rejects(answer)

    def test_extra_result_and_partial_movie_names(self):
        for answer in ('Oddity；她给的评分是 5/5；Nosferatu: 4/5', 'Oddity2: 5/5'):
            with self.subTest(answer=answer):
                self.rejects(answer)


if __name__ == '__main__':
    unittest.main()
