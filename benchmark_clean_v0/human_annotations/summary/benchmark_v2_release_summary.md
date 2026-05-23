# Benchmark-v2 Release Summary

Generated: 2026-05-23

## Query Counts

| File | Queries |
|---|---|
| `functional_queries_v1.jsonl` | 133 |
| `pilot_20_queries.jsonl` | 20 |
| `minimal_pairs_v1.jsonl` | 28 pairs |
| `long_range_stress_queries_v1.jsonl` | 40 |
| **Total (functional + long-range)** | **173** |

Long-range stress breakdown:
- Strict `reference_necessity`: 20 / 40 = **50.0%**
- Contextual `reference_necessity`: 20 / 40 = 50.0%

## Validator Status

| File | Queries | Result |
|---|---|---|
| `pilot_20_queries.jsonl` | 20 | **PASS** (0 error, 0 warning) |
| `functional_queries_v1.jsonl` | 133 | **PASS** (0 error, 0 warning) |
| `long_range_stress_queries_v1.jsonl` | 40 | **PASS** (0 error, 0 warning) |

## Slice / Difficulty-Tag Breakdown (functional_queries_v1)

| Tag | Count | % of 133 |
|---|---|---|
| `same_label_disambiguation` | 119 | 89.5% |
| `geometry_aware` | 99 | 74.4% |
| `functional_relation` | 58 | 43.6% |
| `minimal_pair` | 56 | 42.1% |
| `multi_anchor` | 51 | 38.3% |
| `endpoint_ambiguity` | 21 | 15.8% |
| `hard_negative` | 15 | 11.3% |
| `simple_functional` | 7 | 5.3% |

Cross-tag: `multi_anchor AND geometry_aware` co-occurrence: 43 queries; `geometry_aware` only: 56.

`is_label_only_solvable`: 2 / 133 = 1.5%.

## Minimal Pairs Breakdown

| `changed_factor` | Pairs |
|---|---|
| `spatial_qualifier` | 11 |
| `anchor_object` | 9 |
| `geometry_direction` | 7 |
| `functional_relation` | 1 |
| **Total** | **28** |

## Scene Coverage

### functional_queries_v1 (6 scenes)

| Scene | Queries |
|---|---|
| 420683 | 14 |
| 421013 | 14 |
| 421254 | 27 |
| 421380 | 32 |
| 421602 | 13 |
| 469011 | 33 |

### long_range_stress_queries_v1 (8 scenes — 6 new in Phase 4)

| Scene | Queries | New in Phase 4? |
|---|---|---|
| 421063 | 4 | Yes |
| 421380 | 8 | No (shared with main) |
| 422391 | 2 | Yes |
| 422813 | 4 | Yes |
| 460417 | 6 | Yes |
| 466192 | 2 | Yes |
| 466803 | 2 | Yes |
| 469011 | 12 | No (shared with main) |

**Total unique scenes across both files: 12**
`420683, 421013, 421063, 421254, 421380, 421602, 422391, 422813, 460417, 466192, 466803, 469011`

## Target Label Distribution

### functional_queries_v1

| Target Label | Count |
|---|---|
| knob | 84 |
| handle | 30 |
| remote | 8 |
| electric outlet | 7 |
| light switch | 2 |
| faucet / handle | 1 |
| switch panel / electric outlet | 1 |

### long_range_stress_queries_v1

| Target Label | Count |
|---|---|
| knob | 15 |
| handle | 6 |
| button / knob | 5 |
| electric outlet | 3 |
| knob / button | 2 |
| faucet / handle | 2 |
| handle / faucet | 2 |
| button | 1 |
| electric outlet / power strip | 1 |
| faucet / knob / handle | 1 |
| power strip | 1 |
| remote | 1 |

## Supporting-Edge Coverage

- `functional_queries_v1.jsonl`: 133 / 133 have `supporting_edge_ids` (100%)
- `long_range_stress_queries_v1.jsonl`: 40 / 40 have `supporting_edge_ids` (100%) — each has exactly 2 edges (target→anchor + reference→anchor)

## What Is New vs Benchmark-v1 (pre-Phase 3)

**Phase 3 additions (2026-05-20):**
- Expanded `functional_queries_v1.jsonl` with minimal-pair and hard-slice queries
- New file `minimal_pairs_v1.jsonl`: 28 contrastive pairs across 4 changed-factor classes
- Updated `hard_slice_summary_v1.json`

**Phase 4 additions (2026-05-23):**
- New file `long_range_stress_queries_v1.jsonl`: 40 long-range `junction_2hop` queries
- 6 new scenes added (421063, 422391, 422813, 460417, 466192, 466803)
- 20/40 strict `reference_necessity` (50.0%)

## Robot Trials Sidecar (Step 6–8)

| File | Rows |
|---|---|
| `robot_trials/robot_execution_sidecar_v1.jsonl` | 192 (all execution_feasible=True, 179 actionable) |
| `robot_trials/robot_trial_manifest_v1.jsonl` | 25 selected demo trials (from 133 main queries) |

Manifest selection: top-25 by `num_same_label_distractors`, max 5/scene, all 3 action types covered. `route_expected=verifier` for all 25 (none are label-only solvable).

## Classification Note

`long_range_stress_queries_v1.jsonl` is an **auxiliary stress slice** — it is NOT merged into the main test split without Mingqian's explicit approval. The robot trials sidecar (under `robot_trials/`) is execution metadata only, not a query benchmark.
