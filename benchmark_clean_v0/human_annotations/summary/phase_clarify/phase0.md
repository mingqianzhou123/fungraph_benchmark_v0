# Phase 0 详细计划：备选 Scene / Edge 遴选

> 这是 `phase.md` 的 Phase 0 展开版。脚本放到 `benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/`，输出放到 `benchmark_clean_v0/human_annotations/functional_queries_v1/`。

---

## Context

**为什么要先做 Phase 0？**

Phase 1 开始写 query 之前，必须先知道：

> **当前 SceneFun3D 的 23 个 annotated scenes 里，哪些 scene 值得优先标注？哪些 functional edge 最适合出题？**

不先做场景遴选，直接开始写 query 会遇到：
- 随机选到的 scene 里没有 same-label distractor → 写不出 hard case
- 选到的 edge 两端都是 lamp/radiator → 写不出 endpoint ambiguity
- 选到的 scene 所有 node 都没有 bbox → geometry_aware tag 没法贴

Phase 0 的输出 `scene_audit_v1.csv` 是 Phase 1 写 query 的基础，`annotation_notes.md` 是向 Mingqian 汇报的载体。**Phase 0 完成后不需要停下来等 review，直接进入 Phase 1。**

---

## 数据背景（已确认）

| 事实 | 数值 |
|------|------|
| OpenFunGraph annotated scenes | 23 个（dev: 9 + test: 14） |
| 有 bbox 的 scenes / nodes | 20 / 317 |
| SceneFun3D functional queries 总数 | 870 条 |
| 全部 SceneFun3D queries | 1,485 条 |
| Functional edge 类型数 | 21 种 |
| Node label 类型数 | 52 种 |

---

## 输入文件

### 1. Query JSONL（主要输入）
路径：`benchmark_clean_v0/queries/all_queries_index.jsonl`

每行一条 JSON。**只处理 `dataset == "scenefun3d"` 且 `query_type == "functional"` 的条目**。

已确认字段（schema inspection 结果）：

| 字段 | 类型 | 示例 |
|------|------|------|
| `query_id` | str | `"q_0000_v0"` |
| `scene_id` | str | `"420683"` |
| `split` | str | `"train"` / `"val"` / `"test"` |
| `query_type` | str | `"functional"` |
| `dataset` | str | `"scenefun3d"` |
| `target_node_ids` | list[str] | `["e0047d50-..."]` |
| `target_labels` | list[str] | `["knob"]` |
| `anchor_node_id` | str \| null | `"8a1b9af6-..."` |
| `action_verb` | str \| null | `"rotate"` / `"pull"` / `"press"` |
| `supporting_edge_id` | str \| null | `"target_id\|edge_desc\|anchor_id"` |
| `supporting_edge_ids` | list[str] | 通常长度为 1 |

**supporting_edge_id 解析规则：**
```python
src_node_id, edge_description, tgt_node_id = edge_id.split("|", 2)
# src = target（你操作的对象），tgt = anchor（它控制的对象）
```

### 2. Geometry JSON
路径：`benchmark_clean_v0/geometry/scenefun3d_node_geom.json`

```json
{
  "<scene_id>": {
    "<node_id>": {
      "bbox_center": [x, y, z],
      "bbox_min": [x, y, z],
      "bbox_max": [x, y, z]
    }
  }
}
```

20 scenes / 317 nodes。用于检查每个 target/anchor node 是否有 bbox。

### 3. 全量边类型（已知，无需脚本读取）
路径：`benchmark_clean_v0/annotations/openfungraph/all_edges.json`

21 种 functional edge description，完整列表：

```
"press to open or close, or adjust the setting"
"rotate to control the water flow"
"press or rotate to open"
"push to flush"
"pull or rotate to open or close"
"rotate to adjust the temperature"
"rotate or press to adjust the setting"
"rotate to adjust the setting"
"rotate to open or close"
"pull to open or close"
"control, turn on or turn off"
"press or rotate to flush"
"press or rotate to control the water flow"
"rotate to adjust setting or temperature"
"pull to open or close a drawer"
"rotate to adjust the setting or open or close"
"control the water flow"
"provide power"
"press or rotate to control the water flow"
"control"
"rotate to flush"
```

