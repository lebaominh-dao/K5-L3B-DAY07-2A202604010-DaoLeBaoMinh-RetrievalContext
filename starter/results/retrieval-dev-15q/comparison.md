# Retrieval benchmark — dev

Strategy B chunks; metrics over 15 answerable questions; context = top-3 packed into 3000 chars; ranking depth 10.

| Method | Hit@1 | Evidence Hit@3 | Hit@10 | MRR@10 | Context Evidence | Filter | Median ms | Embedding $ | Miss @3 |
|---|---|---|---|---|---|---|---:|---:|---|
| dense | 10/15 | 13/15 | 15/15 | 0.8 | 13/15 | 2/2 | 721.8 | 0.000005 | D05, D09 |
| bm25 | 9/15 | 11/15 | 15/15 | 0.723 | 11/15 | 2/2 | 0.4 | 0.000000 | D02, D04, D09, D11 |
| tfidf | 7/15 | 10/15 | 15/15 | 0.635 | 10/15 | 2/2 | 0.5 | 0.000000 | D02, D04, D05, D09, D12 |
| hybrid | 9/15 | 14/15 | 15/15 | 0.758 | 14/15 | 2/2 | 709.5 | 0.000005 | D09 |
