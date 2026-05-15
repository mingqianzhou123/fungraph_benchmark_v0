# Task Plan: Benchmark Quality Extension for Functional Grounding

## 0. 为什么要做

我们现在的 benchmark 已经可以支持 FCGP / L-FCGP / EFCG 的主实验，但为了让 paper 更 solid，还需要补强两个方面：

```text
1. 数据集本身更可信：
   - 更多人工写、人工验证的 functional queries
   - 每条 query 有清楚的 supporting evidence
   - 每个 hard case 有可审计的难点标签

2. 方法分析更有说服力：
   - 不只报 overall R@1
   - 能单独分析 same-label、endpoint ambiguity、geometry-aware、hard negative 等关键 slice
   - 能证明方法真的用到了 functional edge / endpoint / geometry，而不是只靠 object label prior
```

这个任务不是让你改 FCGP / EFCG 方法，也不是让你跑主实验。

你的任务是：

```text
为 benchmark_clean_v0 增加一个高质量、可审计、append-only 的 functional grounding 数据扩展层。
```

Mingqian 会负责：

```text
方法训练
主实验
paper table
最终是否把这些 query 合入正式 benchmark
```

你负责：

```text
人工 query 标注
query quality audit
hard-slice 标注
minimal-pair / adversarial query 设计
validator / validation report
```

重要：这些输出先作为 sidecar extension，不要覆盖现有 benchmark。

---

## 1. 工作位置

所有新文件都写到：

```text
benchmark_clean_v0/human_annotations/functional_queries_v1/
```

建议最终目录结构：

```text
benchmark_clean_v0/human_annotations/functional_queries_v1/
  TASK_PLAN_HUMAN_FUNCTIONAL_QUERIES.md
  TASK_PLAN_BENCHMARK_QUALITY_EXTENSION.md
  pilot_20_queries.jsonl
  functional_queries_v1.jsonl
  long_range_stress_queries_v1.jsonl
  minimal_pairs_v1.jsonl
  functional_query_diagnostics_v1.jsonl
  existing_query_quality_audit_v1.csv
  hard_slice_summary_v1.json
  annotation_notes.md
  validation_report.md
  scripts/
    validate_functional_queries.py
```

---

## 2. 绝对不能改的文件

不要修改这些 frozen benchmark 文件：

```text
benchmark_clean_v0/queries/
benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/
benchmark_clean_v0/annotations/
benchmark_clean_v0/manifests/
benchmark_clean_v0/multimodal_extension/
benchmark_clean_v0/INTERN_GEOMETRY_TASK_PLAN.md
```

如果你觉得某个原始 query 或 graph 有问题，不要直接改。请写到：

```text
annotation_notes.md
validation_report.md
```

格式：

```text
[issue] scene_id=... query_id=... problem=... suggested_fix=...
```

---

## 3. 主要输入文件

优先使用轻量 query index：

```text
benchmark_clean_v0/queries/all_queries_index.jsonl
benchmark_clean_v0/queries/train_queries_index.jsonl
benchmark_clean_v0/queries/val_queries_index.jsonl
benchmark_clean_v0/queries/test_queries_index.jsonl
```

需要完整 scene graph 时读取：

```text
benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json
```

需要 geometry 时读取：

```text
benchmark_clean_v0/geometry/scenefun3d_node_geom.json
benchmark_clean_v0/multimodal_extension/node_geometry_features.csv
benchmark_clean_v0/multimodal_extension/feature_index.json
```

需要追溯 OpenFunGraph 原始 annotation / relation 时读取：

```text
benchmark_clean_v0/annotations/openfungraph/SceneFun3D.annotations.json
benchmark_clean_v0/annotations/openfungraph/SceneFun3D.relations.json
```

---

## 4. 总体交付目标

最终交付不是一个单独文件，而是一组可审计 sidecar：

```text
1. pilot_20_queries.jsonl
   - 先交 20 条人工 functional queries 给 Mingqian review

2. functional_queries_v1.jsonl
   - pilot 通过后扩展到 80-150 条高质量 local functional queries

3. long_range_stress_queries_v1.jsonl
   - 30-50 条 long-range stress queries，单独保存，不混入主 benchmark

4. minimal_pairs_v1.jsonl
   - 同一 scene 中只改变 anchor / spatial qualifier / functional relation 的 query pairs

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

## 5. 新增 query 的 JSONL schema

每一行是一个 JSON object。

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

## 6. ==Difficulty Tags==

请只使用下面这些 tag。不要临时发明新 tag，除非写在 `annotation_notes.md` 里等 Mingqian 确认。

```text
simple_functional
functional_relation
same_label_disambiguation
endpoint_ambiguity
geometry_aware
multi_anchor
hard_negative
minimal_pair
long_range
```

==含义：==

```text
simple_functional:
  简单一跳功能关系。保留一部分，避免数据全是难例。

