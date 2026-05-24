# Phase 4 详细计划：Long-Range Stress Set（锚定 30 条 junction 2-hop）

> 这是 `phase.md` 的 Phase 4 展开版。所有新文件写到
> `benchmark_clean_v0/human_annotations/functional_queries_v1/`，frozen 目录绝对不动。

---

## Context

**Phase 3 已完成 133 条主集 + 28 对 minimal pair，等学长 ack。Phase 4 是 multi-hop stress 阶段，单独输出到 `long_range_stress_queries_v1.jsonl`，不混入主集。**

Phase 3 产出状态（截至 2026-05-20）：

- `functional_queries_v1.jsonl` 133 条 + `pilot_20_queries.jsonl` 20 条 + `minimal_pairs_v1.jsonl` 28 对
- 三 validator 全 0 ERROR / 0 WARN（C1–C13 + C19–C23 主集；C14–C18 派生 pair 视图）
- 3 个 PENDING_MINGQIAN_ACK：PAIR_QUERY_CONFLICT（28 对 vs 30）/ FUNC_REL_CEILING_1 / target_label 67% knob

**Phase 4 的论文价值（TASK_PLAN §11 + Research Plan §8.5）：**

> ==专门测试 FCGP / EFCG 的多跳边界——验证 query-conditioned propagation 在长功能链上是否仍稳定，而 1-hop retrieval 在 hop 数增加时是否衰减。==

TASK_PLAN §11 行 462 明确说 "**这不是主 benchmark，不要混入 `functional_queries_v1.jsonl`**"，且 phase.md 行 466 提示 "当前 EFCG 主要是 local endpoint grounding，不要把 long-range stress set 当成主结果"。Phase 4 在论文里的位置是 **stress set / supplementary**，不是主表评测对象。

Phase 4 完成后**仍要停下来等学长 ack**，再决定是否进 Phase 5（existing query audit）或直接结束。

---

## ==关键结构性发现（写题前必读）==

执行 Phase 4 Step 0 audit 后确认（2026-05-23 调研结论）：

```text
20 个 SceneFun3D scene 的 functional scene graph 都是严格二部图：
  - interactive element (knob/handle/switch/outlet/remote/...) 只有出边
  - appliance/container (cabinet/oven/light/fridge/...) 只有入边
  - 0 个节点同时具有入边和出边
  → A→B→C 三个不同节点的同向 graph 链在数据集层面完全不存在
```

phase.md 行 444–454 的 Phase 4 示例（`bed --near--> desk; desk --supports--> lamp; switch --controls--> lamp`）依赖的 `near` / `supports` 空间边在 SceneFun3D `scene_graph.edges` 里**不存在**——示例是论文级愿景，不是数据集事实。

**学长 2026-05-23 ack：** 采用 **junction 2-hop** 作为可行替代：

```text
Junction 2-hop:
  target_node  →[rel_1]→  shared_anchor  ←[rel_2]←  reference_node

  3 个不同节点 + 2 条真实功能边 + 共享 anchor。
  graph distance(target, reference) = 2（途经 shared_anchor）。
```

学长同时 ack：**可以适当扩展 scene，只要 Phase 4 质量和数量达标。** Phase 0 audit 可重跑，找 junction 丰富的新 scene 加入 Phase 4 范围（**不回填 Phase 1–3**）。

---

## ==本次锚定==

| 维度 | 锚定 | 说明 |
|------|------|------|
| Query 总数 | **30 条 minimum / 40 条 ideal** | TASK_PLAN §11 行 484–489 给 30 minimum / 50 ideal；本批先打 30，audit 顺利再追到 40 |
| 文件落点 | **`long_range_stress_queries_v1.jsonl`（独立文件）** | TASK_PLAN §11 行 462 硬性规定，**绝对不能混入** `functional_queries_v1.jsonl` |
| `is_long_range` | **全 true** | 与 Phase 1/2/3 区分；validator C12 主集 / C28 long_range 双重校验 |
| `evidence_hop_count` | **≥ 2**（绝大多数 = 2） | TASK_PLAN §11 行 469 原文 "需要两个或更多 evidence steps"；junction 2-hop 是结构性下限，3+ hop 在二部图里罕见但 audit 找到则允许收 |
| `supporting_edge_ids` 长度 | **≥ 2** | 与 Phase 1/2/3 的 length=1 区分；长度跟随 `evidence_hop_count` |
| `evidence_chain` 长度 | **≥ 2** | 同上，与 `supporting_edge_ids` 长度一致 |
| `difficulty_tags` | **必含 `long_range`** | 可叠加其他 tag（如 `same_label_disambiguation` / `functional_relation` / `geometry_aware`） |
| `source` | `"human_phase4"` | 区分 Phase 1 / 2 的 `"human"` 和 Phase 3 的 `"human_phase3"` |
| `query_id` 命名 | **`lr_v1_000001` 起**（推荐） | 走独立命名空间，避免与 `human_func_v1_*` 主集 ID 冲突；若学长偏好沿用前缀可改 `human_func_v1_lr_000001` |
| scene 范围 | **6 已选 + Step 0 audit 后按需扩** | audit 不足 30 时新增 scene，仅 Phase 4 用 |
| Evidence hop 上限 | **不设硬上限**（结构性上界为 2） | 二部图拓扑下 3+ hop 几乎写不出来；若 Step 0 audit 找到罕见 3-hop 候选（例如 power strip 反向边连接两个 junction）也合法 |

> ==质量比数量重要。==（TASK_PLAN §16）一条勉强算 long-range 的 query 不如不收。

**关键待学长决策项**（不阻塞，可执行时默认走推荐项）：

> 全走推荐项吧！

1. **`query_id` 命名**：推荐 `lr_v1_000001`（独立命名空间），还是沿用 `human_func_v1_lr_000001`（统一前缀，但与主集编号容易混淆）？
   - **推荐**：`lr_v1_000001`
2. **`shared_anchor` / `reference` 字段是否强制必填**：推荐强制，方便 validator C26/C27 直接读字段而非从 `supporting_edge_ids` 反解析。
   - **推荐**：强制必填
3. **Step 0 audit 是否独立脚本**：推荐独立 `scripts/phase4_scene_audit.py`（与 `phase0_scene_audit.py` 解耦，后者只查 same-label distractor）。
   - **推荐**：独立
