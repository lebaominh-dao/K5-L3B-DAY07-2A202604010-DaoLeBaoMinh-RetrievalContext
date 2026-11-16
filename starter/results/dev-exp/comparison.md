## Per configuration

| Config | Settings | Runs | Context evidence (mean) | Cited evidence (mean) | Abstain ok (min) | False abstain (max) | Errors | Searches/case | Median s | Tokens/case | $/case |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | hybrid, top-3, 4000 chars, effort medium | 2 | 14.0/15 | 14.0/15 | 3/3 | 1/15 | 0 | 1.78 | 4.70 | 4351 | 0.00058 |
| C1 | hybrid, top-5, 6000 chars, effort medium | 2 | 15.0/15 | 15.0/15 | 3/3 | 0/15 | 0 | 1.58 | 4.95 | 4578 | 0.00060 |
| C2 | hybrid, top-3, 4000 chars, effort low | 2 | 14.0/15 | 14.0/15 | 3/3 | 1/15 | 0 | 1.47 | 4.58 | 3777 | 0.00050 |
| C3 | dense, top-3, 4000 chars, effort medium | 2 | 14.5/15 | 14.5/15 | 3/3 | 1/15 | 0 | 1.67 | 4.67 | 4067 | 0.00054 |

## Per run

| Run | Context evidence | Cited evidence | Abstain ok | False abstain | Errors | Searches/case | Median s | $/case | Context missing | False-abstain ids | No-evidence answered |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0-r1 | 14/15 | 14/15 | 3/3 | 0/15 | 0 | 1.72 | 4.22 | 0.00056 | D09 | - | - |
| A0-r2 | 14/15 | 14/15 | 3/3 | 1/15 | 0 | 1.83 | 5.18 | 0.00059 | D09 | D09 | - |
| C1-r1 | 15/15 | 15/15 | 3/3 | 0/15 | 0 | 1.67 | 4.89 | 0.00061 | - | - | - |
| C1-r2 | 15/15 | 15/15 | 3/3 | 0/15 | 0 | 1.50 | 5.0 | 0.00058 | - | - | - |
| C2-r1 | 14/15 | 14/15 | 3/3 | 0/15 | 0 | 1.50 | 4.36 | 0.00052 | D09 | - | - |
| C2-r2 | 14/15 | 14/15 | 3/3 | 1/15 | 0 | 1.44 | 4.79 | 0.00049 | D09 | D09 | - |
| C3-r1 | 14/15 | 14/15 | 3/3 | 1/15 | 0 | 1.78 | 4.64 | 0.00057 | D09 | D09 | - |
| C3-r2 | 15/15 | 15/15 | 3/3 | 0/15 | 0 | 1.56 | 4.71 | 0.00051 | - | - | - |