functional_relation:
  必须依赖 controls / opens / powers / connected_to / part_of 等功能关系。

same_label_disambiguation:
  场景中存在多个同名 target 候选，例如多个 switch / knob / handle / drawer。

endpoint_ambiguity:
  supporting edge 两端都可能被模型误选，例如 handle opens drawer，target 应该是 handle。

geometry_aware:
  query 使用 lower / upper / left / right / near / far / top / bottom 等几何描述，且 geometry 有助于唯一定位。

multi_anchor:
  query 中出现多个 reference objects。

hard_negative:
  query 表面上像 semantic 或 spatial，但正确答案必须依赖 functional edge。

minimal_pair:
  与另一条 query 构成最小差异对，只改变一个 anchor、方向词或 functional relation。

long_range:
  需要多跳 evidence chain。必须单独放到 long_range_stress_queries_v1.jsonl。
```

---

## 7. Phase 0 — 准备和 scene/edge 选择

目标：先找值得标注的 scenes 和 functional edges。

### 做什么

读取 SceneFun3D benchmark，统计每个 scene：

```text
functional edge 数量
switch / knob / handle / drawer / button / remote 等可操作 target 数量
same-label candidate 数量
有 bbox 的 target / anchor 数量
```

优先选择：

```text
1. functional edges 丰富的 scene
2. 有多个同名 distractors 的 scene
3. 有 handle-drawer / switch-lamp / knob-appliance 等 endpoint ambiguity 的 scene
4. geometry 可以区分 upper/lower/left/right 的 scene
```

### 输出

写到：

```text
annotation_notes.md
```

至少包含：

```text
selected_scenes:
  - scene_id: ...
    why_selected: ...
    candidate_edges: ...
    same_label_candidates: ...
```

### 停止条件

选出至少：

```text
6 个 scenes
30 条候选 functional edges
```

然后进入 Phase 1。

---

## 8. Phase 1 — Pilot 20 条人工 queries

目标：先验证 schema、query 风格、evidence_chain、validator 是否工作。

### 做什么

写 20 条高质量人工 query：

```text
10 条 local functional
5 条 same-label / endpoint hard cases
3 条 geometry-aware functional
2 条 hard negative
```

不要在 pilot 里写 long-range，除非单独放到 long_range 文件。

### 输出

```text
pilot_20_queries.jsonl
annotation_notes.md
validation_report.md
```

### 成功标准

每条 query 必须：

```text
有唯一 target
target_node_id 存在于 scene graph
anchor_node_id 存在于 scene graph
supporting_edge_ids 存在于 scene graph
target 和 anchor 至少能被 evidence_chain 清楚解释
difficulty_tags 与 scene 事实一致
```

### Escalation gate

Phase 1 完成后先停下来，发给 Mingqian review。

不要直接扩到 80 条。

---

## 9. Phase 2 — 正式 local functional query 扩展

目标：扩展主人工 functional set，提高 benchmark 的 human-authored 质量。

### 数量目标

```text
minimum: 80 条
ideal: 150 条
stretch: 200 条
```

质量比数量重要。不要为了凑数写模糊 query。

### 推荐比例

```text
simple_functional: 20-30%
same_label_disambiguation: 25-35%
endpoint_ambiguity: 20-30%
geometry_aware: 15-25%
hard_negative: 10-20%
multi_anchor: 5-10%
```

一条 query 可以有多个 tag，所以比例不需要加起来等于 100%。

### 输出

```text
functional_queries_v1.jsonl
functional_query_diagnostics_v1.jsonl
hard_slice_summary_v1.json
validation_report.md
```

---

## 10. Phase 3 — Minimal-pair / adversarial queries

目标：证明模型真的使用 functional evidence / geometry / anchor，而不是 label prior。

### 什么是 minimal pair

同一 scene 中两条 query 只改变一个关键条件，但答案不同。

例子：

```text
press the switch that controls the desk lamp
press the switch that controls the ceiling light
```

```text
pull the handle on the upper drawer
pull the handle on the lower drawer
```

```text
turn the knob connected to the left burner
turn the knob connected to the right burner
```

### 输出 schema

写到：

```text
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

