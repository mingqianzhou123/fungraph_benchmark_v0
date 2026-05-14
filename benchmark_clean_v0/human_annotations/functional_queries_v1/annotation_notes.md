# Annotation Notes

> Append-only working log for the human functional query annotation task.
> Source plan: `human_annotations/summary/phase_clarify/phase0.md`
> Frozen benchmark must not be edited — log issues here instead.

---

## Phase 0 — Scene & Edge Selection — 2026-05-12

### Overview

Ran `scripts/phase0_scene_audit.py` on the 870 SceneFun3D functional queries.
All 6 sanity checks passed. The scan found **20 scenes** with functional queries
(matches the 20 scenes that have bbox coverage in `geometry/scenefun3d_node_geom.json`).

Score distribution (recommendation_score 0–4):
- score = 4 (perfect)  : 16 scenes
- score = 3 (high)     : 3 scenes
- score = 2 (medium)   : 1 scene
- score < 2 (low)      : 0 scenes

Surprising finding: target_bbox_rate = 1.000 for every scene — every functional
query target and every functional query anchor already has bbox in geometry. So
the bbox criterion does not actually differentiate scenes. The real differentiation
is `n_unique_edges`, `max_same_label_count`, `n_endpoint_ambig_edges`, and `z_axis_range`.
See "Phase 0 progress" at the bottom for the implication.

---

### ==Selected Scenes (6 scenes, 89 candidate edges total)==

Selected the top 6 score-4 scenes by `n_unique_edges`. Diversity check below the list.

#### 1. scene_id: 469011  ⭐⭐⭐ (highest-yield scene)

- why_selected: 24 unique edges, 144 existing queries, 22 actionable targets,
  18 endpoint-ambiguous edges, knob group of 19 same-label nodes,
  z-axis range 2.168 (large vertical variation → good for upper/lower queries).
  Combines water-flow, power, and pull edges → very diverse functional vocabulary.

> 24 条唯一边、144 条已有查询、22 个可操作目标、18 条端点歧义边、含 19 个同标签节点的旋钮组、z 轴范围 2.168（垂直变化大 → 适合上/下方位查询）。涵盖水流、电力和拉取边 → 功能词汇极为多样。

- **candidate_edges: 24**
- top_edge_descs:
  - `pull to open or close` × 15 distinct edges (drawer + cabinet)
  - `rotate to adjust the setting` (5 distinct)
  - `provide power` (electric outlets)
  - `control the water flow`
- **same_label_candidates:**
  - `knob`: **19 nodes** ← strongest same-label disambig opportunity in dataset
  - `handle`: 2 nodes
  - `electric outlet`: 2 nodes
- endpoint_ambiguity_edge_types:
  - `control the water flow` (faucet ↔ sink)
  - `provide power` (outlet ↔ device)
  - `pull to open or close` (handle ↔ drawer/door)
- **has_geometry:**
  - all 24 target nodes have bbox ✓
  - all 15 anchor nodes have bbox ✓
  - **z_axis_range = 2.168 → can ask upper/lower queries**

#### 2. scene_id: 421254  ⭐⭐⭐ (best same-label disambig)

- why_selected: knob group of **20 nodes** (highest in dataset!), 17 unique edges,
  17 endpoint-ambiguous edges. Drawer-heavy scene (42 pull verbs) → ideal for
  handle-vs-drawer endpoint ambiguity tests.

> 选择原因：旋钮组 **20 个节点**（数据集最高！）、17 条唯一边、17 条端点歧义边。抽屉密集场景（42 个拉取动词）→ 适合测试把手对抽屉端点歧义。

- candidate_edges: 17
- top_edge_descs:
  - `pull to open or close a drawer` × 7 distinct edges
  - `control` × 1 distinct
  - `provide power` × 1 distinct
- **same_label_candidates:**
  - `knob`: **20 nodes** ← THE same-label scene
  - `remote`: 2 nodes
- endpoint_ambiguity_edge_types:
  - `control` (button/switch ↔ device)
  - `provide power` (outlet ↔ device)
  - `pull to open or close a drawer` (knob/handle ↔ drawer)
- has_geometry: 23/23 targets, 5/5 anchors, z_range 1.222

#### 3. scene_id: 421380  ⭐⭐ (drawer-heavy, low z-range)

- why_selected: 17 unique edges, 102 queries, knob group of 15, 16 endpoint-ambig.
  Heavy drawer scene (84 pull verbs) → many opportunities for endpoint-ambiguity
  tests. NOTE: z_range only 0.802 → less suitable for vertical geometry queries.

