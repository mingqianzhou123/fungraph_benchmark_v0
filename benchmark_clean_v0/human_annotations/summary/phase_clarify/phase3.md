# Phase 3 详细计划：Minimal-Pair / Adversarial Queries（锚定 20 pairs）

> 这是 `phase.md` 的 Phase 3 展开版。所有新文件写到
> `benchmark_clean_v0/human_annotations/functional_queries_v1/`，frozen 目录绝对不动。

---

## Context

**Phase 2 已经完成 93 条（0 ERROR），正等学长 review。Phase 3 是第一个不再"扩 query 数量"的阶段，目标变成 pair-level 反事实证明。**

Phase 2 产出状态（截至 2026-05-17）：

- `functional_queries_v1.jsonl` 93 条 + `pilot_20_queries.jsonl` 20 条 = **113 条人工 query 可作为 Phase 3 挖矿池**
- Validator 13 项检查 0 ERROR / 0 WARN（pilot 20 + main 93 都 PASS）
- Phase 2 tag 分布：`same_label_disambiguation` 92.5% / `geometry_aware` 79.6% / `multi_anchor` 44.1%；93 条中 `is_label_only_solvable=true` 仅 2 条（2.2%）
- 6 个选定 scene，CAP_LIMIT 的结构性原因已说明（phase2.md `[issue] CAP_LIMIT`）

**Phase 3 在论文里的价值（TASK_PLAN §10）：**

> ==证明模型真正使用了 functional evidence / geometry / anchor，而不是 label prior。==

Phase 2 给的是 **slice-level R@1 拆分**（"模型在 same_label 切片上表现差"）；Phase 3 给的是 **pair-level 反事实**（"同一对 query，只改一个变量，模型应该翻转答案；翻转率证明模型用了那个变量"）。这是两个互补但独立的论据。

Phase 3 完成后建议**仍然停一下**等学长 ack，再进 Phase 4 long-range。TASK_PLAN §17 只硬性规定 Phase 1/2 必停；Phase 3 起按惯例汇报后小停。

---

## ==本次锚定==

| 维度 | 锚定 | 说明 |
|------|------|------|
| Pair 总数 | **20 pairs** | TASK_PLAN §10 给 15 minimum / 30 ideal；本次主目标 20，理由见"数量上界"段 |
| Query 来源 | **优先复用已有 113 条 + 必要时补写** | 已有 query 不浪费、补写量受 Phase 2 CAP_LIMIT 限制 |
| 补写 query 落点 | **`minimal_pair_queries_v1.jsonl`（独立文件）** | 不污染已 review 中的 `functional_queries_v1.jsonl` 93 条；ID 接续 `human_func_v1_000114` 起 |
| `changed_factor` 分布 | 详见"changed_factor 分布"段 | 4 类至少各覆盖 1 对 |
| Evidence hop | **= 1（强制）** | ≥ 2 跳走 Phase 4，不进本批 |
| `is_long_range` | 全 false | 同 Phase 2 |
| `source` 字段（补写 query） | `"human_phase3"` | 区分 Phase 1 pilot（"human"）和 Phase 2（"human"）；便于后续切片 |

> ==质量比数量重要。==（TASK_PLAN §9 行 374）一条"勉强算 minimal pair"的对，不如不收。

**关键待学长决策项**（在动手前 ack）：

1. **补写 query 是否独立文件？** 推荐独立 `minimal_pair_queries_v1.jsonl`，理由：① Phase 2 的 93 条还在 review 流程里，加新 query 会破坏 review 快照；② Phase 3 的补写 query 用途单一（仅为构对），与 Phase 2 主集质量基线不同（pair 内一条可能 `is_label_only_solvable=true`，但只要 pair 整体能区分就有价值）。
2. **Pair 中允许两条都是新写的吗？** 推荐允许，但**优先**至少一条来自 Phase 2 已有 query（最大化已有 query 的二次利用）。
3. **数量上界 20 vs 30？** 见下方"数量上界估算"，建议先 20 对，若挖矿 + 补写顺利、scene 还有余量再追加到 30。

> 回答：当然独立文件，minimal_pair_queries_v1.jsonl
>
> 允许都是新写的
>
> 先 20 对，若挖矿 + 补写顺利、scene 还有余量再追加到 30。

---

## 输入文件（只读，绝对不修改）

| 路径 | 用途 |
|------|------|
| `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` | 完整 scene graph，验证补写 query 的 UUID/edge 真实性 |
| `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` | bbox center/min/max，验证 `geometry_aware` pair 的几何区分 |
| `human_annotations/functional_queries_v1/pilot_20_queries.jsonl` | Phase 1 pilot，挖矿池组成部分（20 条） |
| `human_annotations/functional_queries_v1/functional_queries_v1.jsonl` | Phase 2 主集，挖矿池主体（93 条） |
| `human_annotations/functional_queries_v1/functional_query_diagnostics_v1.jsonl` | 配套诊断，挖矿时读 `distractor_node_ids` 节省 graph 查询 |
| `human_annotations/functional_queries_v1/scene_graph_summary_v1.txt` | UUID / edge 真实性唯一权威来源（修订 3，phase1.md） |

**Frozen rule（CLAUDE.md）：** `benchmark_clean_v0/{queries, graphs, geometry, annotations, manifests, multimodal_extension}/` 一律只读。发现疑似错的 frozen 数据，写 `[issue] scope=... problem=... suggested_fix=...` 到 `annotation_notes.md`。

---

## 继承自 Phase 0/1/2 的口径修订