### 4. 全量 node label（已知，无需脚本读取）
路径：`benchmark_clean_v0/annotations/openfungraph/all_labels.json`

52 种 node label（详见文档末尾附录）。

---

## 核心定义

### Actionable Target Labels（可操作对象）

这些 label 的 node 才可能成为 query 的 target（用户直接操作的物体）：

```python
ACTIONABLE_LABELS = {
    # handle / faucet 类
    "handle / faucet", "handle", "faucet / handle", "faucet / knob / handle",
    # knob / button 类
    "knob / button", "knob", "button / knob", "button",
    # switch 类
    "light switch", "switch panel", "switch panel / electric outlet",
    # remote
    "remote",
    # drawer / door（直接被 pull 的对象）
    "drawer", "nightstand drawer", "door", "glass door",
    # 可拉开的 cabinet
    "cabinet / closet",
}
```

### ==Endpoint Ambiguity Edge Types==

以下 edge 两端都可能被误选为 target，属于 endpoint_ambiguity：

```python
ENDPOINT_AMBIG_EDGE_PATTERNS = [
    "pull to open or close",           # handle ↔ drawer/door
    "pull to open or close a drawer",  # handle ↔ drawer
    "pull or rotate to open or close", # handle ↔ door
    "control, turn on or turn off",    # switch ↔ lamp/appliance
    "control",                         # switch/button ↔ device
    "control the water flow",          # faucet/handle ↔ sink
    "rotate to control the water flow",
    "press or rotate to control the water flow",
    "provide power",                   # power strip/outlet ↔ device
]
```

判断方式：edge 的 src（target）是 ACTIONABLE_LABELS，而且 tgt（anchor）的 label 也在人类直觉上"可以被选"。

### Same-Label Disambiguation 判断

在同一 scene 中，同一 `target_label` 出现次数 ≥ 2 → 存在 same-label distractor。

---

## Algorithm

### Step 1：读取所有 SceneFun3D functional queries

```python
from collections import defaultdict
import json, csv

QUERY_PATH = "benchmark_clean_v0/queries/all_queries_index.jsonl"
GEOM_PATH  = "benchmark_clean_v0/geometry/scenefun3d_node_geom.json"

functional_queries = []
with open(QUERY_PATH) as f:
    for line in f:
        q = json.loads(line)
        if q["dataset"] == "scenefun3d" and q["query_type"] == "functional":
            functional_queries.append(q)

# 预期结果：870 条
assert len(functional_queries) == 870, f"Expected 870, got {len(functional_queries)}"
```

### Step 2：读取 geometry

```python
with open(GEOM_PATH) as f:
    geom = json.load(f)

def has_bbox(scene_id, node_id):
    return scene_id in geom and node_id in geom[scene_id]
```

### Step 3：按 scene_id 分组，构建 per-scene 统计

```python
scenes = defaultdict(lambda: {
    "queries": [],
    "edges": {},            # edge_id -> edge_description
    "target_nodes": {},     # node_id -> label
    "anchor_nodes": {},     # node_id -> label
    "label_to_nodes": defaultdict(set),  # label -> set of node_ids
})

for q in functional_queries:
    sid = q["scene_id"]
    scenes[sid]["queries"].append(q["query_id"])

    # 解析 supporting_edge_id
    for edge_id in q.get("supporting_edge_ids", []):
        if edge_id and "|" in edge_id:
            parts = edge_id.split("|", 2)
            if len(parts) == 3:
                src_id, edge_desc, tgt_id = parts
                scenes[sid]["edges"][edge_id] = edge_desc

    # 记录 target nodes
    for nid, lbl in zip(q.get("target_node_ids", []), q.get("target_labels", [])):
        scenes[sid]["target_nodes"][nid] = lbl
        scenes[sid]["label_to_nodes"][lbl].add(nid)

    # 记录 anchor node
    if q.get("anchor_node_id"):
        anchor_label = (q.get("anchor_labels") or [None])[0] or "unknown"
        scenes[sid]["anchor_nodes"][q["anchor_node_id"]] = anchor_label
        scenes[sid]["label_to_nodes"][anchor_label].add(q["anchor_node_id"])
```

### Step 4：对每个 scene 计算 audit 指标