> 选择原因：17 条唯一边、102 条查询、旋钮组 15 个节点、16 条端点歧义边。抽屉密集场景（84 个拉取动词）→ 端点歧义测试机会多。注意：z 范围仅 0.802 → 不适合垂直几何查询。

- candidate_edges: 17
- top_edge_descs:
  - `pull to open or close a drawer` × 10 distinct
  - `pull to open or close` × 4 distinct
  - `control` × 2 distinct
- same_label_candidates:
  - `knob`: 15 nodes
  - `remote`: 2 nodes
- endpoint_ambiguity_edge_types:
  - `control` (switch ↔ device)
  - `pull to open or close` (handle ↔ door)
  - `pull to open or close a drawer` (knob/handle ↔ drawer)
- has_geometry: 17/17 targets, 3/3 anchors, **but z_range only 0.802** → flag for
  horizontal-geometry queries (left/right/near/far) instead of upper/lower

#### 4. scene_id: 421602  ⭐⭐⭐ (best handle scene with vertical variation)

- why_selected: handle group of 11 nodes (strongest handle-disambig case),
  12 unique edges, z_range 2.009 (high vertical variation). Mostly drawer pulls.

> 选择原因：把手组 11 个节点（最强把手消歧案例）、12 条唯一边、z 范围 2.009（垂直变化大）。以抽屉拉取为主。

- candidate_edges: 12
- top_edge_descs:
  - `pull to open or close a drawer` × 5
  - `pull to open or close` × 1
  - `rotate to open or close` × 1
- same_label_candidates:
  - `handle`: **11 nodes** ← strongest handle-disambig
- endpoint_ambiguity_edge_types:
  - `pull to open or close` (handle ↔ door)
  - `pull to open or close a drawer` (handle ↔ drawer)
- has_geometry: 12/12 targets, 5/5 anchors, z_range 2.009 → great for upper/lower

#### 5. scene_id: 421013  ⭐⭐⭐ (best for control + pull mix)

- why_selected: 10 unique edges, handle×9, includes the rare
  `control, turn on or turn off` edge type (switch/lamp scenarios). z_range 2.170 (best).

> 选择原因：10 条唯一边、把手 × 9 个节点，包含罕见的 `control, turn on or turn off`（控制，打开或关闭）边类型（开关/灯具场景）。z 范围 2.170（最高）。

- candidate_edges: 10
- top_edge_descs:
  - `pull to open or close a drawer` × 3
  - `pull to open or close` × 2
  - `control, turn on or turn off` × 1
- same_label_candidates:
  - `handle`: 9 nodes
- endpoint_ambiguity_edge_types:
  - `control, turn on or turn off` (switch ↔ lamp/appliance) ← textbook
    endpoint-ambig case
  - `pull to open or close` (handle ↔ door)
  - `pull to open or close a drawer` (handle ↔ drawer)
- has_geometry: 10/10 targets, 5/5 anchors, z_range 2.170 (highest among picks)

#### 6. scene_id: 420683  ⭐⭐ (mixed knob + handle + control)

- why_selected: 9 unique edges, knob×9 + handle×2, includes
  `control, turn on or turn off` edge. Mix of action verbs (pull/rotate/press).
  Best "broad coverage" scene — represents many edge categories.

> 选择原因：9 条唯一边，旋钮 × 9 + 把手 × 2，包含 `control, turn on or turn off` 边。动作动词多样（拉/转/按）。"覆盖面最广"的场景——代表多种边类别。

- candidate_edges: 9
- top_edge_descs:
  - `pull to open or close` × 4
  - `pull to open or close a drawer` × 3
  - `control, turn on or turn off` × 1
- same_label_candidates:
  - `knob`: 9 nodes
  - `handle`: 2 nodes
- endpoint_ambiguity_edge_types:
  - `control, turn on or turn off` (switch ↔ lamp)
  - `pull to open or close` (handle ↔ door)
  - `pull to open or close a drawer` (knob ↔ drawer)
- has_geometry: 12/12 targets, 7/7 anchors, z_range 1.750

---

### Diversity Check Across the 6 Selected Scenes

Confirms the picks cover all priority dimensions:

| Dimension | Min | Max | Selected scenes covered |
|-----------|-----|-----|-------------------------|
| n_unique_edges | 9 | 24 | range 9–24 (good spread) |
| max_same_label_count | 9 | 20 | knob heavy (469011, 421254, 421380, 420683) + handle heavy (421602, 421013) |
| n_endpoint_ambig_edges | 7 | 18 | every picked scene ≥ 7 |
| z_axis_range | 0.802 | 2.170 | 5/6 ≥ 1.2 (upper/lower queries OK); 421380 flagged for horizontal-only |
| action verb mix | — | — | pull dominant in 421254/421380/421602/421013; mixed in 469011/420683 |

