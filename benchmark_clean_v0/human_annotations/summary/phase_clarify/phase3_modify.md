# Phase 3 修订执行计划：30 pairs + 自描述 schema

## Context

学长（Mingqian）2026-05-19 review 后给出两组指示，对当前 Phase 3 产物（20 对独立 pair 文件）进行结构性修订：

**指示 A（5 条质量要求）：** Phase 3 不要堆 knob/handle；优先补 outlet/switch/remote/faucet 类 functional relation；query_text 去掉裸坐标；增加自然语言变体；做真 minimal pair；保持 Phase 2，不重写大批旧 query。

**指示 B（schema 重设计）：** 新 query 写进 `functional_queries_v1.jsonl`（不开独立文件，符合 TASK_PLAN §4）。每条参与 pair 的 query **自身**带 `minimal_pair_id` / `minimal_pair_role` / `minimal_pair_partner_id` 三个字段，双向互指。Pair 两条 query 必须**同一文件相邻写**，便于人工 review 和后续 validator 编写。

**当前问题：**

- 现 `minimal_pairs_v1.jsonl`（20 对独立 pair 文件）= 单向引用，不符指示 B
- 现 7 条 pilot retag + 30 条 main retag 给了 `minimal_pair` tag，但没有 partner_id 等新字段
- 20 对里 85% target 是 knob/handle，22/37 query_text 含裸坐标，违反指示 A criteria 1/2
- pilot 和 main 跨文件的 pair 共 7 对，违反指示 B rule 2

**目标：** 把当前 20 对扩到 **30 对**（10 挖矿 + 20 新写），全部落到 `functional_queries_v1.jsonl`，用新 schema 重写。

---

## 锚定

| 维度 | 锚定 | 备注 |
|---|---|---|
| pair 总数 | **30 对** | TASK_PLAN §10 ideal 上界；之前 20 对 + 10 新对 |
| 挖矿对数 | **10 对** | 从现 20 对的 13 个 main-only pair 里挑最优 10 个；删掉 7 跨文件 pair + 1 全 pilot pair + 多余的同类 |
| 新写对数 | **20 对**（**40 条新 query**） | 全部走指示 A 5 条标准 |
| 新 query 落点 | `functional_queries_v1.jsonl` 末尾 | ID `human_func_v1_000114` 起，pair 内相邻写 |
| 新 query `source` 字段 | `"human_phase3"` | 区分 Phase 1/2 的 `"human"` |
| pilot 文件 | **回滚** 7 条 `minimal_pair` tag | pilot 不再参与任何 pair |
| `minimal_pairs_v1.jsonl` | 改为**派生视图**（脚本生成） | 权威源 = query 内嵌字段；保留此文件以符合 TASK_PLAN §4 §4 交付清单 |
| 字段命名 | 沿用 Phase 1/2（`query_text` / `supporting_edge_ids` / `difficulty_tags`） | 学长示例用了 `query`/`supporting_edge_id`/`tags`，但那是"推荐格式"非强制；保持现有 schema 一致性，只**新增** 3 字段 |

---

## 文件级改动

### 1. `pilot_20_queries.jsonl` ← in-place 修改
- 移除 7 条 query 的 `difficulty_tags` 列表中的 `"minimal_pair"`（回滚之前 retag patch 对 pilot 的影响）
- 其他字段不动
- 影响：pilot 20 条全部保持原 Phase 1 状态，不再参与任何 pair

### 2. `functional_queries_v1.jsonl` ← in-place 修改 + 末尾追加
- **修改现有 93 条**：
  - 对 10 对挖矿保留的 ~20 个 main query：在 `difficulty_tags` 保留 `"minimal_pair"`，并**新增** 3 字段
  - 对其他 main query（含先前 retag 但被弃用的 ~10 条）：移除 `difficulty_tags` 中的 `"minimal_pair"`
