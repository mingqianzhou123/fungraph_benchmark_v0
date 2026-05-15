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

---

## Phase 1 progress — 2026-05-15

Did:
- 写 scripts/phase1_scene_explorer.py（仅标准库），生成 scene_graph_summary_v1.txt
  —— 6 个选中 scene 的 node / edge / 同名分组；关键修正：过滤 "unknown" 标签，不计入
  同名 distractor。
- 写 scripts/validate_functional_queries.py，最终 13 项检查（C1–C13）+ Phase 1 分布
  分析。C12 增强为同时查 long_range tag 与 is_long_range 字段；C13 新增重复 instance
  检查（同一 target+anchor+edge tuple）；新增 category distribution 检查自动比对 10/5/3/2。
- ==写 20 条 pilot queries（pilot_20_queries.jsonl），覆盖全部 6 个 scene==。

- 术语澄清（==**供后续标注参考Mingqian可以忽略**==；基于 OpenFunGraph CVPR'25 Sec. 1/3 与 Research Plan）：
  内部 review 曾把 local/remote 误说成"按动词类型分的 edge family"，已修正：
  • **local edge / remote edge**（OpenFunGraph 物理定义）按**物理依附 vs 物理分离**
    分类，**不是按动词类型**：local = interactive element 刚性 part of object
    （如 handle-door、knob-cabinet）；remote = element 与 object 物理分离、远距离
    操作（如 switch controls ceiling light、outlet powers fridge、remote-TV）。
    动词（opens/pulls vs controls/powers）只是物理关系的 proxy，不是定义。
  • **long_range**（TASK_PLAN Section 6）= evidence chain ≥ 2 跳（**图论多跳**）。
    Research Plan Section 8.5 另定义了 "spatially long-range"（target↔anchor 的
    **3D 物理距离大**），与图跳数互为独立轴。
  • **TASK_PLAN Section 8 "10 条 local functional"** 中的 "local" 上下文反义词是
    long_range（Section 6 + Phase 4 规定 pilot 禁写 long_range），所以这里 "local"
    = local-range（图上单跳），**与 OpenFunGraph 的 "local-type edge" 不是同一
    概念**。pilot 这 10 条单跳 functional 既含物理 local-type 边（knob→radiator）
    也含单跳 remote-type 边（outlet→fridge）。
  • 附注：6 条 remote-type 单跳 query（000006/000009/000012/000013/000018/000019）
    虽然图跳=1、不算 long_range tag，但 target↔anchor 的 3D 距离往往较大（如墙
    开关 ↔ 天花板灯 ~2.5m）；从 Research Plan Section 8.5 的物理距离视角看可属
    "spatially long-range" 案例——这是 graph-hop 与 3D-distance 两个 long-range
    轴在 pilot 上的具体体现。

Counts:
- pilot_20_queries.jsonl：20 条，全部 unique instance（C13 通过）。
- difficulty 四类分布：local=10, same/endpoint=5, geometry=3, hard_neg=2 —— 符合
  TASK_PLAN Section 8 的 10/5/3/2。
- difficulty_tags 计数：simple_functional=4, functional_relation=13,
  same_label_disambiguation=5, endpoint_ambiguity=3, geometry_aware=3, hard_negative=2。
- Scene 分布：469011=4, 421013=4, 420683=4, 421254=3, 421602=3, 421380=2（每个 ≥2）。
- edge-family 粗分布（人工按 research plan Table 1 归类）：functional_local=14,
  functional_remote=6。
- is_long_range 全 false，无 long_range tag。
- Validator：20/20 PASS，0 ERROR，0 WARN。

Potential issues:
- [issue] scene_id=469011 problem=469011 的 144 条 functional queries 的
  `anchor_labels` 字段全部为空（涉及 15 个 unique anchor_node_id）；
  phase0_scene_audit.py:142 将空 anchor_labels 兜底为字符串 "unknown"，导致
  scene_audit_v1.csv 显示 "unknown=15"。**scene_graph 节点本身没有 'unknown'
  label**（已实测：469011 的 43 个节点全部有合法 label，unknown 计数 = 0）。
  suggested_fix=anchor 身份由 node_id 唯一确定，pilot 通过 scene_graph 反查得到
  合法 label，不阻塞。源头修复需补 enriched JSON 里 query 层的 `anchor_labels`
  字段（这是数据集级缺失，不是单节点错误）。
- [issue] scope=multimodal_extension/phase2 problem=phase2.md 设计决策 "高度轴=y"
  与实测 geometry 冲突。实测 ceiling light 在 z 轴 3/3 scene 排第 1、y 轴排中部
  （#13/#10/#5），==证明 z 才是垂直轴==

Files ready for review:
- pilot_20_queries.jsonl（20 条，分布 10/5/3/2，全部 validator PASS）
- scripts/phase1_scene_explorer.py
- scripts/validate_functional_queries.py（13 项检查 + 分布分析）
- scene_graph_summary_v1.txt
- validation_report.md

==STOP HERE — Phase 1 完成，等 Mingqian 审核后再进入 Phase 2==

---

## Phase 1 manual review fixes — 2026-05-15