4. **40 ideal 后是否继续追到 50 stretch**：取决于 audit 实际产出；若 14 未启用 scene 贡献远超预估则可追，否则 40 封顶。
   - **推荐**：先 30 / 40，stretch 由学长 ack 决定

---

## 输入文件（只读，绝对不修改）

| 路径 | 用途 |
|------|------|
| `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` | 完整 scene graph，UUID / edge 真实性来源；Step 0 audit 读这里 |
| `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` | 节点 bbox（center / min / max），**`bbox_center[2]`(z) 是 scene-internal 垂直/up 轴**（CLAUDE.md 坐标轴 gotcha）|
| `human_annotations/functional_queries_v1/scene_graph_summary_v1.txt` | 6 已选 scene 的 edge 唯一来源（修订 3）；Phase 4 写题前必查；新 scene 需在 Step 0 audit 输出对应段 |
| `human_annotations/functional_queries_v1/pilot_20_queries.jsonl` | Phase 1 已通过的 20 条，作为风格 reference；**禁止复用 query** |
| `human_annotations/functional_queries_v1/functional_queries_v1.jsonl` | Phase 2/3 已有 133 条；**禁止复用 query**，可复用 target/anchor UUID 知识 |
| `human_annotations/functional_queries_v1/minimal_pairs_v1.jsonl` | 28 对派生视图，Phase 4 不产生此文件的新内容 |

**Frozen rule（CLAUDE.md）：** `benchmark_clean_v0/{queries, graphs, geometry, annotations, manifests, multimodal_extension}/` 一律只读。发现疑似错的 frozen 数据，写 `[issue] scope=... problem=... suggested_fix=...` 到 `annotation_notes.md`。

---

## 继承自 Phase 0–3 的口径修订

Phase 1/2/3 已写过的修订在 Phase 4 同样生效，写题前重新读 phase1.md 行 28–59 / phase2.md "继承自 Phase 0/1 的口径修订" 段 / phase3.md "继承自 Phase 0/1/2 的口径修订" 段。简要重述：

### 修订 1：`unknown` 不是真实 distractor
junction 2-hop 中 `reference_node` 的 label 若为 `unknown` 一律不收（reference 必须用真实 label 在 query_text 里自然描述）。`num_same_label_distractors` 沿用 Phase 1–3 口径，排除 `unknown`。

### 修订 2：421380 几何写法 v2
若 Phase 4 query 内部使用几何方位词区分**同一 anchor 上多个候选 target 或 reference**，沿用 Phase 2 v2 规则：
- ✅ 允许 intra-anchor 垂直（如 TV stand cluster 上下）
- ❌ 禁止 scene-wide 垂直（跨 anchor 跨场景 z 比较）
- ✅ 水平描述任意

### 修订 3：edge 真实性来自 scene_graph，不据 CSV 频次估
junction 2-hop 的两条 evidence edge **必须先在** `scene_graph_summary_v1.txt`（或 Step 0 audit 的新 scene 段）**中确认真实存在**再填 `supporting_edge_ids`。

### 修订 4：z 是 scene-internal 垂直轴（已实测）
若 Phase 4 涉及垂直区分（如 reference 在 target 上方/下方），沿用 z 轴口径。**不动 multimodal phase2 那个有争议的 `height_from_floor_m = center_y - scene_min_y`**，继续等学长统一裁决。

### 修订 5：query_text 不含裸坐标（Phase 3 学长 criteria 2）
Phase 4 query_text **严禁出现 `x=1.07`、`z≈193.749` 等裸坐标**。同结构需要区分时用自然语言方位词（`upper-left`、`closer to`、`next to`）。

### 修订 6：自然语言变体（Phase 3 学长 criteria 3）
Phase 4 query 风格鼓励多样化：直接问 / 间接问 / 描述性 / 意图驱动皆可。例："Press the knob that adjusts the oven the handle pulls open." / "To set the oven temperature, which knob should I rotate on the oven whose door the handle opens?" 两种风格都合法。

---

## ==Junction 2-hop 严格定义（默认路径；3+ hop 见附注）==

==**TASK_PLAN §11 行 469 原文："需要两个或更多 evidence steps"——即 `evidence_hop_count ≥ 2`，不是恰好 = 2。**==

Phase 4 默认走 **junction 2-hop**（数据集结构性下限，详 §"关键结构性发现"）。若 Step 0 audit 找到罕见的 3+ hop 候选也合法，但每条 query 仍须满足下面前 4 条 + 改写后的第 5 条（见"3+ hop 扩展"附注）。

一条合法的 junction 2-hop query 必须**同时满足下面 5 条**：

```text
1. scene_id 是 SceneFun3D 的 20 个 scene 之一（必须有 bbox 几何覆盖）

2. evidence_chain 长度 ≥ 2，每个 step 是 scene_graph 里真实存在的 functional edge

3. 两条 edge 在 anchor 节点上"会合"（2-hop 默认路径）：
     edge_1: target_node ─[rel_1]→ shared_anchor
     edge_2: reference_node ─[rel_2]→ shared_anchor
   即两条 edge 的 target 端（"|"右端）相同

4. target_node、shared_anchor、reference_node 是 3 个互不相同的 UUID

5. query_text 必须自然语言地引用 reference_node 的存在
   （不能只描述 shared_anchor 就停——那样退化为 1-hop functional query）
```

### 3+ hop 扩展（罕见路径，仅在 Step 0 audit 发现真实候选时启用）

如某 scene 内出现"链式 junction"——例如：
```text
target → anchor1 ← reference1
reference1 → anchor2 ← reference2   (reference1 既作为 anchor1 的 source 又作为 anchor2 的 source？)
```
二部图拓扑下，interactive element 只有 1 条出边——但 `phase4_scene_audit.py` 仍会扫一遍是否有反例（如 power strip 在 421267/466803 中既作为 outlet 类 source 又作为某更上层 power 链的 target）。若找到：
- `evidence_chain` 长度 = 实际 step 数
- `supporting_edge_ids` 同步加长
- 字段 `long_range_pattern` 改为 `"chain_3hop"` / `"junction_chain_Nhop"` 等
- 严格定义第 3 条改为"相邻两条 edge 共享一个端点（任一端）"
- 第 5 条："query_text 必须自然语言地引用 chain 中所有非 target 的关键节点"

**预期出现率 < 5%**；不强求，audit 没找到就不写。本批 90%+ 仍是 junction 2-hop。

