## Per configuration

| Config | Settings | Runs | Context evidence (mean) | Cited evidence (mean) | Abstain ok (min) | False abstain (max) | Errors | Searches/case | Median s | Tokens/case | $/case |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | hybrid, top-3, 4000 chars, effort medium | 2 | 23.0/25 | 23.0/25 | 6/6 | 1/25 | 0 | 1.79 | 4.89 | 4145 | 0.00056 |
| C1 | hybrid, top-5, 6000 chars, effort medium | 2 | 25.0/25 | 25.0/25 | 6/6 | 0/25 | 0 | 1.65 | 4.79 | 4556 | 0.00060 |
| C2 | hybrid, top-3, 4000 chars, effort low | 2 | 22.5/25 | 22.5/25 | 6/6 | 0/25 | 0 | 1.45 | 4.67 | 3584 | 0.00049 |
| C3 | dense, top-3, 4000 chars, effort medium | 2 | 22.0/25 | 22.0/25 | 6/6 | 1/25 | 0 | 1.82 | 5.01 | 4309 | 0.00058 |

## Per run

| Run | Context evidence | Cited evidence | Abstain ok | False abstain | Errors | Searches/case | Median s | $/case | Context missing | False-abstain ids | No-evidence answered |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0-r1 | 23/25 | 23/25 | 6/6 | 1/25 | 0 | 1.81 | 4.98 | 0.00058 | D09, D17 | D09 | - |
| A0-r2 | 23/25 | 23/25 | 6/6 | 0/25 | 0 | 1.77 | 4.8 | 0.00055 | D09, D17 | - | - |
| C1-r1 | 25/25 | 25/25 | 6/6 | 0/25 | 0 | 1.68 | 4.72 | 0.00059 | - | - | - |
| C1-r2 | 25/25 | 25/25 | 6/6 | 0/25 | 0 | 1.61 | 4.87 | 0.00060 | - | - | - |
| C2-r1 | 23/25 | 23/25 | 6/6 | 0/25 | 0 | 1.48 | 4.69 | 0.00050 | D09, D17 | - | - |
| C2-r2 | 22/25 | 22/25 | 6/6 | 0/25 | 0 | 1.42 | 4.64 | 0.00048 | D09, D17, D19 | - | - |
| C3-r1 | 22/25 | 22/25 | 6/6 | 1/25 | 0 | 1.77 | 4.72 | 0.00058 | D09, D17, D19 | D09 | - |
| C3-r2 | 22/25 | 22/25 | 6/6 | 1/25 | 0 | 1.87 | 5.3 | 0.00058 | D09, D17, D19 | D09 | - |