Phase 1/2 已写过的三条修订在 Phase 3 同样生效，写题前重新读 phase1.md 行 28–59 与 phase2.md "继承自 Phase 0/1 的口径修订"段。简要重述：

### 修订 1：`unknown` 不是真实 distractor
`num_same_label_distractors` 只数与 target 同一**真实 label** 的其他节点，**排除 `unknown`**。Phase 3 补写 query 的 distractor 计数沿用此口径；minimal_pair 内若两条 query target_label 相同，distractor 计数应一致。

### 修订 2：421380 几何写法（v2）
- ✅ 允许 **intra-anchor 垂直**（TV stand 上 cluster A/B 各 5 knob 垂直堆叠 0.4m）
- ❌ 禁止 **scene-wide 垂直**（跨 anchor 跨场景 z 比较）
- ✅ 水平描述任意

> Phase 3 主战场之一就是 421380 的 cluster A/B（Phase 2 q104–q113 已经按 v2 规则写了 10 条 intra-anchor cluster query），minimal pair 在这两个 cluster 上结构上天然成立——见"挖矿可行性预估"。

### 修订 3：edge 真实性来自 scene graph，不据 CSV 频次估
补写的 query 必须先在 `scene_graph_summary_v1.txt` 中确认 edge 真实存在再填 `supporting_edge_ids`。Pair 内若 `changed_factor != functional_relation`，两条 query 的 edge relation 应该一致（同一 relation 名）。

---

## ==Minimal Pair 严格定义==

一对 minimal pair 必须**同时满足下面 4 条**：

```text
1. scene_id 相同
2. 至少 3 个字段相同：query_type / target_label / supporting_edge_ids 的 relation
3. 恰好 1 个语义维度发生变化（changed_factor 4 类之一）
4. target_node_id 不同（即正确答案不同）
```

**不满足任一条 → 不是 minimal pair，丢回候选池。**

### `changed_factor` 4 类定义（TASK_PLAN §10 行 410–416）

| changed_factor | 定义 | 必须保持相同 | 必须不同 | 典型 query 形式 |
|----------------|------|--------------|----------|-----------------|
| `anchor_object` | anchor 物体改变，target_label 与 relation 不变 | scene_id, target_label, edge.relation | anchor_node_id, target_node_id, anchor_label/text | "press the switch that controls **the desk lamp**" ↔ "press the switch that controls **the ceiling light**" |
| `spatial_qualifier` | 几何修饰词改变，anchor 与 relation 不变 | scene_id, target_label, anchor_node_id, edge.relation | target_node_id, query_text 中的方位词 | "pull the **upper** drawer handle" ↔ "pull the **lower** drawer handle" |
| `functional_relation` | edge relation 改变，target_label 与 anchor 不变 | scene_id, target_label, anchor_node_id | target_node_id（必然，因为 edge 变了）, edge.relation | "**rotate** the knob that adjusts the temperature" ↔ "**pull** the knob that opens the drawer"（同一 anchor 上两个 knob） |
| `geometry_direction` | 几何方向词改变（spatial_qualifier 的子集，专指方向轴的对立） | scene_id, target_label, anchor_node_id, edge.relation | target_node_id, query_text 中的方向词（left↔right / top↔bottom 等） | "turn the knob connected to the **left** burner" ↔ "turn the knob connected to the **right** burner" |

> **`spatial_qualifier` vs `geometry_direction` 区分原则：** `geometry_direction` 必须是**严格对立轴**（left↔right, top↔bottom, near↔far, leftmost↔rightmost）；`spatial_qualifier` 涵盖更广（如 topmost ↔ 2nd-from-top ↔ middle 都算 spatial_qualifier，因为不是严格对立轴）。
> 如果犹豫 → 优先打 `spatial_qualifier`（更宽松）。phase2.md 的 421380 cluster 5 个位置（topmost / 2nd / middle / 2nd-bottom / bottommost）相邻对算 `spatial_qualifier`，两端对（topmost ↔ bottommost）可单独标 `geometry_direction`。

### ==不算 minimal pair 的反例==

```text
[反例 1] 同 scene 同 target_label，但 target_node_id 相同
  → 不是 pair，是同一题的两个 paraphrase

[反例 2] scene 不同
  → 跨 scene 的"看似 minimal" pair 无意义（distractor 池不一样）

[反例 3] 同时改了 anchor 和 spatial_qualifier
  → 不"minimal"，是"adversarial 多变量"。不收，或拆成两对各只改一个变量

[反例 4] changed_factor = functional_relation 但 target_label 也变了
  → 关系变 + 物体变 = 两个独立问题，不是 minimal pair

[反例 5] 两条 query 答案恰好相同（target_node_id 相同）
  → 不是 pair（参 §"严格定义"第 4 条）。这种情况其实暴露 Phase 2 一条 query
    的歧义性，应作为 [issue] 报回 Phase 2，不进 Phase 3 minimal pair
```

---

## ==挖矿可行性预估（基于 113 条已有 query）==

不读全 113 条的情况下，按 scene + target_label 已有的 Phase 2 结构做粗估：

### Phase 2 已有的天然 pair 候选源

**最大头：421380 cluster A/B（q104–q113，10 条）**

phase2.md 修订 2 v2 下，421380 的 TV stand 上 cluster A (x≈1.07) 与 cluster B (x≈1.47) 各 5 条 query，按位置标 topmost / 2nd / middle / 2nd-bottom / bottommost。

