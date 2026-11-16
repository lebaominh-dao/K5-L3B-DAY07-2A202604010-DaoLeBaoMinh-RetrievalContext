"""Check the Day 7 benchmark and build benchmark/cases.json.

Inputs (benchmark/):
  questions.json      answerable questions with gold evidence (from day6_export.py)
  abstain_cases.json  questions without evidence, each with an `absence_check`
Checks:
  - answerable gold resolves to a chunk (starter/baseline.validate);
  - every `absence_check.terms` entry is missing from every chunk, and every
    `near_topic_terms` entry is present (so the case stays close to the corpus);
  - IDs are unique and the split minimums of BENCHMARK.md are met.
Output: cases.json with only what an agent run may see (id, split, question,
filter) plus `answerable` / `expected_behavior` for starter/agent_metrics.py.

Run from the repo root:
  python src/build_benchmark.py --chunks starter/data/day6/chunks.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import validate  # noqa: E402

MINIMUMS = {('dev', True): 15, ('dev', False): 2, ('test', True): 5, ('test', False): 2}


def check_abstain(cases, chunks):
    """Return a list of problems; an empty list means every case passes."""
    texts = [c['text'].lower() for c in chunks]
    problems = []
    for case in cases:
        cid = case.get('id')
        if case.get('answerable') is not False or case.get('expected_behavior') != 'search_and_abstain':
            problems.append(f'{cid}: needs answerable=false and expected_behavior=search_and_abstain')
        if not case.get('absence_reason'):
            problems.append(f'{cid}: missing absence_reason')
        check = case.get('absence_check') or {}
        if not check.get('terms'):
            problems.append(f'{cid}: absence_check.terms is empty')
        for term in check.get('terms', []):
            found = [c['id'] for c, t in zip(chunks, texts) if term.lower() in t]
            if found:
                problems.append(f'{cid}: absent term {term!r} found in {found[:3]}')
        for term in check.get('near_topic_terms', []):
            if not any(term.lower() in t for t in texts):
                problems.append(f'{cid}: near-topic term {term!r} not in corpus')
    return problems


def build_cases(questions, abstain):
    cases = []
    for q in questions:
        case = {'id': q['id'], 'split': q['split'], 'question': q['question'],
                'answerable': True, 'expected_behavior': 'search_and_answer'}
        if q.get('filter'):
            case['filter'] = q['filter']
        cases.append(case)
    for a in abstain:
        cases.append({k: a[k] for k in ('id', 'split', 'question', 'answerable', 'expected_behavior')})
    ids = [c['id'] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate case IDs across questions.json and abstain_cases.json')
    counts = {key: sum((c['split'], c['answerable']) == key for c in cases) for key in MINIMUMS}
    short = {f'{s}/{"answerable" if a else "abstain"}': f'{counts[(s, a)]}<{m}'
             for (s, a), m in MINIMUMS.items() if counts[(s, a)] < m}
    if short:
        raise ValueError(f'benchmark below BENCHMARK.md minimums: {short}')
    return cases, counts


def main():
    parser = argparse.ArgumentParser(description='Check benchmark and write benchmark/cases.json')
    parser.add_argument('--chunks', required=True, type=Path)
    parser.add_argument('--benchmark', default=ROOT / 'benchmark', type=Path)
    args = parser.parse_args()
    chunks = json.loads(args.chunks.read_text(encoding='utf-8'))
    questions = json.loads((args.benchmark / 'questions.json').read_text(encoding='utf-8'))
    abstain = json.loads((args.benchmark / 'abstain_cases.json').read_text(encoding='utf-8'))
    validate(chunks, questions)
    problems = check_abstain(abstain, chunks)
    if problems:
        raise SystemExit('Abstain check failed:\n  ' + '\n  '.join(problems))
    cases, counts = build_cases(questions, abstain)
    out = args.benchmark / 'cases.json'
    out.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'OK: {len(cases)} cases -> {out}')
    for (split, answerable), n in counts.items():
        print(f'  {split:4} {"answerable" if answerable else "abstain   "}: {n}')


if __name__ == '__main__':
    main()
