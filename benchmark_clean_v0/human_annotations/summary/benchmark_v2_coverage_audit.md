# Benchmark-v2 Coverage Audit

Generated: 2026-05-23

This document provides a quantitative coverage analysis of all human-annotated functional queries. Intended for the CoRL paper's benchmark section / appendix.

---

## 1. Query Type Distribution

All 173 queries across both files are `query_type: "functional"`.

| File | functional | spatial | mixed |
|---|---|---|---|
| `functional_queries_v1.jsonl` | 133 | 0 | 0 |
| `long_range_stress_queries_v1.jsonl` | 40 | 0 | 0 |

---

## 2. Scene Distribution

### functional_queries_v1 (6 scenes)

| Scene | Queries |
|---|---|
| 420683 | 14 |
| 421013 | 14 |
| 421254 | 27 |
| 421380 | 32 |
| 421602 | 13 |
| 469011 | 33 |

### long_range_stress_queries_v1 (8 scenes)

| Scene | Queries |
|---|---|
| 421063 | 4 |
| 421380 | 8 |
| 422391 | 2 |
| 422813 | 4 |
| 460417 | 6 |
| 466192 | 2 |
| 466803 | 2 |
| 469011 | 12 |

Total unique scenes combined: **12**.

---

## 3. Target Label Distribution

### functional_queries_v1

| Target Label | Count | % |
|---|---|---|
| knob | 84 | 63.2% |
| handle | 30 | 22.6% |
| remote | 8 | 6.0% |
| electric outlet | 7 | 5.3% |
| light switch | 2 | 1.5% |
| faucet / handle | 1 | 0.8% |
| switch panel / electric outlet | 1 | 0.8% |

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

---

## 4. Anchor Label Distribution (functional_queries_v1)

| Anchor Label | Count |
|---|---|
| dresser / chest of drawers | 28 |
| television stand / cabinet | 27 |
| oven | 11 |
| kitchen cabinet | 11 |
| television | 8 |
| dresser / nightstand | 7 |
| chest of drawers / dresser | 6 |
| wardrobe | 6 |
| fridge | 5 |
| nightstand drawer | 4 |
| radiator | 3 |
| door | 3 |
| ceiling light | 3 |
| exhaust hood / ventilation fan | 3 |
| nightstand / dresser | 2 |
| cabinet | 1 |
| kitchen sink | 1 |
| cabinet / closet | 1 |
| dishwasher | 1 |
| lamp | 1 |
| window | 1 |

---

## 5. Same-Label Ambiguity (num_same_label_distractors)

### functional_queries_v1 histogram

| Distractors | Count | % |
|---|---|---|
| 0 | 6 | 4.5% |
| 1 | 14 | 10.5% |
| 2–4 | 4 | 3.0% |
| 5–9 | 30 | 22.6% |
| 10–19 | 79 | 59.4% |

`is_label_only_solvable`: 2 / 133 = 1.5% (nearly all queries require context beyond the target label).

### long_range_stress_queries_v1 histogram

| Distractors | Count |
|---|---|
| 0 | 9 |
| 1 | 12 |
| 2 | 5 |
| 5 | 1 |
| 14 | 8 |
| 18 | 5 |

---

## 6. Minimal Pair Coverage

28 pairs (56 queries) out of 133 main queries are part of minimal pairs (42.1%).

| `changed_factor` | Pairs |
|---|---|
| `spatial_qualifier` | 11 |
| `anchor_object` | 9 |
| `geometry_direction` | 7 |
| `functional_relation` | 1 |

By scene: 420683×2, 421013×2, 421254×3, 421380×12, 421602×2, 469011×7.

---

## 7. Long-Range Stress Slice (reference_necessity)

| `reference_necessity` | Count | % |
|---|---|---|
| strict | 20 | 50.0% |
| contextual | 20 | 50.0% |

All 40 use `long_range_pattern: "junction_2hop"` and `evidence_hop_count: 2`.

**Strict definition**: target node has ≥1 same-label distractor AND the distractor cannot be ruled out without the reference node (the anchor type or label alone is insufficient).

**Contextual definition**: reference node corroborates the answer but the anchor label alone could plausibly narrow it.

---

## 8. Geometry Coverage

| File | Target nodes with geometry | % |
|---|---|---|
| `functional_queries_v1.jsonl` | 133 / 133 | 100% |
| `long_range_stress_queries_v1.jsonl` | 40 / 40 | 100% |

All queries in both files have geometry-backed target nodes (bbox_center, bbox_min, bbox_max in `scenefun3d_node_geom.json`).

Note: geometry data covers 20 of 23 SceneFun3D scenes. All 12 scenes used by these queries are within the covered set.

---

## 9. Supporting-Edge and Evidence-Chain Coverage

| File | Has `supporting_edge_ids` | Has `evidence_chain` |
|---|---|---|
| `functional_queries_v1.jsonl` | 133 / 133 | 133 / 133 |
| `long_range_stress_queries_v1.jsonl` | 40 / 40 | 40 / 40 |

Every query in both files has verified edge IDs and written evidence chains.

---

## 10. Unsupported Evidence (Color / Material)

Color and material attributes are **not available** in the current scene graph metadata (`SceneFun3D.relations.json`, `scenefun3d_funrag_benchmark_enriched.json`). No queries in either file rely on color or material for disambiguation. This was a design constraint applied during annotation — all geometry cues use positional/geometric reasoning (higher/lower, leftmost/rightmost, etc.).

---

## 11. Difficulty-Tag Co-occurrence (functional_queries_v1)

| Tag combination | Count |
|---|---|
| `multi_anchor AND geometry_aware` | 43 |
| `geometry_aware` only (not multi_anchor) | 56 |
| `same_label_disambiguation` (all) | 119 / 133 = 89.5% |
| `functional_relation` | 58 / 133 = 43.6% |

The benchmark is heavily geometry-aware (74.4%) and almost entirely requires same-label disambiguation (89.5%), reflecting the SceneFun3D scenes' high node-label ambiguity.
