# Retrieval benchmark — dev

Strategy B chunks; metrics over 25 answerable questions; context = top-3 packed into 3000 chars; ranking depth 10.

| Method | Hit@1 | Evidence Hit@3 | Hit@10 | MRR@10 | Context Evidence | Filter | Median ms | Embedding $ | Miss @3 |
|---|---|---|---|---|---|---|---:|---:|---|
| dense | 17/25 | 22/25 | 25/25 | 0.799 | 22/25 | 2/2 | 757.8 | 0.000011 | D05, D09, D17 |
| bm25 | 18/25 | 21/25 | 25/25 | 0.814 | 21/25 | 2/2 | 0.4 | 0.000000 | D02, D04, D09, D11 |
| tfidf | 14/25 | 20/25 | 25/25 | 0.714 | 20/25 | 2/2 | 0.5 | 0.000000 | D02, D04, D05, D09, D12 |
| hybrid | 17/25 | 24/25 | 25/25 | 0.815 | 24/25 | 2/2 | 735.7 | 0.000011 | D09 |
