# Phase 2 详细计划：正式 Local Functional Query 扩展（锚定 150 条）

> 这是 `phase.md` 的 Phase 2 展开版。所有新文件写到
> `benchmark_clean_v0/human_annotations/functional_queries_v1/`，frozen 目录绝对不动。

---

## Context

**Phase 1 pilot 已通过 review，Phase 2 是从 20 条扩展到 150 条 ideal 的主标注阶段。**

Phase 1（20 条 pilot）输出状态：

- Validator 13 项检查全部 PASS（见 `validation_report.md`，0 ERROR / 0 WARN）
- 学长（Mingqian）manual review 给出 4 项修正，已全部合入 `pilot_20_queries.jsonl`：
  - 000003 target 选错（z 应取 170.932 而非 170.741）
  - 000009 query 两个合法答案（两 remote 都连同一 TV）
  - 000007 / 000011 缺 `same_label_disambiguation` tag（同名 knob ≥ 14 满足条件）
- Phase 1 实际类别分布 7 / 6 / 5 / 2（计划 10 / 5 / 3 / 2），漂移方向由学长 ack（详见 `annotation_notes.md` 行 305–430）

学长在 Phase 1 review 末尾给出 Phase 2 明确方向：

> ==**"下一批提高 hard non-label-only query 比例（尤其 same-label disambiguation / endpoint ambiguity / geometry-aware / hard negative）"**==

Phase 2 完成后**必须停下来等 Mingqian review**，不能直接进 Phase 3 minimal pair（TASK_PLAN §17：「Phase 1 和 Phase 2 完成后必须停下来等 review」）。

---

## 本次锚定（用户确认）

| 维度 | 锚定 | 说明 |
|------|------|------|
| Query 总数 | **ideal 150 条** | TASK_PLAN §9 给出 80 minimum / 150 ideal / 200 stretch；本次主目标 150。80 是可接受下限（hard candidate 不足时下调），200 stretch 仅在 §7 scene 分配仍有充足 hard edge 时考虑 |
| 难度漂移 | **靠 hard 上界** | `simple_functional` 设 ~20% 地板（保留 baseline）；`same_label_disambiguation` / `endpoint_ambiguity` / `geometry_aware` / `hard_negative` 取 §9 区间**上界** |
| `multi_anchor` 补齐 | **≥ 5%（≥ 8 条 @ 150）** | Phase 1 完全未覆盖该 tag，Phase 2 至少补到下界 |
| Evidence hop | **= 1（强制）** | ≥ 2 跳一律走 Phase 4 `long_range_stress_queries_v1.jsonl`，不进本批 |
| Source 字段 | `"human"` | 与 pilot 一致 |
| `query_id` 起始 | `human_func_v1_000021` | 接续 pilot 20 条编号 |

> ==质量比数量重要。不要为了凑数写模糊 query。==（TASK_PLAN §9 行 374，原文）

---

## 输入文件（只读）

| 路径 | 用途 |
|------|------|
| `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` | 完整 scene graph，UUID 与 edge 真实性来源 |
| `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` | 节点 bbox（center / min / max），`geometry_aware` 验证；**`bbox_center[2]` (z) 是 scene-internal 垂直/up 轴**（参 CLAUDE.md 坐标轴 gotcha） |
| `human_annotations/functional_queries_v1/phase1_outputs/scene_graph_summary_v1.txt` | 每场景 unique edge 列表；写 `supporting_edge_ids` 前必查（参 phase1.md 修订 3） |
| `human_annotations/functional_queries_v1/pilot_20_queries.jsonl` | Phase 1 已通过的 20 条，作为风格 / 字段 / tag 用法 reference |
| `human_annotations/functional_queries_v1/phase0_outputs/scene_audit_v1.csv` | Phase 0 选场审计（参考，不据其频次估题，参修订 3） |

**Frozen rule（CLAUDE.md）：** `benchmark_clean_v0/{queries, graphs, geometry, annotations, manifests, multimodal_extension}/` 一律只读。发现疑似错的 frozen 数据，用 `[issue] scope=... problem=... suggested_fix=...` 写到 `annotation_notes.md`，**不在原文件改**。

---

## 继承自 Phase 0/1 的口径修订

Phase 1 已写过的三条修订在 Phase 2 同样生效，写题前重新读 `phase1.md` 行 28–59。要点：

### 修订 1：`unknown` 不是真实 distractor
`num_same_label_distractors` 只数与 target 同一**真实 label** 的其他节点，**排除 `unknown`**。Validator C10 按此口径校验；Phase 0 CSV 的 `same_label_groups_detail` 中 `unknown=N` 条目 Phase 2 一律忽略。

