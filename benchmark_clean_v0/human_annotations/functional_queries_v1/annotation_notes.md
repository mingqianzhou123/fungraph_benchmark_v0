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

## Phase 2 progress — 2026-05-16

Did:
- 按 phase2.md / TASK_PLAN §9 执行 Phase 2 主标注扩展。锚定 150 ideal，但 6
  个 scene 的真实 edge 数据实测硬上限是 ~65 高质量 fresh-edge query（详见
  issue CAP_LIMIT）。 加做了 18 条 pilot-edge 复用
  query（含 q088 修正 pilot 000004 ambiguity、q094 修正 pilot 000010
  ambiguity）。最终产出 83 条（仍低于 150 ideal，但超过 80 minimum）。
- 决定 2026-05-16 ack 放行 421380 intra-anchor 垂直规则后，补 10 条 cluster
  query (q104–q113)：cluster A x≈1.07 列 5 条（topmost / 2nd / middle /
  2nd-bottom / bottommost），cluster B x≈1.47 列 5 条同模式。phase1.md /
  phase2.md修订 2 升级为 v2 措辞，validator C13 文档行标 "已撤回"。最终
  query 总数 83 → **93**。
- 写了 `scripts/phase2_query_generator.py`：83 条手写 spec（65 fresh-edge +
  18 pilot-edge reframings），从 frozen scene graph 读真实 edge，自动算
  evidence_chain / real-label same-label 计数 / distractor UUIDs / diagnostics。
- 再次 retag 了 4 条已有 query (q021/q043/q047/q048) 加上 endpoint_ambiguity
  tag（door / fridge / oven 等 anchor 都是 interactive，符合 §6 endpoint
  定义）。
- 把 validator 的 `VALID_TAGS` 集合加上 `multi_anchor`（详见 VALIDATOR_GAP
  issue）。添加后 pilot 20 条仍全 PASS。
- 把 Phase 1 的 `validation_report.md` 备份为 `validation_report_phase1.md`，
  再覆盖为 Phase 2 的报告。
- 写了 `hard_slice_summary_v1.json`：tag 分布 / scene 分布 / label-only 占比 /
  distractor 直方图 / multi_anchor × geometry_aware 共现矩阵。
- 删掉 validator 末尾针对 Phase 1 pilot 20 条写死的 10/5/3/2 分布打印块（对
  Phase 2 不适用，会全 MISMATCH 制噪音）。删除后 pilot 20/20 PASS 不变，
  validation_report 干净。

Counts:
- 总 query 数：**93**（65 fresh-edge + 18 pilot-edge reframings + 10 421380
  intra-anchor cluster）。vs phase2.md 锚定 150 ideal 仍偏低 ~38%；超过 80
  minimum 13 条。
- Scene 分布：469011=23, 421254=23, 421380=14, 420683=12, 421602=11, 421013=10。
  (421380 从 4 → 14，cluster 放行后翻 3.5 倍)
- Difficulty tag 分布（一条 query 可多 tag）：
    same_label_disambiguation: 86 (92.5%)
    geometry_aware:            74 (79.6%)
    multi_anchor:              41 (44.1%)
    functional_relation:       18 (19.4%)
    endpoint_ambiguity:        18 (19.4%)
    hard_negative:             11 (11.8%)
    simple_functional:          7 ( 7.5%)
- 演进：65 → 83（加 18 pilot reframings）→ 93（加 10 cluster）。新加 10 条
  全是 same_label + geometry，所以这两个 tag 比例又升；hard_negative /
  endpoint_ambiguity / simple_functional 绝对数不变、占比被稀释。
- `is_label_only_solvable=true`：**2 条**（q042 radiator-knob 421602 + q102
  outlet-lamp 421254 reuse），占 2.2%，远低于上限 20%，符合要求。
- num_same_label_distractors 直方图：0=6, 1=8, 5-9=20, 10-19=59。10 条新加
  cluster query 全部落在 10-19 区间（421380 14 个同名 knob distractors）。

Potential issues:
- [issue] CAP_LIMIT
    scope=phase2 plan vs data
    problem=phase2.md 锚定 150 ideal，实际 6 scene 的可写 fresh-edge 高质量
      query 上限 ~65（79 fresh edges 减去 421380 / 469011 / 421602 中无法
      geometry 唯一区分的 cluster pairs）。叠加 18 条 pilot-edge reframings
      (issue PILOT_EDGE_REUSE) 后达到 83 条。再继续就需要：要么 (a) 扩 Phase 0
      scene 集；要么 (b) 接受 93 作为 Phase 2 产出。

