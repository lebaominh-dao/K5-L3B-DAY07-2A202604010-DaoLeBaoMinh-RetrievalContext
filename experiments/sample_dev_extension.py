"""Pick source chunks for the dev extension without looking at any retrieval result.

Rules (fixed before writing questions):
  - seed 20261116; strategy B chunks from starter/data/day6/chunks.json;
  - skip chunks shorter than 400 characters (too little to ask about);
  - skip every page that holds test gold evidence, so dev and test stay disjoint;
  - skip chunks that already contain gold evidence of an existing question;
  - 10 chunks for answerable questions, 3 more for near-miss no-evidence questions;
  - question types assigned round-robin in sampled order.

  python3 experiments/sample_dev_extension.py
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import hit  # noqa: E402

SEED = 20261116
TYPES = ('paraphrase', 'condition_or_exception', 'specific_detail', 'why_explanation')

chunks = json.loads((ROOT / 'starter/data/day6/chunks.json').read_text(encoding='utf-8'))
questions = json.loads((ROOT / 'benchmark/questions.json').read_text(encoding='utf-8'))
test_pages = {(g['source_id'], g['page']) for q in questions if q['split'] == 'test' for g in q['gold']}
gold_chunks = {c['id'] for c in chunks for q in questions if hit(c, q['gold'])}
pool = [c for c in chunks if len(c['text']) >= 400 and (c['source_id'], c['page']) not in test_pages
        and c['id'] not in gold_chunks]
picked = random.Random(SEED).sample(pool, 13)
out = {'seed': SEED, 'pool_size': len(pool), 'excluded_test_pages': sorted(test_pages),
       'answerable': [{'chunk_id': c['id'], 'type': TYPES[i % len(TYPES)]} for i, c in enumerate(picked[:10])],
       'near_miss_abstain': [c['id'] for c in picked[10:]]}
(ROOT / 'experiments/dev_extension_sample.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
print(json.dumps(out, indent=2))
