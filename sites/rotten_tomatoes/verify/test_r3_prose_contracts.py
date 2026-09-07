"""Finite R3 producer-statement regressions; these are constructed inputs."""
import json
import unittest
import verify_3 as r3
from verify_lib import VerificationError

DATE_ROWS = '\n- **Oppenheimer**：Nov 21, 2023\n- **The Dark Knight**：Jun 14, 2010'
ORIGINAL = '两页 Movie Info 中共同署名的制片人是 **Emma Thomas、Charles Roven**。\n\nRelease Date (Streaming)：\n' + DATE_ROWS


class R3ProseContracts(unittest.TestCase):
    def reject(self, answer):
        with self.assertRaises(VerificationError):r3.check_answer(answer)

    def test_original_chinese_narrative_with_date_section(self):
        r3.check_answer(ORIGINAL)

    def test_chinese_label_boundary_and_sentence_punctuation(self):
        for statement in [
            '共同制片人是 **Charles Roven、Emma Thomas**。',
            '两页列出的制片人为 Emma Thomas、Charles Roven。',
            'Movie Info中的共同制片人：Emma Thomas 和 Charles Roven。',
            '两页共同制片人包括 Emma Thomas、Charles Roven。',
            'Emma Thomas、Charles Roven是共同制片人。',
        ]:
            with self.subTest(statement=statement):r3.check_answer(statement+DATE_ROWS)

    def test_chinese_full_stop_delimits_inline_movie_date_clauses(self):
        r3.check_answer('两页的制片人是 Emma Thomas、Charles Roven。Oppenheimer：2023年11月21日。The Dark Knight：2010年6月14日。')

    def test_date_section_heading_ends_the_producer_list(self):
        for heading in ['Release Date (Streaming)：','**Release Date (Streaming)**:']:
            with self.subTest(heading=heading):r3.check_answer('共同制片人：\n- Emma Thomas\n- Charles Roven\n\n'+heading+DATE_ROWS)

    def test_partial_and_extra_names_are_still_rejected(self):
        for names in ['Emma Thomas','Charles Roven','Emma Thomas、Charles Roven、Christopher Nolan',
                      'Emma Thomas、Charles Roven、Madeup Person','Emma Thomas、Charles Roven、张三']:
            with self.subTest(names=names):self.reject('两页的制片人是 **'+names+'**。'+DATE_ROWS)

    def test_additional_producer_assertions_after_dates_are_rejected(self):
        for extra in ['两页共同制片人还包括 Christopher Nolan。','共同制片人也是 Madeup Person。',
                      'Madeup Person也是共同制片人。','张三是共同制片人。',
                      'The shared producers also include Madeup Person.']:
            with self.subTest(extra=extra):self.reject(ORIGINAL+'\n'+extra)

    def test_negated_required_credit_is_not_a_positive_name_list(self):
        for statement in ['两页没有共同制片人：Emma Thomas、Charles Roven。',
                          '两页的非共同制片人是 Emma Thomas、Charles Roven。',
                          '共同制片人不是 Emma Thomas、Charles Roven。',
                          'Emma Thomas、Charles Roven并非共同制片人。']:
            with self.subTest(statement=statement):self.reject(statement+DATE_ROWS)
        self.reject(ORIGINAL+'\nEmma Thomas 不是共同制片人。')

    def test_paired_dates_and_contradictions_remain_exact(self):
        for answer in [ORIGINAL.replace('Nov 21, 2023','SWAP').replace('Jun 14, 2010','Nov 21, 2023').replace('SWAP','Jun 14, 2010'),
                       ORIGINAL.replace('Nov 21, 2023','Nov 20, 2023'),
                       ORIGINAL+'\nOppenheimer：2024年1月1日。',
                       ORIGINAL.replace('The Dark Knight','Another Movie')]:
            with self.subTest(answer=answer):self.reject(answer)

    def test_structured_unknown_names_and_duplicate_fields_still_fail(self):
        base={'共同制片人':['Emma Thomas','Charles Roven'],'dates':{'Oppenheimer':'2023-11-21','The Dark Knight':'2010-06-14'}}
        r3.check_answer(json.dumps(base,ensure_ascii=False))
        base['共同制片人'].append('张三');self.reject(json.dumps(base,ensure_ascii=False))
        self.reject('{"共同制片人":["张三"],"共同制片人":["Emma Thomas","Charles Roven"],"dates":{"Oppenheimer":"2023-11-21","The Dark Knight":"2010-06-14"}}')

    def test_english_word_internal_label_and_unrecognized_value_remain_rejected(self):
        for statement in ['nonproducers are Emma Thomas and Charles Roven.',
                          '两页的制片人是 Emma Thomas、Charles Roven、未识别的人名。']:
            with self.subTest(statement=statement):self.reject(statement+DATE_ROWS)


if __name__=='__main__':unittest.main(verbosity=2)
