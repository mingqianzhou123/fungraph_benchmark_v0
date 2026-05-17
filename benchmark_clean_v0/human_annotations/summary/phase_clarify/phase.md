# Phase Plan: Benchmark Quality Extension for Functional Grounding

> 任务性质：数据标注与质量审计任务，不是方法实验任务。你负责生产高质量、可审计的人工 functional query 数据集扩展；学长 Mingqian 负责把这些数据用于 FCGP/L-FCGP 训练、主实验和论文。

---

## 背景：你在整个项目中的位置

学长正在写一篇 CoRL 论文，题目是 **Function-Conditioned Graph Propagation (FCGP)**，核心思路是：给定自然语言指令，在功能性 3D 场景图中检索支持功能关系的子图，然后用 LLM 对目标物体定位（grounding）。

目前 benchmark 已经建好了（frozen），支持：
- 自然语言 query
- 场景图节点（target / anchor）
- 支持功能边（supporting edge）
- 文本级别的 functional / spatial / semantic query

**但是**，为了让论文更 solid，需要两方面的补强：

```
1. 数据集本身更可信：
   - 更多人工写的、人工验证的 functional queries
   - 每条 query 有清晰的 supporting evidence（不能靠 label prior 作弊）
   - 每个 hard case 有可审计的难点标签

2. 方法分析更有说服力：
   - 不只看 overall R@1
   - 能单独分析 same-label、endpoint ambiguity、geometry-aware、hard negative 等关键 slice
   - 能证明方法真正用到了 functional edge / endpoint / geometry，而不是只靠 object label prior
```

这个任务不是让你改 FCGP/EFCG 方法，也不是让你跑主实验。

你的任务是：

```
为 benchmark_clean_v0 增加一个高质量、可审计、append-only 的 functional grounding 数据扩展层。
```

Mingqian 会负责：

```
方法训练
主实验
paper table
最终是否把这些 query 纳入正式 benchmark
```

你负责：

```
人工 query 标注
query quality audit
hard-slice 标注
minimal-pair / adversarial query 设计
validator / validation report
```

重要：这些输出作为 sidecar extension，不要覆盖现有 benchmark。

---

## 规则：必须遵守

```
禁止修改：
  benchmark_clean_v0/queries/
  benchmark_clean_v0/graphs/
  benchmark_clean_v0/geometry/
  benchmark_clean_v0/annotations/
  benchmark_clean_v0/manifests/
  benchmark_clean_v0/multimodal_extension/
  benchmark_clean_v0/INTERN_GEOMETRY_TASK_PLAN.md

所有新文件只能写到：
  benchmark_clean_v0/human_annotations/functional_queries_v1/
```

如果你发现原始 query 或 graph 有问题，不要直接改，请写到：

```
annotation_notes.md
```

格式：

```
[issue] scene_id=... query_id=... problem=... suggested_fix=...
```

---

## 主要输入文件

| 文件 | 用途 |
|------|------|
| `queries/all_queries_index.jsonl` | 全量 query（14,678 条，每行一条 JSON） |
| `queries/train/val/test_queries_index.jsonl` | 按 split 的 query index |
| `queries/scenefun3d_funrag_benchmark_enriched.json` | 完整场景图（含节点和边），需要时读取 |
| `geometry/scenefun3d_node_geom.json` | 节点 bbox 信息（center/min/max） |
| `multimodal_extension/node_geometry_features.csv` | 节点 geometry 特征（辅助判断空间位置） |
| `multimodal_extension/feature_index.json` | node feature 索引 |
| `annotations/openfungraph/SceneFun3D.annotations.json` | 原始 OpenFunGraph 节点标注 |
| `annotations/openfungraph/SceneFun3D.relations.json` | 原始功能边标注 |

**数据规模参考：**
- SceneFun3D：1,485 queries（870 functional / 405 spatial / 210 semantic），20 scenes，317 nodes 有 bbox
- 3DSSG：13,193 queries（本任务只处理 SceneFun3D 部分）

---

## 总体交付目标

最终交付不是一个单独文件，而是一组可审计 sidecar：

