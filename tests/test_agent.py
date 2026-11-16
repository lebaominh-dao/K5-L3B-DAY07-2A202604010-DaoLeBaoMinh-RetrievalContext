"""Agent loop checks with a scripted fake client; they test control flow, not model quality."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from agent import Agent
from run_agent import score

C1 = {'id': 'c1', 'text': 'Extinction is the decrease in the conditioned response.', 'source_id': 'ch6',
      'source': 'b.pdf', 'page': 200, 'metadata': {'chapter': 6}}
C2 = {'id': 'c2', 'text': 'Spontaneous recovery is the return of a response.', 'source_id': 'ch6',
      'source': 'b.pdf', 'page': 201, 'metadata': {'chapter': 6}}


def search(query, id='t1'):
    return NS(type='tool_use', id=id, name='search_corpus', input={'query': query})


def submit(status, answer, citations, id='t9'):
    return NS(type='tool_use', id=id, name='submit_answer',
              input={'status': status, 'answer': answer, 'citations': citations})


def reply(*blocks, stop='tool_use'):
    return NS(content=list(blocks), stop_reason=stop,
              usage=NS(input_tokens=100, output_tokens=20, cache_creation_input_tokens=0, cache_read_input_tokens=0))


class FakeClient:
    def __init__(self, replies):
        self.replies, self.requests = iter(replies), []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append({**kwargs, 'messages': list(kwargs['messages'])})
        r = next(self.replies)
        if isinstance(r, Exception):
            raise r
        return r


class FakeRetriever:
    method = 'fake'

    def __init__(self, *batches):
        self.batches, self.calls = list(batches), []

    def search(self, query, *, filters=None, top_k=3):
        self.calls.append((query, filters, top_k))
        rows = self.batches.pop(0) if self.batches else []
        return [{**c, 'score': 0.5, 'rank': i} for i, c in enumerate(rows, 1)]


class AgentTests(unittest.TestCase):
    def test_search_then_cited_answer(self):
        client = FakeClient([reply(search('extinction')),
                             reply(submit('answered', 'It decreases the response [S1].', ['S1']))])
        retriever = FakeRetriever([C1])
        t = Agent(client, retriever).run('What is extinction?', filters={'chapter': 6}, query_id='q')
        self.assertEqual((t['status'], t['citations'], t['n_searches']), ('answered', ['c1'], 1))
        self.assertEqual(retriever.calls, [('extinction', {'chapter': 6}, 3)])  # filter from input, not model
        tool_result = client.requests[1]['messages'][-1]['content'][0]
        self.assertIn('[S1]', tool_result['content'])
        self.assertEqual(t['answer'], 'It decreases the response [c1].')  # labels mapped back to chunk ids
        self.assertEqual(t['usage']['input'], 200)

    def test_citation_outside_context_is_dropped_and_answer_without_valid_citation_abstains(self):
        client = FakeClient([reply(search('x')), reply(submit('answered', 'Claim [S2] and [S1].', ['S2', 'S1']))])
        t = Agent(client, FakeRetriever([C1])).run('q')
        self.assertEqual(t['citations'], ['c1'])
        client = FakeClient([reply(search('x')), reply(submit('answered', 'Claim [S2].', ['S2']))])
        t = Agent(client, FakeRetriever([C1])).run('q')
        self.assertEqual((t['status'], t['citations']), ('abstain', []))
        self.assertEqual(t['events'][-1]['event'], 'invalid_or_missing_citations')

    def test_citations_come_from_labels_in_text_and_leaked_markup_is_removed(self):
        # D08 on dev: citations leaked into the answer string, the citations array was empty.
        leaked = 'Variable ratio [S1].</answer>\n<parameter name="citations">["S1"]'
        client = FakeClient([reply(search('x')), reply(submit('answered', leaked, []))])
        t = Agent(client, FakeRetriever([C1])).run('q')
        self.assertEqual((t['status'], t['citations'], t['answer']), ('answered', ['c1'], 'Variable ratio [c1].'))
        self.assertIn('leaked_markup_removed', [e['event'] for e in t['events']])

    def test_listed_citation_without_label_in_text_does_not_count(self):
        client = FakeClient([reply(search('x')), reply(submit('answered', 'No label here.', ['S1']))])
        self.assertEqual(Agent(client, FakeRetriever([C1])).run('q')['status'], 'abstain')

    def test_search_limit_returns_error_result_and_model_must_finish(self):
        client = FakeClient([reply(search('a')), reply(search('b')),
                             reply(submit('abstain', 'Not covered.', []))])
        retriever = FakeRetriever([C1], [C2])
        t = Agent(client, retriever, max_searches=1).run('q')
        self.assertEqual(len(retriever.calls), 1)
        self.assertEqual(t['status'], 'abstain')
        limit_result = client.requests[2]['messages'][-1]['content'][0]
        self.assertTrue(limit_result['is_error'])

    def test_budget_and_dedup_across_searches(self):
        client = FakeClient([reply(search('a')), reply(search('b')), reply(submit('answered', 'A [S1].', ['S1']))])
        t = Agent(client, FakeRetriever([C1], [C1, C2]), budget=len(C1['text']) + 60).run('q')
        second = [e for e in t['events'] if e['event'] == 'search'][1]
        self.assertEqual(second['already_in_context'], ['c1'])
        self.assertEqual(second['omitted_by_budget'], 1)  # c2 did not fit
        self.assertEqual(t['context_ids'], ['c1'])

    def test_text_only_reply_gets_one_reminder_then_error(self):
        text = NS(type='text', text='I think...')
        t = Agent(FakeClient([reply(text, stop='end_turn'), reply(text, stop='end_turn')]), FakeRetriever()).run('q')
        self.assertEqual(t['status'], 'error')
        self.assertIn('nudge', [e['event'] for e in t['events']])

    def test_provider_error_and_refusal_are_reported_not_faked(self):
        t = Agent(FakeClient([RuntimeError('boom')]), FakeRetriever()).run('q')
        self.assertEqual((t['status'], t['answer']), ('error', ''))
        t = Agent(FakeClient([reply(stop='refusal')]), FakeRetriever()).run('q')
        self.assertEqual(t['error'], 'stop_reason=refusal')

    def test_score_uses_context_and_citations(self):
        cases = [{'id': 'a', 'answerable': True}, {'id': 'n', 'answerable': False}]
        gold = {'a': [{'source_id': 'ch6', 'page': 201, 'evidence': 'Spontaneous recovery'}]}
        base = {'n_searches': 1, 'elapsed_s': 1.0, 'cost_usd': 0.0,
                'usage': {'input': 1, 'output': 1, 'cache_write': 0, 'cache_read': 0}}
        traces = [{**base, 'query_id': 'a', 'status': 'answered', 'context_ids': ['c1', 'c2'], 'citations': ['c1']},
                  {**base, 'query_id': 'n', 'status': 'abstain', 'context_ids': ['c1'], 'citations': []}]
        s = score(traces, cases, gold, {'c1': C1, 'c2': C2})
        self.assertEqual(s['context_evidence_rate']['n'], 1)
        self.assertEqual(s['cited_evidence_auto']['n'], 0)  # cited c1, evidence is in c2
        self.assertEqual((s['abstention']['n'], s['false_abstention']['n']), (1, 0))


if __name__ == '__main__':
    unittest.main()