**不满足任一条 → 不收。**

### 不算 Phase 4 long-range 的反例

```text
[反例 1] 真同向 A→B→C（target → intermediate → reference）
  → 数据集二部图结构决定写不出，0 个候选；不强求

[反例 2] B 是 shared_anchor，但 query_text 只描述了 B、没提 reference C
  → 这是 Phase 2/3 的 1-hop functional query（如 "press the knob to open the oven"），
    不是 long-range；丢回 Phase 2 候选池

[反例 3] reference 与 target 同 label 且无其他区分线索
  → 退化为 same_label_disambiguation 而非 multi-hop reasoning。
    若 reference 同 label 但有几何区分（"the upper handle vs the knob below"）
    可收，但 difficulty_tags 要补 same_label_disambiguation

[反例 4] 用 geometric 关系串两条 functional edge（"the knob near the lamp the outlet powers"）
  → geometric step 不是 scene_graph edge，不算 graph hop；
    这类属 Research Plan §8.5 spatially long-range，**不在** Phase 4 范围（见 Appendix B）

[反例 5] evidence_chain 长度 < 2
  → 0 / 1 跳走 Phase 1/2/3，validator C12 会拒
  → 长度 ≥ 3 在二部图下结构性罕见但**允许**（见"3+ hop 扩展"附注），不算反例
```

### Worked example（469011 oven junction）

```json
{
  "query_id": "lr_v1_000001",
  "scene_id": "469011",
  "query_text": "Rotate the second-from-left knob that adjusts an appliance the silver handle pulls open.",
  "query_type": "functional",
  "target_node_id": "06b684bb-7a5c-4717-847a-d343bd6824d9",
  "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
  "supporting_edge_ids": [
    "06b684bb-7a5c-4717-847a-d343bd6824d9|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552",
    "47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552"
  ],
  "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
  "is_long_range": true,
  "evidence_chain": [
    "knob --rotate to adjust the setting--> oven",
    "handle --pull to open or close--> oven"
  ],
  "source": "human_phase4",
  "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
  "shared_anchor_label": "oven",
  "reference_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
  "reference_label": "handle",
  "reference_relation": "pull to open or close",
  "long_range_pattern": "junction_2hop",
  "evidence_hop_count": 2,
  "reference_necessity": "strict",
  "is_label_only_solvable": false,
  "num_same_label_distractors": 18,
  "notes": "Phase 4 strict mode: query_text avoids naming the oven; reference 'handle pulls open' indirectly identifies the appliance. Erasing reference -> 6 candidate knobs (5 oven + 1 dishwasher knob), second-from-left flips; with reference -> 5 oven knobs only, second-from-left x=2.528 = knob 06b684bb."
}
```

5 条严格定义逐项核对：

1. ✅ scene_id=469011 在 20 SceneFun3D 中
2. ✅ evidence_chain 长度 = 2，两条 edge 都在 `scene_graph_summary_v1.txt` 469011 段
3. ✅ 两条 edge target 端都是 oven `8e66432e`
4. ✅ knob `06b684bb` ≠ oven `8e66432e` ≠ handle `47d6518d`
5. ✅ query_text 自然语言提到 "the silver handle pulls open"（reference 显式）

---

## ==挖矿可行性预估==

### 6 已选 scene（按 strict junction 定义）

junction 定义：appliance/container 节点 v 同时被 ≥ 2 条 incoming edge 指向，且这些 edge 来自 ≥ 2 个不同的 (source_label, relation) 组合（避免同 source 同 relation 的 paraphrase 灌水）。

| scene | 强 junction 候选 | 估计可写 query |
|---|---|---|
| 469011 | **oven** (5 knob `rotate to adjust the setting` + 1 handle `pull to open or close`) + **fridge** (1 outlet `provide power` + 1 handle `pull to open or close`) | **7–10 条** |
| 421254 | 0 strong junction（所有 anchor 单一 source 类型） | 0 |
| 421380 | **TV stand** (4 knob `pull to open or close` + 11 knob `pull to open or close a drawer`——同 source `knob`、不同 relation) | **3–4 条** |
| 421602 | 0 strong junction（每 appliance 上都是同类 element 同 relation） | 0 |
| 421013 | 0 strong junction | 0 |
| 420683 | 0 strong junction | 0 |
| **小计 6 scene** | — | **10–14 条** |

### 14 未启用 scene（Step 0 audit 待补）

Phase 0 audit 阶段曾扫过这 14 scene 的 `n_functional_queries` 等 same-label distractor 指标，**但未审计 junction 结构**。2026-05-23 调研发现：

- 大多数 scene 仍是严格 bipartite，但可能有 oven / microwave / TV stand 类 multi-relation junction
- **421267 / 466803** 含 `power strip → provide power → laptop / washing machine` 这种"appliance-source"反向边，扩大 junction 可能性

**保守估计：14 scene Step 0 audit 后总贡献 15–25 junction candidate query**

### 加总

| 来源 | junction 候选 query 数 |
|---|---|
| 6 已选 scene | 10–14 |
| 14 待 audit scene | 15–25 |
| **加总（估计）** | **25–40 条** |

**结论：**

- ==30 minimum 锚定**有足够空间靠 Step 0 audit + 6 scene 挖矿达成**==
- 40 ideal **几乎需要完整 14 scene audit + 部分 phase4-exclusive scene 加入**
- 50 stretch **必须用 phase4-exclusive scene + 把可能"弱 junction"（同 source 同 relation 但 reference 几何区分明确）也算入**，本批不强求

### Step 0 audit 脚本规格

`scripts/phase4_scene_audit.py`（标准库 only，无外部依赖）：

```text
输入：
  - scenefun3d_funrag_benchmark_enriched.json（完整 scene graph）
  - scenefun3d_node_geom.json（bbox，可选）

处理：
  1. 按 scene 分组
  2. 对每个 scene，按 edge["|"右端] 分组 → 找 incoming-degree ≥ 2 的 anchor
  3. 对每个 candidate anchor，列出所有 (source_label, relation, source_node_id) 三元组
  4. 计算 writable_pairs：从 incoming edges 里任选两条 e1=(s1,r1), e2=(s2,r2)
     满足 s1 != s2 AND (r1 != r2 OR source_label(e1) != source_label(e2))
     → 排除"两条同 (source_label, relation) 的灌水对"
  5. **额外扫描 3+ hop 候选**：检查是否有某 node 同时具有入边和出边（二部图反例
     如 421267 / 466803 的 power strip），若有则枚举可达的 chain 路径
  6. 输出 phase4_junction_audit.csv（每行一个 candidate (scene, anchor, e1, e2)
     或 chain (scene, edge_path)）

输出：
  - phase4_junction_audit.csv（候选清单，2-hop junctions + 罕见 3+ hop chains）
  - phase4_audit_summary.txt（按 scene 汇总：n_anchors, n_writable_pairs,
    n_chain_candidates, top anchor labels）
```