```
1. pilot_20_queries.jsonl
   - 提交 20 条人工 functional queries 给 Mingqian review

2. functional_queries_v1.jsonl
   - pilot 通过后扩展到 80-150 条高质量 local functional queries

3. long_range_stress_queries_v1.jsonl
   - 30-50 条 long-range stress queries，单独保存，不混入主 benchmark

4. minimal_pairs_v1.jsonl
   - 同一 scene 中只改 anchor / spatial qualifier / functional relation 的 query pairs

5. functional_query_diagnostics_v1.jsonl
   - 每条新增 query 的难点、是否 label-only solvable、distractor 数量、预期失败模式

6. existing_query_quality_audit_v1.csv
   - 对现有 SceneFun3D functional queries 的质量审计

7. hard_slice_summary_v1.json
   - same-label / endpoint / geometry-aware / hard-negative / human-authored 等 slice 的统计

8. validation_report.md
   - validator 检查结果、发现的问题、不能自动判断的 case
```

---

## 新增 Query 的 JSONL Schema

每行是一个 JSON object。

必须字段：

```json
{
  "query_id": "human_func_v1_000001",
  "scene_id": "420683",
  "query_text": "press the switch that controls the desk lamp",
  "query_type": "functional",
  "target_node_id": "switch_03",
  "anchor_node_id": "lamp_01",
  "supporting_edge_ids": ["switch_03|control|lamp_01"],
  "difficulty_tags": ["same_label_disambiguation", "endpoint_ambiguity"],
  "is_long_range": false,
  "evidence_chain": ["switch_03 --control--> lamp_01"],
  "source": "human",
  "notes": "Multiple switches exist; the controls edge disambiguates the target."
}
```

可选但推荐字段：

```json
{
  "target_label": "switch",
  "anchor_label": "desk lamp",
  "expected_failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_switch"],
  "geometry_cues": ["lower", "left"],
  "num_same_label_distractors": 3,
  "is_label_only_solvable": false
}
```

---

## Difficulty Tags（只能用这些，不许临时发明新 tag）

如需新增 tag，必须先写到 `annotation_notes.md` 等 Mingqian 确认。

| Tag | 含义 |
|-----|------|
| `simple_functional` | 简单、无跳转功能关系，保留一部分避免数据全是难例 |
| `functional_relation` | 必须依赖 controls / opens / powers / connected_to / part_of 等功能关系 |
| `same_label_disambiguation` | 场景中存在多个同类 target 候选，例如多个 switch / knob / handle / drawer |
| `endpoint_ambiguity` | supporting edge 两端都可能被模型误选，例如 handle opens drawer，target 应该是 handle |
| `geometry_aware` | query 使用 lower / upper / left / right / near / far / top / bottom 等几何描述，且 geometry 有助于唯一定位 |
| `multi_anchor` | query 中出现多个 reference objects |
| `hard_negative` | query 表面上是 semantic 或 spatial，但正确答案必须依赖 functional edge |
| `minimal_pair` | 与另一条 query 形成最小差异对，只改了一个 anchor、改变语义 functional relation |
| `long_range` | 需要多跳 evidence chain，必须单独放到 long_range_stress_queries_v1.jsonl |

一条 query 可以有多个 tag，比例不需要加起来等于 100%。

---

## Phase 0 — 备选 Scene / Edge 遴选（准备工作）

### 目标
找到标注价值最高的 scenes 和 functional edges，为后续写 query 打基础。

### 做什么
读取 SceneFun3D benchmark，统计每个 scene：

```
functional edge 数量
switch / knob / handle / drawer / button / remote 等可操作 target 数量
same-label candidate 数量
有 bbox 的 target / anchor 数量
```

优先选择：
```
1. functional edges 丰富的 scene
2. 有多个同类 distractors 的 scene
3. 有 handle-drawer / switch-lamp / knob-appliance 等 endpoint ambiguity 的 scene
4. geometry 可以区分 upper/lower/left/right 的 scene
```

### 输出

写到：

```
annotation_notes.md
```

至少包含：

```markdown
selected_scenes:
  - scene_id: ...
    why_selected: ...（为什么选这个 scene）
    candidate_edges: ...（有哪些可用的 functional edges）
    same_label_candidates: ...（有哪些同类干扰物）
    has_geometry: ...（哪些节点有 bbox）
```

### 停止条件

选出至少：

```
6 个 scenes
30 条候选 functional edges
```

然后进入 Phase 1。

---

## Phase 1 — Pilot 20 条人工 Queries（必须，评审门槛 ⚠️）

