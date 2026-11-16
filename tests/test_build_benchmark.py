"""Checks for the benchmark builder and the committed benchmark files."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from build_benchmark import MINIMUMS, build_cases, check_abstain

CHUNKS = [{'id': 'c1', 'text': 'Pavlov studied the digestive system of dogs.'}]
ABSTAIN = {'id': 'DA1', 'split': 'dev', 'question': 'When did Pavlov win the Nobel Prize?',
           'answerable': False, 'expected_behavior': 'search_and_abstain', 'absence_reason': 'not in text',
           'absence_check': {'terms': ['Nobel'], 'near_topic_terms': ['Pavlov']}}


def answerable(i, split):
    return {'id': f'{split}{i}', 'split': split, 'question': 'q', 'gold': [], 'expected_answer': 'a'}


class BuildBenchmarkTests(unittest.TestCase):
    def test_absent_term_passes_and_present_term_fails(self):
        self.assertEqual(check_abstain([ABSTAIN], CHUNKS), [])
        bad = {**ABSTAIN, 'absence_check': {'terms': ['digestive'], 'near_topic_terms': ['Pavlov']}}
        self.assertIn('found in', check_abstain([bad], CHUNKS)[0])

    def test_near_topic_term_must_exist(self):
        far = {**ABSTAIN, 'absence_check': {'terms': ['Nobel'], 'near_topic_terms': ['Skinner']}}
        self.assertIn('near-topic', check_abstain([far], CHUNKS)[0])

    def test_minimums_and_no_gold_in_cases(self):
        qs = [answerable(i, 'dev') for i in range(15)] + [answerable(i, 'test') for i in range(5)]
        ab = [{**ABSTAIN, 'id': f'D{i}'} for i in range(2)] + [{**ABSTAIN, 'id': f'T{i}', 'split': 'test'} for i in range(2)]
        cases, _ = build_cases(qs, ab)
        self.assertEqual(len(cases), 24)
        self.assertTrue(all('gold' not in c and 'absence_check' not in c for c in cases))
        with self.assertRaises(ValueError):
            build_cases(qs, ab[:3])

    def test_committed_benchmark_meets_minimums(self):
        cases = json.loads((ROOT / 'benchmark/cases.json').read_text(encoding='utf-8'))
        for (split, ans), n in MINIMUMS.items():
            self.assertGreaterEqual(sum(c['split'] == split and c['answerable'] is ans for c in cases), n)
        self.assertTrue(all(set(c) <= {'id', 'split', 'question', 'answerable', 'expected_behavior', 'filter'}
                            for c in cases))


if __name__ == '__main__':
    unittest.main()
