"""Benchmark retrieval methods on one split (dev by default; test only after tuning is frozen).

Metrics over answerable questions (same hit definition as starter/baseline.hit:
right source + page and the whole evidence string inside the chunk):
  Hit@1, Evidence Hit@3, Hit@10, MRR@10, Context Evidence Rate (top-3 packed into
  a character budget), filter compliance, latency, embedding cost.
Questions without evidence are searched too (top-3 kept for later abstention
work) but are not part of any retrieval metric.

Run from the repo root:
  .venv/bin/python src/run_retrieval.py --split dev --output starter/results/retrieval-dev
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
sys.path.insert(0, str(ROOT / 'src'))
from baseline import hit, pack_context  # noqa: E402
from retrieval import (BM25Retriever, DenseRetriever, HybridRetriever, QueryEmbedder,  # noqa: E402
                       TfidfRetriever, matches)

METHODS = ('dense', 'bm25', 'tfidf', 'hybrid')
TRACE_FIELDS = ('id', 'rank', 'score', 'source_id', 'page', 'metadata', 'component_ranks')


def build(method, chunks, embedder):
    if method == 'dense':
        return DenseRetriever(embedder)
    if method == 'bm25':
        return BM25Retriever(chunks)
    if method == 'tfidf':
        return TfidfRetriever(chunks)
    if method == 'hybrid':
        return HybridRetriever([DenseRetriever(embedder), BM25Retriever(chunks)])
    raise ValueError(method)


def evaluate_question(retriever, q, depth, budget):
    start = time.perf_counter()
    results = retriever.search(q['question'], filters=q.get('filter'), top_k=depth)
    elapsed_ms = (time.perf_counter() - start) * 1000
    top3 = results[:3]
    context, context_ids = pack_context(top3, budget)
    hits = [hit(r, q['gold']) for r in results]
    first = next((i for i, h in enumerate(hits, 1) if h), None)
    return {
        'query_id': q['id'], 'question': q['question'], 'filter': q.get('filter'),
        'hit1': bool(hits[:1] and hits[0]), 'hit3': any(hits[:3]), 'hit10': first is not None,
        'first_hit_rank': first, 'context_hit': any(h and r['id'] in context_ids for r, h in zip(top3, hits)),
        'context_ids': context_ids, 'context_chars': len(context),
        'filter_ok': all(matches(r, q.get('filter')) for r in results),
        'elapsed_ms': round(elapsed_ms, 2),
        'results': [{**{k: r[k] for k in TRACE_FIELDS if k in r}, 'hit': h,
                     'text_preview': r['text'][:160]} for r, h in zip(results, hits)],
    }


def summarize(method, traces, abstain_traces, embedder):
    n = len(traces)
    with_filter = [t for t in traces if t['filter']]
    ms = sorted(t['elapsed_ms'] for t in traces + abstain_traces)
    frac = lambda k: {'n': sum(t[k] for t in traces), 'N': n, 'rate': round(sum(t[k] for t in traces) / n, 3)}
    uses_embedding = method in ('dense', 'hybrid')
    return {
        'method': method, 'n_answerable': n,
        'hit_at_1': frac('hit1'), 'evidence_hit_at_3': frac('hit3'), 'hit_at_10': frac('hit10'),
        'mrr_at_10': round(sum(1 / t['first_hit_rank'] for t in traces if t['first_hit_rank']) / n, 3),
        'context_evidence_rate': frac('context_hit'),
        'filter_compliant': f"{sum(t['filter_ok'] for t in with_filter)}/{len(with_filter)}",
        'failed_hit3': [t['query_id'] for t in traces if not t['hit3']],
        'median_ms': round(statistics.median(ms), 1), 'max_ms': round(ms[-1], 1),
        'embedding_tokens': embedder.tokens if uses_embedding else 0,
        'embedding_cost_usd': round(embedder.cost_usd(), 7) if uses_embedding else 0.0,
        'abstain_top1_score': {t['query_id']: t['results'][0]['score'] if t['results'] else None
                               for t in abstain_traces},
    }


def comparison_table(summaries, args):
    lines = [f'# Retrieval benchmark — {args.split}', '',
             f'Strategy B chunks; metrics over {summaries[0]["n_answerable"]} answerable questions; '
             f'context = top-3 packed into {args.budget} chars; ranking depth {args.depth}.', '',
             '| Method | Hit@1 | Evidence Hit@3 | Hit@10 | MRR@10 | Context Evidence | Filter | Median ms | Embedding $ | Miss @3 |',
             '|---|---|---|---|---|---|---|---:|---:|---|']
    for s in summaries:
        f = lambda k: f"{s[k]['n']}/{s[k]['N']}"
        lines.append(f"| {s['method']} | {f('hit_at_1')} | {f('evidence_hit_at_3')} | {f('hit_at_10')} | "
                     f"{s['mrr_at_10']} | {f('context_evidence_rate')} | {s['filter_compliant']} | "
                     f"{s['median_ms']} | {s['embedding_cost_usd']:.6f} | {', '.join(s['failed_hit3']) or '-'} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Benchmark retrieval methods on one split')
    parser.add_argument('--split', required=True, choices=('dev', 'test'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--chunks', default=ROOT / 'starter/data/day6/chunks.json', type=Path)
    parser.add_argument('--benchmark', default=ROOT / 'benchmark', type=Path)
    parser.add_argument('--methods', default=','.join(METHODS))
    parser.add_argument('--depth', type=int, default=10, help='ranking depth for Hit@10 / MRR@10')
    parser.add_argument('--budget', type=int, default=3000, help='context budget in characters')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')

    chunks = json.loads(args.chunks.read_text(encoding='utf-8'))
    # Only the requested split is loaded, so dev runs never touch test gold.
    questions = [q for q in json.loads((args.benchmark / 'questions.json').read_text(encoding='utf-8'))
                 if q['split'] == args.split]
    abstain = [{'id': a['id'], 'question': a['question']}
               for a in json.loads((args.benchmark / 'abstain_cases.json').read_text(encoding='utf-8'))
               if a['split'] == args.split]

    summaries, all_traces = [], {}
    for method in args.methods.split(','):
        embedder = QueryEmbedder() if method in ('dense', 'hybrid') else None  # fresh cache per method
        retriever = build(method, chunks, embedder)
        traces = [evaluate_question(retriever, q, args.depth, args.budget) for q in questions]
        abstain_traces = []
        for a in abstain:
            start = time.perf_counter()
            res = retriever.search(a['question'], top_k=3)
            abstain_traces.append({'query_id': a['id'], 'question': a['question'],
                                   'elapsed_ms': round((time.perf_counter() - start) * 1000, 2),
                                   'results': [{k: r[k] for k in TRACE_FIELDS if k in r} for r in res]})
        summaries.append(summarize(method, traces, abstain_traces, embedder))
        all_traces[method] = {'answerable': traces, 'abstain': abstain_traces}
        print(f"{method:7} hit@1 {summaries[-1]['hit_at_1']['n']}/{len(traces)}  "
              f"hit@3 {summaries[-1]['evidence_hit_at_3']['n']}/{len(traces)}  "
              f"miss@3 {summaries[-1]['failed_hit3']}")

    config = {'split': args.split, 'methods': args.methods.split(','), 'depth': args.depth,
              'budget_chars': args.budget, 'chunks': str(args.chunks), 'n_chunks': len(chunks),
              'bm25': {'k1': 1.5, 'b': 0.75}, 'hybrid': {'components': ['dense', 'bm25'], 'rrf_k': 60,
                                                          'candidates_per_component': 20}}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, obj in (('summary.json', {'config': config, 'methods': summaries}), ('traces.json', all_traces)):
        (args.output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'comparison.md').write_text(comparison_table(summaries, args), encoding='utf-8')
    print(comparison_table(summaries, args))


if __name__ == '__main__':
    main()