### 修订 2：421380 几何写法限制（v2，2026-05-16 学长放行 intra-anchor 垂直）
421380 `z_axis_range = 0.802`，**scene-wide** 垂直区分度低；但**单 anchor 内部** TV
stand 上的 cluster A / B 两个 knob 列 z spread 达 0.4m，**intra-anchor 上下区分有意义**：
- ✅ **允许 intra-anchor 垂直**：描述同一 anchor 上多个同名 target 的相对上下位置，
  可用 `upper / lower / top / bottom / topmost / lowest / middle / 2nd-from-top` 等
- ❌ **禁止 scene-wide 垂直**：不能写跨 anchor 的 "the highest knob in the room"
- ✅ **水平描述任意**：`left / right / near / far / leftmost / rightmost` + 显式 x 坐标
- 其余 5 个 scene（z_range ≥ 1.2）规则不变（跨 anchor 垂直也允许）

### 修订 3：edge 真实性来自 scene graph，不据 CSV 频次估
`scene_audit_v1.csv` 的 `top_edge_descs` 是 **query 频次**不是 unique edge 频次（一条 edge 可能被 5–10 条 paraphrase query 引用 → 频次虚高）。每条 query 的 `supporting_edge_ids` 必须先在 `scene_graph_summary_v1.txt` 中确认 edge 真实存在再填。

---

## 6 场景画像（按真实 label 去 unknown 的口径）

| scene_id | n_unique_edges | max_same_label | key labels | z_range | 几何方向 | Phase 2 建议分配 |
|----------|----------------|----------------|------------|---------|----------|------------------|
| 469011   | 24             | knob×19        | knob, handle, outlet, faucet | 2.168 | 垂直+水平 | **30–35** |
| 421254   | 17             | **knob×20（MAX）** | knob, remote | 1.222 | 垂直+水平 | **25–30** |
| 421380   | 17             | knob×15        | knob, remote | **0.802** | **水平 + intra-anchor 垂直**（v2） | **20–25** |
| 421602   | 12             | handle×11      | handle | 2.009 | 垂直+水平 | **20–25** |
| 421013   | 10             | handle×9       | handle, light switch | 2.170 | 垂直+水平 | **20–25** |
| 420683   | 9              | knob×9, handle×2 | knob, handle | 1.750 | 垂直+水平 | **15–20** |
| **合计** | —              | —              | —          | —       | —        | **130–160** |

注：上下界给 retag 漂移留 ±10 余量，落地在 **150 附近**。一条 unique edge 通常只写一条 query（避免 paraphrase 灌水），所以 469011 / 421254 即使 edge 多也别集中堆。

**关键 edge 家族（写题主战场）：**
- **469011**：`provide power`（outlet → device）、`control the water flow`（faucet → sink）→ `hard_negative` + `functional_relation`
- **421254 / 421380**：knob×15+ → `same_label_disambiguation` 主场，配 `geometry_aware`（421254 任意垂直/水平；421380 水平 + intra-anchor 垂直，v2 规则）
- **421602**：handle×11 → `same_label` + `geometry_aware` upper/lower handle
- **421013 / 420683**：`control, turn on or turn off`（switch ↔ ceiling light）→ `endpoint_ambiguity` + `hard_negative`

---

## TASK_PLAN §9 比例区间 vs Phase 2 实际锚定

§9 给出的推荐区间（行 378–385，原文）：

```text
simple_functional:           20–30%
same_label_disambiguation:   25–35%
endpoint_ambiguity:          20–30%
geometry_aware:              15–25%
hard_negative:               10–20%
multi_anchor:                5–10%
```

> 一条 query 可以有多个 tag，所以比例不需要加起来等于 100%。（TASK_PLAN §9 行 387）

**Phase 2 落地锚定**（150 条基准下的目标条数）：

| Tag | §9 区间 | Phase 2 锚定 | 锚定条数（≈ 150） | 落点理由 |
|-----|---------|--------------|--------------------|----------|
| `simple_functional`         | 20–30% | **下界 ~20%** | ≥ 30 | baseline，防全 hard 偏斜 |
| `same_label_disambiguation` | 25–35% | **上界 ~33%** | ~50  | 学长 review 重点方向 |
| `endpoint_ambiguity`        | 20–30% | **上界 ~28%** | ~42  | 学长 review 重点方向 |
| `geometry_aware`            | 15–25% | **上界 ~23%** | ~34  | 学长 review 重点方向 |
| `hard_negative`             | 10–20% | **上界 ~18%** | ~27  | 学长 review 重点方向 |
| `multi_anchor`              | 5–10%  | **下界 ~6%**  | ≥ 9  | Phase 1 未覆盖，至少补到下界 |

