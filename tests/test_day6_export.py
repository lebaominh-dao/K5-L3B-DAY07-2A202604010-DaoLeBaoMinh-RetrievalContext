"""Checks for the Day 6 -> Day 7 export adapter (no database needed)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import validate
from day6_export import chunk_from_row, load_questions, question_from_day6

ROW = {'chunk_id': 'B-ch6-p198-0', 'document_id': 'psych2e-ch6', 'source': 'Psychology2e_WEB.pdf',
       'page': 198, 'chapter': 6, 'section': '6.2', 'metadata': {'title': 'Classical Conditioning'},
       'text': 'Higher-order conditioning. It is hard to achieve anything above second-order conditioning.'}
QUESTION = {'id': 'D05', 'split': 'dev', 'type': 'conditional', 'question': 'How far can conditioning go?',
            'expected_answer': 'Rarely beyond second order.', 'gold_source_id': 'psych2e-ch6', 'gold_page': 198,
            'evidence_quote': 'Higher-order conditioning', 'filter': {'chapter': 6},
            'alt_gold': [{'gold_source_id': 'psych2e-ch6', 'gold_page': 198,
                          'evidence_quote': 'It is hard to achieve anything above second-order conditioning.'}]}


class Day6ExportTests(unittest.TestCase):
    def test_chapter_and_section_move_into_metadata(self):
        c = chunk_from_row(ROW)
        self.assertEqual((c['id'], c['source_id'], c['page']), ('B-ch6-p198-0', 'psych2e-ch6', 198))
        self.assertEqual(c['metadata'], {'title': 'Classical Conditioning', 'chapter': 6, 'section': '6.2'})
        self.assertEqual(chunk_from_row({**ROW, 'section': None})['metadata'].get('section'), None)

    def test_existing_metadata_is_not_overwritten(self):
        c = chunk_from_row({**ROW, 'metadata': {'chapter': 99}})
        self.assertEqual(c['metadata']['chapter'], 99)

    def test_questions_object_or_array(self):
        self.assertEqual(load_questions({'meta': {}, 'questions': [QUESTION]}), [QUESTION])
        self.assertEqual(load_questions([QUESTION]), [QUESTION])
        with self.assertRaises(ValueError):
            load_questions({'meta': {}})

    def test_alt_gold_is_kept_and_filter_preserved(self):
        q = question_from_day6(QUESTION)
        self.assertEqual(len(q['gold']), 2)
        self.assertEqual(q['gold'][1]['evidence'], QUESTION['alt_gold'][0]['evidence_quote'])
        self.assertEqual(q['filter'], {'chapter': 6})
        validate([chunk_from_row(ROW)], [q])

    def test_alt_gold_on_wrong_page_fails_validation(self):
        bad = {**QUESTION, 'alt_gold': [{**QUESTION['alt_gold'][0], 'gold_page': 199}]}
        with self.assertRaises(ValueError):
            validate([chunk_from_row(ROW)], [question_from_day6(bad)])


if __name__ == '__main__':
    unittest.main()