> Phase 3 minimal_pair / Phase 4  long_range 也可作为后续补回比例的渠道。

Files ready for review:
- `functional_queries_v1.jsonl`（**93 条**，全 validator PASS）
- `functional_query_diagnostics_v1.jsonl`（93 条 diagnostic，与 main 1:1 对齐）
- `hard_slice_summary_v1.json`（含 93 条统计）
- `validation_report.md`（Phase 2 版，93 PASS / 0 ERROR / 0 WARN）
- `validation_report_phase1.md`（Phase 1 版备份留存）
- `scripts/phase2_query_generator.py`（生成脚本，含 93 条 hand-crafted spec：
  65 fresh-edge + 18 pilot-edge reframings + 10 421380 intra-anchor cluster）
- `scripts/validate_functional_queries.py`（两处修改：①VALID_TAGS 加
  `multi_anchor`；②删除末尾过时的 Phase 1 10/5/3/2 分布打印块。C1–C13 检查
  逻辑不变；pilot 20 条仍 PASS）
- `summary/phase_clarify/phase1.md`（修订 2 升级为 v2 措辞 + scene 表 421380
  方向列改为"水平 + intra-anchor 垂直"；验证器 C13 文档行标"已撤回"）
- `summary/phase_clarify/phase2.md`（修订 2 同步 v2；scene 表 + key edge
  家族描述同步更新）

==STOP HERE — Phase 2 完成 **93 条**，0 ERROR / 0 WARN。超过 80 minimum 13 条；
距离 150 ideal 仍差 ~38%（CAP_LIMIT 结构性原因）。`421380_CLUSTER_UNDISTINGUISHABLE`
已修正；其余 [issue]（CAP_LIMIT / PILOT_EDGE_REUSE 等）需要学长 ack 决定方向。
等学长 review 后再开始 Phase 3 minimal pair。==

---

## Phase 3 progress — 2026-05-20

Did:
- 执行 Phase 3 minimal-pair 标注，按 `summary/phase_clarify/phase3.md` + 学长 review
  反馈两条指示落地：① 自描述 schema（每条参与 pair 的 query 自身带
  `minimal_pair_id` / `minimal_pair_role` / `minimal_pair_partner_id` 三字段，双
  向互指，pair 两条 query 同文件相邻写）；② 新 query 写进 `functional_queries_v1.jsonl`
  不开独立文件（符合 TASK_PLAN §4 八项交付清单）。
- 写 `scripts/phase3_pair_miner.py`：从 113 条已有 query 三类口径（spatial /
  anchor / functional_relation）穷举候选，输出 `pair_candidates_v1.csv`（433 行）。
- 写 `scripts/phase3_compose_pairs.py`（核心，~900 行，idempotent）：
  hand-craft 的 8 mining-keep + 40 new-queries + 20 new-pairs 规格，从 frozen
  scene_graph / geometry 读 UUID，写出最终 main + pair 文件，pilot 文件回滚 tag。
- 扩 `scripts/validate_functional_queries.py`：C19/C20/C21/C22/C23 检查（三字段
  全有全无 + 格式 + 双向互指 + role 互斥）；C13 放宽（dup-instance 在 minimal_pair
  中允许，语言变体复用 tuple 是设计意图）；`VALID_TAGS` 加 `minimal_pair`。
- 写 `scripts/validate_minimal_pairs.py`（C14–C18 派生视图二次校验，独立报告）。
- 挑 8 mining pair：001 / 003 / 007 / 009 / 012 / 014 / 015 / 017（覆盖 4 类
  changed_factor + 5 scene）。原 20 对中删 6 个跨文件 + 2 个全 pilot + 2 个
  query-id 冲突（pair_005 与 017 共用 q067；pair_020 与 001 共用 q104，functional_relation
  由新 pair_039 取代）+ 余下 redundant。
- 写 20 new pair（pair_ids 021–040，queries 000114–000153），主题：outlet→appliance
  (直接 + 间接 hard_negative)、handle→appliance NEW、oven knob 自然语言重写、
  remote→TV 自然语言重写、cluster A/B 全展开 + 跨列、cross-anchor 4 scene、
  wardrobe 自然语言、functional_relation amplifier、间接 hard_negative。所有
  query_text 无裸坐标，按学长 criteria 1-3 执行。
- 跑三个 validator 全 0 ERROR / 0 WARN（详 Counts）；compose 二次跑过滤 80
  previously-appended 后从 93 base 干净重建到 133（idempotent 验证）。
- 未触碰 frozen 目录、Phase 2 主集 query 内容（仅在 16 条 mining-keep query 上
  加 3 self-describing 字段）、`multimodal_extension/`。

