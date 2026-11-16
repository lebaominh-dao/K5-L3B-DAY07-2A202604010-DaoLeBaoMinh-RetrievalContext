"""Compare agent runs: the mean per configuration, then one row per run.

Run directories are named <CONFIG>-r<N> (e.g. A0-r1) and hold summary.json from run_agent.py.

  python3 src/compare_runs.py starter/results/dev-exp --output starter/results/dev-exp/comparison.md
"""
import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


def load_runs(root):
    runs = []
    for d in sorted(Path(root).iterdir()):
        m = re.fullmatch(r'(.+)-r(\d+)', d.name)
        if m and (d / 'summary.json').exists():
            summary = json.loads((d / 'summary.json').read_text(encoding='utf-8'))
            runs.append({'config_id': m.group(1), 'rep': int(m.group(2)), **summary})
    return runs


def stats(r):
    n = r['cases']
    dist = r['searches_per_run']
    return {
        'searches': sum(int(k) * v for k, v in dist.items()) / max(1, sum(dist.values())),
        'tokens_per_case': (r['tokens']['input'] + r['tokens']['output']) / n,
        'usd_per_case': (r['cost_usd'] + r.get('embedding_cost_usd', 0)) / n,
        'errors': len(r['errors']),
    }


def frac(r, key):
    return f"{r[key]['n']}/{r[key]['N']}"


def per_config(runs):
    groups = defaultdict(list)
    for r in runs:
        groups[r['config_id']].append(r)
    lines = ['| Config | Settings | Runs | Context evidence (mean) | Cited evidence (mean) | Abstain ok (min) | '
             'False abstain (max) | Errors | Searches/case | Median s | Tokens/case | $/case |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for cid, rs in groups.items():
        s = [stats(r) for r in rs]
        c = rs[0]['config']
        mean_n = lambda k: statistics.mean(r[k]['n'] for r in rs)
        lines.append(
            f"| {cid} | {c['retriever']}, top-{c['top_k']}, {c['budget_chars']} chars, effort {c['effort']} | "
            f"{len(rs)} | {mean_n('context_evidence_rate'):.1f}/{rs[0]['context_evidence_rate']['N']} | "
            f"{mean_n('cited_evidence_auto'):.1f}/{rs[0]['cited_evidence_auto']['N']} | "
            f"{min(r['abstention']['n'] for r in rs)}/{rs[0]['abstention']['N']} | "
            f"{max(r['false_abstention']['n'] for r in rs)}/{rs[0]['false_abstention']['N']} | "
            f"{sum(x['errors'] for x in s)} | {statistics.mean(x['searches'] for x in s):.2f} | "
            f"{statistics.mean(r['median_s'] for r in rs):.2f} | "
            f"{statistics.mean(x['tokens_per_case'] for x in s):.0f} | "
            f"{statistics.mean(x['usd_per_case'] for x in s):.5f} |")
    return '\n'.join(lines)


def per_run(runs):
    lines = ['| Run | Context evidence | Cited evidence | Abstain ok | False abstain | Errors | Searches/case | '
             'Median s | $/case | Context missing | False-abstain ids | No-evidence answered |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in runs:
        s = stats(r)
        lines.append(
            f"| {r['config_id']}-r{r['rep']} | {frac(r, 'context_evidence_rate')} | {frac(r, 'cited_evidence_auto')} | "
            f"{frac(r, 'abstention')} | {frac(r, 'false_abstention')} | {s['errors']} | {s['searches']:.2f} | "
            f"{r['median_s']} | {s['usd_per_case']:.5f} | {', '.join(r['context_missing']) or '-'} | "
            f"{', '.join(r['false_abstain_ids']) or '-'} | {', '.join(r['abstain_answered']) or '-'} |")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Compare agent runs named <CONFIG>-r<N>')
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    runs = load_runs(args.root)
    if not runs:
        raise SystemExit(f'no <CONFIG>-r<N>/summary.json under {args.root}')
    text = '## Per configuration\n\n' + per_config(runs) + '\n\n## Per run\n\n' + per_run(runs) + '\n'
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