- **末尾追加 40 条新 query**（ID 000114–000153），全部带 `"minimal_pair"` tag 和 3 个新字段
- **重排**：让每对 pair 的两条 query 物理相邻（满足学长 rule 2）。挖矿对保留位置不变（已是相邻或同 cluster）；新 query 顺序写入即可天然相邻。
- 总条数：93 → **133**

### 3. `minimal_pairs_v1.jsonl` ← 重写为派生视图
- 由 `scripts/phase3_compose_pairs.py`（新脚本）从 `functional_queries_v1.jsonl` 的 `minimal_pair_id` 字段聚合生成
- 每行仍含 pair_id / scene / query_a_id / query_b_id / changed_factor / why_hard / pair_evidence_used / target_a/b_xyz / target_geom_diff_m / shared_relation / notes（保持当前 schema）
- 总数：20 → **30 对**

### 4. `scripts/phase3_retag_minimal_pair.py` ← **删除**
- 被新 `phase3_compose_pairs.py` 取代（自描述 schema 不需要事后 retag）

### 5. `scripts/phase3_compose_pairs.py` ← **新建**
- 输入：手工编辑的 pair 规格清单（脚本内 `SELECTED_PAIRS` dict）
- 处理：
  - 读 `functional_queries_v1.jsonl` 当前 93 条 → 决定哪些保留 `minimal_pair_id` 字段
  - 应用 40 条新 query 规格（脚本内 hand-craft 的 query 文本 + UUID）
  - 写出新 schema 的 `functional_queries_v1.jsonl`（133 条）
  - 生成 `minimal_pairs_v1.jsonl`（30 对，派生）
  - 同步 pilot 文件移除 `minimal_pair` tag
  - 重算 `hard_slice_summary_v1.json`
- idempotent：可重跑，每次产生相同输出

### 6. `scripts/validate_functional_queries.py` ← 扩展（不破坏 C1–C13）
- 在主 validator 末尾追加 5 项新检查（C19–C23）：
  - **C19**：若 `minimal_pair_id` 存在 → `minimal_pair_role` ∈ {"a","b"} 且 `minimal_pair_partner_id` 存在
  - **C20**：`minimal_pair_id` 存在 ⟺ `difficulty_tags` 含 `"minimal_pair"`
  - **C21**：`minimal_pair_partner_id` 必须在同一文件内存在
  - **C22**：双向一致：partner 的 `minimal_pair_partner_id` == 本 query 的 `query_id`；partner 的 `minimal_pair_id` == 本 query 的 `minimal_pair_id`
  - **C23**：partner 的 `minimal_pair_role` 与本 query 的不同（一个 "a"、一个 "b"）
- C9 的 `VALID_TAGS` 已含 `minimal_pair`（先前 retag patch 加过）—— 不动

### 7. `scripts/validate_minimal_pairs.py` ← 简化
- 不再独立检查 pair 文件结构（结构由 C19–C23 在 query 层保证）
- 仅保留 C16（target_a≠target_b 二次校核）+ C17（changed_factor 合法）+ C18（changed_factor 一致性）的派生视图校验
- 主要作用变成"生成报告"而非"错误检查"

### 8. `scripts/phase3_pair_miner.py` ← 不改
- 仍可重跑产生 `pair_candidates_v1.csv`（已存在）
- 作为辅助工具保留

### 9. `scripts/phase3_pair_builder.py` ← **删除**
- 被 `phase3_compose_pairs.py` 完全替代

### 10. `hard_slice_summary_v1.json` ← 重算
- `total_queries`: 93 → 133
- `difficulty_tag_counts` / `_ratios_pct`: 全部重算
- `minimal_pairs` 段：total_pairs 20 → 30；by_changed_factor / by_scene 重算
- 添加 `query_source_breakdown` 子段（新 vs 老 query 数）

### 11. `annotation_notes.md` ← 追加新段
- 在 Phase 3 progress 段后追加 `## Phase 3 revision — 2026-05-19`，按 4 子段（Did/Counts/Potential issues/Files modified）记录本次重构
- 不删先前 Phase 3 progress / retag patch 段（保留历史）