```python
rows = []

for scene_id, data in sorted(scenes.items()):
    queries = data["queries"]
    edges   = data["edges"]

    # --- 基础计数 ---
    n_queries      = len(set(queries))
    n_unique_edges = len(edges)

    # --- Action verb 分布 ---
    action_counts = defaultdict(int)
    for q in functional_queries:
        if q["scene_id"] == scene_id and q.get("action_verb"):
            action_counts[q["action_verb"]] += 1

    # --- Edge description 分布 ---
    edge_desc_counts = defaultdict(int)
    for desc in edges.values():
        edge_desc_counts[desc] += 1

    # --- Actionable target 统计 ---
    actionable_targets = {
        nid: lbl for nid, lbl in data["target_nodes"].items()
        if lbl in ACTIONABLE_LABELS
    }
    n_actionable_targets = len(actionable_targets)

    # --- Same-label distractor 统计 ---
    same_label_groups = {
        lbl: len(nids)
        for lbl, nids in data["label_to_nodes"].items()
        if len(nids) >= 2
    }
    max_same_label_count = max(same_label_groups.values(), default=0)
    n_same_label_groups  = len(same_label_groups)

    # --- Endpoint ambiguity 统计 ---
    endpoint_ambig_edges = {
        eid: desc for eid, desc in edges.items()
        if any(pat in desc for pat in ENDPOINT_AMBIG_EDGE_PATTERNS)
    }
    n_endpoint_ambig = len(endpoint_ambig_edges)

    # --- Bbox 覆盖 ---
    n_target_with_bbox = sum(
        1 for nid in data["target_nodes"] if has_bbox(scene_id, nid)
    )
    n_anchor_with_bbox = sum(
        1 for nid in data["anchor_nodes"] if has_bbox(scene_id, nid)
    )
    n_target_total   = len(data["target_nodes"])
    n_anchor_total   = len(data["anchor_nodes"])
    target_bbox_rate = n_target_with_bbox / n_target_total if n_target_total else 0
    anchor_bbox_rate = n_anchor_with_bbox / n_anchor_total if n_anchor_total else 0

    # --- Geometry 空间区分度（Z 轴跨度，判断 scene 是否适合写 upper/lower query）---
    scene_node_zvals = []
    if scene_id in geom:
        scene_node_zvals = [v["bbox_center"][2] for v in geom[scene_id].values()]
    z_range = max(scene_node_zvals) - min(scene_node_zvals) if len(scene_node_zvals) >= 2 else 0

    # --- 推荐分（0~4，对应4个选场景标准）---
    score = 0
    if n_unique_edges >= 5:         score += 1  # functional edges 丰富
    if max_same_label_count >= 3:   score += 1  # same-label distractors 多
    if n_endpoint_ambig >= 2:       score += 1  # endpoint ambiguity 丰富
    if target_bbox_rate >= 0.8:     score += 1  # geometry 覆盖好

    rows.append({
        "scene_id":                  scene_id,
        "n_functional_queries":      n_queries,
        "n_unique_edges":            n_unique_edges,
        "n_actionable_targets":      n_actionable_targets,
        "n_same_label_groups":       n_same_label_groups,
        "max_same_label_count":      max_same_label_count,
        "same_label_groups_detail":  "; ".join(f"{l}={c}" for l,c in sorted(same_label_groups.items())),
        "n_endpoint_ambig_edges":    n_endpoint_ambig,
        "endpoint_ambig_edge_descs": "; ".join(set(endpoint_ambig_edges.values())),
        "n_target_nodes":            n_target_total,
        "n_anchor_nodes":            n_anchor_total,
        "n_target_with_bbox":        n_target_with_bbox,
        "target_bbox_rate":          round(target_bbox_rate, 3),
        "n_anchor_with_bbox":        n_anchor_with_bbox,
        "anchor_bbox_rate":          round(anchor_bbox_rate, 3),
        "z_axis_range":              round(z_range, 3),
        "action_verb_dist":          "; ".join(f"{k}={v}" for k,v in sorted(action_counts.items())),
        "top_edge_descs":            "; ".join(
            f"{d}×{c}" for d,c in sorted(edge_desc_counts.items(), key=lambda x:-x[1])[:3]
        ),
        "recommendation_score":      score,
    })
```

