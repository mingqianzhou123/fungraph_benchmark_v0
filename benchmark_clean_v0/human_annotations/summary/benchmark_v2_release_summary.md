# Benchmark-v2 Release Summary

Generated: 2026-05-24

## Query Counts

| File | Queries |
|---|---|
| `functional_queries_v1.jsonl` | 133 |
| `pilot_20_queries.jsonl` | 20 |
| `minimal_pairs_v1.jsonl` | 28 pairs |
| `long_range_stress_queries_v1.jsonl` | 50 |
| **Total (functional + long-range)** | **183** |

Long-range stress breakdown:
- Strict `reference_necessity`: 26 / 50 = **52.0%**
- Contextual `reference_necessity`: 24 / 50 = 48.0%

## Validator Status

| File | Queries | Result |
|---|---|---|
| `pilot_20_queries.jsonl` | 20 | **PASS** (0 error, 0 warning) |
| `functional_queries_v1.jsonl` | 133 | **PASS** (0 error, 0 warning) |
| `long_range_stress_queries_v1.jsonl` | 50 | **PASS** (0 error, 0 warning) |

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

### long_range_stress_queries_v1 (11 scenes — 6 new in Phase 4, 3 new in Phase 4b)

| Scene | Queries | Status |
|---|---|---|
| 421063 | 4 | New in Phase 4 |
| 421254 | 4 | New in Phase 4b |
| 421267 | 3 | New in Phase 4b |
| 421380 | 8 | Shared with main |
| 422007 | 3 | New in Phase 4b |
| 422391 | 2 | New in Phase 4 |
| 422813 | 4 | New in Phase 4 |
| 460417 | 6 | New in Phase 4 |
| 466192 | 2 | New in Phase 4 |
| 466803 | 2 | New in Phase 4 |
| 469011 | 12 | Shared with main |

**Total unique scenes across both files: 14**
`420683, 421013, 421063, 421254, 421267, 421380, 421602, 422007, 422391, 422813, 460417, 466192, 466803, 469011`

Note: scene 421254 appears in both `functional_queries_v1.jsonl` (27 queries) and `long_range_stress_queries_v1.jsonl` (4 queries).

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
| knob | 22 |
| handle | 9 |
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
- `long_range_stress_queries_v1.jsonl`: 50 / 50 have `supporting_edge_ids` (100%) — each has exactly 2 edges (target→anchor + reference→anchor)

## What Is New vs Benchmark-v1 (pre-Phase 3)

**Phase 3 additions (2026-05-20):**
- Expanded `functional_queries_v1.jsonl` with minimal-pair and hard-slice queries
- New file `minimal_pairs_v1.jsonl`: 28 contrastive pairs across 4 changed-factor classes
- Updated `hard_slice_summary_v1.json`

**Phase 4 additions (2026-05-23):**

- New file `long_range_stress_queries_v1.jsonl`: initial 40 long-range `junction_2hop` queries
- 6 new scenes added (421063, 422391, 422813, 460417, 466192, 466803)
- 20/40 strict `reference_necessity` (50.0%)

**Phase 4b additions (2026-05-24):**

- Expanded `long_range_stress_queries_v1.jsonl` from 40 → 50 queries
- 3 new scenes added (421254, 421267, 422007) — dresser/cabinet with handle targets
- Reduced knob concentration (knob share 40% → 44% of long-range; handle share 15% → 18%)
- Reduced scene concentration: top-3 scenes (421380/469011/460417) now 52% vs 65% before
- strict now 26/50 = 52.0% (up from 50.0%)

## Robot Trials Sidecar (Step 6–8)

| File | Rows |
|---|---|
| `robot_trials/robot_execution_sidecar_v1.jsonl` | 192 (all execution_feasible=True, 179 actionable) |
| `robot_trials/robot_trial_manifest_v1.jsonl` | 25 selected demo trials (from 133 main queries) |

Manifest selection: top-25 by `num_same_label_distractors`, max 5/scene, all 3 action types covered. `route_expected=funrag_prior` for all 25. This field records the baseline route used in the current manifest, not an oracle/verifier recommendation.

## Classification Note

`long_range_stress_queries_v1.jsonl` is an **auxiliary stress slice** — it is NOT merged into the main test split without Mingqian's explicit approval. The robot trials sidecar (under `robot_trials/`) is execution metadata only, not a query benchmark.
