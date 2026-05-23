# Plan: Benchmark-v2 Release Package

## Context

Phase 4 (long-range stress set) is complete with 30 queries all passing validation. Mingqian's feedback confirms the direction is correct but requires a full Benchmark-v2 release package before any further scattershot query additions. The goals are:

- **Freeze Benchmark-v2** as a stable, verifiable, auditable release (possibly used to re-run main experiments; otherwise an auxiliary stress-test release for the CoRL paper).
- **Increase strict reference_necessity** from 33.3% → ≥50% in long-range stress set.
- **Add a robot execution sidecar** for CoRL relevance (grounding → robot action target).

All work is append-only to sidecar directories. The frozen benchmark under `benchmark_clean_v0/queries/`, `graphs/`, `geometry/`, `annotations/`, `manifests/` is never touched.

---

## Current State (from exploration)

| File | Count | Validation |
|---|---|---|
| `long_range_stress_queries_v1.jsonl` | 30 queries | ALL PASS (C24–C29) |
| `functional_queries_v1.jsonl` | 133 queries | ALL PASS (C1–C23) |
| `minimal_pairs_v1.jsonl` | 28 pairs | ALL PASS |
| `pilot_20_queries.jsonl` | 20 queries | ALL PASS |

Long-range breakdown: 10 strict (33.3%) + 20 contextual (66.7%). All 30 use `junction_2hop` pattern. 8 scenes covered (6 new in Phase 4 + 421380 and 469011).

Summary dir: `benchmark_clean_v0/human_annotations/summary/` — CLAUDE.md + phase notes only. No benchmark_v2 files yet.

Robot trials dir: **does not exist**.

---

## Delivery Order (from Mingqian's feedback)

1. `long_range_stress_queries_v1.jsonl` → 40–50 queries, ≥50% strict
2. Validation reports → 0 error / 0 warning on all three files
3. `benchmark_v2_release_summary.md`
4. `benchmark_v2_changelog.md`
5. `benchmark_v2_coverage_audit.md`
6. `robot_execution_sidecar_v1.jsonl`
7. `robot_trial_manifest_v1.jsonl`
8. `robot_trial_readme.md`

Items 1–5 are highest priority. Items 6–8 are CoRL-relevance bonus, must not block freezing.

---

## Step 1 — Expand long_range_stress_queries_v1.jsonl

**Goal**: Grow from 30 → 40–50 queries with strict reference_necessity ≥50%.

**Math**: To hit 50% strict with 40 total queries: need 20 strict (add 10 more strict). With 50 total: need 25 strict (add 15 more strict from 20 additions). Target: **add 15–20 queries, all or mostly strict**.

**Approach**:
1. Read `scripts/phase4_junction_audit.csv` (exists from Phase 4 work) to identify unused junction candidates across the 20 geometry-covered scenes.
2. Also check the 12 scenes not yet used in Phase 4 (from 20 total minus 8 used). The agent noted 4 Phase 1-3 scenes had "zero viable junctions" but 12 others remain unexplored.
3. **Strict criteria**: A junction is strict if the target node has ≥2 same-label candidates in the scene — so the reference node is needed to disambiguate. Prefer junctions with `num_same_label_distractors ≥ 1` for the target.
4. Write new queries manually following the exact schema:
   - Required: `query_id` (lr_v1_000031...), `scene_id`, `query_text`, `query_type="functional"`, `target_node_id`, `anchor_node_id`, `supporting_edge_ids` (≥2), `difficulty_tags` (must include `long_range`), `is_long_range=true`, `evidence_chain`, `source="human_phase4"`, `target_label`, `anchor_label`, `shared_anchor_node_id`, `reference_node_id`, `reference_label`, `reference_relation`, `long_range_pattern`, `evidence_hop_count`, `reference_necessity`, `geometry_cues`, `num_same_label_distractors`, `is_label_only_solvable`, `notes`
5. Append to `long_range_stress_queries_v1.jsonl` (never mix into `functional_queries_v1.jsonl`).
6. Run validator immediately after each batch: `python scripts/validate_functional_queries.py long_range_stress_queries_v1.jsonl`

**Key constraint**: All current 30 queries are `junction_2hop` due to bipartite graph structure (true 3-hop chain is impossible). New queries will also be `junction_2hop`. Diversity comes from scene variety, target-type variety, and reference_necessity strictness.