### Step 5：排序 & 输出 CSV

按 `recommendation_score` 降序，同分再按 `n_unique_edges` 降序。

### Step 6：打印 stdout 摘要

```
Scene selection summary:
  Total scenes with functional queries: N
  Scenes with score >= 3 (high priority): N
  Scenes with score == 2 (medium priority): N

Top scenes:
  scene_id | score | edges | max_same_label | endpoint_ambig | target_bbox
  ...
```

### Step 7（手动）：根据 CSV 选 scene，写 annotation_notes.md

**选择条件（满足越多越好）：**

```
优先级 1 ⭐⭐⭐：
  recommendation_score == 4（完美 scene）

优先级 2 ⭐⭐：
  n_unique_edges >= 5 AND max_same_label_count >= 3

优先级 3 ⭐：
  n_endpoint_ambig_edges >= 2 OR target_bbox_rate >= 0.8

必须排除：
  n_unique_edges < 2（edge 太少，没东西可写）
  target_bbox_rate == 0（没有 geometry，写不了 geometry_aware tag）
```

**最终选出至少 6 个 scene，覆盖至少 30 条候选 functional edges。**

---

## ==输出文件规格==

### 1. `scene_audit_v1.csv`（脚本生成）

==**每行一个 scene**，列固定顺序：==

```
scene_id
n_functional_queries        # 现有 functional query 数量
n_unique_edges              # scene 中唯一 supporting edges 数量
n_actionable_targets        # actionable label 的 target node 数量
n_same_label_groups         # 同 label ≥ 2 的 label 类型数
max_same_label_count        # 最多同名节点数（反映 distractor 密度）
same_label_groups_detail    # 明细：label=count; ...
n_endpoint_ambig_edges      # endpoint ambiguity 边数量
endpoint_ambig_edge_descs   # 具体边类型（分号分隔）
n_target_nodes              # 唯一 target node 数
n_anchor_nodes              # 唯一 anchor node 数
n_target_with_bbox          # target nodes 中有 bbox 的数量
target_bbox_rate            # target bbox 覆盖率（0~1）
n_anchor_with_bbox          # anchor nodes 中有 bbox 的数量
anchor_bbox_rate            # anchor bbox 覆盖率（0~1）
z_axis_range                # scene 中 bbox_center_z 的最大跨度（用于判断 upper/lower）
action_verb_dist            # action verb 分布（pull=N; rotate=N; press=N）
top_edge_descs              # 出现最多的3种 edge description
recommendation_score        # 推荐分（0~4）
```

### 2. `annotation_notes.md`（手动写）

格式（追加写，按时间顺序）：

```markdown
# Annotation Notes

## Phase 0 — Scene & Edge Selection — YYYY-MM-DD

### Selected Scenes

- scene_id: 420683
  why_selected: 最多 functional edges（8条），有3个同名 knob，handle-drawer endpoint ambiguity 丰富，target bbox 覆盖率 100%
  candidate_edges:
    - "e0047d50-...|rotate to adjust the temperature|8a1b9af6-..."
    - "eb945e52-...|pull to open or close|6564cece-..."
  same_label_candidates:
    - knob: 3 nodes（node_ids: ...）
    - handle: 2 nodes
  endpoint_ambiguity_edges:
    - "pull to open or close": handle→drawer（两端都是 operable object）
  has_geometry:
    - knob nodes: all 3 have bbox ✓
    - handle nodes: 1/2 has bbox

- scene_id: 421013
  ...

### Candidate Edge Pool Summary
  Total candidate edges: N
  By action type:
    pull: N
    rotate: N
    press: N
  By ambiguity type:
    endpoint_ambiguous: N
    same_label_required: N
    geometry_needed: N

### Issues Found (do NOT modify original files)
  [issue] scene_id=... problem=... suggested_fix=...

### Phase 0 Counts
  Selected scenes: N（≥6）
  Candidate edges: N（≥30）
  Ready for Phase 1: YES
```

---

## 脚本实现计划

### 文件位置
```
benchmark_clean_v0/human_annotations/functional_queries_v1/
└── scripts/
    └── phase0_scene_audit.py    ← 唯一新建代码文件
```

### 脚本结构（`phase0_scene_audit.py`）