- Cluster A 内相邻 spatial_qualifier pair：(topmost, 2nd), (2nd, middle), (middle, 2nd-bottom), (2nd-bottom, bottommost) → **4 对**
- Cluster A 两端 geometry_direction pair：(topmost, bottommost) → **1 对**
- Cluster B 同上 → **4 + 1 = 5 对**
- ==**Cluster A × Cluster B 的 anchor_object pair**==：同一 z-位置不同 cluster 的 knob 是同一 TV stand anchor 不同列，严格说不是 `anchor_object`（anchor 相同），而是 `spatial_qualifier`（"左列 topmost" ↔ "右列 topmost"）。**5 对**
- 小计 cluster 内可挖：**4+1+4+1+5 = 15 对**（其中部分语义重复，去重后估 **10–12 对**）

**次大头：multi-knob/handle scene（469011, 421254, 421602 同 anchor 多 target）**

- 469011 knob×19：Phase 2 估计写了 10+ 条不同 (knob, anchor) 组合；同 anchor 不同 knob 的 pair 估 **3–5 对**
- 421254 knob×20 / remote×2：q021 之后写了多条同 anchor 不同 knob 的 query；估 **3–5 对**
- 421602 handle×11：Phase 1 已有 000003 / 000015 是同 anchor 上下 handle（minimal pair 模板）→ 必出 **1 对**；Phase 2 可能再多 **1–2 对**

**最难挖：anchor_object pair 和 functional_relation pair**
- `anchor_object`：要求"同 target_label 同 relation，anchor 不同"。Phase 2 写题时倾向于每 (target_label, anchor) 组合只写一条 → 此类 pair 在已有 113 条里**估计 < 5 对**，是补写的主战场。
- `functional_relation`：要求"同 anchor 不同 relation"。这种 anchor 必须有两种 functional element（比如某 cabinet 既被 handle 拉，又被 knob 旋）→ 6 scene 里**估计 < 3 对**，可能需要补写。

### ==粗估总量==

| 来源 | spatial_qualifier | geometry_direction | anchor_object | functional_relation | 小计 |
|------|--------|--------|--------|--------|------|
| 421380 cluster A/B 挖矿 | 8–10 | 2 | 0 | 0 | 10–12 |
| 其他 5 scene 挖矿 | 4–6 | 2–3 | 1–3 | 0–1 | 7–13 |
| **挖矿小计** | **12–16** | **4–5** | **1–3** | **0–1** | **17–25** |
| 补写填空（若挖矿 < 20）| 0 | 0–1 | 3–5 | 2–3 | 5–9 |

**结论：**

- ==锚定 20 对**有足够空间靠挖矿达成**==，理论上界估计 25 对（不补写）
- 锚定 30 对（stretch）**几乎必须补写** ≥ 5 条新 query 才能达成，且 6 scene 余量很紧
- ==**建议先锚 20，挖矿完成后看 changed_factor 分布是否补写**==

### Step 0 候选脚本输出（建议）

写一个 `phase3_pair_miner.py`（独立脚本）做 Step 0 挖矿：

```text
输入：pilot_20_queries.jsonl + functional_queries_v1.jsonl（合计 113 条）
处理：
  1. 按 (scene_id, target_label, edge.relation) 分组
  2. 同组内任意两条 query 比对 4 类 changed_factor 条件
  3. 同组内 anchor 不同 → 候选 anchor_object pair
  4. 同组同 anchor 内 query_text 有几何方位词 → 候选 spatial_qualifier / geometry_direction
  5. 按 (scene_id, anchor_node_id) 分组找 relation 不同的 query 对 → 候选 functional_relation
输出：pair_candidates_v1.csv（候选清单，含两条 query_id / pair_type / 共同字段 / 差异字段）
```

==该脚本只产生**候选**，不自动写 `minimal_pairs_v1.jsonl`——所有 pair 还要经过人工"答案确实不同""changed_factor 单一"的核查。==

---

## ==changed_factor 分布锚定==

按 TASK_PLAN §10 4 类（含 geometry_direction 作为 spatial_qualifier 的细分），20 对的目标分布：

| changed_factor | 锚定数 | 占比 | 主要场景 |
|----------------|--------|------|----------|
| `spatial_qualifier` | **9** | 45% | 421380 cluster A/B（intra-anchor 垂直）、421013/421602 跨 z 大场景 |
| `geometry_direction` | **4** | 20% | 421380 cluster 两端、421013/420683 左右对立 |
| `anchor_object` | **5** | 25% | 469011（kitchen 多 anchor 类型）、421254（dresser/nightstand 多个）|
| `functional_relation` | **2** | 10% | 6 scene 内有同 anchor 多 relation 的极少数 edge 组合 |
| **合计** | **20** | 100% | 6 scene |

> 4 类下界（每类 ≥ 1）确保切片分析时**每类都有数据点**；`functional_relation` 仅锚 2 对是因为 6 scene 上限就这么多，硬凑只会写出牵强 pair。

==**Phase 1 / 2 都出现过实际落点偏离锚定的情况**（10/5/3/2 → 7/6/5/2；150 ideal → 实际 93）。Phase 3 同样允许 ±20% 漂移，但每类 ≥ 1 是硬底线。==

---

## Step-by-step 标注流程