`functional_relation` 不计入比例（§9 之外的通用 tag），但会自然伴随大多数 query。

**Phase 1 漂移参考：** 10/5/3/2 → 7/6/5/2，Phase 2 在此基础上继续往 hard 方向走，`simple_functional` 占比从 Phase 1 的 ~35% 降到 ~20%。

---

## Step-by-step 标注流程

### Step 0：建 edge candidate pool

从 `scene_graph_summary_v1.txt` 读 6 个场景所有 unique edges，按 relation 家族分桶：

| 家族 | 典型 relation | 推荐 tag |
|------|---------------|----------|
| 开关动作 | `open / close / pull to open / pull to close` | `simple_functional`, `endpoint_ambiguity`（handle ↔ drawer） |
| 旋转   | `rotate / turn`                              | `simple_functional`, `same_label_disambiguation`（knob×N） |
| 远程控制 | `control, turn on or turn off`, `provide power` | `endpoint_ambiguity`, `hard_negative`（switch ↔ light, outlet ↔ device） |
| 水/气流 | `control the water flow`                     | `hard_negative` |
| 结构   | `connected_to / part_of`                     | `multi_anchor`（搭配其他 edge） |

每条 edge 标注一个 candidate 卡片：`(scene_id, edge_id, src_label, relation, tgt_label, num_same_label_distractors_src, num_same_label_distractors_tgt, has_bbox_target)`。

### Step 1：三问筛（TASK_PLAN §16）

对每条候选 edge 先回答：

```text
1. 为什么答案是这个 target？
2. 哪条 supporting edge / evidence chain 支撑这个答案？
3. 这个 query 难在哪里，能不能被 label-only shortcut 解决？
```

任何一问答不清 → **不写**，丢回候选池。

### Step 2：写 query + 填 schema（TASK_PLAN §5）

必填字段：

```json
{
  "query_id": "human_func_v1_000021",
  "scene_id": "420683",
  "query_text": "press the switch that controls the desk lamp",
  "query_type": "functional",
  "target_node_id": "<UUID>",
  "anchor_node_id": "<UUID>",
  "supporting_edge_ids": ["<src>|<relation>|<tgt>"],
  "difficulty_tags": ["same_label_disambiguation", "endpoint_ambiguity"],
  "is_long_range": false,
  "evidence_chain": ["switch --control--> lamp"],
  "source": "human",
  "notes": "Two switches in the scene; controls edge disambiguates the target."
}
```

推荐字段（强烈建议都填，给 diagnostics 用）：
- `target_label`, `anchor_label`
- `expected_failure_modes`：列出可能的误选模式（如 `["choose_anchor", "same_label_wrong_knob"]`）
- `geometry_cues`：如 `["lower", "left"]`
- `num_same_label_distractors`：**必填**（配合 validator C10，real label 计数）
- `is_label_only_solvable`：**必填**（配合 diagnostics）

### Step 3：edge 方向 trap 检查（高频 bug）

参 phase1.md / CLAUDE.md：
- `target_node_id` = supporting edge 的 **src**（用户操作的那一端）
- `anchor_node_id` = supporting edge 的 **tgt**（被影响的那一端）

Validator C7 / C8 会检测方向反转。Phase 1 早期 pilot 主要 bug 就是把方向写反——批量写题时尤其要复核。

### Step 4：`is_label_only_solvable` 自评

回答 Step 1 第 3 问：**去掉 functional / geometry 信息，只靠 label 能否定位 target？**
- **是** → `is_label_only_solvable: true`，**比例 ≤ 20%**（baseline 防偏斜，且在 `notes` 说明为何仍收录）
- **否** → `is_label_only_solvable: false`，进入 hard 主集

