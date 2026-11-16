"""English -> Vietnamese translation for the review tool (RouteAPI, OpenAI-compatible).

Translations only help a Vietnamese reader; labels must still be judged against
the English original. Results are cached on disk by (model, text) so re-building
the tool does not pay twice. Failures are reported per text, never invented.

Env: ROUTEAPI_API_KEY (sk-...), optional ROUTEAPI_BASE_URL, TRANSLATE_MODEL.
"""
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_BASE_URL = 'https://api.routeapi.ai/v1'
DEFAULT_MODEL = 'deepseek-v4.1-flash'
SYSTEM_PROMPT = (
    'Translate the user text from English to Vietnamese for a reader grading answers about a psychology '
    'textbook. Rules: output only the translation; keep every bracketed id such as '
    '[B:psych2e-ch6:p203:c001] or [S1] exactly as written; keep names, years and numbers unchanged; on the '
    'first use of a psychology term, add the English term in parentheses, e.g. "điều kiện hóa cổ điển '
    '(classical conditioning)"; do not add, remove or explain content.'
)


class Translator:
    def __init__(self, cache_path, model=None, base_url=None, api_key=None, workers=6):
        from openai import OpenAI
        self.model = model or os.getenv('TRANSLATE_MODEL', DEFAULT_MODEL)
        key = api_key or os.getenv('ROUTEAPI_API_KEY')
        if not key:
            raise RuntimeError('ROUTEAPI_API_KEY is empty in .env')
        self.client = OpenAI(api_key=key, base_url=base_url or os.getenv('ROUTEAPI_BASE_URL', DEFAULT_BASE_URL))
        self.cache_path = Path(cache_path)
        self.cache = json.loads(self.cache_path.read_text(encoding='utf-8')) if self.cache_path.exists() else {}
        self.workers = workers
        self.tokens = {'prompt': 0, 'completion': 0}

    def key(self, text):
        return hashlib.sha1(f'{self.model}\n{text}'.encode('utf-8')).hexdigest()

    def check_model(self):
        """Fail early if the model id is not served for this key."""
        ids = [m.id for m in self.client.models.list()]
        if self.model not in ids:
            close = [i for i in ids if 'deepseek' in i.lower()]
            raise RuntimeError(f'model {self.model!r} not available; deepseek models for this key: {close}')

    def _call(self, text):
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': text}])
        if resp.usage:
            self.tokens['prompt'] += resp.usage.prompt_tokens
            self.tokens['completion'] += resp.usage.completion_tokens
        out = (resp.choices[0].message.content or '').strip()
        if not out:
            raise RuntimeError('empty translation')
        return out

    def translate_many(self, texts):
        """Return {text: translation or None}; None means the call failed (reported in `errors`)."""
        todo = [t for t in dict.fromkeys(texts) if t and self.key(t) not in self.cache]
        self.errors = {}

        def work(text):
            try:
                return text, self._call(text), None
            except Exception as exc:  # report, do not fabricate
                return text, None, f'{type(exc).__name__}: {exc}'

        with ThreadPoolExecutor(self.workers) as pool:
            for text, out, err in pool.map(work, todo):
                if err:
                    self.errors[text[:60]] = err
                else:
                    self.cache[self.key(text)] = out
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        return {t: self.cache.get(self.key(t)) for t in texts if t}