### Step 0：跑 pair_miner（脚本，自动）

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase3_pair_miner.py
```

输出 `pair_candidates_v1.csv`（约 30–60 行候选，含重复和不合格 pair）。

### Step 1：人工筛选候选

对 CSV 每行候选，按"严格定义" 4 条 + "不算 minimal pair 的反例" 5 条逐一核查：

```text
□ scene_id 相同？
□ target_label 相同？
□ supporting_edge relation 相同？（functional_relation pair 除外）
□ 恰好 1 个 changed_factor？
□ target_node_id 不同？
□ 不是反例 1–5？
```

通过的 → 进入 Step 2；未通过的 → 在 CSV 标 `rejected_reason`。

### Step 2：判定 changed_factor 与 why_hard

对每对通过的 pair：

```text
1. 确定 changed_factor 是 4 类中的哪一类（不允许 multi-class）
2. 写 why_hard（一句话）：解释为什么这对 pair 能区分"label prior vs. functional/geometry 使用"
   例："Both queries ask for a knob on the same TV stand; only the row position changes,
        so a model relying on label or anchor alone will pick the same target for both."
3. 检查 evidence_hop_count 是否都 = 1（即 supporting_edge_ids 长度都为 1）
```

### Step 3：补写 query 填空（若需要）

==**仅在挖矿后某 changed_factor 类 < 锚定下界时执行。**==

补写规则：
- 写到 `minimal_pair_queries_v1.jsonl`（独立文件），ID `human_func_v1_000114` 起
- 沿用 Phase 1/2 schema，`source: "human_phase3"`，`is_long_range: false`，`evidence_hop_count: 1`
- 跑 validator C1–C13 必须 PASS（沿用 Phase 2 validator，不改）
- 每补一条新 query，必须能立即组成一对 minimal pair（不允许写孤立 query）

==**补写的另一半 query 可以是已有的 Phase 1/2 query**——这是补写效率最高的方式。==

### Step 4：写 minimal_pairs_v1.jsonl

按 schema（下节）写。每行一对，`pair_id` 命名规范 `minpair_v1_NNNNNN` 6 位零填充。

### Step 5：跑 validator（含新加 C14–C18）

```powershell
# 主 validator 先验补写的 query（如果有）
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\minimal_pair_queries_v1.jsonl

# 然后验 minimal_pairs（脚本可以是同一个，加 --mode pair）
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_minimal_pairs.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\minimal_pairs_v1.jsonl
```

通过标准：
- 主 validator：补写 query 0 ERROR / C1–C13 全过
- pair validator：C14–C18 全过（详见"Validator 扩展"节）

### Step 6：更新 hard_slice_summary_v1.json

在已有 hard_slice 结构上追加：

```json
{
  "minimal_pairs": {
    "total_pairs": 20,
    "by_changed_factor": {
      "spatial_qualifier": 9,
      "geometry_direction": 4,
      "anchor_object": 5,
      "functional_relation": 2
    },
    "by_scene": {
      "421380": 10,
      "469011": 3,
      "421254": 3,
      "421602": 2,
      "421013": 1,
      "420683": 1
    },
    "n_pairs_using_phase2_only": 15,
    "n_pairs_with_phase3_query": 5,
    "n_phase3_new_queries": 5
  }
}
```

### Step 7：annotation_notes.md 追加 Phase 3 progress + STOP

按 TASK_PLAN §17 模板，4 个固定子段（Did / Counts / Potential issues / Files ready for review），最后 `==STOP HERE — 等学长 ack 后开始 Phase 4 long-range stress set==`。

---

## ==Schema 详解==

### minimal_pairs_v1.jsonl 每行

必填字段（TASK_PLAN §10 行 399–408 基础 5 项）：

```json
{
  "pair_id":        "minpair_v1_000001",
  "scene_id":       "421380",
  "query_a_id":     "human_func_v1_000104",
  "query_b_id":     "human_func_v1_000105",
  "changed_factor": "spatial_qualifier",
  "why_hard":       "Both queries ask for a knob on the same TV stand cluster A column; only the vertical position changes (topmost vs 2nd-from-top). A model using only label or anchor will pick the same target."
}
```

推荐字段（**强烈建议都填**，给 validator / diagnostics 用）：

```json
{
  "target_a_node_id":    "<UUID 来自 query_a>",
  "target_b_node_id":    "<UUID 来自 query_b>",
  "target_label":        "knob",
  "anchor_a_node_id":    "<UUID>",
  "anchor_b_node_id":    "<UUID 与 a 可同可不同>",
  "shared_relation":     "pull to open or close a drawer",
  "diff_summary":        "spatial: topmost (z=193.749) vs 2nd-from-top (z=193.649)",
  "pair_evidence_used":  ["geometry_z_axis"],
  "notes":               "Both targets in cluster A column at x≈1.07. z spread within column = 0.10m, distinguishable."
}
```

字段约束：

| 字段 | 约束 |
|------|------|
| `pair_id` | 格式 `minpair_v1_\d{6}`，文件内唯一 |
| `scene_id` | 6 个选定 scene 之一，且与 query_a/b 的 scene_id 一致 |
| `query_a_id` / `query_b_id` | 必须存在于 `pilot_20_queries.jsonl` / `functional_queries_v1.jsonl` / `minimal_pair_queries_v1.jsonl` 三者之一 |
| `changed_factor` | 4 类之一：`anchor_object` / `spatial_qualifier` / `functional_relation` / `geometry_direction` |
| `target_a_node_id ≠ target_b_node_id` | 必须不同（C16） |
| `shared_relation` | `changed_factor != functional_relation` 时两条 query 应共享同一 relation |
| `pair_evidence_used` | 候选值：`functional_edge` / `anchor_identity` / `geometry_x_axis` / `geometry_z_axis` / `multi_anchor_reference` —— 这条 pair 检验模型用了什么 cue |

### minimal_pair_queries_v1.jsonl 每行（如有补写）

沿用 Phase 1/2 schema 100%（phase1.md Step 4 完整字段 checklist），仅两处不同：

```text
□ source: "human_phase3"           ← 与 Phase 1/2 的 "human" 区分
□ notes 末尾追加: "[pair: minpair_v1_NNNNNN]"   ← 与 pair_id 反向引用
```

ID 接续：`human_func_v1_000114` 起（Phase 1 占 000001–000020，Phase 2 占 000021–000113）。

---

## ==Validator 扩展（C14–C18）==

==**Phase 2 的 13 项 C1–C13（C13 已撤回 → 实为 duplicate instance）一项不动**，新增独立检查脚本 `validate_minimal_pairs.py`==。

| # | 检查项 | 级别 | 说明 |
|---|--------|------|------|
| C14 | `pair_id` 格式匹配 `minpair_v1_\d{6}` 且唯一 | ERROR | 格式/重复 |
| C15 | `query_a_id` / `query_b_id` 都在已知 query 池中（pilot + main + phase3 补写） | ERROR | 引用不存在的 query |
| C16 | `target_a_node_id != target_b_node_id` | ERROR | pair 答案必须不同（严格定义第 4 条） |
| C17 | `changed_factor` 在 4 类固定集合内 | ERROR | 非法值 |
| C18 | `changed_factor` 一致性（条件检查，见下方实现细节） | WARN | tag 与事实不符 |

### C18 实现细节

```python
def check_c18(pair, query_a, query_b, scene_graph):
    cf = pair["changed_factor"]
    if cf == "anchor_object":
        # 必须：scene_id 同、target_label 同、relation 同、anchor 不同
        assert_eq(query_a["scene_id"], query_b["scene_id"])
        assert_eq(query_a.get("target_label"), query_b.get("target_label"))
        assert_eq(edge_relation(query_a), edge_relation(query_b))
        assert_ne(query_a["anchor_node_id"], query_b["anchor_node_id"])
    elif cf in ("spatial_qualifier", "geometry_direction"):
        # 必须：anchor 同、relation 同、target_label 同
        assert_eq(query_a["anchor_node_id"], query_b["anchor_node_id"])
        assert_eq(edge_relation(query_a), edge_relation(query_b))
        assert_eq(query_a.get("target_label"), query_b.get("target_label"))
        # 推荐：target 之间的几何差异 >= 0.05m（防止"伪几何 pair"）
        warn_if_geom_diff_below(query_a, query_b, threshold=0.05)
    elif cf == "functional_relation":
        # 必须：anchor 同、target_label 同、relation 不同
        assert_eq(query_a["anchor_node_id"], query_b["anchor_node_id"])
        assert_eq(query_a.get("target_label"), query_b.get("target_label"))
        assert_ne(edge_relation(query_a), edge_relation(query_b))