### 12. `summary/phase_clarify/phase3.md` ← 追加修订段
- 在文档末尾追加 `## Revision 1 — 学长 2026-05-19 review 反馈` 段
- 不改 phase3.md 正文（保留原决策快照，作为"事后修订"对照）

### 13. `validation_report.md` / `validation_report_phase3.md` ← 自动重写
- 跑 validator 后自动更新

### 14. `pair_candidates_v1.csv` ← 不改
- 历史挖矿产物保留

---

## 新写 40 条 query 的主题分布

按 6-scene 真实可写边的结构性上界，40 条新 query → 20 对 pair：

| 主题 | scene | pair 数 | changed_factor | 备注 |
|---|---|---|---|---|
| outlet → appliance | 469011 (6 outlets 接不同电器) | 4 对 | anchor_object | 主战场，fix knob/handle dominance |
| switch → ceiling light | 420683, 421013 | 3 对 | endpoint_ambiguity / spatial_qualifier | 含 "press switch vs press other element" |
| remote → TV（自然语言变体）| 421380, 421254 | 2 对 | spatial_qualifier / geometry_direction | "the remote closer to the TV" 类 |
| faucet/handle → sink | 469011 | 1 对 | endpoint_ambiguity | 唯一可写 |
| 现有 handle/knob 非坐标重写 | 各 scene | 6 对 | spatial_qualifier | 同结构换自然语言（"the upper-left knob" 不带 x=） |
| hard_negative 风格变体（间接问法）| 各 scene | 4 对 | anchor_object / functional_relation | "I need light — what do I press" 类 |
| **小计** | — | **20 对** = **40 条 query** | — | — |

**新 query 严格规则：**
- `query_text` **不含**裸坐标（"x=1.07"、"x≈"、"x=-0.443" 等一律禁止）
- 同结构 pair 内两条 query 应有词级差异（"upper" vs "lower"、"left" vs "right"、"fridge" vs "exhaust hood"）
- 自然语言多样化：同一对里 query_a 直接问、query_b 间接问也可（学长 criteria 3）
- 所有 supporting_edge_id 必须先在 `scene_graph_summary_v1.txt` 中确认真实存在
- 加 `phase_purpose` tag 候选值：`"phase3_language_diverse"`（fix criteria 5）—— **需要先扩 `VALID_TAGS`，等学长 ack 后加**

---

## 自描述 schema 字段（每条参与 pair 的 query 上）

按学长示例（沿用 Phase 1/2 字段命名）：

```json
{
  "query_id": "human_func_v1_000114",
  "scene_id": "469011",
  "query_text": "Which outlet powers the refrigerator?",
  "query_type": "functional",
  "target_node_id": "548a6569-...",
  "anchor_node_id": "7fddf637-...",
  "supporting_edge_ids": ["548a6569-...|provide power|7fddf637-..."],
  "difficulty_tags": ["anchor_object", "functional_relation", "minimal_pair", "hard_negative"],
  "is_long_range": false,
  "evidence_chain": ["electric outlet --provide power--> fridge"],
  "source": "human_phase3",
  "target_label": "electric outlet",
  "anchor_label": "fridge",
  "num_same_label_distractors": 5,
  "is_label_only_solvable": false,
  "notes": "Phase 3 new pair. Direct question form.",
  "minimal_pair_id": "minpair_v1_000021",
  "minimal_pair_role": "a",
  "minimal_pair_partner_id": "human_func_v1_000115"
}
```

字段约束：
- `minimal_pair_id` 格式 `minpair_v1_\d{6}`，每对两条 query 共用
- `minimal_pair_role` ∈ {"a", "b"}，按 query_id 字典序 a < b
- `minimal_pair_partner_id` 是另一条 query 的 `query_id`（互指）

---

## Verification（执行后自检）

1. **跑主 validator on functional_queries_v1.jsonl**：
   - `python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py benchmark_clean_v0\human_annotations\functional_queries_v1\functional_queries_v1.jsonl`
   - 预期：133 PASS / 0 ERROR / 0 WARN（含 C1–C13 + C19–C23）
