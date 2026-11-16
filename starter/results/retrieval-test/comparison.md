# Retrieval benchmark — test

Strategy B chunks; metrics over 5 answerable questions; context = top-3 packed into 3000 chars; ranking depth 10.

| Method | Hit@1 | Evidence Hit@3 | Hit@10 | MRR@10 | Context Evidence | Filter | Median ms | Embedding $ | Miss @3 |
|---|---|---|---|---|---|---|---:|---:|---|
| dense | 4/5 | 5/5 | 5/5 | 0.9 | 5/5 | 2/2 | 735.4 | 0.000003 | - |
| bm25 | 5/5 | 5/5 | 5/5 | 1.0 | 5/5 | 2/2 | 0.4 | 0.000000 | - |
| tfidf | 4/5 | 4/5 | 5/5 | 0.825 | 4/5 | 2/2 | 0.5 | 0.000000 | T19 |
| hybrid | 5/5 | 5/5 | 5/5 | 1.0 | 5/5 | 2/2 | 712.4 | 0.000003 | - |
