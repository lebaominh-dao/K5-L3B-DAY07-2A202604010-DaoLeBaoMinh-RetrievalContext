"""Retrieval behaviour without database or API (dense is covered by src/check_setup.py)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from retrieval import BM25Retriever, DenseRetriever, HybridRetriever, TfidfRetriever
from run_retrieval import evaluate_question


def chunk(id, text, chapter, page=1):
    return {'id': id, 'text': text, 'source_id': f'ch{chapter}', 'source': 'book.pdf', 'page': page,
            'metadata': {'chapter': chapter}}


CHUNKS = [
    chunk('a', 'Extinction weakens the conditioned response when the stimulus is no longer paired.', 6),
    chunk('b', 'Blocking is forgetting when information is on the tip of the tongue.', 8, page=2),
    chunk('c', 'Spontaneous recovery returns a conditioned response after a rest period.', 6, page=3),
    chunk('d', 'Long-term memory stores information for a long time.', 8, page=4),
]


class FakeRetriever:
    """Returns a fixed order, honouring filters like the real retrievers."""

    def __init__(self, method, order):
        self.method, self.order = method, order

    def search(self, query, *, filters=None, top_k=3):
        rows = [c for i in self.order for c in CHUNKS if c['id'] == i
                and all(c['metadata'].get(k) == v for k, v in (filters or {}).items())]
        return [{**c, 'score': 1 / r, 'rank': r, 'method': self.method} for r, c in enumerate(rows[:top_k], 1)]


class RetrievalTests(unittest.TestCase):
    def test_bm25_ranks_matching_chunk_first_and_gives_ranks(self):
        out = BM25Retriever(CHUNKS).search('conditioned response extinction', top_k=2)
        self.assertEqual([r['id'] for r in out], ['a', 'c'])
        self.assertEqual([r['rank'] for r in out], [1, 2])
        self.assertTrue(all(r['method'] == 'bm25' for r in out))

    def test_lexical_filters_are_applied_before_ranking(self):
        for retriever in (BM25Retriever(CHUNKS), TfidfRetriever(CHUNKS)):
            out = retriever.search('information forgetting', filters={'chapter': 6}, top_k=3)
            self.assertTrue(all(r['metadata']['chapter'] == 6 for r in out), retriever.method)

    def test_no_match_returns_empty_not_fake(self):
        self.assertEqual(BM25Retriever(CHUNKS).search('zzzz unknown'), [])

    def test_rrf_prefers_chunks_ranked_by_both(self):
        hybrid = HybridRetriever([FakeRetriever('dense', ['b', 'a', 'c']), FakeRetriever('bm25', ['a', 'c', 'd'])])
        out = hybrid.search('q', top_k=3)
        self.assertEqual(out[0]['id'], 'a')  # rank 2 + rank 1 beats a single rank 1
        self.assertEqual(out[0]['component_ranks'], {'dense': 2, 'bm25': 1})
        self.assertAlmostEqual(out[0]['score'], 1 / 62 + 1 / 61)

    def test_dense_rejects_unknown_filter_before_any_call(self):
        dense = DenseRetriever(embedder=None, database_url='postgresql://unused', strategy='B')
        with self.assertRaises(ValueError):
            dense.search('q', filters={'year': 2025})

    def test_evaluate_question_metrics(self):
        q = {'id': 'q1', 'question': 'q', 'filter': None,
             'gold': [{'source_id': 'ch6', 'page': 3, 'evidence': 'Spontaneous recovery'}]}
        t = evaluate_question(FakeRetriever('x', ['a', 'c', 'b', 'd']), q, depth=10, budget=3000)
        self.assertEqual((t['hit1'], t['hit3'], t['first_hit_rank'], t['context_hit']), (False, True, 2, True))
        tight = evaluate_question(FakeRetriever('x', ['a', 'c']), q, depth=10, budget=150)
        self.assertTrue(tight['hit3'])
        self.assertFalse(tight['context_hit'])  # retrieved but did not fit the budget


if __name__ == '__main__':
    unittest.main()
