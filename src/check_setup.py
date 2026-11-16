"""Day 7 setup check: vector store, query embedding, dense search, Claude tool call.

Read-only, costs well under one cent. Run from the repo root:
  .venv/bin/python src/check_setup.py
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

QUERY = 'How is learning different from reflexes and instincts?'  # dev question D01
SEARCH_TOOL = {
    'name': 'search_corpus',
    'description': 'Search the psychology textbook corpus and return matching passages.',
    'strict': True,
    'input_schema': {
        'type': 'object',
        'properties': {'query': {'type': 'string', 'description': 'Search query'}},
        'required': ['query'],
        'additionalProperties': False,
    },
}


def need(name):
    value = os.getenv(name)
    if not value:
        sys.exit(f'[FAIL] {name} is empty in .env (copy .env.example to .env and fill it in)')
    return value


def check_store():
    import psycopg
    with psycopg.connect(need('DATABASE_URL'), connect_timeout=5) as conn:
        version = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()
        rows, dims = conn.execute(
            'SELECT count(*), max(vector_dims(embedding)) FROM chunks WHERE strategy = %s',
            (need('DAY6_STRATEGY'),)).fetchone()
    if not version or not rows:
        sys.exit('[FAIL] pgvector extension or Day 6 chunks missing; run Day 6 ingest first')
    print(f'[OK] pgvector {version[0]}: {rows} chunks, {dims} dims (strategy {os.getenv("DAY6_STRATEGY")})')
    return dims


def check_embedding(dims):
    from openai import OpenAI
    client = OpenAI(api_key=need('OPENROUTER_API_KEY'), base_url='https://openrouter.ai/api/v1')
    resp = client.embeddings.create(model=need('EMBEDDING_MODEL'), input=[QUERY])
    vector = resp.data[0].embedding
    if len(vector) != dims:
        sys.exit(f'[FAIL] query embedding has {len(vector)} dims, index has {dims}')
    print(f'[OK] query embedding {os.getenv("EMBEDDING_MODEL")}: {len(vector)} dims')
    return vector


def check_dense(vector):
    import psycopg
    literal = '[' + ','.join(map(str, vector)) + ']'
    with psycopg.connect(need('DATABASE_URL'), connect_timeout=5) as conn:
        rows = conn.execute(
            'SELECT chunk_id, page, 1 - (embedding <=> %s::vector) AS score FROM chunks '
            'WHERE strategy = %s ORDER BY embedding <=> %s::vector LIMIT 3',
            (literal, os.getenv('DAY6_STRATEGY'), literal)).fetchall()
    print('[OK] dense top-3 for D01:')
    for chunk_id, page, score in rows:
        print(f'       {score:.3f}  p.{page}  {chunk_id}')


def check_claude():
    import anthropic
    need('ANTHROPIC_API_KEY')
    model = need('AGENT_MODEL')
    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model, max_tokens=1024, output_config={'effort': 'low'}, tools=[SEARCH_TOOL],
            messages=[{'role': 'user', 'content': f'Use the search tool to find evidence for: {QUERY}'}])
    except anthropic.AuthenticationError:
        sys.exit('[FAIL] ANTHROPIC_API_KEY rejected (401)')
    except anthropic.NotFoundError:
        sys.exit(f'[FAIL] model {model!r} not found for this key (404)')
    except anthropic.APIStatusError as exc:
        sys.exit(f'[FAIL] Claude API error {exc.status_code}: {exc.message}')
    except anthropic.APIConnectionError:
        sys.exit('[FAIL] cannot reach the Claude API (network)')
    calls = [b for b in resp.content if b.type == 'tool_use']
    if resp.stop_reason != 'tool_use' or not calls:
        sys.exit(f'[FAIL] {model} did not call the tool (stop_reason={resp.stop_reason})')
    u = resp.usage
    print(f'[OK] {resp.model} tool call: search_corpus({json.dumps(calls[0].input, ensure_ascii=False)}) '
          f'| tokens in/out {u.input_tokens}/{u.output_tokens}')


if __name__ == '__main__':
    dims = check_store()
    check_dense(check_embedding(dims))
    check_claude()
    print('Setup OK.')