```

> C18 不强制 `geometry_cues` 字段内容（沿用 phase1.md C13 "已撤回" 的口径——validator 不做语义检查）。

### validation_report_phase3.md 格式

仿 Phase 2 `validation_report.md`：

```markdown
## Phase 3 Validation Report — YYYY-MM-DD HH:MM

Input files:
  - minimal_pair_queries_v1.jsonl (N条补写 query)
  - minimal_pairs_v1.jsonl (N对)

Main query validator (C1–C13) on补写 queries:
  PASS: N / N
  ERRORS: 0

Pair validator (C14–C18) on minimal_pairs:
  PASS: N / N
  ERRORS: 0
  WARNINGS:
    - C18 geom_diff_below_threshold: N

changed_factor distribution:
  spatial_qualifier:  N
  geometry_direction: N
  anchor_object:      N
  functional_relation: N

scene distribution:
  421380: N
  469011: N
  ...

pair_evidence_used distribution:
  geometry_z_axis:        N
  geometry_x_axis:        N
  anchor_identity:        N
  functional_edge:        N
  multi_anchor_reference: N
```

---

## 文件清单与改动

**Phase 3 新建文件：**

| 文件 | 动作 | 说明 |
|------|------|------|
| `scripts/phase3_pair_miner.py` | 新建 | 从 113 条已有 query 挖 pair 候选，输出 CSV |
| `scripts/validate_minimal_pairs.py` | 新建 | C14–C18 检查（不动 C1–C13 主 validator） |
| `pair_candidates_v1.csv` | 新建（脚本生成） | 候选清单 + 人工筛选标注 |
| `minimal_pairs_v1.jsonl` | 新建（手动写） | 20 对最终 pair |
| `minimal_pair_queries_v1.jsonl` | 新建（手动写，仅在补写时） | 0–9 条补写 query |
| `validation_report_phase3.md` | 新建（脚本生成） | Phase 3 验证报告 |
| `hard_slice_summary_v1.json` | **更新**（已有） | 追加 `minimal_pairs` 段 |
| `annotation_notes.md` | **追加写**（已有） | 末尾追加 `## Phase 3 progress — YYYY-MM-DD` 段 |

**只读引用（绝对不修改）：**

- 所有 frozen 目录
- `functional_queries_v1.jsonl`（Phase 2 主集，93 条）
- `pilot_20_queries.jsonl`（Phase 1 pilot，20 条）
- `functional_query_diagnostics_v1.jsonl`
- `scene_graph_summary_v1.txt`
- `scripts/validate_functional_queries.py`（主 validator，C1–C13）

==**Phase 2 的 93 条 + pilot 20 条绝对不动**。==如挖矿时发现某条 query 有 tag/distractor 计数问题，按 phase2.md "不达标处置" 规则 `[issue]` 写到 `annotation_notes.md` 等学长决定，不在 Phase 3 顺手改。