### Step 5：跑 validator

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\functional_queries_v1.jsonl
```

通过标准：
- 0 ERROR
- C1–C13 全过
- Phase 1 distribution informational 检查：Phase 2 总数 ≠ 20，原检查可能 MISMATCH。把解释写到 `annotation_notes.md`，**不动 validator**。

### Step 6：填 diagnostics + hard_slice_summary

每条 query 在 `functional_query_diagnostics_v1.jsonl` 写一条对应记录（schema 见下节）。

`hard_slice_summary_v1.json` 至少包含：
- 总条数、各 tag 计数与比例
- 各 scene 分布
- `is_label_only_solvable=true` 的条数与比例
- `num_same_label_distractors` 分布（直方图）
- `multi_anchor` × `geometry_aware` 共现矩阵

### Step 7：按 TASK_PLAN §17 模板汇报，STOP

把 Phase 2 progress 追加到 `annotation_notes.md`，**停在这里**等学长 review。

---

## 输出文件规格（TASK_PLAN §9 行 389–396）

全部位于 `benchmark_clean_v0/human_annotations/functional_queries_v1/`：

| 文件 | 内容 | 与 Phase 1 关系 |
|------|------|----------------|
| `functional_queries_v1.jsonl` | 150 条主 functional queries（80 minimum / 200 stretch） | **新文件**；与 `pilot_20_queries.jsonl` 默认保留独立，是否合并由学长 review 决定 |
| `functional_query_diagnostics_v1.jsonl` | 与 main JSONL 同 `query_id` 对齐的诊断 | 新文件 |
| `hard_slice_summary_v1.json` | tag / scene / diagnostics 汇总 | 新文件 |
| `validation_report.md` | 跑完 validator 后覆盖 | 先把 Phase 1 版本 copy 为 `validation_report_phase1.md` 留存，再覆盖 |

---

## Diagnostics schema（TASK_PLAN 行 335–350）

每条 query 一条 JSON：

```json
{
  "query_id": "human_func_v1_000021",
  "scene_id": "420683",
  "is_label_only_solvable": false,
  "num_same_label_distractors": 3,
  "expected_failure_modes": ["same_label_wrong_switch", "choose_anchor"],
  "distractor_node_ids": ["switch_01", "switch_02"],
  "geometry_cues_used": ["lower"],
  "evidence_hop_count": 1
}
```

字段约束：
- `evidence_hop_count` **必须 = 1**。≥ 2 跳走 `long_range_stress_queries_v1.jsonl`（Phase 4）
- `num_same_label_distractors` 同 main JSONL 对应字段（real label，去 unknown）
- `distractor_node_ids` 是真实存在的同 label 节点 UUID
- `geometry_cues_used` ⊆ main JSONL `geometry_cues`，记录实际用到的几个

---

## ==质量标准（TASK_PLAN §16）==

每条 query 都要能清楚回答 3 个问题：

```text
1. 为什么答案是这个 target？
2. 哪条 supporting edge / evidence chain 支撑这个答案？
3. 这个 query 难在哪里，能不能被 label-only shortcut 解决？
```

==**任何一问答不清的 query 不能进 `functional_queries_v1.jsonl`。**==

不达标处置：
- 信息不足（如 anchor label 缺失）→ 标 `[issue]` 写到 `annotation_notes.md`，等学长决定
- 两个合法答案 → 丢回候选池或拆成 **minimal pair** 留给 Phase 3
- evidence chain 跨多跳 → 移到 Phase 4 `long_range_stress_queries_v1.jsonl`

---

## Validator 期望（13 项不变）

沿用 Phase 1 的 `validate_functional_queries.py`，C1–C13 一项不改。Phase 2 特别留意：

| 项 | 说明 | Phase 2 风险点 |
|----|------|-------------|
| C7 / C8 | supporting_edge 方向（src = target, tgt = anchor） | 写题量大易写反，Step 3 必查 |
| C10 | `same_label_disambiguation` 要求 real-label 同名 ≥ 2 | unknown 不计；Phase 2 此 tag 占 ~33%，最大风险点 |
| C11 | `geometry_aware` 要求 target 有 bbox | Phase 0 已确认 6 场景 100% bbox 覆盖；写题时再核 target_node_id 是否在 `scenefun3d_node_geom.json` |
| C12 | `long_range` tag 不进本文件 | Phase 2 全部 `is_long_range: false`；多跳 query 移到 Phase 4 |
| 421380 vertical | 修订 2 v2：禁止 **scene-wide** 垂直；允许 **intra-anchor** 垂直 | 文档约束（validator 不检查 geometry_cues 内容） |

新增检查项（如发现需要）作为 `[issue] suggested_fix=新增 CXX 检查...` 写到 `annotation_notes.md`，**不强行改 validator**，等学长定。

---

## Escalation gate（TASK_PLAN §17 行 693）

**Phase 2 完成后必须停下来等 Mingqian review，不直接进 Phase 3 minimal pair。**

汇报方式：在 `annotation_notes.md` 末尾追加一节，严格按 §17 模板：

```text
## Phase 2 progress — YYYY-MM-DD

Did:
- ...

Counts:
- 总条数、各 tag 计数与比例、各 scene 分布、is_label_only_solvable 比例

