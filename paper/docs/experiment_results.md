
### Main Benchmark Summary Table
| Variant | Tasks | Trials | Hard Success Rate | Judge Success Rate | Judge Score | Latency (s) | Tool Calls |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| full | 20 | 60 | 88.3% ± 6.7% | 10.0% ± 9.2% | 46.9 ± 7.6 | 363.4 | 5.5 |
| plan_only | 20 | 60 | 100.0% ± 0.0% | 13.3% ± 10.0% | 56.5 ± 5.4 | 237.6 | 6.0 |
| react_baseline | 20 | 60 | 6.7% ± 5.8% | 1.7% ± 2.5% | 4.1 ± 3.9 | 114.5 | 0.7 |
| review_revise_baseline | 1 | 1 | 100.0% | 0.0% | 50.0 | 520.3 | 5.0 |
| sop_baseline | 20 | 60 | 46.7% ± 15.0% | 5.0% ± 5.0% | 23.0 ± 7.9 | 547.3 | 0.5 |
| wo_evolution | 20 | 60 | 88.3% ± 8.3% | 18.3% ± 9.2% | 54.8 ± 7.4 | 369.5 | 5.6 |
| wo_memory | 20 | 60 | 90.0% ± 8.3% | 11.7% ± 9.2% | 51.6 ± 6.3 | 348.1 | 5.8 |
| wo_orchestration | 20 | 60 | 73.3% ± 13.3% | 28.3% ± 12.5% | 52.3 ± 10.7 | 439.6 | 11.7 |

### ReAct Recursion Limit Sensitivity Scan
| Limit | Hard SR | Judge SR | Score |
| :--- | :--- | :--- | :--- |
| 10 | 0.0% | 0.0% | N/A |
| 25 | 0.0% | 0.0% | N/A |
| 50 | 0.0% | 0.0% | N/A |