==该脚本只产生候选，不自动写 JSONL——所有 query 都需人工核查"reference 在 query_text 里是否自然""target 与 reference 不会混淆"等语义条件。==

---

## ==tag 与 scene 分布锚定==

| 维度 | 锚定 | 说明 |
|---|---|---|
| `difficulty_tags` 必含 | `long_range` | 硬性，validator C28 检 |
| `difficulty_tags` 推荐叠加 | `functional_relation` ≥ 80% / `same_label_disambiguation` ≥ 30% / `geometry_aware` ≥ 20% / `endpoint_ambiguity` 10–20% | 多 tag 反映 junction query 天然兼具多种 hard 特征 |
| `is_label_only_solvable=true` 比例 | ≤ 10% | 比 Phase 2 (20%) 更严，long-range 应几乎都不可 label-only 解 |
| scene 分布 | **6 scene 各 ≥ 2 条**（覆盖率） + Phase 4 新加 scene 各 ≥ 3 条 | 防单 scene 主导（如 469011 oven 一家独大） |
| `long_range_pattern` | 默认 `"junction_2hop"`（预计 90%+）；若有 3+ hop 候选则用 `"chain_3hop"` / `"junction_chain_Nhop"` | 字段值集合不封闭，按 Step 0 audit 实际发现追加 |
| `evidence_hop_count` 分布 | 预计 `{"2": ≥27, "3": 0–3}` @ 30 总条 | 二部图下 3+ hop 罕见；不强求 |

> 4 类下界确保切片分析时**每类都有数据点**；Phase 1–3 多次出现锚定 ±20% 漂移，Phase 4 同样允许漂移，但 30 minimum 与单 scene ≥ 2 条是硬底线。

---

## Step-by-step 标注流程

### Step 0：跑 phase4 scene audit（脚本，自动）

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase4_scene_audit.py
```

输出：
- `phase4_junction_audit.csv`（约 40–80 行 candidate (scene, anchor, edge_a, edge_b)）
- `phase4_audit_summary.txt`（按 scene 汇总）

### Step 1：选 junction + 估总数

对 audit CSV 每行 candidate：

```text
□ scene 内可访问？（6 已选 scene 优先；未启用 scene 需在 annotation_notes 段说明加入理由）
□ (source_a, relation_a) ≠ (source_b, relation_b)？（避免灌水）
□ reference_label 真实非 unknown？
□ shared_anchor 在 query_text 里能自然描述？（不能光靠 UUID）
□ target、reference 几何上能否唯一区分（如 5 knob rotate oven，必须用 geometry 或额外 cue 选其中一个）
```

通过的 → 写到 `selected_junctions` 段（annotation_notes.md Phase 4 progress 节）；rejected 的标 `rejected_reason`。

目标：选出 ≥ 30 个合格 candidate。

### Step 2：手写 query + 填 schema

对每个选定 candidate，按 §"Schema 详解" 必填 + 推荐字段写一条 JSONL 行。**同一 junction 可写多条 query**（变换 target 或 reference）。

每条 query 写完后立即跑 §"质量标准" 4 问自检。

### Step 3：edge 方向 trap 检查（高频 bug）

参 phase1.md / CLAUDE.md：
- `target_node_id` = edge_1 的 **src**（用户操作的那一端）
- `anchor_node_id` = edge_1 的 **tgt** = `shared_anchor_node_id`（被操作的那一端）
- `reference_node_id` = edge_2 的 **src**（另一条 evidence 的源端）

Validator C25/C26/C27 全部从严校验。批量写题时尤其要复核 supporting_edge_ids 两条的"|"右端是否一致。

### Step 4：跑 validator

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\long_range_stress_queries_v1.jsonl
```

通过标准：
- 0 ERROR
- C1–C13（除 C12 long_range 互斥外）全过
- C12 检 `is_long_range==true` 不出现在 main JSONL（双向校验）
- C24–C28（新增）全过

回归：再跑 pilot / main 主集，预期仍 0 ERROR / 0 WARN。

### Step 5：填 diagnostics + summary + STOP

写 `long_range_diagnostics_v1.jsonl`（与 main JSONL 一一对齐，schema 见 §"Diagnostics"）。

更新 `hard_slice_summary_v1.json`，追加 `long_range_stress` 段：

```json
{
  "long_range_stress": {
    "total_queries": 30,
    "by_pattern": {"junction_2hop": 28, "chain_3hop": 2},
    "by_scene": {"469011": 8, "421380": 4, "421602": 3, "...": "..."},
    "scenes_added_in_phase4": ["422007", "421267"],
    "evidence_hop_count_dist": {"2": 28, "3": 2},
    "shared_anchor_label_dist": {"oven": 7, "fridge": 4, "television stand": 4, "...": "..."},
    "difficulty_tag_counts": {"long_range": 30, "functional_relation": 25, "same_label_disambiguation": 12, "...": "..."},
    "is_label_only_solvable_count": 2,
    "is_label_only_solvable_ratio": 0.067
  }
}
```

annotation_notes.md 追加 `## Phase 4 progress — YYYY-MM-DD` 段（4 子段 Did / Counts / Potential issues / Files ready for review），末尾 `==STOP HERE — 等学长 ack 后决定 Phase 5/6/7==`。

---

## ==Schema 详解==

### long_range_stress_queries_v1.jsonl 每行（必填）

沿用 Phase 1/2/3 schema 100%，仅 5 处不同：

| 字段 | Phase 1–3 值 | Phase 4 值 |
|---|---|---|
| `is_long_range` | `false` | **`true`** |
| `supporting_edge_ids` 长度 | 1 | **≥ 2**（默认 2，罕见 3+） |
| `evidence_chain` 长度 | 1 | **≥ 2**（与 `supporting_edge_ids` 长度一致） |
| `evidence_hop_count`（diagnostics） | 1 | **≥ 2** |
| `source` | `"human"` / `"human_phase3"` | **`"human_phase4"`** |