---

## ==质量标准（TASK_PLAN §10 + Phase 2 §16 三问扩展）==

每对 minimal pair 都要能清楚回答 **5 个问题**（前 3 个继承 Phase 2，后 2 个 Phase 3 新增）：

```text
1. 为什么 query_a 的答案是 target_a？  （继承 §16）
2. 为什么 query_b 的答案是 target_b？  （继承 §16）
3. 两条 query 都不能靠 label prior 解决吗？  （继承 §16）
4. 这一对 changed_factor 单一吗？（不是同时改了 anchor 和 spatial）
5. 这一对能否区分"模型用了 X cue vs. 没用"？（X = pair_evidence_used 字段）
```

==**任何一问答不清的 pair 不能进 minimal_pairs_v1.jsonl**==。退而求其次的处置：
- 答案有歧义 → 报 `[issue]` 回 Phase 2 对应 query，不进 Phase 3
- changed_factor 不单一 → 拆成两对，每对只改一个变量；或丢弃
- 几何差异 < 5cm → C18 WARN，notes 说明为何仍收录（一般是 cluster 内紧凑堆叠）

---

## 完成定义（Phase 3 checklist）

Phase 3 完成必须全部 ✅：

```text
[ ] phase3_pair_miner.py 已写，pair_candidates_v1.csv 已生成（建议 ≥ 25 行候选）
[ ] minimal_pairs_v1.jsonl ≥ 15 对（理想 20 对）
[ ] 每对通过 §"质量标准" 5 问
[ ] changed_factor 每类 ≥ 1 对（4 类全覆盖）
[ ] validate_minimal_pairs.py 已写，C14–C18 全过；0 ERROR
[ ] 若补写了 query：minimal_pair_queries_v1.jsonl 沿用 Phase 1/2 schema，主 validator C1–C13 全过
[ ] 所有 pair 的 evidence_hop_count = 1（is_long_range 全 false）
[ ] hard_slice_summary_v1.json 追加 minimal_pairs 段
[ ] validation_report_phase3.md 写完
[ ] annotation_notes.md 追加 `## Phase 3 progress — YYYY-MM-DD` 段，末尾 `==STOP HERE==`
[ ] frozen 目录 + Phase 2 已交付文件无任何改动（git status 确认）
[ ] Phase 2 主 validator 重跑 pilot_20 + functional_queries_v1（93 条）仍 0 ERROR（回归检查）
```

---

## Escalation Gate

```text
================================================================================
  STOP HERE
  Phase 3 完成后建议停下来等 Mingqian 审核，再开始 Phase 4 long-range stress set
================================================================================
```

> TASK_PLAN §17 行 693 硬性规定只 Phase 1/2 必停；Phase 3+ 是建议性，但 minimal pair 的 changed_factor 分布和 evidence_used 选择都涉及方法论判断，建议小停。

**向 Mingqian 汇报模板：**

```text
Phase 3 minimal pair 已完成，请审核：

文件：
  functional_queries_v1/minimal_pairs_v1.jsonl
  functional_queries_v1/minimal_pair_queries_v1.jsonl（若有补写）
  functional_queries_v1/pair_candidates_v1.csv
  functional_queries_v1/validation_report_phase3.md
  functional_queries_v1/hard_slice_summary_v1.json（已追加 minimal_pairs 段）

概要：
  - N 对 minimal pair（vs 锚定 20 对）
  - changed_factor 分布：spatial_qualifier=N, geometry_direction=N, anchor_object=N, functional_relation=N
  - scene 分布：[6 scene 各 N 对]
  - 补写新 query：N 条（vs 挖矿 < 锚定时的填空）
  - validator：0 ERROR；C18 WARN: N
  - 发现 issue：[列出，或"无"]