### 目标
验证 schema、query 风格、evidence_chain、validator 是否工作，让 Mingqian 确认方向后再大规模扩展。

### 做什么
写 20 条高质量人工 query，构成：

```
10 条 local functional（直接功能关系）
5  条 same-label / endpoint hard cases
3  条 geometry-aware functional
2  条 hard negative
```

不要在 pilot 里放 long-range，除非单独放到 long_range 文件。

### 每条 query 必须满足

```
有唯一 target
target_node_id 存在于 scene graph
anchor_node_id 存在于 scene graph
supporting_edge_ids 存在于 scene graph
target 和 anchor 至少能被 evidence_chain 清楚解释
difficulty_tags 与 scene 事实一致
```

### 输出文件

| 文件 | 内容 |
|------|------|
| `pilot_20_queries.jsonl` | 20 条 pilot queries |
| `annotation_notes.md` | Phase 0 选场景 + Phase 1 过程记录 |
| `validation_report.md` | validator 跑完的结果 |

### 评审门槛（Escalation gate）

Phase 1 完成后先停下来，发给 Mingqian review。

不要直接扩到 80 条。

---

## Phase 2 — 正式 Local Functional Query 扩展（80–150 条）

### 目标
扩展主人工 functional set，提高 benchmark 的 human-authored 质量。

### 数量目标

```
minimum: 80 条
ideal:   150 条
stretch: 200 条
```

质量比数量重要，不要为了凑数写模糊 query。

### 推荐构成比例（可以调整，一条 query 可有多个 tag）

| Tag | 建议比例 |
|-----|---------|
| `simple_functional` | 20–30% |
| `same_label_disambiguation` | 25–35% |
| `endpoint_ambiguity` | 20–30% |
| `geometry_aware` | 15–25% |
| `hard_negative` | 10–20% |
| `multi_anchor` | 5–10% |

### 输出文件

| 文件 | 内容 |
|------|------|
| `functional_queries_v1.jsonl` | 80–150 条主 functional queries |
| `functional_query_diagnostics_v1.jsonl` | 每条 query 的诊断信息（难点、失败模式、distractor 数等） |
| `hard_slice_summary_v1.json` | 按 tag 统计的 slice 计数（给 Mingqian 用） |
| `validation_report.md` | 更新后的 validator 报告 |

### functional_query_diagnostics_v1.jsonl Schema

每行对应一条 query：

```json
{
  "query_id": "human_func_v1_000001",
  "scene_id": "420683",
  "is_label_only_solvable": false,
  "num_same_label_distractors": 3,
  "expected_failure_modes": ["same_label_wrong_switch", "choose_anchor"],
  "distractor_node_ids": ["switch_01", "switch_02"],
  "geometry_cues_used": ["lower"],
  "evidence_hop_count": 1
}
```

### 每条 query 质量自检清单

```
1. 为什么答案是这个 target？（不是其他同名 candidate？）
2. 哪条 supporting edge / evidence chain 支撑这个答案？（不能靠 label prior 猜）
3. 这个 query 难在哪里？能不能被 label-only shortcut 解决？
```

如果这三个问题答不清楚，不要收进 `functional_queries_v1.jsonl`。

---

## Phase 3 — Minimal-Pair / Adversarial Queries（15–30 pairs）

### 目标
证明模型真正使用了 functional evidence / geometry / anchor，而不是 label prior。

### 什么是 minimal pair

同一 scene 中两条 query 只改了一个关键条件，但答案不同。

示例：

```
Query A: "press the switch that controls the desk lamp"
Query B: "press the switch that controls the ceiling light"
（changed_factor: anchor_object）

Query A: "pull the handle on the upper drawer"
Query B: "pull the handle on the lower drawer"
（changed_factor: spatial_qualifier / geometry）

Query A: "turn the knob connected to the left burner"
Query B: "turn the knob connected to the right burner"
（changed_factor: spatial_qualifier）
```

### 输出

写到：

```
minimal_pairs_v1.jsonl
```

每行：

```json
{
  "pair_id": "minpair_v1_000001",
  "scene_id": "420683",
  "query_a_id": "human_func_v1_000021",
  "query_b_id": "human_func_v1_000022",
  "changed_factor": "anchor_object",
  "why_hard": "Both queries ask for a switch; only the controlled object changes."
}
```

`changed_factor` 建议值：
```
anchor_object
spatial_qualifier
functional_relation
geometry_direction
```