`target_node_id` 仍是 edge_1 的 src；`anchor_node_id` 仍是 edge_1 的 tgt（= shared_anchor）。**reference 用独立的 `reference_node_id` 字段，不复用 `anchor_node_id`。**

### Phase 4 新字段（**全部必填**，含 `reference_necessity`）

```json
{
  "shared_anchor_node_id":   "<UUID = anchor_node_id，但显式重复一份方便 validator>",
  "shared_anchor_label":     "oven",
  "reference_node_id":       "<UUID = edge_2 的 src>",
  "reference_label":         "handle",
  "reference_relation":      "pull to open or close",
  "long_range_pattern":      "junction_2hop",
  "evidence_hop_count":      2,
  "reference_necessity":     "strict"
}
```

字段约束：

| 字段 | 约束 |
|------|------|
| `query_id` | 格式 `lr_v1_\d{6}` 或 `human_func_v1_lr_\d{6}`（待 ack），文件内唯一 |
| `is_long_range` | 必须 `true` |
| `supporting_edge_ids` | 长度 ≥ 2，每条格式 `"<src>\|<relation>\|<tgt>"`；2-hop 时两条的 `<tgt>` 必须相同（junction 共享 anchor）；3+ hop 时相邻两条须共享一个端点 |
| `target_node_id` | = `supporting_edge_ids[0]` 的 src |
| `anchor_node_id` | = `supporting_edge_ids[0]` 的 tgt（2-hop 时 = `shared_anchor_node_id`） |
| `reference_node_id` | = `supporting_edge_ids[-1]` 的 src（chain 末端），且 ≠ target_node_id ≠ anchor_node_id |
| `evidence_chain` | 长度与 `supporting_edge_ids` 一致；自然语言描述与之逐项对齐（同顺序）|
| `difficulty_tags` | 必含 `"long_range"`；其他 tag 来自 §6 固定列表 |
| `long_range_pattern` | 2-hop 默认 `"junction_2hop"`；3+ hop 用 `"chain_3hop"` / `"junction_chain_Nhop"` 等（按 Step 0 audit 实际发现命名） |

### long_range_diagnostics_v1.jsonl 每行

与 main JSONL 同 query_id 对齐，沿用 Phase 2 diagnostics schema：

```json
{
  "query_id":                 "lr_v1_000001",
  "scene_id":                 "469011",
  "is_label_only_solvable":   false,
  "num_same_label_distractors": 18,
  "expected_failure_modes":   ["pick_wrong_appliance_anchor", "pick_oven_handle_instead_of_oven_knob"],
  "distractor_node_ids":      ["<UUID list of 18 same-label knobs in scene>"],
  "geometry_cues_used":       [],
  "evidence_hop_count":       2,
  "long_range_pattern":       "junction_2hop",
  "target_anchor_3d_distance_m": 0.83
}
```

字段约束：
- `evidence_hop_count` 必须 ≥ 2，且与 main JSONL 的 `supporting_edge_ids` 长度一致
- `target_anchor_3d_distance_m`（新增 Phase 4 字段）= target_node 与 anchor_node 的 bbox_center 欧氏距离，用于 Research Plan §8.5 切片分析的辅助 metadata（不强制为约束）

---

## ==Validator 扩展（C24–C29）==

==**Phase 1/2/3 的 C1–C13 + C19–C23 一项不动**，新增 6 项 C24–C29，作用于 `is_long_range==true` 的行。== Phase 3 的 `validate_minimal_pairs.py` (C14–C18) 同样不动。

| # | 检查项 | 级别 | 说明 |
|---|---|---|---|
| C24 | `is_long_range==true` ⟹ `supporting_edge_ids` 长度 ≥ 2 且 `evidence_chain` 长度 = `supporting_edge_ids` 长度 | ERROR | Phase 4 schema 硬性（≥ 2 跟随 TASK_PLAN §11） |
| C25 | 所有 supporting_edge 都在 scene_graph 中真实存在（沿用 C7 主集逻辑扩展到所有条目） | ERROR | edge 真实性（修订 3） |
| C26 | **junction_2hop** (长度=2)：两条 edge 的 target（"\|"右端）一致；且与 `anchor_node_id` / `shared_anchor_node_id` 一致。**chain_Nhop** (长度≥3)：相邻两条 edge 共享一个端点（任一端） | ERROR | junction / chain 拓扑严格定义第 3 条 |
| C27 | `target_node_id` ≠ `reference_node_id` ≠ `shared_anchor_node_id`，且 `evidence_chain` 内涉及的所有 UUID 互不相同（chain 节点不重复） | ERROR | 严格定义第 4 条 |
| C28 | `is_long_range==true` ⟹ `difficulty_tags` 含 `long_range`，且该 query_id 不出现在 `pilot_20_queries.jsonl` / `functional_queries_v1.jsonl` 任一 | ERROR | 文件隔离硬性；与 C12 主集 long_range 互斥呼应 |
| C29 | `is_long_range==true` ⟹ `reference_necessity` 字段存在，值 ∈ {`"strict"`, `"contextual"`} | ERROR | 第 4 问操作化分类必填 |

### C12 主集逻辑（不变）

```python
# 主集 (pilot / functional_queries_v1) 中：
def check_c12(query):
    if query.get("is_long_range", False) is True:
        return ERROR  # long_range query 不能出现在主集
    if "long_range" in query.get("difficulty_tags", []):
        return ERROR  # tag 也不能出现
```

C12 与 C28 互补：C12 防"long_range 渗入主集"，C28 防"主集 query_id 被复用到 long_range 文件"。

### C25 实现细节

```python
def check_c25(query, scene_graph):
    if not query.get("is_long_range"):
        return PASS  # 不触发
    edges_in_graph = {(e["source"], e["relation"], e["target"]) for e in scene_graph["edges"]}
    for edge_id_str in query["supporting_edge_ids"]:
        src, rel, tgt = edge_id_str.split("|")
        if (src, rel, tgt) not in edges_in_graph:
            return ERROR(f"supporting_edge {edge_id_str} not in scene_graph")
    return PASS
```

### validation_report_phase4.md 格式