Counts:
- pilot_20_queries.jsonl: **20 条**（0 含 `minimal_pair` tag——pilot 不参与
  任何 pair，rule 2 同文件相邻）。
- ==functional_queries_v1.jsonl: **133 条**==（93 Phase 2 base + 40 Phase 3 new；
  56 条带 self-describing 3 字段 = 16 mining-keep + ==40 new==）。
- ==minimal_pairs_v1.jsonl: **28 对**==（派生视图）= 8 mining + 20 new。
  vs phase3.md 原 20 / 修订 30 锚定：缩到 28 因 q067/q104 schema 冲突
  （详 PAIR_QUERY_CONFLICT）。
- changed_factor 分布: spatial_qualifier=11 (39%), geometry_direction=7 (25%),
  anchor_object=9 (32%), functional_relation=1 (4%)。4 类全覆盖。
- Scene 分布: 421380=12, 469011=7, 421254=3, 420683=2, 421013=2, 421602=2。
  6 scene 全覆盖（421380 仍 43%，cluster A/B 集中提供多类 pair）。
- pair_evidence_used: geometry_z_axis=9, geometry_x_axis=9, anchor_identity=9,
  functional_edge=3。
- Validators: 主 pilot 20/20 PASS, 主 main 133/133 PASS (C1–C13 + C19–C23),
  pair validator 28/28 PASS (C14–C18)。0 ERROR / 0 WARN 全过。
- difficulty_tag_counts（main 133 条）：same_label_disambiguation=119 (89%),
  geometry_aware=99 (74%), functional_relation=58 (44%), minimal_pair=56 (42%),
  multi_anchor=51 (38%), endpoint_ambiguity=21 (16%), hard_negative=15 (11%),
  simple_functional=7 (5%)。
- target_label（28 对引用的 query 中）: knob ~67%, handle ~17%, electric outlet
  4 query, remote 4 query, 其他 2 query。vs retag patch 时 85%（criteria 1
  改善 18 pp）。

Potential issues:
- [issue] FUNC_REL_CEILING_1 (PENDING_MINGQIAN_ACK)
    functional_relation 这一类全场只有 1 对。原因：6 个 scene 里只有 421380
    那台 TV 柜上的旋钮同时承担两种 relation（pull-to-open 开柜门 +
    pull-to-open-a-drawer 拉抽屉），其他 anchor 都只支持一种 relation，写不
    出第二对。本次用新写的 pair_039（q150+q151）替代了原挖矿的 pair_020，
    但数量上界仍是 1。要凑第 2 对必须扩 Phase 0 重选 scene，超出本阶段范围。
- [issue] target_label 仍以 knob 为主（informational, PENDING_MINGQIAN_ACK）
    学长 criteria 1 要求降低 knob/handle 占比。本次 knob 占比从 retag 阶段的
    85% 降到 67%（改善 18 个百分点），但还没到"均衡"。原因是 6 scene 内**非**
    knob/handle 的可用功能边只够写 6 对新 pair（outlet 2 对、handle→appliance
    1 对、remote 2 对、faucet 1 对），其余 14 对必须复用 cluster knob、靠自然
    语言改写来满足 criteria 2/3。要把 knob 占比压到 50% 以下，同样需要扩
    Phase 0 重选 scene。

Files ready for review:
- `functional_queries_v1.jsonl`（**133 条**，56 条 in-pair 带自描述 3 字段，
  pilot/main 全 validator PASS）
- `minimal_pairs_v1.jsonl`（**28 对**派生视图，每行含 pair-level 元信息
  changed_factor / why_hard / pair_evidence_used / diff_summary / target_geom_diff_m）
- `pilot_20_queries.jsonl`（20 条原 Phase 1 状态，不参与 pair）
- `pair_candidates_v1.csv`（433 候选，挖矿追溯用）
- `hard_slice_summary_v1.json`（total_queries=133；含 minimal_pairs 段 +
  query_source_breakdown）
- `validation_report.md` / `validation_report_phase3.md`（最新版）
- `scripts/phase3_pair_miner.py` + `scripts/phase3_compose_pairs.py` +
  `scripts/validate_functional_queries.py`（扩 C19-C23）+
  `scripts/validate_minimal_pairs.py`
- `summary/phase_clarify/phase3.md`（含 Revision 1 段记录正文锚定推翻）

==STOP HERE — Phase 3 完成 **28 对** minimal pair==，三 validator 全 0 ERROR /
0 WARN，4 类 changed_factor 全覆盖，6 scene 全覆盖。等学长 ack 后启动 Phase 4
long-range stress set。3 个 PENDING_MINGQIAN_ACK 待决：