**Files modified**: `long_range_stress_queries_v1.jsonl` (appended)

---

## Step 2 — Run Full Validation (0 error / 0 warning)

Run the validator on all three target files in sequence:

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\pilot_20_queries.jsonl

python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\functional_queries_v1.jsonl

python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\long_range_stress_queries_v1.jsonl
```

Requirements: 0 ERROR, 0 WARN. No duplicate `query_text`. No naked coordinates in `query_text`. Stable `query_id` sequence.

**Files written**: `validation_report.md` (overwritten by last run; save each intermediate report if needed)

---

## Step 3 — benchmark_v2_release_summary.md

**New file**: `benchmark_clean_v0/human_annotations/summary/benchmark_v2_release_summary.md`

Content (read counts from actual JSONL files and hard_slice_summary_v1.json):

```markdown
# Benchmark-v2 Release Summary

Generated: 2026-05-23

## Query Counts
- Total functional queries (functional_queries_v1.jsonl): 133
- New human-authored functional queries (Phase 1–3): 133
- Minimal pairs (minimal_pairs_v1.jsonl): 28
- Long-range stress queries (long_range_stress_queries_v1.jsonl): [N]
  - Strict reference_necessity: [S] ([S/N]%)
  - Contextual reference_necessity: [C] ([C/N]%)

## Slice Breakdown
- same_label_disambiguation: [count]
- geometry_aware: [count]
- functional_relation: [count]
- minimal_pair: [count]
- endpoint_ambiguity: [count]
- hard_negative: [count]
- simple_functional: [count]

## Scene Coverage
- functional_queries_v1: 6 scenes
- long_range_stress: 8+ scenes (6 new in Phase 4)
- Total unique scenes: [N]

## Target Label Distribution
[table from functional_queries_v1 and long_range_stress]

## Supporting-Edge Coverage
- Queries with supporting_edge_ids: [count] / [total]
- Queries with verified evidence_chain: [count]

## Validator Status
- pilot_20_queries.jsonl: PASS (0 error, 0 warning)
- functional_queries_v1.jsonl: PASS (0 error, 0 warning)
- long_range_stress_queries_v1.jsonl: PASS (0 error, 0 warning)

## What's New vs Benchmark-v1 (pre-Phase 3)
[Phase 3 + Phase 4 additions]
```

**All counts must be computed from the actual files** by reading them (not hardcoded).

---

## Step 4 — benchmark_v2_changelog.md

**New file**: `benchmark_clean_v0/human_annotations/summary/benchmark_v2_changelog.md`

Content:

```markdown
# Benchmark-v2 Changelog

## Phase 3 additions (2026-05-20)
Files added/modified:
- functional_queries_v1.jsonl: [N] new queries added (minimal pair expansion)
- minimal_pairs_v1.jsonl: 28 pairs
- functional_query_diagnostics_v1.jsonl: [...]
- hard_slice_summary_v1.json: updated
New scenes: none (all 6 Phase 1–3 scenes)
Classification: main functional extension

## Phase 4 additions (2026-05-23)
Files added:
- long_range_stress_queries_v1.jsonl: [N] long-range stress queries
New scenes: 421063, 422391, 422813, 460417, 466192, 466803 (6 new)
Classification: auxiliary stress slice — NOT in main test split