```markdown
## Phase 4 Validation Report — YYYY-MM-DD HH:MM

Input file:
  - long_range_stress_queries_v1.jsonl (N 条)

Main query validator (C1–C13) on long_range queries:
  PASS: N / N
  ERRORS: 0

Phase 4 validator (C24–C29):
  PASS: N / N
  ERRORS: 0
  WARNINGS: 0

reference_necessity distribution:
  strict:      N (target >= 30%, ideal 50%)
  contextual:  N

Distribution:
  by_scene:              { ... }
  by_shared_anchor_label: { ... }
  by_long_range_pattern: { junction_2hop: N, chain_3hop: N (若有), ... }
  evidence_hop_count:    { 2: N, 3: N (若有), ... }

Regression check (Phase 1/2/3 主集回归):
  pilot_20_queries:               20 / 20 PASS
  functional_queries_v1:         133 / 133 PASS
  minimal_pairs_v1 (派生视图):     28 / 28 PASS
```

---

## 文件清单与改动

**Phase 4 新建文件：**

| 文件 | 动作 | 说明 |
|------|------|------|
| `scripts/phase4_scene_audit.py` | 新建 | 跨 20 scene 找 junction，输出 CSV + summary |
| `scripts/phase4_query_generator.py` | 新建 | 30 条 hand-craft spec → JSONL（idempotent，沿用 Phase 2/3 pattern） |
| `phase4_junction_audit.csv` | 新建（脚本生成） | junction 候选清单 |
| `phase4_audit_summary.txt` | 新建（脚本生成） | 按 scene 汇总 |
| `long_range_stress_queries_v1.jsonl` | 新建（手动 + 脚本） | 30 条 Phase 4 query |
| `long_range_diagnostics_v1.jsonl` | 新建 | 与 main 一一对齐的诊断 |
| `validation_report_phase4.md` | 新建（脚本生成） | Phase 4 验证报告 |
| `hard_slice_summary_v1.json` | **追加更新** | 加 `long_range_stress` 段 |
| `annotation_notes.md` | **追加写** | 末尾追加 `## Phase 4 progress — YYYY-MM-DD` 段 |
| `scripts/validate_functional_queries.py` | **追加 C24–C28** | 不动 C1–C13 / C19–C23；新增独立段 |

**只读引用（绝对不修改）：**

- 所有 frozen 目录
- `functional_queries_v1.jsonl`（Phase 2/3 主集，133 条）
- `pilot_20_queries.jsonl`（Phase 1 pilot，20 条）
- `minimal_pairs_v1.jsonl`（Phase 3 派生，28 对）
- `functional_query_diagnostics_v1.jsonl`
- `scene_graph_summary_v1.txt`
- `scripts/phase3_compose_pairs.py` / `phase3_pair_miner.py` / `validate_minimal_pairs.py`（Phase 3 已交付脚本）

==**Phase 1/2/3 的 153 条 query + 28 对 pair 绝对不动**。==如 Step 0 audit 时发现某条 Phase 1–3 query 在 junction 视角下其实是"伪 1-hop"（实际涉及 2 个 edge），按 phase2.md "不达标处置" 流程 `[issue]` 写到 `annotation_notes.md` 等学长决定，**不在 Phase 4 顺手改**。

---

## ==质量标准（4 问）==

每条 Phase 4 query 都要能清楚回答 **4 个问题**（前 3 个继承 Phase 2，第 4 个 Phase 4 新增）：

```text
1. 为什么 query 的答案是这个 target？（继承 §16 第 1 问）
   → 5 个 oven-rotate knob 里，是哪一个？靠什么线索区分？

2. 哪两条 supporting edge 分别在 evidence chain 的哪一步？（继承 §16 第 2 问 + 扩展）
   → edge_1: target → rel_1 → shared_anchor（target 操作的功能）
   → edge_2: reference → rel_2 → shared_anchor（reference 的功能，用来标识 shared_anchor）

3. 模型能不能靠 label prior 解决？（继承 §16 第 3 问）
   → 18 个 knob 在 469011 全场存在；reference handle 是 shared_anchor 的关键
     disambiguator；纯靠 "knob" label 100% 解不出

4. ==reference 在 query 里起什么作用？==（Phase 4 新增，**标注而非 reject**）
   → 做 "reference 抹除" 心理实验：去掉 query_text 里关于 reference 的所有信息后，
     target 是否仍唯一可定位？
   - **NO**（抹后多候选） → `reference_necessity = "strict"`，reference 严格必要
   - **YES**（抹后仍唯一） → `reference_necessity = "contextual"`，reference 提供 multi-hop
     上下文但不严格必要——**仍接受**，因为 query 结构上仍是合法 2-hop（两条真实
     functional edge），仍能测试 Edge Recall / Supporting Edge Recovery 等 §8.5 指标
   - 详见 §"第 4 问操作化"段落（含 strict / contextual 设计技巧 + 比例锚定）
```

==**第 1 / 2 / 3 问答不清的 query 不能进 `long_range_stress_queries_v1.jsonl`；第 4 问做分类标注，不 reject。**==

不达标处置：
- 第 1 / 2 问答不清 → 信息不足或 evidence 模糊，丢回候选池或重写
- 第 3 问答"能（label-only solvable）" → `is_label_only_solvable=true`，比例 ≤ 10% 且 `notes` 说明
- 第 4 问 → 按 strict / contextual 二分填 `reference_necessity` 字段；strict 比例锚定 ≥ 30%（理想 50%），contextual 比例 ≤ 70%（结构上不可避免）

### 第 4 问操作化（strict / contextual 二分标注，**不**作为 reject 条件）

==**Phase 4 数据现实**：20 个 SceneFun3D scene 中**每个 appliance label 几乎都是唯一的**（1 oven / 1 fridge / 1 dishwasher / 1 sink 等）。这意味着 query_text 一旦直接命名 appliance（"the oven"），reference 在结构上就不会改变 target 的可定位性——严格"抹除 reference 后 target 仍唯一"会让几乎所有候选 query 被淘汰，Phase 4 实际数量上界 ≤ 5。==

为此把第 4 问从 hard reject 改为 **strict / contextual 二分标注**，两类都收入，但显式分类：