Potential issues:
- [issue] scope=... problem=... suggested_fix=...

Files ready for review:
- functional_queries_v1.jsonl
- functional_query_diagnostics_v1.jsonl
- hard_slice_summary_v1.json
- validation_report.md
```

汇报后写 `==STOP HERE — 等学长 ack 后开始 Phase 3==`，参照 Phase 1 末尾停点（`annotation_notes.md` 行 428–430）。

---

## Out of scope（显式排除）

- ❌ Minimal pair / adversarial → **Phase 3**，`minimal_pairs_v1.jsonl`
- ❌ Long-range（≥ 2 跳 evidence）→ **Phase 4**，`long_range_stress_queries_v1.jsonl`
- ❌ 修改 frozen 目录 → `[issue] ...` 报到 `annotation_notes.md`，不直接改
- ❌ 改 `multimodal_extension/` 任何文件 → 另一支线产物，annotation 视为只读
- ❌ 改 `validate_functional_queries.py` → 除非有 `[issue]` 经学长 ack
- ❌ 写超过 200 条 → TASK_PLAN §9 stretch 上限
- ❌ 给 ≥ 2 跳 query 贴 `long_range` tag 后留在本文件 → validator C12 会 fail

---

## Appendix A：四个易混术语（参 CLAUDE.md "Concepts that get conflated"）

这四个词在工作日志里被多次混淆，写题 / 读题前再确认一遍：

### 1. `long_range`（TASK_PLAN §6 行 439–456）
- **定义**：evidence chain ≥ 2 graph hops
- **Phase 2 用法**：**禁止**。所有 query `is_long_range: false`
- **去哪**：单独到 `long_range_stress_queries_v1.jsonl`（Phase 4）

### 2. "Spatially long-range"（Research Plan §8.5）
- **定义**：target 与 anchor 的 3D 距离大
- **与 `long_range` 关系**：**独立维度**。一条 single-hop edge（switch → ceiling light）graph 上只 1 跳，但 3D 距离可能 ~2.5m
- **Phase 2 用法**：非 schema 字段，可在 `notes` 提一下，用于后续研究分析

### 3. `local` / `remote` edge（OpenFunGraph CVPR'25 §1 / §3）
- **定义**：物理是否依附
  - **local**：interactive element 是 object 的一部分（handle 装在 drawer 上）
  - **remote**：element 从远处操作 object（switch 控制 ceiling light，outlet 给 fridge 供电）
- **不是动词类别**：`open / pull` vs `control / power` 只是论文 verb-grouping 代理，不等同物理定义
- **Phase 2 用法**：非 schema 字段，但 `hard_negative` 主战场就在 remote 类（switch ↔ light, outlet ↔ device, faucet ↔ sink）

### 4. TASK_PLAN §8 中的 "local functional"
- **定义**：相对于 `long_range`，**= 单跳 query**
- **不是 OpenFunGraph 的 local-type edge**：本批 query 既可包含物理 local edge（handle-drawer），也可包含物理 remote 但单跳的 edge（outlet-fridge）
- **Phase 2 用法**：本批所有 query 都是这个意义上的 "local functional"

引文位置：
- CLAUDE.md "Concepts that get conflated" 节
- TASK_PLAN §6 行 439–456
- `annotation_notes.md` 行 305–324（Phase 1 已记录过的辨析）

---

## Appendix B：完成定义（Phase 2 checklist）

Phase 2 完成必须全部 ✅：

```text
[ ] functional_queries_v1.jsonl 至少 80 条（理想 150 条）
[ ] 每条 query 通过 §16 三问
[ ] validator 0 ERROR，C1–C13 全过
[ ] tag 分布满足锚定：
    [ ] simple_functional ≤ 30%（地板 ~20%）
    [ ] same_label_disambiguation ≥ 25%
    [ ] endpoint_ambiguity ≥ 20%
    [ ] geometry_aware ≥ 15%
    [ ] hard_negative ≥ 10%
    [ ] multi_anchor ≥ 5%（≥ 8 条 @ 150）
[ ] is_label_only_solvable=true 比例 ≤ 20%
[ ] 全部 is_long_range=false，evidence_hop_count=1
[ ] functional_query_diagnostics_v1.jsonl 与 main JSONL 一一对齐
[ ] hard_slice_summary_v1.json 写完
[ ] validation_report.md 更新（先把 Phase 1 版本 copy 为 validation_report_phase1.md）
[ ] annotation_notes.md 追加 Phase 2 progress 节，末尾 ==STOP HERE== 等学长 review
[ ] frozen 目录无任何改动（git status 检查）
```