### 数量目标

```
minimum: 15 pairs
ideal:   30 pairs
```

---

## Phase 4 — Long-Range Stress Set（30–50 条）

### 目标
专门测试 FCGP / EFCG 的多跳边界，单独保存，不混入主 benchmark。

**重要：这不是主 benchmark，不要混入 `functional_queries_v1.jsonl`。**

写到：

```
long_range_stress_queries_v1.jsonl
```

### 什么算 long-range

需要两个或更多 evidence steps：

```
示例 scene 结构：
  bed --near--> desk
  desk --supports--> lamp
  switch --controls--> lamp
  target = switch

示例 query：
  "press the switch for the lamp on the desk beside the bed"

Evidence chain（3+ hops）：
  bed → desk → lamp → switch
```

### 数量目标

```
minimum: 30 条
ideal:   50 条
```

### 注意

当前 EFCG 主要是 local endpoint grounding，不要把 long-range stress set 当成主结果。这是一个额外压力测试集。

### 输出

| 文件 | 内容 |
|------|------|
| `long_range_stress_queries_v1.jsonl` | 30–50 条 long-range queries（单独文件） |

---

## Phase 5 — Existing Query Quality Audit

### 目标
审计现有 SceneFun3D functional queries，让 paper 可以诚实报告数据质量。

### 审计对象

```
benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json
```

只审计：

```
dataset == "scenefun3d"
query_type == "functional"
```

### 输出

```
existing_query_quality_audit_v1.csv
```

建议列：

```
query_id
scene_id
split
query
annotation_source
target_node_ids
anchor_node_id
supporting_edge_ids
is_answer_unique
is_label_only_solvable
requires_functional_edge
requires_endpoint_resolution
has_same_label_distractor
num_same_label_distractors
has_geometry
quality_flags
notes
```

### quality_flags 建议值

| 值 | 含义 |
|----|------|
| `ok` | 通过所有检查 |
| `ambiguous_query` | 表述不清晰 |
| `missing_supporting_edge` | edge 不存在于 scene graph |
| `target_not_endpoint` | target / anchor 混淆 |
| `label_only_easy` | 不需要 functional edge 就能解决 |
| `weak_functional_wording` | 功能描述措辞很弱 |
| `needs_human_review` | 边界情况，需要人工判断 |

---

## Phase 6 — Validator（必须）

### 目标
新增 query 不能只靠人工目测检查，必须有脚本做基础一致性验证。

### 输出文件

| 文件 | 内容 |
|------|------|
| `scripts/validate_functional_queries.py` | 验证脚本 |
| `validation_report.md` | 验证报告（每次运行更新） |

### Validator 必须检查

对每条新增 query：

```
query_id 是否唯一
scene_id 是否存在
target_node_id 是否存在于 scene graph
anchor_node_id 是否存在于 scene graph
supporting_edge_ids 是否存在于 scene graph
supporting edge 是否连接 target/anchor，或 evidence_chain 是否解释多跳
difficulty_tags 是否来自固定 tag list
same_label_disambiguation tag 是否确实有同名 distractor
geometry_aware tag 的相关 nodes 是否有 bbox
minimal_pair 引用的 query_id 是否存在
long_range query 是否只出现在 long_range_stress_queries_v1.jsonl
```

### validation_report.md 至少包含

```markdown
## Validation Report — YYYY-MM-DD

Total queries checked: N
✓ Passed: N
✗ Failed: N

Warnings by type:
- missing_supporting_edge: N
- invalid_tag: N
- same_label_tag_without_distractor: N
- geometry_tag_without_bbox: N

Needs human review:
- human_func_v1_000005: reason...
- human_func_v1_000042: reason...

Hard-slice counts:
  same_label_disambiguation: N
  endpoint_ambiguity: N
  geometry_aware: N
  hard_negative: N
  minimal_pair: N
  long_range: N
```

---

## Phase 7 — Hard-Slice Summary（给论文用）

### 目标
给 Mingqian 和 paper table / analysis 时直接可用的统计。

### 输出

```
hard_slice_summary_v1.json
```

### Schema