```text
对每条候选 query，做 "reference 抹除" 心理实验：

  原 query: 含 reference 描述
       ↓ 抹除 reference
  抹后 query: 不含 reference

  抹后 target 是否唯一可定位？
    NO  → reference_necessity = "strict"（理想：reference 严格必要）
    YES → reference_necessity = "contextual"（reference 提供 multi-hop 上下文，
          但不严格 disambiguating——仍接受，仍是合法 2-hop query）
```

**strict 模式设计技巧**：query_text **不直接命名 appliance**，让 reference 通过 functional edge 间接指认。例：

```text
✓ strict 模式：
  "Rotate the leftmost knob that adjusts an appliance the handle pulls open."
  - 抹除 reference: "Rotate the leftmost knob that adjusts an appliance"
  - 抹前候选：5 oven knob（"appliance the handle pulls open" 指认 oven）→ leftmost=d003c3b8
  - 抹后候选：6 knob（5 oven + 1 dishwasher，都能 "rotate" 一个 appliance）→ leftmost=ba5246d7（dishwasher knob，x=0.848）
  - 抹前后 target 不同 → reference 必要 → strict ✓

✗ contextual 模式（仍接受，但显式标注）：
  "Press the knob that adjusts the oven the silver handle pulls open."
  - "the oven" 直接命名 → reference "the silver handle pulls open" 是冗余描述
  - 抹除 reference 后 "the knob that adjusts the oven" 候选仍 5 个 → leftmost 也仍是 d003c3b8
  - reference 不严格必要，但 query 仍包含真实 2-hop evidence chain
  - 仍是合法 Phase 4 query，标 reference_necessity = "contextual"
```

**Phase 4 比例锚定**：
- `reference_necessity = "strict"` ≥ 30%（理想 50%）
- `reference_necessity = "contextual"` ≤ 70%（结构上不可避免——20 个 SceneFun3D scene 里每种 appliance 几乎都是唯一的，多数 query 一旦命名 appliance 就让 reference 失去严格 disambiguating 作用；写 strict 必须靠"不命名 appliance、用 reference 间接指认"的技巧，可行场景受限）
- 比例**不作为 ERROR**，但 hard_slice_summary 里报；strict ratio 过低（< 25%）时学长 review 应触发讨论是否扩 scene

`reference_necessity` 字段**强制必填**，写入 main JSONL 和 diagnostics；validator C29 检字段存在且值合法（见 §"Validator 扩展"段落更新）。

数据现实下不强求所有 query 全 strict——这是 SceneFun3D scene 结构性限制，不是写题质量问题。学长 review 时按 strict 比例判断切片价值。

---

## 完成定义（Phase 4 checklist）

Phase 4 完成必须全部 ✅：

```text
[ ] phase4_scene_audit.py 已写，phase4_junction_audit.csv 已生成（候选 ≥ 40 行）
[ ] long_range_stress_queries_v1.jsonl ≥ 30 条（理想 40）
[ ] 每条 query 通过 §"质量标准" 4 问（特别第 4 问反测试）
[ ] 每条 query is_long_range=true, evidence_hop_count ≥ 2,
    supporting_edge_ids 长度 ≥ 2, evidence_chain 长度 = supporting_edge_ids 长度
[ ] target_node_id ≠ shared_anchor_node_id ≠ reference_node_id；chain 内所有节点互不相同（C27）
[ ] junction_2hop：两条 edge 的 "|"右端一致；chain_Nhop：相邻 edge 共享一个端点（C26）
[ ] 每条 query reference_necessity ∈ {strict, contextual}（C29）；strict 比例 ≥ 30%（理想 50%）
[ ] validator C1–C13 + C24–C29 全过；0 ERROR
[ ] long_range_diagnostics_v1.jsonl 与 main 一一对齐
[ ] hard_slice_summary_v1.json 追加 long_range_stress 段
[ ] validation_report_phase4.md 写完
[ ] annotation_notes.md 追加 Phase 4 progress 段，末尾 ==STOP HERE==
[ ] 6 选定 scene 各 ≥ 2 条；Phase 4 新加 scene 各 ≥ 3 条（scene 分布锚定）
[ ] is_label_only_solvable=true 比例 ≤ 10%
[ ] frozen 目录 + Phase 1/2/3 已交付文件无任何改动（git status 确认）
[ ] 主 validator 重跑 pilot / main / minimal_pair 仍 0 ERROR（回归检查）
```

---

## Escalation Gate

```text
================================================================================
  STOP HERE
  Phase 4 完成后建议停下来等 Mingqian 审核，再决定 Phase 5 / 6 / 7
================================================================================
```

> TASK_PLAN §17 行 693 硬性规定只 Phase 1/2 必停；Phase 3/4 是建议性，但 Phase 4 涉及 schema 扩展（5 个新字段）、validator 扩展（C24–C28）、可能的 scene 集扩展——决策面比较宽，建议小停。

**向 Mingqian 汇报模板：**

```text
Phase 4 long-range stress set 已完成，请审核：

文件：
  functional_queries_v1/long_range_stress_queries_v1.jsonl
  functional_queries_v1/long_range_diagnostics_v1.jsonl
  functional_queries_v1/phase4_junction_audit.csv
  functional_queries_v1/phase4_audit_summary.txt
  functional_queries_v1/validation_report_phase4.md
  functional_queries_v1/hard_slice_summary_v1.json（已追加 long_range_stress 段）

概要：
  - N 条 junction 2-hop（vs 锚定 30 / 40 ideal）
  - scene 分布：[6 已选 + Phase 4 新加 scene 各 N 条]
  - junction shared_anchor_label 类型分布：oven=N, fridge=N, TV stand=N, ...
  - difficulty_tags：long_range=N, functional_relation=N, same_label_disambig=N, ...
  - is_label_only_solvable=true 比例：N%（vs 上限 10%）
  - validator：0 ERROR；C1–C13 + C24–C29 全过；回归 pilot/main/pair 0 ERROR
  - reference_necessity 分布：strict=N (≥30%, 理想 50%), contextual=N
  - 发现 issue：[列出，或"无"]

等 review 通过后决定 Phase 5（existing query audit）/ Phase 6（已完成 validator）/ Phase 7（汇总 summary）的优先级。
```

---

## Out of scope（显式排除）