1. PAIR_QUERY_CONFLICT 接受 28 对（vs 原锚定 30）
2. FUNC_REL_CEILING_1 接受 1 对 vs 扩 Phase 0 scene 集
3. target_label 67% knob 接受 vs 扩 Phase 0 进一步降占比==

---

## Phase 4 progress — 2026-05-23

Did:
- 执行 Phase 4 Long-Range Stress Set，按 `summary/phase_clarify/phase4.md` + 学长
  2026-05-23 ack 落地（junction 2-hop 替代不可实现的真同向 A→B→C 链）。
- 写 `scripts/phase4_scene_audit.py`（仅标准库）：扫描全部 20 个 SceneFun3D scene 的
  functional scene graph，输出 `phase4_junction_audit.csv`（59 候选对）+
  `phase4_audit_summary.txt`。关键发现：20 个 scene 全部是严格二部图，0 个节点同时
  具有入边和出边（bipartite confirmed），真同向 A→B→C 链在数据集层面完全不存在。
- 写 `scripts/phase4_query_generator.py`（idempotent）：30 条手写 spec（含 scene_id /
  target_uuid / anchor_uuid / reference_uuid / 两条 supporting_edge_ids / query_text /
  tags / ref_necessity / fail_modes / notes），从 frozen scene_graph 读真实 UUID+edge，
  自动算 evidence_chain / reference_label / target_anchor_3d_distance_m / distractor UUIDs。
- 生成 `long_range_stress_queries_v1.jsonl`（30 条 junction 2-hop query，独立文件与
  main JSONL 严格隔离）及 `long_range_diagnostics_v1.jsonl`（30 条诊断行）。
- 扩展 `scripts/validate_functional_queries.py`：
  ① `load_data()` 改为读取全部 20 个 scene（原只读 6 SELECTED_SCENES），使 Phase 4
     新增的 6 个 scene（421063/422391/422813/460417/466192/466803）可校验；
  ② C1 检查接受 `lr_v1_NNNNNN` 格式（原只接受 `human_func_v1_`）；
  ③ C7 放宽：long_range query 只检查 edge[0] source = target_node_id（edge[1] source
     是 reference_node_id，不同节点，属设计意图）；
  ④ C8 对 long_range query 跳过（C26 junction anchor 一致性取代）；
  ⑤ 新增 C24–C29 六项 long_range 专用检查（见下方）；
  ⑥ write_report() 增加 reference_necessity 分布统计。
- 更新 `hard_slice_summary_v1.json`：追加 `long_range_stress` 段（30 条统计 + scene
  分布 + tag 分布 + reference_necessity 分布 + 6 新 scene 说明）。
- 写 `validation_report_phase4.md`（Phase 4 专用报告）。
- 未触碰 frozen 目录、Phase 1–3 文件内容、multimodal_extension/。

Counts:
- long_range_stress_queries_v1.jsonl：**30 条**，全部 validator PASS（0 ERROR / 0 WARN）。
- 新增 scene：421063 (2), 422391 (2), 422813 (2), 460417 (5), 466192 (2), 466803 (2)。
  保留原 6 scene 中有 junction 的两个：421380 (8), 469011 (7)。
  原 6 scene 中 4 个零 junction：421254 / 421602 / 421013 / 420683（结构性原因）。
- reference_necessity: strict=10 (33.3%), contextual=20 (66.7%)。phase4.md 锚定 ≥30%
  strict，已满足（33.3%）。
- Difficulty tags（30 条）：long_range=30, functional_relation=30,
  same_label_disambiguation=14, geometry_aware=13, hard_negative=4, multi_anchor=4。
- evidence_hop_count: 全部 = 2（==结构性上限，非设计选择：20 个 scene 全部严格二部图==，
  phase4_scene_audit.py 确认 chain bridges = 0，3-hop 在当前数据集层面不可实现）；
  long_range_pattern: 全部 "junction_2hop"。TASK_PLAN §11 允许 ≥2，本批上限即为 2。
- Validator 回归：pilot_20_queries.jsonl 20/20 PASS，functional_queries_v1.jsonl
  133/133 PASS，long_range_stress_queries_v1.jsonl 30/30 PASS（C24–C29 全通过）。

