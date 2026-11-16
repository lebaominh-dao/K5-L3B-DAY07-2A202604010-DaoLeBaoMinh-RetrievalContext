"""Export the Day 6 pgvector store and benchmark to the Day 7 JSON contract.

Fixes three gaps of `starter/convert_day6.py` for this Day 6 repo:
1. `chapter` / `section` are table columns, not metadata; they are copied into
   `metadata` so Day 6 filters such as {"chapter": 6} keep working.
2. `benchmark/questions.json` is `{meta, questions}`, not an array.
3. `alt_gold` (alternative evidence, e.g. D05) is appended to `gold`.

Every output is checked with `starter/baseline.validate`: each gold evidence
must sit inside one chunk with the same source and page.

Run from the repo root (needs the Day 6 Docker container running):
  DATABASE_URL=postgresql://... python src/day6_export.py \
      --questions ../Day06/benchmark/questions.json --strategy B \
      --output starter/data/day6
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import validate  # noqa: E402
from convert_day6 import convert_chunk, convert_question  # noqa: E402

CHUNK_COLUMNS = ('chunk_id', 'document_id', 'source', 'page', 'chapter', 'section', 'text', 'metadata')


def chunk_from_row(row):
    """Map one Day 6 `chunks` row (dict of CHUNK_COLUMNS) to a Day 7 chunk."""
    metadata = dict(row.get('metadata') or {})
    for key in ('chapter', 'section'):
        if row.get(key) is not None:
            metadata.setdefault(key, row[key])
    return convert_chunk({**row, 'metadata': metadata})


def load_questions(raw):
    """Accept the Day 6 `{meta, questions}` object or a plain array."""
    if isinstance(raw, dict):
        raw = raw.get('questions')
    if not isinstance(raw, list):
        raise ValueError('questions file must be a JSON array or an object with a "questions" array')
    return raw


def question_from_day6(q):
    """Convert one Day 6 question and keep its alternative evidence."""
    result = convert_question(q)
    for alt in q.get('alt_gold', []):
        result['gold'].append({'source_id': alt['gold_source_id'], 'page': alt['gold_page'],
                               'evidence': alt['evidence_quote']})
    if 'type' in q:
        result['type'] = q['type']
    return result


def fetch_rows(database_url, strategy):
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(database_url, connect_timeout=5, row_factory=dict_row) as conn:
        rows = conn.execute(
            f"SELECT {', '.join(CHUNK_COLUMNS)}, vector_dims(embedding) AS dims "
            "FROM chunks WHERE strategy = %s ORDER BY document_id, page, chunk_id", (strategy,)).fetchall()
        strategies = [r['strategy'] for r in conn.execute('SELECT DISTINCT strategy FROM chunks ORDER BY 1')]
    if not rows:
        raise SystemExit(f'No chunks for strategy {strategy!r}; available: {strategies}')
    return rows


def main():
    parser = argparse.ArgumentParser(description='Export Day 6 pgvector chunks + benchmark to Day 7 JSON')
    parser.add_argument('--questions', required=True, type=Path, help='Day 6 benchmark/questions.json')
    parser.add_argument('--strategy', default='B', help='Day 6 chunking strategy to export (default: B)')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--database-url', default=os.getenv('DATABASE_URL'),
                        help='defaults to $DATABASE_URL (see Day06/starter/.env)')
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit('Set DATABASE_URL or pass --database-url')

    rows = fetch_rows(args.database_url, args.strategy)
    chunks = [chunk_from_row(r) for r in rows]
    raw_questions = load_questions(json.loads(args.questions.read_text(encoding='utf-8')))
    questions = [question_from_day6(q) for q in raw_questions]
    validate(chunks, questions)

    meta = {
        'source': 'Day 6 pgvector table `chunks`', 'strategy': args.strategy,
        'embedding_dims': sorted({r['dims'] for r in rows}), 'n_chunks': len(chunks),
        'n_questions': len(questions),
        'splits': {s: sum(q['split'] == s for q in questions) for s in ('dev', 'test')},
        'n_gold_alternatives': sum(len(q['gold']) - 1 for q in questions),
        'questions_file': str(args.questions),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in (('chunks.json', chunks), ('questions.json', questions), ('export_meta.json', meta)):
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main()