```python
"""Phase 0: Scene & Edge Selection Audit for Human Annotation Task."""
from __future__ import annotations
import json, csv
from collections import defaultdict
from pathlib import Path

# 脚本位置：
#   benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/phase0_scene_audit.py
# parents[0]=scripts/, parents[1]=functional_queries_v1/,
# parents[2]=human_annotations/, parents[3]=benchmark_clean_v0/
BENCH_ROOT  = Path(__file__).resolve().parents[3]
QUERY_INDEX = BENCH_ROOT / "queries"  / "all_queries_index.jsonl"
GEOM_PATH   = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR     = BENCH_ROOT / "human_annotations" / "functional_queries_v1"

ACTIONABLE_LABELS = {
    "handle / faucet", "handle", "faucet / handle", "faucet / knob / handle",
    "knob / button", "knob", "button / knob", "button",
    "light switch", "switch panel", "switch panel / electric outlet",
    "remote",
    "drawer", "nightstand drawer", "door", "glass door",
    "cabinet / closet",
}

ENDPOINT_AMBIG_EDGE_PATTERNS = [
    "pull to open or close",
    "pull to open or close a drawer",
    "pull or rotate to open or close",
    "control, turn on or turn off",
    "control",
    "control the water flow",
    "rotate to control the water flow",
    "press or rotate to control the water flow",
    "provide power",
]

def load_functional_queries(path: Path) -> list[dict]:
    """Load SceneFun3D functional queries only."""
    ...

def load_geometry(path: Path) -> dict:
    """Load {scene_id: {node_id: {bbox_center, bbox_min, bbox_max}}}."""
    ...

def compute_scene_stats(queries: list[dict], geom: dict) -> list[dict]:
    """Compute per-scene statistics and recommendation scores."""
    ...

def write_scene_audit_csv(rows: list[dict], path: Path) -> None:
    """Write scene_audit_v1.csv with fixed column order."""
    ...

def print_summary(rows: list[dict]) -> None:
    """Print top-N scenes to stdout."""
    ...

def run_sanity_checks(queries: list[dict], rows: list[dict]) -> None:
    """Print [CHECK N] pass/FAIL for each sanity check."""
    ...

def main() -> None:
    queries = load_functional_queries(QUERY_INDEX)
    geom    = load_geometry(GEOM_PATH)
    rows    = compute_scene_stats(queries, geom)
    rows    = sorted(rows, key=lambda r: (-r["recommendation_score"], -r["n_unique_edges"]))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_scene_audit_csv(rows, OUT_DIR / "scene_audit_v1.csv")
    print_summary(rows)
    run_sanity_checks(queries, rows)

if __name__ == "__main__":
    main()
```

**依赖：** 只用标准库（`json`, `csv`, `collections`, `pathlib`）。无需 pandas、torch。

---

## 验证步骤

### 运行脚本

```powershell
# 工作目录不限，脚本内使用绝对路径
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase0_scene_audit.py
```

### 必须通过的 Sanity Checks（run_sanity_checks 函数打印）

```
[CHECK 1]  functional query 总数 == 870                        pass/FAIL
[CHECK 2]  所有 query 的 dataset == "scenefun3d"               pass/FAIL
[CHECK 3]  scene 总数 <= 23（OpenFunGraph annotated scenes）   pass/FAIL
[CHECK 4]  supporting_edge_id 格式均为 3 段（两个"|"）         pass/FAIL（报告异常数量）
[CHECK 5]  所有 scene_id 均为纯数字字符串                      pass/FAIL
[CHECK 6]  recommendation_score 范围 0~4                       pass/FAIL
```

### 人工验收（查看 scene_audit_v1.csv 后）

```
1. 打开 scene_audit_v1.csv，按 recommendation_score 降序查看
2. 选 recommendation_score >= 3 的 scene，目标 >= 6 个
3. 每个选中 scene，从 CSV 的 same_label_groups_detail 和 endpoint_ambig_edge_descs
   里抄出候选 edge 和 distractor，填入 annotation_notes.md
4. 候选 edge 总数 >= 30 → Phase 0 结束，进入 Phase 1
```

### 完成定义

