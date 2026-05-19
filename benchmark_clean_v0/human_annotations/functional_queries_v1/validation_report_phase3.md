## Phase 3 Validation Report -- 2026-05-19 13:45 UTC

Input files:
  - minimal_pairs_v1.jsonl (28 pairs)
  - minimal_pair_queries_v1.jsonl: not present (mining yielded enough pairs)

Query pool size (pilot + main + supplemental): 153

Pair validator (C14-C18):
  PASS (no errors): 28 / 28
  FAIL (>=1 error): 0
  WARN only:        0

changed_factor distribution:
  anchor_object: 9
  functional_relation: 1
  geometry_direction: 7
  spatial_qualifier: 11

scene distribution:
  420683: 2
  421013: 2
  421254: 3
  421380: 12
  421602: 2
  469011: 7

pair_evidence_used distribution:
  anchor_identity: 9
  functional_edge: 3
  geometry_x_axis: 9
  geometry_z_axis: 9