- ❌ 真同向 A→B→C 三跳链 → 数据集不存在（二部图结构），写不出（与 3+ hop chain 不同，见下）
- ❌ Geometric step 串 functional edges（如 "the knob near the lamp the outlet powers"）→ 反例 4，属 Research Plan §8.5 spatially long-range，不在 Phase 4
- ⚠️ **3+ hop chains 不禁止**（TASK_PLAN §11 允许 ≥ 2），但二部图下结构性罕见；Step 0 audit 若发现真实候选（如 power strip 反向边形成的 chain）可收，按"Junction 2-hop 严格定义 → 3+ hop 扩展"附注的字段命名规则填写
- ❌ 修改 Phase 1/2/3 已交付文件 → 发现问题报 `[issue]` 到 `annotation_notes.md`，等学长定
- ❌ 改 validator C1–C13 / C19–C23 主逻辑 → 仅追加 C24–C28
- ❌ 把 long_range query 混入 `functional_queries_v1.jsonl` 或 `pilot_20_queries.jsonl` → C12 / C28 双重 fail
- ❌ Phase 3 minimal pair 在 Phase 4 上扩展（hop 数本身是 changed_factor）→ phase3.md Appendix C 已说明
- ❌ 改 `multimodal_extension/` 任何文件 → 另一支线产物，annotation 视为只读
- ❌ 回填 Phase 4 新加 scene 到 Phase 1/2/3 主集 → 学长 ack 仅允许 phase4-exclusive 新 scene
- ❌ Stretch 50 条强冲 → 锚定 30 minimum / 40 ideal，超过需学长 ack

---

## Appendix A：与 Phase 3 minimal pair 的关系

Phase 3 `evidence_hop_count = 1` 是为了让"changed_factor 单变量"不被 graph hop 数稀释；Phase 4 `evidence_hop_count ≥ 2`（默认 2，罕见 3+）是另一个独立维度。两阶段完全独立：

- 若两条 long_range query 只差 reference_node（如同一 oven 的 5 个 knob 中选不同 target）→ 算 Phase 4 内部对比，**不**走 `minimal_pairs_v1.jsonl`，schema 上**不引用** `minimal_pair_id` / `minimal_pair_role` / `minimal_pair_partner_id`
- 若 Phase 4 内部确实想做 pair-level 对比分析，可以在 `long_range_diagnostics_v1.jsonl` 加 `phase4_pair_id` 这种**独立命名**字段（不重用 Phase 3 schema），但本批不强制
- Phase 3 minimal_pair 与 Phase 4 long_range 在 hard_slice_summary 里分两段统计，**不互相计入**

参 phase3.md Appendix C 已说明：Phase 4 不消化 minimal pair 任务。

---

## Appendix B：与 Research Plan §8.5 spatially long-range 的关系

Research Plan §8.5（Long-Range Functional Reasoning）定义的 "spatially long-range" = target ↔ anchor **3D 距离**大（不是 graph hop 数）。两个维度完全独立，构成 2×2：

| | graph hop=1 | graph hop=2 (junction) |
|---|---|---|
| **spatial 近**（< 1m） | Phase 1/2/3 多数 query | Phase 4 多数 junction（target 与 reference 都在同一 appliance 上，几何近） |
| **spatial 远**（≥ 1.5m） | Phase 1 标记的 6 条 remote-type single-hop（000006/000009/000012/000013/000018/000019）+ Phase 2/3 类似 | Phase 4 偶发命中（如 outlet 提供 fridge 电、handle 拉 fridge 门，outlet 离 handle 可能跨墙） |

- Phase 1 annotation_notes 已记录这 6 条 single-hop spatially-long-range 在主集（不算 graph long_range）
- Phase 4 **不专门生产** §8.5 spatially long-range query；§8.5 评测可由学长在 paper analysis 时按 `target_anchor_3d_distance_m` 切片**现有** query（主集 + Phase 4） 完成
- Phase 4 query 在 diagnostics 里记 `target_anchor_3d_distance_m` 作为辅助 metadata，供后续切片用，但**不作硬约束**

工作日志多次混淆 graph long-range vs spatial long-range，本 phase 严格按 graph hop 数定义 Phase 4，spatial 视角留作 analysis-time 切片。详 CLAUDE.md "Concepts that get conflated" + phase1.md 行 305–324 + phase2.md Appendix A。

---

## Appendix C：Phase 0 audit re-run 的依据

学长 2026-05-23 ack："可以适当扩展 scene，只要能达到 phase4 的数据的质量和数量要求就可以。"

`phase4_scene_audit.py` 与 `phase0_scene_audit.py` 互补：

| 脚本 | 找什么 | 适合 |
|---|---|---|
| `phase0_scene_audit.py` | same-label distractor 丰富的 scene（n_unique_edges / max_same_label_count / n_endpoint_ambig_edges / z_axis_range）| Phase 1–3 1-hop functional query |
| `phase4_scene_audit.py` | junction 丰富的 scene（incoming-degree ≥ 2 的 anchor、≥ 2 种 (source, relation) 组合）| Phase 4 2-hop junction query |

可能选出 **4–6 个全新 scene** 加入 Phase 4 范围，例如：
- 422007（13 edges，可能有 microwave / TV junction）
- 421267（含 power strip 反向边，特殊 junction）
- 466803（同上）
- 460417 / 460419 / 421015 / 421063（待 audit 确认）

**仅 Phase 4 使用，不回填 Phase 1–3**——Phase 1–3 已交付的 153 条 query + 28 对 pair 是 review 快照，scene 集**冻结**，Phase 4 扩 scene 不应触发 Phase 1–3 重写。

---

## Appendix D：与已知 PENDING_MINGQIAN_ACK 的关系

Phase 3 留下 3 个 PENDING_MINGQIAN_ACK，与 Phase 4 关系：

1. **PAIR_QUERY_CONFLICT（Phase 3 28 对 vs 锚定 30）** — 与 Phase 4 无直接关系；Phase 4 不补 minimal pair
2. **FUNC_REL_CEILING_1（functional_relation 上界 1 对）** — Phase 4 同样受 6 scene functional_relation 多样性限制；若学长 ack 扩 Phase 0 scene 集，Phase 4 可同时受益（更多 functional_relation junction）。本 phase 不主动追赶，等学长决定
3. **target_label 67% knob** — Phase 4 由于 junction 多在 oven / fridge / TV stand，target_label 仍会以 knob / handle 为主（结构性原因）。Phase 4 不强行降比例，但 hard_slice_summary 段会同样统计 target_label 分布供学长 review
