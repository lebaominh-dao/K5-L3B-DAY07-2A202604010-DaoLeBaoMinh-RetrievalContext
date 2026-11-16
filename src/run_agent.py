"""Run the agent on one split and compute automatic metrics.

The agent only sees benchmark/cases.json (id, question, filter). Gold evidence
for the same split is loaded afterwards to score:
  - tool use: share of runs with >= 1 search; distribution of searches per run
  - Context Evidence Rate: gold evidence inside a chunk of the final context
  - cited evidence (automatic proxy): a cited chunk contains the gold evidence
  - abstention on no-evidence cases; false abstention on answerable cases
  - errors, latency, tokens and cost
Answer quality and citation support still need human labels: a
reviews_template.json is written for starter/agent_metrics.py.

  .venv/bin/python src/run_agent.py --split dev --output starter/results/agent-dev
"""
import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
sys.path.insert(0, str(ROOT / 'src'))
from baseline import hit  # noqa: E402


def chunk_hits(chunk_ids, gold, chunks_by_id):
    return any(hit(chunks_by_id[i], gold) for i in chunk_ids if i in chunks_by_id)


def score(traces, cases, gold_by_id, chunks_by_id):
    case_by_id = {c['id']: c for c in cases}
    ok = [t for t in traces if t['status'] != 'error']
    answerable = [t for t in ok if case_by_id[t['query_id']]['answerable']]
    abstain = [t for t in ok if not case_by_id[t['query_id']]['answerable']]
    frac = lambda n, N: {'n': n, 'N': N, 'rate': round(n / N, 3) if N else None}
    ctx = [t['query_id'] for t in answerable if chunk_hits(t['context_ids'], gold_by_id[t['query_id']], chunks_by_id)]
    cited = [t['query_id'] for t in answerable if chunk_hits(t['citations'], gold_by_id[t['query_id']], chunks_by_id)]
    answered = [t for t in ok if t['status'] == 'answered']
    times = [t['elapsed_s'] for t in traces]
    return {
        'cases': len(traces), 'errors': [{'id': t['query_id'], 'error': t.get('error')} for t in traces
                                         if t['status'] == 'error'],
        'tool_use': frac(sum(t['n_searches'] > 0 for t in ok), len(ok)),
        'searches_per_run': dict(sorted(Counter(t['n_searches'] for t in ok).items())),
        'context_evidence_rate': frac(len(ctx), len(answerable)),
        'context_missing': [t['query_id'] for t in answerable if t['query_id'] not in ctx],
        'cited_evidence_auto': frac(len(cited), len(answerable)),
        'answers_with_citation': frac(sum(bool(t['citations']) for t in answered), len(answered)),
        'abstention': frac(sum(t['status'] == 'abstain' for t in abstain), len(abstain)),
        'abstain_answered': [t['query_id'] for t in abstain if t['status'] != 'abstain'],
        'false_abstention': frac(sum(t['status'] == 'abstain' for t in answerable), len(answerable)),
        'false_abstain_ids': [t['query_id'] for t in answerable if t['status'] == 'abstain'],
        'median_s': round(statistics.median(times), 2), 'max_s': round(max(times), 2),
        'tokens': {k: sum(t['usage'][k] for t in traces) for k in ('input', 'output', 'cache_write', 'cache_read')},
        'cost_usd': round(sum(t['cost_usd'] for t in traces), 5),
    }


def review_template(traces, cases):
    case_by_id = {c['id']: c for c in cases}
    rows = []
    for t in traces:
        if t['status'] == 'error':
            continue
        row = {'query_id': t['query_id'], 'citation_support': [None] * len(t['citations']), 'note': ''}
        row['answer_grade' if case_by_id[t['query_id']]['answerable'] else 'abstention_correct'] = None
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description='Run the Claude retrieval agent on one split')
    parser.add_argument('--split', required=True, choices=('dev', 'test'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--retriever', default='hybrid', choices=('dense', 'bm25', 'tfidf', 'hybrid'))
    parser.add_argument('--effort', default='medium', choices=('low', 'medium', 'high'))
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--max-searches', type=int, default=4)
    parser.add_argument('--budget', type=int, default=4000, help='context budget in characters')
    parser.add_argument('--ids', help='comma-separated case ids (debugging a subset)')
    parser.add_argument('--chunks', default=ROOT / 'starter/data/day6/chunks.json', type=Path)
    parser.add_argument('--benchmark', default=ROOT / 'benchmark', type=Path)
    args = parser.parse_args()

    import os
    import anthropic
    from dotenv import load_dotenv
    from agent import Agent
    from retrieval import QueryEmbedder
    from run_retrieval import build
    load_dotenv(ROOT / '.env')

    chunks = json.loads(args.chunks.read_text(encoding='utf-8'))
    cases = [c for c in json.loads((args.benchmark / 'cases.json').read_text(encoding='utf-8'))
             if c['split'] == args.split and (not args.ids or c['id'] in args.ids.split(','))]
    embedder = QueryEmbedder() if args.retriever in ('dense', 'hybrid') else None
    agent = Agent(anthropic.Anthropic(), build(args.retriever, chunks, embedder),
                  model=os.getenv('AGENT_MODEL', 'claude-haiku-5-5'), effort=args.effort, top_k=args.top_k,
                  max_searches=args.max_searches, budget=args.budget)

    traces = []
    for case in cases:  # sequential: keeps latency numbers comparable
        t = agent.run(case['question'], filters=case.get('filter'), query_id=case['id'])
        traces.append(t)
        print(f"{case['id']:4} {t['status']:8} searches={t['n_searches']} cites={len(t['citations'])} "
              f"{t['elapsed_s']:5.1f}s  {t.get('error') or t['answer'][:90]!r}")

    # Gold is read only now, after every run of this split has finished.
    gold_by_id = {q['id']: q['gold'] for q in json.loads((args.benchmark / 'questions.json').read_text(encoding='utf-8'))
                  if q['split'] == args.split}
    summary = {'split': args.split, 'model': agent.model,
               'config': {'retriever': args.retriever, 'effort': args.effort, 'top_k': args.top_k,
                          'max_searches': args.max_searches, 'budget_chars': args.budget},
               'embedding_cost_usd': round(embedder.cost_usd(), 7) if embedder else 0.0,
               **score(traces, cases, gold_by_id, {c['id']: c for c in chunks})}
    args.output.mkdir(parents=True, exist_ok=True)
    for name, obj in (('traces.json', traces), ('summary.json', summary),
                      ('reviews_template.json', review_template(traces, cases))):
        (args.output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'config'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