Did:
- 学长 Mingqian 提供 manual review 表
  （`summary/phase_clarify/phase1_manual_review.md`），指出 4 处问题
  并要求修复后重跑 validator、保留 manual review 表原样、不修改 frozen benchmark
  core files。
- 修 `000003`（学长 ⚠️ 问题 1，严重）：query 说 "top drawer of the dresser"，但原
  target=`cde51d66`（z=170.741）只是 5 个连到该 dresser 的 handle 中第 2 高，真正
  z-max 是 `9fcd23c1`（z=170.932）。target_node_id 改为 `9fcd23c1`，supporting_edge
  同步更新。同时 retag 从 `simple_functional` → `geometry_aware` +
  `same_label_disambiguation`（"top" 是几何线索，"handle" 在该 anchor 上有 5 个候选
  → 不是 label-only solvable）。加 `geometry_cues=["top"]`，
  `is_label_only_solvable` 由 true → false。
- 修 `000009`（学长 ⚠️ 问题 2，中等）：原 query "Which remote controls the
  television" 有 2 个合法 target（560f1e2c 和 9c06f662 都连到同一 TV）。按学长
  manual review 选项 A，补充几何描述：query_text 改为
  "Which remote on the right-hand side controls the television"。target 保留
  560f1e2c（x=-0.330，比 9c06f662 的 x=-0.443 更靠右，x diff = 0.113m）。
  difficulty_tags 加 `geometry_aware`，加 `geometry_cues=["right"]`。
- 修 `000007`（学长 ⚠️ 问题 3，轻微）：scene 421380 有 15 knobs，`num_same_label_distractors=14`
  完全满足 `same_label_disambiguation` 条件，加入 tag。
- 修 `000011`（学长 ⚠️ 问题 3，轻微）：scene 469011 有 19 knobs，
  `num_same_label_distractors=18` 满足同上条件，加 tag。
- 重跑 validator：20/20 PASS，0 ERROR，0 WARN，C13（重复 instance）通过。
- 未修改 `phase1_manual_review.md`（学长保留原样指令）；未触碰 frozen 目录
  （queries/、graphs/、geometry/、annotations/、manifests/、multimodal_extension/）。

Counts:
- pilot_20_queries.jsonl：20 条，修改 4 条（000003 / 000007 / 000009 / 000011），
  其余 16 条不变。
- difficulty_tags 计数变化：
  - `simple_functional`：4 → 3（000003 移出）
  - `functional_relation`：13 → 13（不变）
  - `same_label_disambiguation`：5 → 8（+ 000003 / 000007 / 000011）
  - `endpoint_ambiguity`：3 → 3（不变）
  - `geometry_aware`：3 → 5（+ 000003 / 000009）
  - `hard_negative`：2 → 2（不变）
- 四类互斥分布（hard_neg > geometry > same/endpoint > local 优先级）：
  10 / 5 / 3 / 2 → **7 / 6 / 5 / 2**
- Scene 分布：469011=4, 421013=4, 420683=4, 421254=3, 421602=3, 421380=2（不变）
- Validator：20/20 PASS, 0 ERROR, 0 WARN；
  Phase 1 category distribution 检查显示 MISMATCH（informational only）。

Potential issues:
- [issue] (已修正) 000003 target 选错（z=170.741 不是最高，应是 z=170.932 的
  9fcd23c1）。来源：学长 manual review ⚠️ 问题 1。
- [issue] (已修正) 000009 query 有两个合法答案（两个 remote 都连同一 TV）。
  来源：学长 manual review ⚠️ 问题 2。
- [issue] (已修正) 000007 缺 `same_label_disambiguation` tag（14 个 same-label knob
  满足条件）。来源：学长 manual review ⚠️ 问题 3。
- [issue] (已修正) 000011 缺 `same_label_disambiguation` tag（18 个 same-label knob
  满足条件）。来源：学长 manual review ⚠️ 问题 3。
- [issue] (informational, 不阻塞) Phase 1 四类分布从 10/5/3/2 漂移到 7/6/5/2。
  漂移原因 = 诚实 retag（000003 加 geometry+same_label、000007/000011 加 same_label、
  000009 加 geometry）。学长在本轮反馈中明确指示"下一批提高 hard non-label-only
  query 比例（尤其 same-label disambiguation / endpoint ambiguity / geometry-aware
  / hard negative）"，本次漂移正是这个方向：local-7 减少（更少 easy case），
  same/endpoint+1、geometry+2（更多 hard case）。Phase 2 扩展时按此方向继续。

Files ready for review:
- `pilot_20_queries.jsonl`（20 条，4 条修正后全 validator PASS）
- `validation_report.md`（最新，包含修正后分布）
- `summary/phase_clarify/phase1_manual_review.md`（学长 review 表，保留原样）
- `scripts/validate_functional_queries.py`（13 项检查不变）

==STOP HERE — Manual review 修正完成，等学长 ack 后开始 Phase 2（重点：
扩展时刻意提高 same_label_disambiguation / endpoint_ambiguity / geometry_aware /
hard_negative 比例，按学长指示降低 label-only 易解 query 的占比）==
