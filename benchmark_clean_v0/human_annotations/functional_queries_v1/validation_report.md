## Validation Report — 2026-05-14 22:41

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
  geometry_aware: 3
  hard_negative: 2
  same_label_disambiguation: 5
  simple_functional: 4

Phase 1 category distribution (TASK_PLAN Section 8 requires 10/5/3/2):
  local_functional: 10 (expected 10) [OK]
  same_or_endpoint: 5 (expected 5) [OK]
  geometry_aware: 3 (expected 3) [OK]
  hard_negative: 2 (expected 2) [OK]