---

### Candidate Edge Pool Summary

```
Total candidate edges across selected scenes: 89
  (469011: 24, 421254: 17, 421380: 17, 421602: 12, 421013: 10, 420683: 9)

By action type (approximate counts based on top_edge_descs):
  pull-class    : ~55 edges  (dominant)
  rotate-class  : ~12 edges
  press-class   : ~8 edges
  control-class : ~14 edges

By ambiguity type:
  endpoint_ambiguous edges    : 77 (across selected scenes)
  same_label_required scenes  : 6/6 (every selected scene has at least one
                                     label group with ≥ 9 same-label nodes)
  geometry_helpful scenes     : 5/6 (all but 421380 — low z_range)

Coverage requirement check:
  selected_scenes >= 6 : 6 ✓
  candidate_edges >= 30: 89 ✓
```

---

### Issues Found (do NOT modify original files)

```markdown
[issue] scene_id=469011 problem=15 anchor nodes have label="unknown"
        suggested_fix=anchor_labels field may be missing/empty in source
        queries; not blocking — anchor identity is via node_id, label is for
        readability only. Confirm with Mingqian if "unknown" should be
        re-derived from scene graph in Phase 1.

[issue] scene_id=421380 problem=z_axis_range only 0.802 → vertical
        geometry_aware queries (upper/lower) likely won't be uniquely answerable
        in this scene
        suggested_fix=in Phase 1, write only horizontal geometry queries
        (left/right/near/far) for 421380; reserve upper/lower for the other
        5 scenes.

[issue] scene_id=all problem=20/23 OpenFunGraph scenes appear in functional
        queries (the 20 with bbox); the other 3 annotated scenes have no
        functional queries in the benchmark
        suggested_fix=not a bug — those 3 likely have only spatial/semantic
        queries. No action.
```

---

### ==Phase 0 Counts==

```
Selected scenes        : 6   (target ≥ 6 ✓)
Candidate edges        : 89  (target ≥ 30 ✓)
score=4 scenes used    : 6   (of 16 available)
Total queries reachable: 459 (sum of n_functional_queries in selected scenes)
Geometry coverage      : 1.000 (perfect for all selected scenes)
Ready for Phase 1      : YES
```

---

## ==Phase 0 progress — 2026-05-12==

Did:
- 写了 `scripts/phase0_scene_audit.py`（标准库 only，无外部依赖）
- 扫描 870 条 SceneFun3D functional queries + 20-scene geometry
- 生成 `scene_audit_v1.csv`（20 行，全部 sanity check 通过）
- 手动从 score=4 的 16 个 scene 里挑了 top-6（按 n_unique_edges 排序）
- 写了本 annotation_notes.md，记录每个选中 scene 的候选 edge / distractor / endpoint ambig 详情

Counts:
- 总 scene（有 functional query）: 20
- score=4 scenes: 16
- 选中 scenes: 6（≥6 ✓）
- 候选 edges: 89（≥30 ✓）
- 总可达 queries: 459

Scene selection (recommendation_score, n_unique_edges, headline label group):
- 469011: score=4, 24 edges, knob×19, 18 ambig, z=2.168
- 421254: score=4, 17 edges, knob×20 (max!), 17 ambig, z=1.222
- 421380: score=4, 17 edges, knob×15, 16 ambig, z=0.802 (flagged: low z)
- 421602: score=4, 12 edges, handle×11, 10 ambig, z=2.009
- 421013: score=4, 10 edges, handle×9, 9 ambig, z=2.170 (highest z)
- 420683: score=4, 9 edges, knob×9 + handle×2, 7 ambig, z=1.750

Potential issues:
- 15 anchor labels in 469011 are "unknown" — non-blocking, see [issue] above.
- 421380 has very low z_axis_range; flag for horizontal-only geometry queries in Phase 1.
- All 20 scenes have perfect target_bbox_rate = 1.0 → bbox criterion is not
  discriminative; in practice scenes are differentiated by edge / label / ambig
  density. Consider lowering bbox weight in future audit scoring.

Files ready for review:
- `scripts/phase0_scene_audit.py` (脚本)
- `scene_audit_v1.csv`（20 scenes 统计表）
- `annotation_notes.md`（本文件）

Next step: Phase 1 — write 20 pilot queries from these 6 scenes.
  - 10 local functional
  - 5 same-label / endpoint hard cases (draw from knob×19 / knob×20 / handle×11 scenes)
  - 3 geometry-aware functional (use 421013/469011/421602 high z-range scenes)
  - 2 hard negatives
  - Validator script (Phase 6) should be written in parallel with Phase 1.