```json
{
  "total_human_functional_queries": 120,
  "by_tag": {
    "simple_functional": 30,
    "same_label_disambiguation": 45,
    "endpoint_ambiguity": 38,
    "geometry_aware": 22,
    "hard_negative": 18,
    "multi_anchor": 9
  },
  "minimal_pairs": 24,
  "long_range_stress_queries": 40,
  "scenes_covered": 12,
  "avg_queries_per_scene": 10.0,
  "label_only_solvable_count": 8,
  "label_only_solvable_ratio": 0.067
}
```

---

## 必须交付的文件清单

```
benchmark_clean_v0/human_annotations/functional_queries_v1/
├── TASK_PLAN_BENCHMARK_QUALITY_EXTENSION.md    # 已存在，不要改
│
├── annotation_notes.md                          # Phase 0 + 各阶段进度记录
├── validation_report.md                         # Validator 报告（随时更新）
│
├── pilot_20_queries.jsonl                       # Phase 1（必须审核门槛）
│
├── functional_queries_v1.jsonl                  # Phase 2 主 query 集
├── functional_query_diagnostics_v1.jsonl        # Phase 2 诊断信息
│
├── minimal_pairs_v1.jsonl                       # Phase 3
│
├── long_range_stress_queries_v1.jsonl           # Phase 4（单独文件）
│
├── existing_query_quality_audit_v1.csv          # Phase 5
│
├── hard_slice_summary_v1.json                   # Phase 7
│
└── scripts/
    └── validate_functional_queries.py            # Phase 6
```

---

## 推荐工作顺序

```
Phase 0: 选 scene / edge，写 annotation_notes.md
Phase 1: pilot_20_queries.jsonl + validation_report.md
STOP: 等 Mingqian review
Phase 2: functional_queries_v1.jsonl 扩展到 80-150 条
Phase 3: minimal_pairs_v1.jsonl
Phase 4: long_range_stress_queries_v1.jsonl
Phase 5: existing_query_quality_audit_v1.csv
Phase 6: validate_functional_queries.py（建议在 Phase 1 就先写好）
Phase 7: hard_slice_summary_v1.json
```

如果时间不够，优先级是：

```
1. Phase 1 pilot（验证方向）
2. Phase 6 validator（可复用工具）
3. Phase 2 高质量 local functional queries（核心交付）
4. Phase 3 minimal pairs（对论文价值高）
5. Phase 5 existing query audit
6. Phase 4 long-range stress set
7. Phase 7 summary
```

---

## 时间安排参考

| 时间 | 任务 |
|------|------|
| 第 1-2 天 | Phase 0：读 benchmark，选 scene，写 annotation_notes.md |
| 第 2-3 天 | Phase 6：先把 validator 写好，后续每个 phase 都能用 |
| 第 3-5 天 | Phase 1：写 20 条 pilot queries，跑 validator，交 Mingqian 审核 |
| 等审核通过 | Phase 2：扩展到 80-150 条主 queries |
| 之后 | Phase 3：minimal pairs |
| 之后 | Phase 5：existing query audit |
| 之后 | Phase 4：long-range stress set |
| 最后 | Phase 7：hard_slice_summary_v1.json |

---

## 向 Mingqian 汇报的格式

每完成一个 phase，请在 `annotation_notes.md` 末尾追加：

```markdown
## Phase X progress — YYYY-MM-DD

Did:
- 选了 X 个 scenes
- 写了 N 条 queries，类型分布：simple_functional=N, same_label=N, ...
- validator 通过率：N/N

Counts:
- pilot_20_queries.jsonl: N 条
- functional_queries_v1.jsonl: N 条（累计）
- minimal_pairs: N pairs

Potential issues:
- [issue] scene_id=420683 query_id=... problem=... suggested_fix=...

Files ready for review:
- pilot_20_queries.jsonl
- validation_report.md
```

**Phase 1 和 Phase 2 完成后必须停下来等 review。**

任何卡住超过半天的问题，立即找 Mingqian，不要自己猜。

---

## 这个任务对 paper 的价值

完成后，论文可以说：

> We supplement the benchmark with N human-authored functional queries, categorized into difficulty slices: same-label disambiguation (N), endpoint ambiguity (N), geometry-aware (N), and hard negatives (N). Each query is accompanied by a verified evidence chain. We further construct N minimal pairs to probe whether models use functional evidence rather than label priors.

这让项目从 **依赖已有 SceneFun3D 标注** 升级为 **有自己的高质量人工 benchmark 扩展**，让 analysis section 有具体数字可说。