### 数量目标

```text
minimum: 15 pairs
ideal: 30 pairs
```

---

## 11. Phase 4 — Long-range stress set

目标：专门测试 FCGP / EFCG 的多跳边界。

重要：这不是主 benchmark，不要混入 `functional_queries_v1.jsonl`。

写到：

```text
long_range_stress_queries_v1.jsonl
```

### 什么算 long-range

需要两个或更多 evidence steps：

```text
bed --near--> desk
desk --supports--> lamp
switch --controls--> lamp
target = switch
```

示例 query：

```text
press the switch for the lamp on the desk beside the bed
```

### 数量目标

```text
minimum: 30 条
ideal: 50 条
```

### 注意

当前 EFCG 主要是 local endpoint grounding，不要把 long-range stress set 当成主结果。

---

## 12. Phase 5 — Existing query quality audit

目标：审计现有 SceneFun3D functional queries，让 paper 可以透明报告数据质量。

### 审计对象

现有文件：

```text
benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json
```

只审计：

```text
dataset = scenefun3d
query_type = functional
```

### 输出

```text
existing_query_quality_audit_v1.csv
```

建议列：

```text
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

```text
ok
ambiguous_query
missing_supporting_edge
target_not_endpoint
label_only_easy
weak_functional_wording
needs_human_review
```

---

## 13. Phase 6 — Validator

目标：新增 query 不能只靠人工肉眼检查，必须有脚本做基础一致性验证。

### 输出

```text
scripts/validate_functional_queries.py
validation_report.md
```

### Validator 必须检查

对每条新增 query：

```text
query_id 是否唯一👍
scene_id 是否存在
target_node_id 是否存在于 scene graph
anchor_node_id 是否存在于 scene graph
supporting_edge_ids 是否存在于 scene graph
supporting edge 是否连接 target/anchor，或 evidence_chain 是否解释多跳
difficulty_tags 是否来自固定 tag list
same_label_disambiguation tag 是否真的有同名 distractor
geometry_aware tag 的相关 nodes 是否有 bbox
minimal_pair 引用的 query_id 是否存在
long_range query 是否只出现在 long_range_stress_queries_v1.jsonl
```

### validation_report.md 至少包含

```text
total queries checked
passed / failed counts
warnings by type
list of query_ids needing human review
hard-slice counts
```

---

## 14. Phase 7 — Hard-slice summary

目标：给 Mingqian 做 paper table / analysis 时直接可用。

输出：

```text
hard_slice_summary_v1.json
```

内容：

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
  "avg_queries_per_scene": 10.0
}
```

---

## 15. 推荐工作顺序

```text
Phase 0: 选 scene / edge，写 annotation_notes.md
Phase 1: pilot_20_queries.jsonl + validation_report.md
STOP: 等 Mingqian review
Phase 2: functional_queries_v1.jsonl 扩展到 80-150 条
Phase 3: minimal_pairs_v1.jsonl
Phase 4: long_range_stress_queries_v1.jsonl
Phase 5: existing_query_quality_audit_v1.csv
Phase 6: validate_functional_queries.py
Phase 7: hard_slice_summary_v1.json
```

如果时间不够，优先级是：

```text
1. Phase 1 pilot
2. Phase 6 validator
3. Phase 2 high-quality local functional queries
4. Phase 3 minimal pairs
5. Phase 5 existing query audit
6. Phase 4 long-range stress set
7. Phase 7 summary
```

---

## 16. 最重要的质量标准

每条 query 都要能回答下面三个问题：

```text
1. 为什么答案是这个 target？
2. 哪条 supporting edge / evidence chain 支撑这个答案？
3. 这个 query 难在哪里，能不能被 label-only shortcut 解决？
```

==如果这三个问题答不清楚，不要收进 `functional_queries_v1.jsonl`。==

---

## 17. 向 Mingqian 汇报时的格式

每完成一个 phase，请在 `annotation_notes.md` 最后追加：

```text
## Phase X progress — YYYY-MM-DD

Did:
- ...

Counts:
- ...

Potential issues:
- ...

Files ready for review:
- ...
```

Phase 1 和 Phase 2 完成后必须停下来等 review。