等 review 通过后再开始 Phase 4 long-range stress set。
```

---

## Out of scope（显式排除）

- ❌ Long-range query（≥ 2 跳 evidence）→ **Phase 4**，`long_range_stress_queries_v1.jsonl`
- ❌ 修改 Phase 2 的 93 条主 query / pilot 20 条 → 发现问题报 `[issue]`，等学长定
- ❌ 修改 validator C1–C13 主逻辑 → 仅追加独立的 `validate_minimal_pairs.py`
- ❌ 跨 scene 的"看似 minimal" pair → 反例 2，不收
- ❌ 同时改 ≥ 2 个 changed_factor 的"adversarial" pair → 反例 3，不收
- ❌ 两条 query 答案相同的"零差异 pair" → 反例 5，不收（且报 `[issue]` 回 Phase 2）
- ❌ 修改 frozen 目录 → `[issue]` 报到 `annotation_notes.md`
- ❌ 改 `multimodal_extension/` → 另一支线产物，annotation 视为只读

---

## Appendix A：与 phase2.md `CAP_LIMIT` issue 的关系

Phase 2 实际产出 93/150（62%），结构性原因是 6 个 scene 的 unique edge 上限 ~79，扣除 cluster 不可区分的 pair 后只剩 ~65 fresh edge。Phase 3 minimal pair **借用**这个有限池子，**不再消耗新的 unique edge**——所以 Phase 3 的 20 对锚定**不受 CAP_LIMIT 影响**，挖矿可行性预估的 17–25 对上界来自现有 query 的组合数，与 edge 池子相对独立。

==**如果学长在 Phase 3 review 时要求扩到 30+ 对**==，需要先扩 Phase 0 scene 集（这会触发 phase0_scene_audit 重跑、phase1_scene_explorer 增量），不属于 Phase 3 范围。

---

## Appendix B：与 multimodal_extension/phase2.md "y vs z 高度轴" issue 的关系

phase1.md 修订 2 v2 / annotation_notes.md Phase 1 已记录此分歧（z 实测是 scene-internal 垂直轴；multimodal phase2 写的 `height_from_floor_m = center_y - scene_min_y` 用 y）。

Phase 3 的 `spatial_qualifier` / `geometry_direction` pair 大量用 z 轴上下区分（典型如 421380 cluster topmost/bottommost），**沿用 phase1.md 修订 2 v2 的口径——使用 z 作为 scene-internal 垂直轴**。Phase 3 的 `pair_evidence_used` 字段写 `geometry_z_axis`（不是 `height_from_floor`），明确避开 multimodal phase2 那个有争议的字段名。

multimodal phase2 输出文件 Phase 3 视为只读，不在 Phase 3 顺手"修正"——继续等学长统一裁决。

---

## Appendix C：与 Phase 4 long-range 的接力关系

Phase 3 的 `evidence_hop_count` 强制 = 1，是为了让"changed_factor 单变量"这件事不被 graph hop 数稀释（多跳 query 的"variant"很容易隐含改动多个变量）。

Phase 4 的 long-range query（≥ 2 hop）天然没法做严格 minimal pair（hop 数本身就是一个 changed_factor），所以 Phase 4 不会消化 minimal pair 任务。Phase 3 ≠ Phase 4，**两阶段独立**。

如 Phase 3 挖矿时发现某条 Phase 2 query 实际是多跳（应进 Phase 4 而非 Phase 2），按 phase2.md "不达标处置" 流程报 `[issue]` 等学长决定移动归属——不在 Phase 3 顺手转移。

---

## Revision 1 — 学长 2026-05-19 review 反馈（执行修订记录）

> 本节追加于 phase3.md 正文之后，作为"事后修订"对照。正文（20 对 + 独立 `minimal_pair_queries_v1.jsonl` 落点 + 单向 pair 引用）是原始决策快照，**已被本次 revision 推翻**。最终实施请以本节为准。

### 修订动因

学长 2026-05-19 review 给出两组指示：

**指示 A（5 条质量要求）：**
1. 不要继续堆 knob/handle；优先补 outlet/switch/remote/faucet 类 functional relation
2. query_text 去掉裸坐标（`x=1.07`、`x≈-0.443`），改用自然语言（`upper-left knob`、`closer to TV`）
3. 增加自然语言变体（同结构不同问法：直接 / 间接 / 描述性 / 意图驱动）
4. 做真 minimal pair（target_a≠target_b + changed_factor 单一），不写简单 paraphrase
5. 保持 Phase 2，不重写大批旧 query；可只标记用途切片

**指示 B（schema 重设计）：**
1. 新 query 写进 `functional_queries_v1.jsonl`（不开独立文件，符合 TASK_PLAN §4 8 项交付清单）—— 推翻正文"独立 `minimal_pair_queries_v1.jsonl`"决策
2. 每条参与 pair 的 query **自身**带 3 个字段：`minimal_pair_id`（共用）、`minimal_pair_role`（"a"/"b"）、`minimal_pair_partner_id`（双向互指）
3. Pair 两条 query 必须**同一文件相邻写**，便于人工 review
4. 同时两条 query 都带 `minimal_pair` tag；不再单向只在 A 上写 `query_b_id`

### 锚定调整

| 维度 | 正文锚定 | Revision 1 实施 | 备注 |
|---|---|---|---|
| Pair 总数 | 20 | **28**（vs 修订目标 30） | 8 mining + 20 new；减 2 因 query 冲突，详见 PAIR_QUERY_CONFLICT |
| Mining pair | 20 (主要) | **8** | 删 005/020（query 冲突）+ 自动 drop 10 mixed/redundant |
| 新 query 落点 | `minimal_pair_queries_v1.jsonl` 独立文件 | **`functional_queries_v1.jsonl` 末尾**（ID 000114-000153） | 符合 TASK_PLAN §4 |
| `minimal_pairs_v1.jsonl` | 权威 pair 文件 | **派生视图**（脚本生成；权威源在 query 内嵌字段） | 保留以符合 TASK_PLAN §4 |
| pair 字段位置 | pair 文件单向 (`query_b_id`) | **query 内嵌双向**（`minimal_pair_id`/role/partner_id） | 指示 B |
| pilot 文件 | 部分 query 在 pair 中 | **完全回滚** 7 条 `minimal_pair` tag | 指示 B rule 2（同文件相邻） |
| 字段命名 | — | 沿用 Phase 1/2（`query_text`/`supporting_edge_ids`/`difficulty_tags`） | 学长示例的 `query`/`supporting_edge_id`/`tags` 是推荐非强制；保持 schema 一致性 |

### 文件级落地

| 文件 | 操作 |
|---|---|
| `pilot_20_queries.jsonl` | in-place 移除 7 条原带的 `minimal_pair` tag |
| `functional_queries_v1.jsonl` | 93 → **133** 条；16 条 mining-keep query 带 3 字段；40 条新增带 3 字段；其余 77 条无 pair 字段（Phase 2 状态） |
| `minimal_pairs_v1.jsonl` | 20 → **28** 对（派生视图，由 compose 脚本生成） |
| `scripts/phase3_compose_pairs.py` | **新建**（~900 行；含 8+40+20 hand-craft 规格 + 处理逻辑；idempotent） |
| `scripts/phase3_pair_builder.py` | **删除**（被 compose 取代） |
| `scripts/phase3_retag_minimal_pair.py` | **删除**（自描述 schema 不需事后 retag） |
| `scripts/validate_functional_queries.py` | 扩 C19-C23（详见下方）；C13 放宽（dup-instance 在 minimal_pair 中允许） |
| `scripts/validate_minimal_pairs.py` | 不变（C14-C18 派生视图二次校验保留） |
| `hard_slice_summary_v1.json` | 重算 difficulty_tag_counts / minimal_pairs 段 |
| `annotation_notes.md` | 追加 `## Phase 3 revision — 2026-05-19` 段 |
| frozen 目录 | 未触碰（git status 确认） |

