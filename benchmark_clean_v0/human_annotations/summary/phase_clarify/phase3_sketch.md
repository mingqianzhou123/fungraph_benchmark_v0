# Phase 3 Plan Review Hand-off

## Context

用户（intern）要求基于 TASK_PLAN_BENCHMARK_QUALITY_EXTENSION.md + `summary/phase_clarify/{phase, phase0, phase1, phase1_manual_review, phase1_query_comparison, phase2}.md` 这套已有材料，**写一份 phase3.md 草稿描述 Phase 3 minimal-pair / adversarial query 的执行打算**，由学长 Mingqian 先审阅再实施。

phase3.md 草稿已写到：

- [phase3.md](../../d:/my_all_learning/CoRL/fungraph_benchmark_v0/benchmark_clean_v0/human_annotations/summary/phase_clarify/phase3.md)

本 plan 文件仅作为该 phase3.md 的"快速审阅指南"，不替代 phase3.md 本身。phase3.md 即用户要求的交付物，结构沿用 phase2.md 风格（约 480 行）。

---

## phase3.md 关键设计选择速览

学长审阅时主要看这 4 项是否同意，phase3.md 已逐项展开理由：

### 1. 数量锚定 = **20 对** minimal pair
- TASK_PLAN §10 给的是 15 minimum / 30 ideal
- 选 20 因为基于 113 条已有 query（pilot 20 + Phase 2 主集 93），挖矿可行性预估 17–25 对**不补写就够**
- 30 stretch 几乎必须扩 Phase 0 scene 集，超 Phase 3 范围

### 2. Query 来源策略 = **挖矿优先 + 必要时补写到独立文件**
- Phase 2 的 93 条 + Phase 1 的 20 条 = 不浪费的挖矿池
- 补写新 query 落到 **`minimal_pair_queries_v1.jsonl`**（独立文件），ID 接 `human_func_v1_000114` 起；不污染正在 review 的 `functional_queries_v1.jsonl` 93 条
- 推荐：补写时优先与已有 Phase 1/2 query 组对（最大化复用）

### 3. changed_factor 4 类分布
| changed_factor | 锚定数 | 主要 scene |
|----------------|--------|------------|
| `spatial_qualifier` | 9 | 421380 cluster A/B、421013/421602 |
| `geometry_direction` | 4 | 421380 cluster 两端、左右对立 |
| `anchor_object` | 5 | 469011、421254 |
| `functional_relation` | 2 | 6 scene 上限 |

4 类各 ≥ 1 是硬底线（切片分析每类都有数据点）。±20% 漂移可接受。

### 4. Validator 扩展不动 C1–C13
- 新加独立脚本 `validate_minimal_pairs.py`，含 C14–C18（pair 格式、引用存在性、target 不同、changed_factor 一致性）
- 主 validator `validate_functional_queries.py` 一行不改，确保 Phase 2 回归

---

## ==学长审阅时建议重点关注的 3 个待决项==

phase3.md "本次锚定" 段已列出，复述：

1. **补写 query 是否独立文件**？推荐独立 `minimal_pair_queries_v1.jsonl`（不破坏 Phase 2 review 快照）。如学长希望直接 append 到 `functional_queries_v1.jsonl`，会让 Phase 2 的 93 条数字变动，hard_slice_summary 也要重写。
2. **Pair 中允许两条都是新写的吗**？推荐允许但优先复用 Phase 1/2，原因是已有 query 已经过 Phase 1/2 review 和 validator 13 项检查。
3. **数量上界 20 vs 30**？推荐先 20，挖矿完成后看 changed_factor 分布是否需要补写到 30。

---

## phase3.md 的全文结构（便于学长跳读）

```
Context
本次锚定（待学长确认）       ← 4 项关键锚定 + 3 个待决项
输入文件（只读）
继承自 Phase 0/1/2 的口径修订  ← unknown 不计 / 421380 v2 / edge 真实性
Minimal Pair 严格定义        ← 4 必要条件 + 5 反例
挖矿可行性预估                ← 基于 113 条的粗估表（17–25 对）
changed_factor 分布锚定
Step-by-step 标注流程          ← Step 0–7
Schema 详解                    ← minimal_pairs_v1.jsonl + 补写 query
Validator 扩展（C14–C18）
文件清单与改动                 ← 新建 6 / 更新 2 / 只读引用
质量标准                       ← 5 问（继承 Phase 2 三问 + Phase 3 两问）
完成定义 checklist
Escalation Gate                ← STOP HERE
Out of scope
Appendix A：与 CAP_LIMIT 的关系
Appendix B：与 y vs z 高度轴 issue 的关系
Appendix C：与 Phase 4 long-range 的接力关系
```

---

## 不在 phase3.md 中、但学长可能想问的问题

- **为什么不在 Phase 3 就开始写 long-range？** → phase3.md Appendix C 说明：long-range 天然没法做严格 minimal pair（hop 数本身就是 changed_factor），Phase 3/4 独立。
- **Phase 2 的 421380 cluster 10 条已经像 minimal pair 了，为什么不直接打包？** → phase3.md "挖矿可行性预估" 段算了 cluster A/B 可挖 10–12 对（去重后），是 Phase 3 主战场，但仍要走 pair_miner + 人工筛 + pair validator 流程，确保 schema 正确、changed_factor 单一。
- **要不要先写脚本再写 plan？** → phase3.md Step 0 已规划 `phase3_pair_miner.py`，但脚本本身不在本次 plan 范围；学长 ack 后再实施。

---

## Verification（学长审阅完后的下一步）

如学长 ack phase3.md：
1. 用户开始按 Step 0–7 执行
2. 先写 `phase3_pair_miner.py` + 跑出 `pair_candidates_v1.csv`
3. 人工筛 + 写 `minimal_pairs_v1.jsonl`（必要时补写 `minimal_pair_queries_v1.jsonl`）
4. 写 `validate_minimal_pairs.py` + 跑 → `validation_report_phase3.md`
5. 追加 `hard_slice_summary_v1.json` 的 `minimal_pairs` 段
6. `annotation_notes.md` 追加 Phase 3 progress + `==STOP HERE==`

如学长对锚定/来源/分布有修改：
- 直接在 phase3.md 上批注或回复修订点，我按修订重写后再发审

如学长决定 Phase 3 不做或换方向（如先做 Phase 5 existing query audit）：
- 把 phase3.md 移到归档；按新方向重新写对应 phase 的展开 md