## What is NOT in main benchmark split
- long_range_stress_queries_v1.jsonl: remains separate until Mingqian approves merge
- All robot_trials/ files: execution sidecar only, not query benchmark
```

---

## Step 5 — benchmark_v2_coverage_audit.md

**New file**: `benchmark_clean_v0/human_annotations/summary/benchmark_v2_coverage_audit.md`

Content (all values computed from actual data files):

- Query type distribution (functional / spatial / mixed)
- Scene distribution (queries per scene)
- Target label distribution
- Anchor label distribution
- Same-label ambiguity counts (`num_same_label_distractors` histogram)
- Minimal pair count and `changed_factor` distribution
- Long-range stress count, strict/contextual split
- Geometry coverage (bbox available for target node)
- Target/anchor/supporting-edge coverage (% with valid IDs)
- Unsupported evidence (e.g. color/material fields unavailable in graph metadata)

This is intended to go directly into paper benchmark section or appendix.

---

## Step 6 — robot_execution_sidecar_v1.jsonl

**New file**: `benchmark_clean_v0/robot_trials/robot_execution_sidecar_v1.jsonl`

**Approach** (Python script, stdlib-only):
1. Read `benchmark_clean_v0/annotations/openfungraph/SceneFun3D.relations.json` → list all (scene_id, source_node_id, relation_type, target_node_id) tuples.
2. Read `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` → bbox_center, bbox_min, bbox_max per node.
3. Read `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` → node labels.
4. For each interactive source node (the one the robot acts on):
   - Compute `bbox_center_3d = [cx, cy, cz]` from geometry
   - Compute `bbox_extent_3d = [max_x-min_x, max_y-min_y, max_z-min_z]`
   - Set `interaction_point = bbox_center_3d` (best approximation without image data)
   - Map `relation_type` → `affordance_type` and `robot_action` using the rule table below
   - Determine `approach_axis` by object label heuristic (drawer/handle → "front"; knob/button/switch → "front"; ceiling-mounted → "top"; default → "unknown")
   - Set `execution_feasible = true` if geometry exists, else `false`
   - Set `safety_notes` based on object type

**Action mapping rules** (from Mingqian's feedback):
```
"pull to open or close" → affordance_type="pull", robot_action="pull_handle"
"pull to open or close a drawer" → affordance_type="pull", robot_action="pull_handle"
"press or rotate to control" → affordance_type="press", robot_action="press_or_rotate"
"rotate to adjust the setting" → affordance_type="rotate", robot_action="rotate_knob"
"rotate to adjust the temperature" → affordance_type="rotate", robot_action="rotate_knob"
"control" / "control, turn on or turn off" → affordance_type="press", robot_action="press_button"
"provide power" → affordance_type="none", robot_action="none" (diagnostic only)
default → affordance_type="none", robot_action="none"
```

**Output schema per row**:
```json
{
  "scene_id": "...",
  "node_id": "...",
  "node_label": "...",
  "bbox_center_3d": [x, y, z],
  "bbox_extent_3d": [dx, dy, dz],
  "interaction_point": [x, y, z],
  "approach_axis": "front|left|right|top|unknown",
  "affordance_type": "pull|press|rotate|grasp|point|none",
  "robot_action": "pull_handle|press_button|rotate_knob|point_at|navigate_to|none",
  "execution_feasible": true,
  "safety_notes": "..."
}
```

**Script location**: `benchmark_clean_v0/robot_trials/scripts/build_robot_execution_sidecar.py`

---

## Step 7 — robot_trial_manifest_v1.jsonl

**New file**: `benchmark_clean_v0/robot_trials/robot_trial_manifest_v1.jsonl`

Select 15–30 queries from `functional_queries_v1.jsonl` that meet all of:
- Target node has geometry (bbox exists in scenefun3d_node_geom.json)
- Target node appears in robot_execution_sidecar with `execution_feasible=true`
- Same-label distractor exists (`num_same_label_distractors ≥ 1`)
- Action is simple (press/pull/rotate)
- No color-dependency (query_text contains no color words)

**Output schema per row**:
```json
{
  "trial_id": "robot_trial_v1_000001",
  "query_id": "...",
  "scene_id": "...",
  "query_text": "...",
  "target_node_id": "...",
  "target_label": "...",
  "route_expected": "verifier",
  "robot_action": "...",
  "success_metric": "target_acc|reach_bbox|action_success",
  "why_robot_cares": "...",
  "failure_consequence": "..."
}
```

**Script**: `benchmark_clean_v0/robot_trials/scripts/build_robot_trial_manifest.py`

---

## Step 8 — robot_trial_readme.md

**New file**: `benchmark_clean_v0/robot_trials/robot_trial_readme.md`

Content:
- Purpose: lightweight sidecar connecting benchmark grounding results to robot action primitives
- What this is NOT: not a full multimodal pipeline, not CLIP/image features
- How to use: look up query → target_node_id → robot_execution_sidecar entry → get 3D target + action primitive
- Limitations: interaction_point is bbox_center approximation; approach_axis is heuristic; color/material fields unavailable
- File descriptions: what each file contains

---

## Files to Create / Modify

| File | Action | Priority |
|---|---|---|
| `human_annotations/functional_queries_v1/long_range_stress_queries_v1.jsonl` | Append 10–20 strict queries | P0 |
| `human_annotations/functional_queries_v1/validation_report.md` | Regenerated by validator | P0 |
| `human_annotations/summary/benchmark_v2_release_summary.md` | Create new | P0 |
| `human_annotations/summary/benchmark_v2_changelog.md` | Create new | P0 |
| `human_annotations/summary/benchmark_v2_coverage_audit.md` | Create new | P1 |
| `robot_trials/robot_execution_sidecar_v1.jsonl` | Create new | P2 |
| `robot_trials/robot_trial_manifest_v1.jsonl` | Create new | P2 |
| `robot_trials/robot_trial_readme.md` | Create new | P2 |
| `robot_trials/scripts/build_robot_execution_sidecar.py` | Create new | P2 |
| `robot_trials/scripts/build_robot_trial_manifest.py` | Create new | P2 |
| `human_annotations/functional_queries_v1/annotation_notes.md` | Append Phase 4 expansion + v2 release note | P0 |

**Never modify**: anything under `benchmark_clean_v0/queries/`, `graphs/`, `geometry/`, `annotations/`, `manifests/`, `multimodal_extension/`.

---

## Do NOT Do

- Full multimodal pipeline, CLIP features, image crop, segmentation mask alignment
- Modify frozen main benchmark files
- Mix long_range_stress queries into functional_queries_v1.jsonl (unless Mingqian approves)
- Write queries where target is unique and reference is only a contextual description (weak contextual cases)
- Guess color/material attributes

---

## Verification

After each step:
1. **Long-range expansion**: `python validate_functional_queries.py long_range_stress_queries_v1.jsonl` → 0 error, 0 warning; strict% ≥ 50%
2. **Summary files**: Review counts match actual JSONL line counts
3. **Robot sidecar**: All `execution_feasible=true` nodes must have geometry entries; `robot_action` never "none" for actionable relations
4. **Manifest**: All `query_id`s in manifest exist in functional_queries_v1.jsonl; all `target_node_id`s in robot_execution_sidecar

---

## DRAFT — Step 1 Expansion: Queries lr_v1_000031–lr_v1_000040

**Status: AWAITING USER REVIEW — do not execute until confirmed**

### Math check
| After adding | Total | Strict | % |
|---|---|---|---|
| Current | 30 | 10 | 33.3% |
| +10 new strict | **40** | **20** | **50.0% ✓** |

All 10 new queries are **strict**. No contextual queries added, to hit exactly 50%.

### Geometry verification (from `scenefun3d_node_geom.json`, z = vertical axis)

**Scene 421063** (bathroom: sink + bathtub):
| Node | Label | z |
|---|---|---|
| sink c4a12f33 | sink | 293.985 |
| bathtub b0e10097 | bathtub | 293.756 |
| sink faucet a54cd1df | faucet / handle | **294.050** (higher) |
| bathtub faucet 8c74ba89 | faucet / handle | 293.817 (lower) |
| sink button b0e7459d | button / knob | **293.859** (higher) |
| bathtub button 1e33ac6a | button / knob | 293.320 (lower) |

**Scene 422813** (bathroom: sink + bathtub):
| Node | Label | z |
|---|---|---|
| sink 649f5431 | bathroom sink | 275.182 |
| bathtub bb70dccc | bathtub | 274.628 |
| sink faucet b012412a | handle / faucet | **275.262** (higher) |
| bathtub faucet 381968b3 | handle / faucet | 275.024 (lower) |
| sink button 1deb7d86 | button / knob | **275.079** (higher) |
| bathtub button 8315a573 | button / knob | 274.515 (lower) |

→ Sink is consistently **higher z** than bathtub in both scenes. "Higher" = sink side, "lower" = bathtub side.

### Source pairs from phase4_junction_audit.csv (all are writable_score=1.0)

All 10 queries come from junctions already identified in the audit. The 3 source junction types:
- **469011 oven junction**: knob↔handle around oven anchor (5 audit rows, all used for knob-as-target in q001–q005; handle-as-target not yet written)
- **460417 WM junction, pair 4**: knob/button vs outlet 59552624 around WM anchor (audit row 50)
- **421063 sink junction** and **421063 bathtub junction**: button↔faucet (2 audit rows; used contextually in q021/q022 with anchor named; now written strictly without naming anchor)
- **422813 sink junction** and **422813 bathtub junction**: same structure (2 audit rows; used contextually in q023/q024)

---

### q031 — scene 469011, oven handle (ref = leftmost knob)

```json
{"query_id": "lr_v1_000031", "scene_id": "469011", "query_text": "Pull the handle that opens the door of the kitchen appliance whose settings are also adjusted by the leftmost rotating knob on its panel.", "query_type": "functional", "target_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454", "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552", "supporting_edge_ids": ["47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552", "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["handle --pull to open or close--> oven", "knob --rotate to adjust the setting--> oven"], "source": "human_phase4", "target_label": "handle", "anchor_label": "oven", "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552", "shared_anchor_label": "oven", "reference_node_id": "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8", "reference_label": "knob", "reference_relation": "rotate to adjust the setting", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": [], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 handles in scene (47d6518d oven, 2abcdace fridge). Fridge has no rotating-knob control; oven has 5. Reference 'leftmost rotating knob adjusts same appliance' -> oven -> handle 47d6518d. Reverse direction of q001–q005."}
```

---

### q032 — scene 469011, oven handle (ref = rightmost knob)

```json
{"query_id": "lr_v1_000032", "scene_id": "469011", "query_text": "Pull the handle that opens the door of the kitchen appliance whose settings are also regulated by the rightmost rotating knob on its panel.", "query_type": "functional", "target_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454", "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552", "supporting_edge_ids": ["47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552", "85f5f2f0-ef9b-4e32-a0de-cd8a7f54db4b|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["handle --pull to open or close--> oven", "knob --rotate to adjust the setting--> oven"], "source": "human_phase4", "target_label": "handle", "anchor_label": "oven", "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552", "shared_anchor_label": "oven", "reference_node_id": "85f5f2f0-ef9b-4e32-a0de-cd8a7f54db4b", "reference_label": "knob", "reference_relation": "rotate to adjust the setting", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": [], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: same logic as q031 but reference knob = rightmost (85f5f2f0, x=2.814). Different supporting_edge_ids. Query text differs from q031 ('rightmost' vs 'leftmost'). Both strictly require reference to rule out fridge handle."}
```

---

### q033 — scene 460417, WM knob/button (ref = dedicated outlet 59552624)

```json
{"query_id": "lr_v1_000033", "scene_id": "460417", "query_text": "Rotate the knob/button that adjusts the appliance which has a dedicated electric outlet supplying power exclusively to that one appliance.", "query_type": "functional", "target_node_id": "a6956e03-3809-409c-b16d-cee0ef3e1246", "anchor_node_id": "66ce5acd-9d4e-4b6b-af9e-fde601c66cb6", "supporting_edge_ids": ["a6956e03-3809-409c-b16d-cee0ef3e1246|rotate or press to adjust the setting|66ce5acd-9d4e-4b6b-af9e-fde601c66cb6", "59552624-a2f6-4e2b-9a25-9d62b675cada|provide power|66ce5acd-9d4e-4b6b-af9e-fde601c66cb6"], "difficulty_tags": ["long_range", "functional_relation", "hard_negative"], "is_long_range": true, "evidence_chain": ["knob / button --rotate or press to adjust the setting--> washing machine", "electric outlet --provide power--> washing machine"], "source": "human_phase4", "target_label": "knob / button", "anchor_label": "washing machine", "shared_anchor_node_id": "66ce5acd-9d4e-4b6b-af9e-fde601c66cb6", "shared_anchor_label": "washing machine", "reference_node_id": "59552624-a2f6-4e2b-9a25-9d62b675cada", "reference_label": "electric outlet", "reference_relation": "provide power", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": [], "num_same_label_distractors": 0, "is_label_only_solvable": false, "notes": "Strict: 2 rotate-adjust knob controls in scene (a6956e03 WM, f845e4b3 dryer). Outlet 59552624 powers WM only; outlet 9f510124 powers WM+dryer. 'Dedicated outlet supplying only one appliance' -> WM -> knob a6956e03. Dryer's outlet (9f510124) is shared. Hard-negative: dryer also has a knob, but no dedicated outlet."}
```

---

### q034 — scene 421063, sink faucet/handle (ref = higher-positioned sink button/knob)

Strict logic: 2 faucets in scene (sink faucet a54cd1df z=294.050, bathtub faucet 8c74ba89 z=293.817). 2 buttons in scene (sink button b0e7459d z=293.859 = HIGHER, bathtub button 1e33ac6a z=293.320 = LOWER). Without reference: "faucet in fixture that also has a button" → 2 faucets (both fixtures have buttons). With reference "higher button controls same fixture" → higher button (b0e7459d) → sink → sink faucet a54cd1df. STRICT.

```json
{"query_id": "lr_v1_000034", "scene_id": "421063", "query_text": "In this bathroom, which faucet/handle controls water flow for the fixture that also has the higher-mounted button/knob?", "query_type": "functional", "target_node_id": "a54cd1df-50ca-4ca9-b3c0-136fe9224393", "anchor_node_id": "c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "supporting_edge_ids": ["a54cd1df-50ca-4ca9-b3c0-136fe9224393|control the water flow|c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "b0e7459d-07a3-41a9-af61-18f99260e1d3|press or rotate to control the water flow|c4a12f33-c0ab-45d2-bea0-9710e08ef8c4"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["faucet / handle --control the water flow--> sink", "button / knob --press or rotate to control the water flow--> sink"], "source": "human_phase4", "target_label": "faucet / handle", "anchor_label": "sink", "shared_anchor_node_id": "c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "shared_anchor_label": "sink", "reference_node_id": "b0e7459d-07a3-41a9-af61-18f99260e1d3", "reference_label": "button / knob", "reference_relation": "press or rotate to control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["higher-mounted"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 faucet/handle nodes (a54cd1df sink z=294.050, 8c74ba89 bathtub z=293.817). Both fixtures have a button/knob. Reference 'higher button' -> b0e7459d (z=293.859 > 1e33ac6a z=293.320) -> sink -> faucet a54cd1df. Anchor not named in query; geometry_cue on reference disambiguates anchor."}
```

---

### q035 — scene 421063, bathtub faucet/handle (ref = lower-positioned bathtub button/knob)

```json
{"query_id": "lr_v1_000035", "scene_id": "421063", "query_text": "In this bathroom, which faucet/handle controls water flow for the fixture that also has the lower-mounted button/knob?", "query_type": "functional", "target_node_id": "8c74ba89-2f15-4638-97e0-c1a8c294a25e", "anchor_node_id": "b0e10097-ce1f-46d7-8905-b820e381c43e", "supporting_edge_ids": ["8c74ba89-2f15-4638-97e0-c1a8c294a25e|control the water flow|b0e10097-ce1f-46d7-8905-b820e381c43e", "1e33ac6a-7344-4c07-a5a0-d3ff74760222|press or rotate to control the water flow|b0e10097-ce1f-46d7-8905-b820e381c43e"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["faucet / handle --control the water flow--> bathtub", "button / knob --press or rotate to control the water flow--> bathtub"], "source": "human_phase4", "target_label": "faucet / handle", "anchor_label": "bathtub", "shared_anchor_node_id": "b0e10097-ce1f-46d7-8905-b820e381c43e", "shared_anchor_label": "bathtub", "reference_node_id": "1e33ac6a-7344-4c07-a5a0-d3ff74760222", "reference_label": "button / knob", "reference_relation": "press or rotate to control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["lower-mounted"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 faucet/handle nodes (a54cd1df sink, 8c74ba89 bathtub). Reference 'lower button' -> 1e33ac6a (z=293.320 < b0e7459d z=293.859) -> bathtub -> faucet 8c74ba89. Pair of q034."}
```

---

### q036 — scene 422813, sink faucet/handle (ref = higher-positioned sink button/knob)

```json
{"query_id": "lr_v1_000036", "scene_id": "422813", "query_text": "Which handle/faucet is connected to the water fixture whose flow-control button is mounted higher than the other control button in the scene?", "query_type": "functional", "target_node_id": "b012412a-0a59-46b6-a39c-0be4984a68b3", "anchor_node_id": "649f5431-e6cb-4760-a70f-ffa2ed3ac707", "supporting_edge_ids": ["b012412a-0a59-46b6-a39c-0be4984a68b3|control the water flow|649f5431-e6cb-4760-a70f-ffa2ed3ac707", "1deb7d86-ff85-4dd9-bab3-fefffa2ddcdb|press or rotate to control the water flow|649f5431-e6cb-4760-a70f-ffa2ed3ac707"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["handle / faucet --control the water flow--> bathroom sink", "button / knob --press or rotate to control the water flow--> bathroom sink"], "source": "human_phase4", "target_label": "handle / faucet", "anchor_label": "bathroom sink", "shared_anchor_node_id": "649f5431-e6cb-4760-a70f-ffa2ed3ac707", "shared_anchor_label": "bathroom sink", "reference_node_id": "1deb7d86-ff85-4dd9-bab3-fefffa2ddcdb", "reference_label": "button / knob", "reference_relation": "press or rotate to control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["higher"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 handle/faucet nodes (b012412a sink z=275.262, 381968b3 bathtub z=275.024). Reference 'higher button' -> 1deb7d86 (z=275.079 > 8315a573 z=274.515) -> bathroom sink -> faucet b012412a. Scene 422813 counterpart of q034."}
```

---

### q037 — scene 422813, bathtub faucet/handle (ref = lower-positioned bathtub button/knob)

```json
{"query_id": "lr_v1_000037", "scene_id": "422813", "query_text": "Which handle/faucet is connected to the water fixture whose flow-control button is mounted lower than the other control button in the scene?", "query_type": "functional", "target_node_id": "381968b3-9045-484b-bf77-ea95b427a529", "anchor_node_id": "bb70dccc-863c-446d-a1b2-66ca94a389ed", "supporting_edge_ids": ["381968b3-9045-484b-bf77-ea95b427a529|control the water flow|bb70dccc-863c-446d-a1b2-66ca94a389ed", "8315a573-603f-4a3c-9fc6-902a8ab19ad0|press or rotate to control the water flow|bb70dccc-863c-446d-a1b2-66ca94a389ed"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["handle / faucet --control the water flow--> bathtub", "button / knob --press or rotate to control the water flow--> bathtub"], "source": "human_phase4", "target_label": "handle / faucet", "anchor_label": "bathtub", "shared_anchor_node_id": "bb70dccc-863c-446d-a1b2-66ca94a389ed", "shared_anchor_label": "bathtub", "reference_node_id": "8315a573-603f-4a3c-9fc6-902a8ab19ad0", "reference_label": "button / knob", "reference_relation": "press or rotate to control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["lower"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 handle/faucet nodes (b012412a sink, 381968b3 bathtub). Reference 'lower button' -> 8315a573 (z=274.515 < 1deb7d86 z=275.079) -> bathtub -> faucet 381968b3. Pair of q036."}
```

---

### q038 — scene 421063, sink button/knob (ref = higher-positioned sink faucet; anchor NOT named)

Target is the sink button (same node as q021's target), but here the anchor is inferred geometrically via the reference faucet — not explicitly named. q021 was contextual because it names "sink"; q038 is strict because it omits the anchor name and requires geometry reasoning.

```json
{"query_id": "lr_v1_000038", "scene_id": "421063", "query_text": "Press or rotate the button/knob that controls water flow into the same fixture as the higher-mounted faucet/handle.", "query_type": "functional", "target_node_id": "b0e7459d-07a3-41a9-af61-18f99260e1d3", "anchor_node_id": "c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "supporting_edge_ids": ["b0e7459d-07a3-41a9-af61-18f99260e1d3|press or rotate to control the water flow|c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "a54cd1df-50ca-4ca9-b3c0-136fe9224393|control the water flow|c4a12f33-c0ab-45d2-bea0-9710e08ef8c4"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["button / knob --press or rotate to control the water flow--> sink", "faucet / handle --control the water flow--> sink"], "source": "human_phase4", "target_label": "button / knob", "anchor_label": "sink", "shared_anchor_node_id": "c4a12f33-c0ab-45d2-bea0-9710e08ef8c4", "shared_anchor_label": "sink", "reference_node_id": "a54cd1df-50ca-4ca9-b3c0-136fe9224393", "reference_label": "faucet / handle", "reference_relation": "control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["higher-mounted"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 button/knob nodes (b0e7459d sink z=293.859, 1e33ac6a bathtub z=293.320). Both fixtures have a faucet. Reference 'higher faucet' -> a54cd1df (z=294.050 > 8c74ba89 z=293.817) -> sink -> button b0e7459d. Same target as q021 but q021 names 'sink' (contextual); this version omits anchor name (strict). Reverse of q034."}
```

---

### q039 — scene 421063, bathtub button/knob (ref = lower-positioned bathtub faucet; anchor NOT named)

```json
{"query_id": "lr_v1_000039", "scene_id": "421063", "query_text": "Press or rotate the button/knob that controls water flow into the same fixture as the lower-mounted faucet/handle.", "query_type": "functional", "target_node_id": "1e33ac6a-7344-4c07-a5a0-d3ff74760222", "anchor_node_id": "b0e10097-ce1f-46d7-8905-b820e381c43e", "supporting_edge_ids": ["1e33ac6a-7344-4c07-a5a0-d3ff74760222|press or rotate to control the water flow|b0e10097-ce1f-46d7-8905-b820e381c43e", "8c74ba89-2f15-4638-97e0-c1a8c294a25e|control the water flow|b0e10097-ce1f-46d7-8905-b820e381c43e"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["button / knob --press or rotate to control the water flow--> bathtub", "faucet / handle --control the water flow--> bathtub"], "source": "human_phase4", "target_label": "button / knob", "anchor_label": "bathtub", "shared_anchor_node_id": "b0e10097-ce1f-46d7-8905-b820e381c43e", "shared_anchor_label": "bathtub", "reference_node_id": "8c74ba89-2f15-4638-97e0-c1a8c294a25e", "reference_label": "faucet / handle", "reference_relation": "control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["lower-mounted"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 button/knob nodes (b0e7459d sink, 1e33ac6a bathtub). Reference 'lower faucet' -> 8c74ba89 (z=293.817 < a54cd1df z=294.050) -> bathtub -> button 1e33ac6a. Same target as q022 but anchor not named (strict). Reverse of q035. Pair of q038."}
```

---

### q040 — scene 422813, sink button/knob (ref = higher-positioned sink faucet; anchor NOT named)

```json
{"query_id": "lr_v1_000040", "scene_id": "422813", "query_text": "Press or rotate the button/knob whose water flow connects to the same fixture as the higher-positioned faucet/handle in this bathroom.", "query_type": "functional", "target_node_id": "1deb7d86-ff85-4dd9-bab3-fefffa2ddcdb", "anchor_node_id": "649f5431-e6cb-4760-a70f-ffa2ed3ac707", "supporting_edge_ids": ["1deb7d86-ff85-4dd9-bab3-fefffa2ddcdb|press or rotate to control the water flow|649f5431-e6cb-4760-a70f-ffa2ed3ac707", "b012412a-0a59-46b6-a39c-0be4984a68b3|control the water flow|649f5431-e6cb-4760-a70f-ffa2ed3ac707"], "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"], "is_long_range": true, "evidence_chain": ["button / knob --press or rotate to control the water flow--> bathroom sink", "handle / faucet --control the water flow--> bathroom sink"], "source": "human_phase4", "target_label": "button / knob", "anchor_label": "bathroom sink", "shared_anchor_node_id": "649f5431-e6cb-4760-a70f-ffa2ed3ac707", "shared_anchor_label": "bathroom sink", "reference_node_id": "b012412a-0a59-46b6-a39c-0be4984a68b3", "reference_label": "handle / faucet", "reference_relation": "control the water flow", "long_range_pattern": "junction_2hop", "evidence_hop_count": 2, "reference_necessity": "strict", "geometry_cues": ["higher-positioned"], "num_same_label_distractors": 1, "is_label_only_solvable": false, "notes": "Strict: 2 button/knob nodes (1deb7d86 sink z=275.079, 8315a573 bathtub z=274.515). Reference 'higher faucet' -> b012412a (z=275.262 > 381968b3 z=275.024) -> bathroom sink -> button 1deb7d86. Same target as q023 but anchor not named (strict). Reverse of q036. Scene 422813 counterpart of q038."}
```

---

### Validation command (run after appending)

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\long_range_stress_queries_v1.jsonl
```

Expected: **0 ERROR, 0 WARN**, 40 total queries, 20 strict (50.0%).

### Reviewer checklist

- [ ] q031/q032: oven handle strict — fridge has no rotating knob (verify in scene graph)
- [ ] q033: WM knob strict — outlet 59552624 powers WM only, not dryer (verify from relations JSON)
- [ ] q034–q040: bathroom geometry heights — z ordering confirmed (see table above)
- [ ] All 10 query_ids are lr_v1_000031 through lr_v1_000040 (sequential, no gaps)
- [ ] No duplicate query_text vs existing 30 queries
- [ ] target_label matches expected node labels in scene graph
