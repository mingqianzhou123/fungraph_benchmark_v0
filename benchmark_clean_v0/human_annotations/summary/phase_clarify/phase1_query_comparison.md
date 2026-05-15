# 新旧 Query 标注文件对比

## 同一件事，两个版本的描述

> **场景：** scene 420683，有 9 个 knob，1 个 radiator，答案是控制 radiator 温度的那个 knob

---

### 🔴 旧版（`all_queries_index.jsonl`）

```json
{
  "query_id": "q_0000_v0",
  "query":    "Adjust the room's temperature using the radiator thermostat",
  "target_node_ids":   ["e0047d50-..."],
  "anchor_node_id":    "8a1b9af6-...",
  "supporting_edge_id": "e0047d50-...|rotate to adjust the temperature|8a1b9af6-...",
  "supporting_edge_ids": ["e0047d50-...|rotate to adjust the temperature|8a1b9af6-..."],
  "annotation_source": "human",
  "action_verb": "rotate"
}
```

### 🟢 新版（`pilot_20_queries.jsonl`）

```json
{
  "query_id": "human_func_v1_000001",
  "query_text": "Turn the radiator knob to control the room temperature",
  "target_node_id":    "e0047d50-...",
  "anchor_node_id":    "8a1b9af6-...",
  "supporting_edge_ids": ["e0047d50-...|rotate to adjust the temperature|8a1b9af6-..."],
  "difficulty_tags":        ["simple_functional"],
  "evidence_chain":         ["knob --rotate to adjust the temperature--> radiator"],
  "is_label_only_solvable": true,
  "num_same_label_distractors": 8,
  "expected_failure_modes": [],
  "notes": "scene 420683 has 9 knobs but only 1 radiator; anchor uniquely identifies target."
}
```

---

## 字段覆盖度对比

| 字段 | 旧版 | 新版 | 作用 |
|------|:----:|:----:|------|
| `query_id` | ✅ | ✅ | 唯一标识 |
| `target_node_id` | ✅ | ✅ | 正确答案 |
| `anchor_node_id` | ✅ | ✅ | 参照物 |
| `supporting_edge_ids` | ✅ | ✅ | 证据边 |
| `difficulty_tags` | ❌ | ✅ | **难度标签（分片分析的关键）** |
| `evidence_chain` | ❌ | ✅ | **为什么是这个答案** |
| `is_label_only_solvable` | ❌ | ✅ | **能靠 label 猜对吗** |
| `num_same_label_distractors` | ❌ | ✅ | **有几个同名干扰项** |
| `expected_failure_modes` | ❌ | ✅ | **模型容易怎么犯错** |
| `geometry_cues` | ❌ | ✅ | **用了什么空间方向词** |
| `notes` | ❌ | ✅ | 人工审计备注 |

---

## Query 类型分布对比

```
旧版 all_queries_index.jsonl（14679 条）
┌─────────────────────────────────────────────────────────┐
│  functional  ████████████████████░░░░░░  ~40%           │
│  spatial     ██████████████████░░░░░░░░  ~35%           │
│  semantic    ████████████░░░░░░░░░░░░░░  ~25%           │
└─────────────────────────────────────────────────────────┘
  每种类型内部：只有 v0/v1/v2 三个 paraphrase，题目类型完全相同
  difficulty_tags 分布：❌ 未知（没有标注）
```

```
新版 pilot_20_queries.jsonl（20 条，全部 functional）
┌─────────────────────────────────────────────────────────┐
│  simple_functional         ████░░░░░░░░░░░░░  4 条 20% │
│  functional_relation       ████████░░░░░░░░░  6 条（含其他tag）│
│  same_label_disambiguation ████████░░░░░░░░░  8 条（含其他tag）│
│  endpoint_ambiguity        ████░░░░░░░░░░░░░  4 条（含其他tag）│
│  geometry_aware            ███░░░░░░░░░░░░░░  3 条 15% │
│  hard_negative             ██░░░░░░░░░░░░░░░  2 条 10% │
└─────────────────────────────────────────────────────────┘
  每条 query 类型明确，可单独分析模型在各难度子集上的表现
```

---

## 旧版的典型写法 vs 新版的典型写法

### 普通 functional（旧版能做，新版也能做）

```
旧版三个 paraphrase（本质是同一题换说法）：
  v0: "Open the bottom drawer of the dresser"
  v1: "Pull the knob on the bottom drawer of the dresser to open it."
  v2: "I need to access something in the dresser's bottom drawer — which knob should I grab?"

新版的同类型 query（simple_functional）：
  "Turn the radiator knob to control the room temperature"
  多了：evidence_chain、difficulty_tags、notes 等审计字段
```

### Hard Negative（旧版完全没有，新版独有）

```
❌ 旧版没有这类 query

🟢 新版：
  "I need to rest on the bed — which furniture do I open to get pillows"
   ↑ 完全不提 handle / drawer，必须靠语义推理 + functional edge 解答
  
  difficulty_tags: ["hard_negative", "functional_relation"]
  expected_failure_modes: ["ignore_functional_relation", "label_only_shortcut"]
  is_label_only_solvable: false
```

### Endpoint Ambiguity（旧版没有，新版独有）

```
❌ 旧版没有这类 query

🟢 新版：
  "Press the switch to turn on the ceiling light above the bed"
   ↑ 答案是 switch，但 ceiling light 也是可交互对象，模型易混淆
  
  difficulty_tags: ["endpoint_ambiguity", "functional_relation"]
  expected_failure_modes: ["choose_anchor_instead_of_target"]
  evidence_chain: ["light switch --control, turn on or turn off--> ceiling light"]
```

---

## 最核心的差异：能不能做 Slice Analysis

### 旧版能报的结论
```
整体 Recall@1 = 0.72
```

### 新版能报的结论
```
整体 Recall@1 = 0.72
  └── simple_functional           R@1 = 0.91  ← 简单的模型基本对
  └── same_label_disambiguation   R@1 = 0.68  ← 同名消歧有困难
  └── endpoint_ambiguity          R@1 = 0.54  ← 容易选错端点
  └── hard_negative               R@1 = 0.41  ← 不靠 functional edge 就失败
  └── geometry_aware              R@1 = 0.63  ← 几何定位有一定能力

→ 可以证明：模型在 hard_negative 和 endpoint_ambiguity 上明显弱
→ 进而证明：方法提升主要来自对 functional edge 的利用
```

---

## 一图流总结

```
旧版                           新版
─────────────────────          ─────────────────────────────────
大量 query（14679 条）          精选 20 条（Phase 1 pilot）
题型单一（只是 paraphrase）      题型多样（6 种 difficulty）
没有难度标签                    每条有 difficulty_tags
没有 evidence_chain            每条解释"为什么是这个答案"
无法切片分析                    可以做 same_label / hard_negative 等分析
无法证明方法用了 functional edge  可以证明（hard_negative 子集 R@1 低）
```
