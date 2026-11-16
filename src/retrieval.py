"""Retrieval methods for Day 7 over the Day 6 corpus.

Every retriever has `search(query, *, filters=None, top_k=3) -> list[dict]` and
returns Day 7 chunks (id, text, source_id, source, page, metadata) plus
`score`, `rank` (1-based) and `method`. Errors (database, embedding API) are
raised, never replaced by empty or fake results.

- DenseRetriever: query embedding (same model as Day 6) + pgvector cosine search.
- BM25Retriever: Okapi BM25 over the exported chunks.
- TfidfRetriever: the starter TF-IDF baseline, wrapped for the same interface.
- HybridRetriever: Reciprocal Rank Fusion of several retrievers (no score mixing).

Filters are exact matches on chunk metadata, e.g. {"chapter": 6}. They must
come from the user/question input, never from gold labels.
"""
import math
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
sys.path.insert(0, str(ROOT / 'src'))
from baseline import TfidfIndex, tokenize  # noqa: E402
from day6_export import CHUNK_COLUMNS, chunk_from_row  # noqa: E402

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
EMBEDDING_USD_PER_M_TOKENS = {'openai/text-embedding-3-small': 0.02}
FILTER_COLUMNS = ('chapter', 'section')  # columns of the Day 6 `chunks` table


def matches(chunk, filters):
    return not filters or all(chunk['metadata'].get(k) == v for k, v in filters.items())


def ranked(chunks_with_scores, method, top_k):
    out = sorted(chunks_with_scores, key=lambda cs: (-cs[1], cs[0]['id']))[:top_k]
    return [{**c, 'score': s, 'rank': i, 'method': method} for i, (c, s) in enumerate(out, 1)]


class QueryEmbedder:
    """OpenRouter embeddings with an in-run cache; tracks tokens for cost."""

    def __init__(self, model=None, api_key=None):
        from openai import OpenAI
        self.model = model or os.environ['EMBEDDING_MODEL']
        self._client = OpenAI(api_key=api_key or os.environ['OPENROUTER_API_KEY'], base_url=OPENROUTER_BASE_URL)
        self._cache = {}
        self.tokens = 0
        self.calls = 0

    def embed(self, text):
        if text not in self._cache:
            resp = self._client.embeddings.create(model=self.model, input=[text])
            self.calls += 1
            self.tokens += resp.usage.total_tokens if resp.usage else 0
            self._cache[text] = resp.data[0].embedding
        return self._cache[text]

    def cost_usd(self):
        return self.tokens * EMBEDDING_USD_PER_M_TOKENS.get(self.model, 0) / 1e6


class DenseRetriever:
    method = 'dense'

    def __init__(self, embedder, database_url=None, strategy=None):
        self.embedder = embedder
        self.database_url = database_url or os.environ['DATABASE_URL']
        self.strategy = strategy or os.getenv('DAY6_STRATEGY', 'B')

    def search(self, query, *, filters=None, top_k=3):
        filters = filters or {}
        unknown = set(filters) - set(FILTER_COLUMNS)
        if unknown:
            raise ValueError(f'dense filter supports {FILTER_COLUMNS}, got {sorted(unknown)}')
        import psycopg
        from psycopg.rows import dict_row
        vector = '[' + ','.join(map(str, self.embedder.embed(query))) + ']'
        where = ''.join(f' AND {col} = %({col})s' for col in filters)  # col is whitelisted above
        sql = (f"SELECT {', '.join(CHUNK_COLUMNS)}, 1 - (embedding <=> %(v)s::vector) AS score "
               f'FROM chunks WHERE strategy = %(s)s{where} '
               'ORDER BY embedding <=> %(v)s::vector, chunk_id LIMIT %(k)s')
        with psycopg.connect(self.database_url, connect_timeout=5, row_factory=dict_row) as conn:
            rows = conn.execute(sql, {'v': vector, 's': self.strategy, 'k': top_k, **filters}).fetchall()
        return [{**chunk_from_row(r), 'score': float(r['score']), 'rank': i, 'method': self.method}
                for i, r in enumerate(rows, 1)]


class BM25Retriever:
    method = 'bm25'

    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.tf = [Counter(tokenize(c['text'])) for c in chunks]
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg_len = sum(self.len) / len(self.len)
        df = Counter(term for tf in self.tf for term in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query, *, filters=None, top_k=3):
        terms = [t for t in set(tokenize(query)) if t in self.idf]
        scored = []
        for chunk, tf, length in zip(self.chunks, self.tf, self.len):
            if not matches(chunk, filters):
                continue
            score = sum(self.idf[t] * tf[t] * (self.k1 + 1)
                        / (tf[t] + self.k1 * (1 - self.b + self.b * length / self.avg_len))
                        for t in terms if t in tf)
            if score > 0:
                scored.append((chunk, score))
        return ranked(scored, self.method, top_k)


class TfidfRetriever:
    method = 'tfidf'

    def __init__(self, chunks):
        self.chunks = chunks
        self.index = TfidfIndex(chunks)

    def search(self, query, *, filters=None, top_k=3):
        results = self.index.search(query, top_k=len(self.chunks))
        scored = [({k: v for k, v in r.items() if k not in ('score', 'strategy')}, r['score'])
                  for r in results if matches(r, filters)]
        return ranked(scored, self.method, top_k)


class HybridRetriever:
    """Reciprocal Rank Fusion: score = sum over retrievers of 1 / (k + rank)."""

    method = 'hybrid_rrf'

    def __init__(self, retrievers, k=60, candidates=20):
        self.retrievers, self.k, self.candidates = retrievers, k, candidates

    def search(self, query, *, filters=None, top_k=3):
        fused, chunks, sources = Counter(), {}, {}
        for retriever in self.retrievers:
            for r in retriever.search(query, filters=filters, top_k=self.candidates):
                fused[r['id']] += 1 / (self.k + r['rank'])
                chunks.setdefault(r['id'], {k: v for k, v in r.items() if k not in ('score', 'rank', 'method')})
                sources.setdefault(r['id'], {})[retriever.method] = r['rank']
        out = ranked([(chunks[i], s) for i, s in fused.items()], self.method, top_k)
        for r in out:
            r['component_ranks'] = sources[r['id']]
        return out