```
□ scene_audit_v1.csv 存在且可被 python csv.reader 正确读取
□ stdout 打印了 top scenes 摘要 + 全部 sanity checks 通过
□ annotation_notes.md 存在，包含 selected_scenes 段落
□ selected_scenes >= 6 个
□ candidate edges >= 30 条
□ annotation_notes.md 包含 Phase 0 progress note
□ 不需要等 Mingqian review（Phase 0 完成直接进 Phase 1）
```

---

## 关键文件清单

| 文件 | 动作 |
|------|------|
| `human_annotations/functional_queries_v1/scripts/phase0_scene_audit.py` | **新建** |
| `human_annotations/functional_queries_v1/scene_audit_v1.csv` | **新建（脚本生成）** |
| `human_annotations/functional_queries_v1/annotation_notes.md` | **新建（手动写）** |

只读引用（不修改）：
- `benchmark_clean_v0/queries/all_queries_index.jsonl`
- `benchmark_clean_v0/geometry/scenefun3d_node_geom.json`

---

## Out of Scope（Phase 0 明确不做）

- 不写任何 query（那是 Phase 1）
- 不修改 frozen 目录（`queries/`, `graphs/`, `geometry/`, `annotations/`）
- 不读 `scenefun3d_funrag_benchmark_enriched.json`（26.8MB，Phase 0 不需要）
- 不读 `SceneFun3D.annotations.json`（50MB，UUID 体系与 query_index 不一致）
- 不计算 node-level geometry feature（那是 geometry 任务的 Phase 2）
- 不做 existing query quality audit（那是 Phase 5）
  - 不生成 validation report（那是 Phase 6）


---

## Phase 0 Progress Note 模板（写入 annotation_notes.md）

```markdown
## Phase 0 progress — YYYY-MM-DD

Did:
- 运行 phase0_scene_audit.py，扫描 870 条 SceneFun3D functional queries
- 生成 scene_audit_v1.csv（N 个 scene，各场景统计）
- 手动选择了 N 个 scenes 写入 annotation_notes.md

Counts:
- 总 scene 数（有 functional query 的）: N
- 已选 scenes: N（≥6）
- 候选 edges: N（≥30）
- recommendation_score >= 3 的 scene: N

Scene selection:
  420683: score=4（8 edges, knob×3, 3 endpoint ambig edges, bbox 100%）
  421013: score=...
  ...

Potential issues:
  （填写 CSV 里发现的异常，或写 N/A）

Files ready:
  - scene_audit_v1.csv
  - annotation_notes.md（本文件）

Next step: Phase 1 pilot 20 queries
```

---

## 附录：全量 Node Label 列表（52种）

```
handle / faucet, washing machine, handle, bathtub, bathroom sink, dryer,
light bulb, window, fridge, light switch, wardrobe, dresser / nightstand,
toilet, trashcan, knob / button, door, laptop, sink, faucet / handle,
television stand / cabinet, cabinet / closet, lamp, remote, radiator,
drawer, glass door, chest of drawers / dresser, kettle,
nightstand / dresser, projector, dresser / chest of drawers, kitchen sink,
power strip, television, kitchen cabinet, faucet / knob / handle, oven,
cabinet / dresser / nightstand, exhaust hood / ventilation fan, switch panel,
knob, dishwasher, doors, nightstand drawer, chandelier / ceiling light,
switch panel / electric outlet, ceiling light fixture, cabinet,
electric outlet, button / knob, ceiling light, button,
electric outlet / power strip, drawer / cabinet
```

---

## 附录：全量 Edge 类型列表（21种，已分类）

**Pull 类（常见 endpoint ambiguity）：**

```
pull to open or close
pull to open or close a drawer
pull or rotate to open or close
```

**Rotate 类：**
```
rotate to adjust the temperature
rotate to adjust the setting
rotate to adjust setting or temperature
rotate to adjust the setting or open or close
rotate to open or close
rotate to control the water flow
rotate to flush
```

**Press / Press-or-rotate 类：**
```
press to open or close, or adjust the setting
press or rotate to open
press or rotate to flush
press or rotate to control the water flow
press or rotate to adjust the setting
rotate or press to adjust the setting
```

**Control 类（常见 endpoint ambiguity）：**
```
control, turn on or turn off
control
control the water flow
```

**其他：**
```
push to flush
provide power
```