新增检查 C24–C29（仅作用于 is_long_range=true 的 query）：
- C24: supporting_edge_ids + evidence_chain 长度都 ≥ 2 且相等
- C25: 所有 supporting_edge 存在于 scene_graph（由 C6 覆盖）
- C26: junction_2hop 时所有 edge target（"|" 右端）相同 = shared_anchor
- C27: target / shared_anchor / reference 三个 UUID 互不相同
- C28: difficulty_tags 必须含 long_range
- C29: reference_necessity 必须是 "strict" 或 "contextual"

Potential issues:
- ==[issue]==scope=phase4_hop_ceiling
    problem=TASK_PLAN §11 允许 evidence_hop_count ≥ 2，但本批 30 条全部 = 2，无法写出
    3-hop 或更长的链。
    
    原因：SceneFun3D scene_graph 只有功能交互边（pull/rotate/control/
    provide power 等 21 种），没有空间关系边（near/supports/on 等）；且功能边全部是
    interactive element → appliance 的单向结构，任何 appliance 都无出边，图上不存在
    A→B→C 三节点同向链。当前数据集层面的 hop 上限即为 2。
    suggested_fix=数据集结构性约束，非实现问题。若后续基于 bbox 坐标推导空间边并
    扩展 schema，可实现 3-hop。当前无需处理，学长 ack 后关闭。

Files ready for review:
- `long_range_stress_queries_v1.jsonl`（**30 条** junction 2-hop，全 validator PASS）
- `long_range_diagnostics_v1.jsonl`（30 条诊断行）
- `hard_slice_summary_v1.json`（追加 long_range_stress 段）
- `validation_report_phase4.md`（Phase 4 专用报告）
- `phase4_junction_audit.csv` + `phase4_audit_summary.txt`（Step 0 扫描结果）
- `scripts/phase4_scene_audit.py` + `scripts/phase4_query_generator.py`
- `scripts/validate_functional_queries.py`（扩 C24–C29 + 全 scene 加载 + lr_v1 格式）
- `summary/phase_clarify/phase4.md`（Phase 4 详细计划文档）

==STOP HERE — Phase 4 完成 **30 条** long-range stress query==，全 validator PASS，
strict reference_necessity 33.3%（≥30% 满足）。等学长 ack 后进入 Phase 5
（existing query audit）或结束。==

---

## Phase 4 Expansion + Benchmark-v2 Release (2026-05-23)

Per Mingqian's feedback, expanded long_range_stress_queries_v1.jsonl from 30 → 40 queries and produced the full Benchmark-v2 release package.

### long_range_stress_queries_v1.jsonl expansion (q031–q040)

10 new **strict** queries added, bringing totals to 40 queries / 20 strict = 50.0%:

- **q031–q032** (scene 469011): oven handle (47d6518d) as target, reference = leftmost knob (d003c3b8) and rightmost knob (85f5f2f0) respectively. Strict because 2 handles in scene (oven + fridge); fridge has no rotating-knob control.
- **q033** (scene 460417): WM knob/button (a6956e03) as target, reference = dedicated outlet 59552624 (powers WM only, not dryer). Strict because dryer also has a knob but no dedicated outlet.
- **q034–q035** (scene 421063): sink/bathtub faucet as target, reference = higher/lower button. Strict by geometry — both fixtures have buttons; height disambiguates.
- **q036–q037** (scene 422813): same pattern as q034/q035 in the second bathroom scene.
- **q038–q040** (scene 469011): oven handle (47d6518d) as target, reference = 2nd-from-left knob (06b684bb), middle knob (28e9ec26), 2nd-from-right knob (76002344). Different supporting_edge_ids per query → no C13 conflict.

Scripts used:
- `scripts/append_queries_031_040.py` — initial append of q031–q040
- `scripts/fix_queries_038_040.py` — replaced original q038–q040 (which had C13 conflicts) with correct oven-handle strict variants

### Benchmark-v2 release package files created

- `summary/benchmark_v2_release_summary.md` — query counts, validator status, slice breakdown, scene coverage, target label distribution
- `summary/benchmark_v2_changelog.md` — Phase 1–4 history, what is/isn't in the main split
- `summary/benchmark_v2_coverage_audit.md` — quantitative coverage analysis (geometry, supporting edges, distractors, tag co-occurrence)

### Validator status (all three files, 2026-05-23)

| File | Queries | Result |
|---|---|---|
| `pilot_20_queries.jsonl` | 20 | PASS (0 error, 0 warning) |
| `functional_queries_v1.jsonl` | 133 | PASS (0 error, 0 warning) |
| `long_range_stress_queries_v1.jsonl` | 40 | PASS (0 error, 0 warning) |

==Benchmark-v2 data freeze complete. Steps 3–5 of release package delivered. Robot trials sidecar (Steps 6–8) pending.==