### Validator C19-C23 扩展

| # | 检查项 | 级别 |
|---|---|---|
| C19 | `minimal_pair_id` / role / partner_id 三字段全有或全无；id 格式 `minpair_v1_\d{6}`；role ∈ {"a","b"}；partner_id 是 `human_func_v1_` 开头 | ERROR |
| C20 | `minimal_pair_id` 存在 ⟺ `difficulty_tags` 含 `minimal_pair`（充要） | ERROR |
| C21 | `minimal_pair_partner_id` 必须在同一文件内存在 | ERROR |
| C22 | 双向一致：partner 的 `minimal_pair_partner_id` == 本 query 的 `query_id`，且 `minimal_pair_id` 相同 | ERROR |
| C23 | partner 的 role 与本 query 的 role 相反（一个 "a"、一个 "b"） | ERROR |

**C13 放宽**：原 C13 检查"同 (target, anchor, edge_ids) tuple 不可重复"。Phase 3 revision 允许重复（语言变体 pair 故意复用 tuple）—— 仅在两条 query 都不在 minimal_pair 中时报 ERROR。

### 新 pair 主题分布（20 对）

| 主题 | scene | pair 数 | changed_factor | 备注 |
|---|---|---|---|---|
| outlet→appliance 直接/间接 | 469011 | 2 | anchor_object | 主战场，fix knob 占比 |
| handle→appliance NEW | 469011 | 1 | anchor_object | handle→fridge vs handle→oven |
| oven knob 自然语言重写 | 469011 | 2 | spatial / geom_dir | cluster row no-coords |
| remote→TV 自然语言重写 | 421380 / 421254 | 2 | geom_dir | "closer to TV" 类 |
| TV stand cluster A/B 全展开 | 421380 | 5 | spatial / geom_dir | 5 位置 × 2 列 |
| cluster A vs B 跨列 same-rank | 421380 | 1 | spatial | "upper-middle left" vs "upper-middle right" |
| cross-anchor 4 scene | 421254 / 420683 / 421013 / 421602 | 4 | anchor_object | 自然语言重写 mining 对 |
| wardrobe 自然语言重写 | 421013 | 1 | spatial | mining minpair_004 的 lang variant |
| functional_relation amplifier | 421380 | 1 | functional_relation | 取代 mining minpair_020 |
| 间接 hard_negative | 421380 | 1 | spatial | 意图驱动（store small/heavy） |
| **小计** | — | **20** | — | 40 条新 query |

**新 query 严格规则：** query_text 不含裸坐标；同结构 pair 内有词级差异；支持 supporting_edge_id 必须在 `scene_graph_summary_v1.txt` 真实存在；不加 `phase_purpose` tag 体系（等学长 ack 后另行扩 `VALID_TAGS`）。

### Verification（已执行）

- 主 validator on pilot: 20/20 PASS, 0 ERROR / 0 WARN
- 主 validator on main: 133/133 PASS, 0 ERROR / 0 WARN（含 C1-C13 + C19-C23）
- pair validator: 28/28 PASS, 0 ERROR / 0 WARN
- compose script idempotent: 二次跑过滤 80 个 previously-appended 后干净重建到 133
- changed_factor 4 类全覆盖（spatial 11 / geom_dir 7 / anchor 9 / func_rel 1）
- scene 6 个全覆盖（421380 仍 43% 偏重，cluster A/B 集中提供多类 pair）
- target_label 仍 67% knob（vs 学长 criteria 1 期望 reduce；缩到 50% 以下需扩 Phase 0 scene 集）

### 已知 issue（待学长 ack）

- `PAIR_QUERY_CONFLICT`：mining 10 对中 q067/q104 各被两对引用，自描述 schema 单值字段约束下只能各保一对 → mining 缩到 8 对 → 总数 28 对（不到 30）
- `FUNC_REL_CEILING_1`（仍 PENDING）：functional_relation 上界 1 对，结构性限于 6-scene 内 421380 TV stand 是唯一双 relation anchor
- target_label 67% knob（informational，criteria 1 改善 18 pp 但未达 balanced）

### 与 Phase 3 progress 段（前次执行）的关系

Phase 3 progress 段（2026-05-17）记录的是按正文锚定（20 对独立文件）的执行；Phase 3 retag patch 段（2026-05-19）记录的是回写 `minimal_pair` tag 的临时修补。两者均在本次 Revision 1 中被覆盖：
- 独立文件 `minimal_pair_queries_v1.jsonl` 未创建（按指示 B 不创建）
- retag patch 加在 pilot/main 上的 `minimal_pair` tag：pilot 全部回滚；main 中"非保留 mining query"的 retag 也回滚（compose 脚本统一管理）
- pair 文件从 20 对 → 28 对，pair_id 保持稳定（001-020 区间内只保留 8 个；新增 021-040）

annotation_notes.md 历史段落（Phase 3 progress、retag patch）**不删**，保留作为审计轨迹；最终状态以 Phase 3 revision 段为准。
