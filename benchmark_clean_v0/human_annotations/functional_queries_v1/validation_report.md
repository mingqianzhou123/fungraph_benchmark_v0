## Validation Report — 2026-05-15 21:58

Input file: pilot_20_queries.jsonl
Total queries checked: 20

Results:
  PASS (no errors): 20
  FAIL (≥1 error):  0
  WARN only:        0

Scene distribution:
  420683: 4 queries
  421013: 4 queries
  421254: 3 queries
  421380: 2 queries
  421602: 3 queries
  469011: 4 queries

Difficulty tags distribution:
  endpoint_ambiguity: 3
  functional_relation: 13
  geometry_aware: 5
  hard_negative: 2
  same_label_disambiguation: 8
  simple_functional: 3

Phase 1 category distribution (TASK_PLAN Section 8 requires 10/5/3/2):
  local_functional: 7 (expected 10) [MISMATCH]
  same_or_endpoint: 6 (expected 5) [MISMATCH]
  geometry_aware: 5 (expected 3) [MISMATCH]
  hard_negative: 2 (expected 2) [OK]