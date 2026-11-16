"""Build a self-contained HTML page for labelling agent runs by hand.

For every case of each run directory: question, agent answer, cited chunks,
final context, expected answer and gold evidence (or why evidence is missing),
and inputs for the labels
starter/agent_metrics.py needs (answer_grade, citation_support,
abstention_correct) plus context_grade and a note. The page exports reviews.json.
Translation is on demand, one case at a time, through src/review_server.py.

  .venv/bin/python src/build_review_tool.py --split test \
      --runs starter/results/agent-test-A0 starter/results/agent-test-C1 \
      --output starter/results/review-test/review_tool.html
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
sys.path.insert(0, str(ROOT / 'src'))
from baseline import hit  # noqa: E402

TEMPLATE = ROOT / 'src/review_tool_template.html'


def run_settings(trace):
    c = trace['config']
    return (f"{trace['model']}, effort {c['effort']}, {c['retriever']}, top-{c['top_k']}, "
            f"tối đa {c['max_searches']} search, context {c['budget_chars']} ký tự")


def build_case(trace, case, gold_q, absent, chunks_by_id):
    labels = {}
    for e in trace['events']:
        labels.update(e.get('labels', {}))
    gold = gold_q['gold'] if gold_q else []
    context = []
    for cid in trace['context_ids']:
        ch = chunks_by_id[cid]
        context.append({'id': cid, 'page': ch['page'], 'chapter': ch['metadata'].get('chapter'), 'text': ch['text'],
                        'label': labels.get(cid), 'cited': cid in trace['citations'],
                        'has_gold': bool(gold) and hit(ch, gold)})
    return {
        'id': case['id'], 'answerable': case['answerable'], 'question': case['question'],
        'status': trace['status'], 'error': trace.get('error'), 'answer': trace['answer'],
        'citations': trace['citations'], 'n_searches': trace['n_searches'],
        'queries': [e['query'] for e in trace['events'] if e['event'] == 'search'],
        'context': context,
        'expected_answer': gold_q['expected_answer'] if gold_q else None,
        'gold': [{'page': g['page'], 'evidence': g['evidence'], 'alternative': i > 0} for i, g in enumerate(gold)],
        'absence_reason': absent['absence_reason'] if absent else None,
        'auto': {'context_has_gold': any(c['has_gold'] for c in context),
                 'cited_has_gold': any(c['has_gold'] for c in context if c['cited'])},
    }


def main():
    parser = argparse.ArgumentParser(description='Build the HTML review tool for agent runs')
    parser.add_argument('--split', required=True, choices=('dev', 'test'))
    parser.add_argument('--runs', nargs='+', required=True, type=Path, help='run_agent.py output directories')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--benchmark', default=ROOT / 'benchmark', type=Path)
    parser.add_argument('--chunks', default=ROOT / 'starter/data/day6/chunks.json', type=Path)
    args = parser.parse_args()

    load = lambda p: json.loads(p.read_text(encoding='utf-8'))
    chunks_by_id = {c['id']: c for c in load(args.chunks)}
    cases = {c['id']: c for c in load(args.benchmark / 'cases.json') if c['split'] == args.split}
    gold = {q['id']: q for q in load(args.benchmark / 'questions.json') if q['split'] == args.split}
    absent = {a['id']: a for a in load(args.benchmark / 'abstain_cases.json') if a['split'] == args.split}

    runs = []
    for d in args.runs:
        traces = load(d / 'traces.json')
        runs.append({'name': d.name.replace('agent-test-', '').replace('agent-dev-', ''), 'dir': str(d),
                     'settings': run_settings(traces[0]),
                     'cases': [build_case(t, cases[t['query_id']], gold.get(t['query_id']), absent.get(t['query_id']),
                                          chunks_by_id) for t in traces]})

    data = {'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'split': args.split,
            'runs': runs}
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    html = TEMPLATE.read_text(encoding='utf-8').replace('/*__DATA__*/', payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding='utf-8')
    print(f'wrote {args.output} ({len(runs)} runs, {sum(len(r["cases"]) for r in runs)} cases)')


if __name__ == '__main__':
    main()