2. **跑主 validator on pilot_20_queries.jsonl**（回归）：预期 20 PASS / 0 ERROR
3. **跑 phase3_compose_pairs.py** 验 idempotency：第二次运行不改任何文件
4. **跑简化版 validate_minimal_pairs.py on minimal_pairs_v1.jsonl**：预期 30 PASS
5. **手动抽查**：随机选 3 对，确认两条 query 物理相邻、双向指针正确、query_text 无坐标
6. **`git status -s`** 检查：仅 sidecar 路径有改动（pilot + main + scripts + summaries + hard_slice + annotation_notes + phase3.md + minimal_pairs），frozen 目录无任何改动

---

## Out of scope（本次修订不做）

- ❌ 改 phase3.md 正文（只追加 Revision 1 段）
- ❌ 改 TASK_PLAN_BENCHMARK_QUALITY_EXTENSION.md（frozen 类文档；spec gap 由学长决定是否更新）
- ❌ Phase 4 long-range stress set（独立阶段，等学长再 ack）
- ❌ 扩 Phase 0 scene 集解决 functional_relation 上界问题（FUNC_REL_CEILING_1 issue 维持 PENDING）
- ❌ 加 phase_purpose tag 体系（先做 schema 自描述 + 数量扩到 30；phase_purpose 是独立改进，等学长 ack 后再做）
- ❌ 修改 `multimodal_extension/` 任何文件

---

## 待学长 ack 的小决策（不阻塞，可执行时默认走推荐项）

1. **字段命名**：沿用现 Phase 1/2 的 `query_text` / `supporting_edge_ids` / `difficulty_tags`（推荐），还是切到学长示例的 `query` / `supporting_edge_id` / `tags`？后者会破 Phase 1/2 + validator 的所有现有兼容性。
   - **推荐**：沿用现有，仅新增 3 字段
2. **挖矿 10 对的选取**：保留高质量 cluster pair（如 421380 A/B 各 4 对内部步进 + 2 对端点）还是平均分散？
   - **推荐**：4 cluster + 6 跨 anchor 的 spatial/geometry/anchor 对，4 类 changed_factor 全覆盖
3. **新 query 是否带 `geometry_cues` 字段**（Phase 2 cluster 都带，新 query 走自然语言要不要保留这字段名）？
   - **推荐**：保留字段名，但内容写自然语言方向词（"upper", "right-of-fridge"），不带数字坐标
4. **`source` 字段值**：`"human_phase3"`（推荐，可切片）vs `"human"`（与 Phase 1/2 一致）？
   - **推荐**：`"human_phase3"`

---

## 工作量估算

- 重写 `phase3_compose_pairs.py`（含 20 对 hand-craft spec）：~ 2 小时
- 扩 validator C19–C23：~ 30 分钟
- 简化 `validate_minimal_pairs.py`：~ 15 分钟
- 跑 + 调 + 回归 + 报告更新：~ 45 分钟
- **总计：~ 3.5 小时**

---

## 风险点

1. **20 对新 pair 的 anchor_object 上限 ≤ 7** 真实可写（依赖 469011 outlet 多样性 + 420683/421013 switch→light）。若实际不够，会降到 6–7 对 anchor_object，对应缺口转其他 changed_factor 类。
2. **functional_relation 仍只有 1 unique anchor（421380 TV stand）**，本次修订不解决——继续 PENDING_MINGQIAN_ACK（FUNC_REL_CEILING_1）
3. **schema 自描述 + 派生视图** 引入双数据源风险（query 内嵌字段 vs `minimal_pairs_v1.jsonl`）。C22 双向一致性 + 派生脚本 idempotent 设计应能兜底，但首次运行需仔细对账
4. **回滚 pilot retag** 会让 hard_slice 的 minimal_pair tag 数从 30 微调（pilot 不再贡献，仅算 main 中保留的 ~20 条）
