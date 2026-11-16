"""Local server for the review tool: serves the HTML and translates one case on demand.

The RouteAPI key stays in .env on this machine; the page only calls
/api/translate on 127.0.0.1. Translations are cached in
starter/results/translations_vi.json, so a case translated once is served from
disk afterwards.

  .venv/bin/python src/review_server.py --html starter/results/review-test/review_tool.html
  then open http://127.0.0.1:8765
"""
import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from translate import DEFAULT_MODEL, Translator  # noqa: E402

CACHE = ROOT / 'starter/results/translations_vi.json'
MAX_TEXTS, MAX_CHARS = 80, 8000


class State:
    translator = None
    model_checked = False

    @classmethod
    def get(cls):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env', override=True)  # pick up a key added after start
        if cls.translator is None:
            cls.translator = Translator(CACHE)
        if not cls.model_checked:
            cls.translator.check_model()
            cls.model_checked = True
        return cls.translator


def make_handler(html_path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype='application/json; charset=utf-8'):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                return self._send(200, html_path.read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/api/health':
                from dotenv import load_dotenv
                load_dotenv(ROOT / '.env', override=True)
                return self._send(200, {'translate': bool(os.getenv('ROUTEAPI_API_KEY')),
                                        'model': os.getenv('TRANSLATE_MODEL', DEFAULT_MODEL)})
            self._send(404, {'error': 'not found'})

        def do_POST(self):
            if self.path != '/api/translate':
                return self._send(404, {'error': 'not found'})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                texts = [t for t in body.get('texts', []) if isinstance(t, str) and t.strip()]
            except (ValueError, TypeError):
                return self._send(400, {'error': 'body must be JSON {"texts": [...]}'})
            if len(texts) > MAX_TEXTS or any(len(t) > MAX_CHARS for t in texts):
                return self._send(400, {'error': f'at most {MAX_TEXTS} texts of {MAX_CHARS} chars'})
            try:
                tr = State.get()
            except Exception as exc:  # missing key, unknown model, network
                return self._send(502, {'error': f'{type(exc).__name__}: {exc}'})
            cached = sum(tr.key(t) in tr.cache for t in set(texts))
            result = tr.translate_many(texts)
            self._send(200, {'translations': result, 'cached': cached, 'translated': len(set(texts)) - cached,
                             'errors': tr.errors, 'model': tr.model})

        def log_message(self, fmt, *args):
            sys.stderr.write(f'{self.address_string()} {fmt % args}\n')

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Serve the review tool with on-demand translation')
    parser.add_argument('--html', default=ROOT / 'starter/results/review-test/review_tool.html', type=Path)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not args.html.exists():
        raise SystemExit(f'{args.html} not found; run src/build_review_tool.py first')
    server = HTTPServer(('127.0.0.1', args.port), make_handler(args.html.resolve()))
    print(f'Review tool: http://127.0.0.1:{args.port}  (Ctrl+C to stop)', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
