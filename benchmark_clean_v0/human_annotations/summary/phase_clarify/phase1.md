# Phase 1 详细计划：Pilot 20 条人工 Queries

> 这是 `phase.md` 的 Phase 1 展开版。所有新文件写到
> `benchmark_clean_v0/human_annotations/functional_queries_v1/`，frozen 目录绝对不动。

---

## Context

**Phase 0 已完成，Phase 1 是真正的标注起点。**

Phase 0 选出了 6 个 scene，确认了 geometry 覆盖率（全部 1.000）和 same-label distractor
密度。Phase 1 的目标是从这些 scene 的真实 functional edge 里挑出 20 条，写出 20 条高质量
人工 query，验证三件事：

1. **Schema 可用**：`query_id / target_node_id / evidence_chain / difficulty_tags` 等字段能被 validator 通过
2. **Query 风格一致**：不同难度类型的 query 写法有明确参考样例
3. **Validator 可运行**：`validate_functional_queries.py` 脚本能对 20 条 query 全部报 PASS

Phase 1 产出后**必须停下来**，等 Mingqian review，确认方向后再扩展到 80 条。

---

## ⚠ 修订说明（v1.1，针对 Phase 0 审计中发现的三个陷阱）

Phase 0 的 `scene_audit_v1.csv` 有三处统计口径需要在 Phase 1 显式纠正，**否则会写出无效或虚假难度的 query**：

### 修订 1：`unknown` label 不是真实 distractor

Phase 0 的 same-label 统计把 `label == "unknown"` 的节点也算进了 same-label group
（例如 469011 有 15 个 anchor label 为 "unknown"）。这是**统计污染**：

- `unknown` 不是一个真实物体类别，把它们聚成一组毫无意义
- 写 `same_label_disambiguation` query 时，**`unknown` 节点不能算 distractor**
- `num_same_label_distractors` 字段：**只数与 target 同一个"真实 label"的其他节点**，排除 `unknown`

→ Phase 1 的 `phase1_scene_explorer.py` 在构建 same-label group 时**显式跳过 `unknown`**，
  并把 `unknown` 节点单独列出（仅供参考，不计入 distractor）。

### 修订 2：421380 只能写水平几何（z-range 太低）

421380 的 `z_axis_range` 仅 0.802，垂直方向几乎没有区分度。

- 在 421380 里写 `geometry_aware` query：**只能用 left / right / near / far / leftmost / rightmost**
- **禁止** upper / lower / top / bottom / highest / lowest（这些在 421380 不可唯一定位）
- 其余 5 个 scene（z_range ≥ 1.2）才可以写 upper/lower 类垂直几何

### 修订 3：`top_edge_descs` 是 query 频次，不是 unique edge 频次

`scene_audit_v1.csv` 里的 `top_edge_descs` 列（如 `pull to open or closex90`）统计的是
**有多少条已有 query 用到了这种 relation**，不是有多少条不同的 edge。

- 一条 unique edge 可能被 5–10 条 paraphrase query 引用 → 频次虚高
- Phase 1 **必须基于真实的 `supporting_edge_id` 写题**，不能照着 `top_edge_descs` 的数字估算
- 真实可用的 edge 列表来自 **`phase1_scene_explorer.py` 输出的 `scene_graph_summary_v1.txt`**
  （它直接读 scene graph 的 `edges` 数组，每条 edge 只出现一次）

→ 写每条 query 前，**先在 `scene_graph_summary_v1.txt` 里找到那条具体的 edge_id**，
  确认它真实存在，再填 `supporting_edge_ids`。不要凭 CSV 的频次想当然。

### Phase 0 产出回顾（已按修订口径标注）

| scene_id | n_unique_edges | max_same_label（真实 label，排除 unknown） | key labels | z_range | 几何可写方向 |
|----------|----------------|---------------------------------------------|------------|---------|--------------|
| 469011   | 24             | knob×19                                     | knob, handle, outlet | 2.168 | upper/lower + 水平 |
| 421254   | 17             | knob×20 (MAX)                               | knob, remote | 1.222 | upper/lower + 水平 |
| 421380   | 17             | knob×15                                     | knob, remote | **0.802** | **只能水平** |
| 421602   | 12             | handle×11                                   | handle | 2.009 | upper/lower + 水平 |
| 421013   | 10             | handle×9                                    | handle, light switch | 2.170 | upper/lower + 水平 |
| 420683   | 9              | knob×9, handle×2                            | knob, handle | 1.750 | upper/lower + 水平 |

> 注：表中 `max_same_label` 已是排除 `unknown` 后的真实物体类别计数。Phase 0 CSV 里
> `same_label_groups_detail` 含 `unknown=N` 的条目，Phase 1 一律忽略。

关键边类型（来自真实 scene graph，非频次估算）：
- `421013`、`420683` 有 `control, turn on or turn off`（light switch ↔ ceiling light）→ endpoint ambiguity + hard negative
- `469011` 有 `provide power`（outlet ↔ device）和 `control the water flow`（faucet ↔ sink）→ hard negative
- `421254`、`421380` knob 数量最多 → same_label_disambiguation 主场

---

## 输入文件

| 文件路径 | 用途 | 大小参考 |
|----------|------|---------|
| `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` | 完整场景图，含所有 node/edge 的真实 UUID 和 edge 列表 | 26.8 MB |
| `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` | 节点 bbox（center/min/max），用于 geometry_aware 验证 | 小 |
| `benchmark_clean_v0/queries/all_queries_index.jsonl` | 现有查询，用于 query_id 查重 | 中 |

**只读，绝对不修改。**

---

## Phase 1 构成（20 条 query 分配表）

| 类型 | 数量 | 推荐 scene | difficulty_tags |
|------|------|------------|-----------------|
| Local functional — simple | 4 | 420683, 421013 | `simple_functional` |
| Local functional — functional_relation | 6 | 469011, 421602, 421380 | `functional_relation`, `endpoint_ambiguity` |
| Same-label hard | 3 | 421254, 421380 | `same_label_disambiguation`, `functional_relation` |
| Endpoint ambiguity hard | 2 | 421013, 420683 | `endpoint_ambiguity`, `functional_relation` |
| Geometry-aware | 3 | 421013（垂直）, 421602（垂直）, 421380（水平） | `geometry_aware`, `same_label_disambiguation` |
| Hard negative | 2 | 421013, 469011 | `hard_negative`, `functional_relation` |
| **合计** | **20** | — | — |

**Scene 分配建议：**
- `469011`（kitchen，diverse）：3–4 条（pull / rotate / provide_power / water_flow）
- `421254`（dresser heavy，knob×20）：3 条（same_label_disambiguation 主场）
- `421380`（TV stand heavy，**低 z**）：2 条（**只能水平 geometry**）
- `421602`（handle heavy）：4 条（geometry_aware upper/lower handle）
- `421013`（light switch）：4 条（control edge + geometry_aware 垂直）
- `420683`（mixed knob+handle）：4 条（rotary + control + geometry）

> ⚠ geometry-aware 的 3 条里，建议 2 条垂直（421013 / 421602）+ 1 条水平（421380），
> 确保 pilot 同时覆盖两种几何方向，验证 schema 对两类都能跑通。

---

## Step 0：读取场景图（phase1_scene_explorer.py）

写 query 之前**必须先运行 explorer 脚本**，因为：
1. node_id 是 UUID，不能手写，只能从 scene graph 里抄
2. edge_id 格式为 `source_node_id|relation|target_node_id`，必须完整正确，**且必须是真实存在的 edge**（修订 3）
3. bbox_center z 值用于判断 upper/lower（z 大 = 更高），x/y 用于 left/right/near/far
4. same-label group 必须**排除 `unknown`**（修订 1），脚本里直接处理

### 脚本位置

```
benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/phase1_scene_explorer.py
```

### 脚本完整代码

```python
"""Phase 1: Scene Graph Explorer for Human Annotation.

读取 scenefun3d_funrag_benchmark_enriched.json，对 6 个选中 scene 输出：
  - 所有节点（node_id, label, bbox_center）
  - 所有功能边（edge_id, source_label, relation, target_label）—— 直接读 scene graph
    的 edges 数组，每条 unique edge 只出现一次（不是 query 频次）
  - 同名节点分组（用于 same_label_disambiguation）—— 显式排除 label == "unknown"
  - "unknown" 节点单独列出，仅供参考，不计入 distractor

输出到 stdout 和 scene_graph_summary_v1.txt。
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
from pathlib import Path

BENCH_ROOT  = Path(__file__).resolve().parents[3]
ENRICH_PATH = BENCH_ROOT / "queries" / "scenefun3d_funrag_benchmark_enriched.json"
GEOM_PATH   = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR     = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
OUT_TXT     = OUT_DIR / "scene_graph_summary_v1.txt"

SELECTED_SCENES = ["469011", "421254", "421380", "421602", "421013", "420683"]

# 修订 1：unknown / 空 label 不是真实物体类别，不能算 same-label distractor
NON_REAL_LABELS = {"unknown", "", None}

# 修订 2：z_axis_range 低于此阈值的 scene 不适合写 upper/lower 垂直几何 query
LOW_Z_RANGE_SCENES = {"421380"}  # z_range = 0.802


def load_scene_graphs(path: Path) -> dict[str, dict]:
    """返回 {scene_id: scene_graph_dict}，只含 6 个选中 scene。"""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    scene_graphs: dict[str, dict] = {}
    for item in data["data"]:
        sid = item["scene_id"]
        if sid in SELECTED_SCENES and sid not in scene_graphs:
            if item.get("scene_graph"):
                scene_graphs[sid] = item["scene_graph"]
    return scene_graphs


def load_geometry(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def summarize_scene(scene_id: str, sg: dict, geom: dict) -> list[str]:
    lines: list[str] = []
    nodes = sg.get("nodes", [])
    edges = sg.get("edges", [])
    scene_geom = geom.get(scene_id, {})

    geom_note = ("ONLY horizontal geometry (left/right/near/far) — z_range too low"
                 if scene_id in LOW_Z_RANGE_SCENES
                 else "vertical (upper/lower) + horizontal geometry OK")

    lines.append(f"{'='*78}")
    lines.append(f"SCENE {scene_id}  ({len(nodes)} nodes, {len(edges)} edges)")
    lines.append(f"  geometry: {geom_note}")
    lines.append(f"{'='*78}")

    # ---- 节点表 ----
    lines.append("")
    lines.append("NODES:")
    lines.append(f"  {'node_id':38s}  {'label':35s}  {'bbox_center_z':>14}  {'bbox_center_x':>14}  {'bbox_center_y':>14}")
    lines.append(f"  {'-'*38}  {'-'*35}  {'-'*14}  {'-'*14}  {'-'*14}")
    for n in sorted(nodes, key=lambda x: str(x.get("label"))):
        nid = n["node_id"]
        g = scene_geom.get(nid, {})
        cx, cy, cz = g.get("bbox_center", [None, None, None])
        z_str = f"{cz:14.3f}" if cz is not None else f"{'NO_GEOM':>14}"
        x_str = f"{cx:14.3f}" if cx is not None else f"{'':>14}"
        y_str = f"{cy:14.3f}" if cy is not None else f"{'':>14}"
        lines.append(f"  {nid:38s}  {str(n.get('label')):35s}  {z_str}  {x_str}  {y_str}")

    # ---- 同名节点分组（修订 1：排除 unknown）----
    label_to_nodes: dict[str, list] = defaultdict(list)
    unknown_nodes: list[str] = []
    for n in nodes:
        lbl = n.get("label")
        if lbl in NON_REAL_LABELS:
            unknown_nodes.append(n["node_id"])
            continue
        label_to_nodes[lbl].append(n["node_id"])
    same_label = {lbl: nids for lbl, nids in label_to_nodes.items() if len(nids) >= 2}
    if same_label:
        lines.append("")
        lines.append("SAME-LABEL GROUPS (real distractor candidates — 'unknown' EXCLUDED):")
        for lbl, nids in sorted(same_label.items(), key=lambda x: -len(x[1])):
            lines.append(f"  [{lbl}]  count={len(nids)}")
            for nid in nids:
                g = scene_geom.get(nid, {})
                cx, cy, cz = g.get("bbox_center", [None, None, None])
                z_str = f"z={cz:.3f}" if cz is not None else "z=NO_GEOM"
                x_str = f"x={cx:.3f}" if cx is not None else ""
                lines.append(f"    {nid}  {z_str}  {x_str}")
    if unknown_nodes:
        lines.append("")
        lines.append(f"UNKNOWN-LABEL NODES ({len(unknown_nodes)}) — NOT distractors, for reference only:")
        for nid in unknown_nodes:
            lines.append(f"    {nid}")

    # ---- 边表（修订 3：直接读 scene graph edges，每条 unique edge 只出现一次）----
    lines.append("")
    lines.append(f"EDGES ({len(edges)} unique edges — this is the authoritative edge list):")
    lines.append(f"  {'source_label':35s}  {'relation':45s}  {'target_label':35s}")
    lines.append(f"  {'-'*35}  {'-'*45}  {'-'*35}")
    for e in sorted(edges, key=lambda x: str(x.get("relation"))):
        lines.append(
            f"  {str(e.get('source_label')):35s}  {str(e.get('relation')):45s}  {str(e.get('target_label')):35s}"
        )
        lines.append(f"    edge_id: {e['edge_id']}")
    lines.append("")
    return lines


def main() -> int:
    print(f"Loading scene graphs from: {ENRICH_PATH}")
    scene_graphs = load_scene_graphs(ENRICH_PATH)
    print(f"  Loaded {len(scene_graphs)} scene graphs")
    if len(scene_graphs) < len(SELECTED_SCENES):
        missing = [s for s in SELECTED_SCENES if s not in scene_graphs]
        print(f"  WARNING: missing scenes: {missing}")

    print(f"Loading geometry from: {GEOM_PATH}")
    geom = load_geometry(GEOM_PATH)

    all_lines: list[str] = []
    for sid in SELECTED_SCENES:
        if sid not in scene_graphs:
            all_lines.append(f"WARNING: scene {sid} not found in enriched JSON")
            continue
        all_lines.extend(summarize_scene(sid, scene_graphs[sid], geom))

    output = "\n".join(all_lines)
    print(output)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(output, encoding="utf-8")
    print(f"\nWrote summary to: {OUT_TXT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**依赖：** 只用标准库（`json`, `pathlib`, `collections`, `sys`）。无 pip 依赖。

### 运行命令

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase1_scene_explorer.py
```

### 输出文件

```
benchmark_clean_v0/human_annotations/functional_queries_v1/scene_graph_summary_v1.txt
```

输出格式示例片段（scene 420683）：

```
==============================================================================
SCENE 420683  (21 nodes, 12 edges)
  geometry: vertical (upper/lower) + horizontal geometry OK
==============================================================================

NODES:
  node_id                                 label                            bbox_center_z   bbox_center_x
  ------                                  -----                            -------------   -------------
  e0047d50-015b-40d0-8910-f0c4b1fb5b7a    knob                                381.827          -0.487
  8a1b9af6-dc57-4766-98cb-f10cb6266656    radiator                            382.002          -0.240

SAME-LABEL GROUPS (real distractor candidates — 'unknown' EXCLUDED):
  [knob]  count=9
    e0047d50-015b-40d0-8910-f0c4b1fb5b7a  z=381.827  x=-0.487
    8dec8ba5-ee16-44b1-a131-611ee615bba7  z=382.121  x=0.457
    ...

UNKNOWN-LABEL NODES (7) — NOT distractors, for reference only:
    6eabdfdc-d41c-4511-a841-08b177fd3d4b
    ...

EDGES (12 unique edges — this is the authoritative edge list):
  knob                                 rotate to adjust the temperature        radiator
    edge_id: e0047d50-...|rotate to adjust the temperature|8a1b9af6-...
  ...
```

运行脚本后，**打开 `scene_graph_summary_v1.txt`，用它作为写 query 时的唯一查找手册**。
所有 `node_id` / `edge_id` 都从这里抄，不要凭 `scene_audit_v1.csv` 的频次估算（修订 3）。

---

## Step 1：理解 Query 构成要素

每条 query 都从一条 **真实存在的 functional edge** 出发。edge 方向：

```
scene graph edge:
  source_node_id | relation | target_node_id
       ↑                          ↑
   用户操作的对象               被影响的对象
 （query 里的 target_node_id） （query 里的 anchor_node_id）
```

> ⚠ 注意方向反转：scene graph 的 `source` = query 的 `target`；scene graph 的 `target` = query 的 `anchor`。
> 这是最容易填错的字段，validator 会专项检查（C7/C8）。

### Evidence chain 格式

```
source_label --relation--> target_label
```

单跳示例：
```
knob --rotate to adjust the temperature--> radiator
```

多 anchor 示例（`multi_anchor` tag）：
```
handle --pull to open or close a drawer--> chest of drawers / dresser  [anchor: dresser near window]
```

---

## Step 2：各类型 Query 写法详解

**通用流程：** 从 `scene_graph_summary_v1.txt` 找到目标 edge（真实 edge_id）→ 确认 UUID
→ 填写所有字段 → 做 3 问质量自检。

**数 distractor 的统一规则（修订 1）：** `num_same_label_distractors` =
`scene_graph_summary_v1.txt` 里同 `target_label` 分组的节点数 − 1，
**且该分组里不含任何 `unknown` 节点**（脚本已自动排除）。

---

### 2.1 Simple Functional（4条）

**选边原则：** 选 scene 里 anchor 唯一或非常具体的真实 edge，query 不需要几何定位。

**推荐来源（edge_id 必须从 scene_graph_summary_v1.txt 核实）：**
- `420683`：knob → radiator（`rotate to adjust the temperature`，scene 里只有 1 个 radiator）
- `421013`：handle → door（`pull to open or close`，scene 里 1 个 door）
- `421602`：handle → dresser（`rotate to open or close`）
- `421013`：handle → dresser/nightstand（`pull to open or close a drawer`，anchor 唯一）

**写法模板：**
```
[动作动词] the [target_label] to [功能描述]
```

**示例 query（scene 420683，UUID 已验证）：**

```json
{
  "query_id": "human_func_v1_000001",
  "scene_id": "420683",
  "query_text": "Turn the radiator knob to control the room temperature",
  "query_type": "functional",
  "target_node_id": "e0047d50-015b-40d0-8910-f0c4b1fb5b7a",
  "anchor_node_id": "8a1b9af6-dc57-4766-98cb-f10cb6266656",
  "supporting_edge_ids": [
    "e0047d50-015b-40d0-8910-f0c4b1fb5b7a|rotate to adjust the temperature|8a1b9af6-dc57-4766-98cb-f10cb6266656"
  ],
  "difficulty_tags": ["simple_functional"],
  "is_long_range": false,
  "evidence_chain": ["knob --rotate to adjust the temperature--> radiator"],
  "source": "human",
  "target_label": "knob",
  "anchor_label": "radiator",
  "num_same_label_distractors": 8,
  "is_label_only_solvable": true,
  "notes": "scene 420683 has 9 real-label knobs but only 1 radiator; anchor uniquely identifies target despite same-label. distractor count excludes unknown-label nodes."
}
```

> 注：`num_same_label_distractors=8` 来自 `scene_graph_summary_v1.txt` 的 `[knob] count=9`
> 分组（已排除 unknown），9 − 1 = 8。

---

### 2.2 Functional Relation（6条）

**选边原则：** 选 `control`、`provide power`、`control the water flow`、`pull to open or close a drawer`
等明确功能关系的真实 edge。query 里必须出现功能词汇（"controls"、"powers"、"adjusts"、"opens"），
**不能只靠 spatial 或 label 解决**。

**推荐来源（edge_id 从 txt 核实）：**
- `469011`：faucet/handle → kitchen sink（`control the water flow`）
- `469011`：electric outlet → fridge（`provide power`）
- `469011`：knob → oven（`rotate to adjust the setting`，场景里 19 个真实 knob，必须用 anchor 定位）
- `421254`：remote → television（`control`，2 个 remote，用 anchor 区分）
- `421380`：knob → radiator（`rotate to adjust the temperature`）
- `421602`：handle → dresser（`pull to open or close a drawer`）

**示例 query（scene 469011，faucet/handle → kitchen sink，UUID 需从 txt 核实）：**

```json
{
  "query_id": "human_func_v1_000005",
  "scene_id": "469011",
  "query_text": "Locate the faucet handle that controls the water flow to the kitchen sink",
  "query_type": "functional",
  "target_node_id": "<从 scene_graph_summary_v1.txt 查 faucet/handle→kitchen sink 的 source_node_id>",
  "anchor_node_id": "<对应 target_node_id（kitchen sink）>",
  "supporting_edge_ids": ["<完整 edge_id，从 txt 核实>"],
  "difficulty_tags": ["functional_relation", "endpoint_ambiguity"],
  "is_long_range": false,
  "evidence_chain": ["faucet / handle --control the water flow--> kitchen sink"],
  "source": "human",
  "target_label": "faucet / handle",
  "anchor_label": "kitchen sink",
  "expected_failure_modes": ["choose_anchor_instead_of_target"],
  "num_same_label_distractors": 0,
  "is_label_only_solvable": false,
  "notes": "endpoint_ambiguity: sink could also be mistaken as answer. Functional relation 'control the water flow' is key discriminator."
}
```

---

### 2.3 Same-Label Hard（3条）

**选边原则：** 必须选**真实 label**（非 unknown）同名节点数 ≥ 9 的 scene，anchor 在 scene 里唯一或可区分。
query **不含几何方位词**（那是 geometry_aware），只靠 anchor 的唯一性或功能关系定位。

**推荐来源（edge_id 从 txt 核实）：**
- `421254`：remote → television（2 个真实 remote，只有 1 台 television → anchor 唯一）
- `421254`：knob → drawer（20 个真实 knob，anchor 有多个 dresser → 用 anchor 描述区分）
- `421380`：remote → television（2 个真实 remote，1 台 television，`control` 边）

**写法规则：** query 里必须提到足够区分 anchor 的信息，但不能用空间方位词。
`num_same_label_distractors` 必须 ≥ 2，且这个数**只数真实同 label 节点，不含 unknown**（修订 1）。

---

### 2.4 Endpoint Ambiguity Hard（2条）

**选边原则：** 选 `control, turn on or turn off`（switch ↔ lamp）或 `pull to open or close`（handle ↔ drawer），
两端都是"可操作对象"，模型很可能选 anchor 而非 target。

**推荐来源（edge_id 从 txt 核实）：**
- `421013`：light switch → ceiling light（`control, turn on or turn off`）
- `420683`：switch panel → ceiling light（`control, turn on or turn off`）

**写法规则：** query 里用功能动词（"turn on"、"control"、"switch"）明确 target 是"控制源"（source 端），
不是被控制的 lamp/light。

---

### 2.5 Geometry-Aware（3条）

**选边原则：** 选**真实 label** 同名节点多的 scene，且 target node 的 z 或 x 坐标明显区别于 distractor。

**几何方向规则（修订 2）：**

| scene | z_range | 可用几何方向 |
|-------|---------|--------------|
| 421013 | 2.170 | upper / lower / top / bottom + 水平 |
| 421602 | 2.009 | upper / lower / top / bottom + 水平 |
| 469011 | 2.168 | upper / lower / top / bottom + 水平 |
| 420683 | 1.750 | upper / lower / top / bottom + 水平 |
| 421254 | 1.222 | upper / lower（谨慎）+ 水平 |
| **421380** | **0.802** | **只能 left / right / near / far / leftmost / rightmost** |

**推荐 3 条分配（覆盖两种几何方向）：**
- `421013`（垂直）：handle → wardrobe，选 z 值最低的 handle → `lowest handle`
- `421602`（垂直）：handle → dresser，选 z 值最低的 handle → `bottom drawer handle`
- `421380`（**水平**）：knob → 某 anchor，选 x 值最左/最右的 knob → `leftmost knob` / `the knob on the right`

**z / x 值对应关系（Scene 坐标系）：**
- z 值越大 = 物理高度越高（upper/top）；z 值越小 = 越低（lower/bottom）
- x/y 区分 left/right/near/far —— 必须结合 `scene_graph_summary_v1.txt` 里同组节点的实际 x 值确认方向

**写法约束：** 写 geometry query 前，先在 txt 里看同 label 分组的 z（或 x）值，
**确认 target 的坐标在该组里是明确的极值（最高/最低/最左/最右），不是居中**，否则无法唯一定位。

**`geometry_cues` 字段**：geometry_aware tag 的 query 必填；例：`["lower"]`、`["leftmost"]`。
**421380 的 query 的 `geometry_cues` 不允许出现 upper/lower/top/bottom。**

---

### 2.6 Hard Negative（2条）

**选边原则：** 选 `control, turn on or turn off` 或 `provide power` 这类真实 edge，但 query
**表述成看起来是 semantic 或 spatial 的问题**，正确答案必须依赖 functional edge，
不能靠 label prior 或空间邻近解决。

**推荐来源（edge_id 从 txt 核实）：**
- `421013`：light switch → ceiling light，写成 "I need to adjust the lighting — what should I interact with?"
- `469011`：electric outlet → fridge，写成 "Which wall socket keeps the refrigerator running?"

**写法规则：** query **不能**直接说 "control"、"power"、"switch on"；必须用间接描述，
让 label shortcut 和 spatial 策略都失效。

---

## Step 3：query_id 命名规范

格式：`human_func_v1_NNNNNN`（6 位零填充）

Pilot 20 条用 `000001` → `000020`，按写作顺序分配。

```python
def make_query_id(n: int) -> str:
    return f"human_func_v1_{n:06d}"
```

---

## ==Step 4：全字段填写 Checklist==

```
必须字段（缺一条 validator 就 FAIL）：
  □ query_id           格式 human_func_v1_NNNNNN，文件内唯一
  □ scene_id           6 个选定 scene 之一
  □ query_text         英语，1–2 句，不超过 60 词
  □ query_type         固定 "functional"
  □ target_node_id     从 scene_graph_summary_v1.txt 抄的真实 UUID
  □ anchor_node_id     同上（无 anchor 则 null，但 functional query 通常有）
  □ supporting_edge_ids  列表，≥1 条；格式 "target_node_id|relation_text|anchor_node_id"
                         （对应 scene graph 的 source|relation|target，必须是 txt 里真实存在的 edge）
  □ difficulty_tags    列表，从固定 tag set 选；pilot 禁用 "long_range"
  □ is_long_range      false（pilot 全填 false）
  □ evidence_chain     列表，≥1 条；格式 "source_label --relation--> target_label"
  □ source             固定 "human"
  □ notes              ≥1 句描述难点或注意事项

推荐字段（帮助 validator 做更多检查）：
  □ target_label            从 txt 抄
  □ anchor_label            从 txt 抄
  □ expected_failure_modes  ≥1 条（见候选值列表）
  □ num_same_label_distractors  整数 —— 真实同 label 节点数 − 1，排除 unknown（修订 1）
  □ is_label_only_solvable  bool
  □ geometry_cues           geometry_aware tag 的 query 必填；421380 禁用垂直方向词（修订 2）
```

**expected_failure_modes 候选值：**
```
choose_anchor_instead_of_target      # 选了 anchor 而非 target（endpoint ambiguity）
same_label_wrong_instance            # 选了同名但错误的 node
choose_upper_handle / choose_lower_handle   # geometry 方向错误
choose_wrong_outlet_by_proximity     # 靠空间邻近选了错误的 outlet
label_only_shortcut                  # 靠 label 猜对但没用 functional edge
ignore_functional_relation           # 忽略功能边直接选 semantic match
```

---

## Step 5：3 问质量自检（每条 query 必做）

```
Q1. 为什么答案是 TARGET 而不是其他同名 node？
    → anchor + functional relation 能唯一定位 target 吗？
    → 同名 node 的计数只数真实 label，不含 unknown（修订 1）
    → 如果 is_label_only_solvable=true，为什么这条 query 仍然值得写？

Q2. 哪条 supporting edge 支撑这个答案？
    → 从 scene_graph_summary_v1.txt 确认这条 edge_id 真实存在（修订 3）
    → edge 的 source = target_node_id，edge 的 target = anchor_node_id（方向对了吗？）

Q3. 这条 query 难在哪里？不能被 label-only shortcut 解决吗？
    → 如果 is_label_only_solvable=false，至少列 1 个 expected_failure_mode
    → geometry query：用的方向词在该 scene 真的可区分吗？（421380 不能用 upper/lower，修订 2）
```

如果有任何一个问不清楚，**不要收进 pilot_20_queries.jsonl**，先扔到 annotation_notes.md 草稿区。

---

## Step 6：Validator 脚本（Phase 6，与 Phase 1 并行写）

### 脚本位置

```
benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/validate_functional_queries.py
```

### 用法

```powershell
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\pilot_20_queries.jsonl
```

### 13 项必检规则（C13 为修订 2 新增）

| # | 检查项 | 级别 | 说明 |
|---|--------|------|------|
| C1 | `query_id` 格式匹配 `human_func_v1_\d{6}` | ERROR | 格式错误 |
| C2 | `query_id` 在当前文件内唯一 | ERROR | 重复 ID |
| C3 | `scene_id` 存在于 enriched JSON | ERROR | 无效 scene |
| C4 | `target_node_id` 存在于该 scene 的 nodes | ERROR | 无效 node |
| C5 | `anchor_node_id` 存在于该 scene 的 nodes（若非 null） | ERROR | 无效 anchor |
| C6 | 每条 `supporting_edge_ids` 存在于该 scene 的 edges | ERROR | 无效 edge（修订 3：必须真实存在） |
| C7 | supporting edge 的 source = `target_node_id` | ERROR | target/anchor 方向反了 |
| C8 | supporting edge 的 target = `anchor_node_id` | ERROR | anchor 不匹配 |
| C9 | `difficulty_tags` 每项在 `VALID_TAGS` 内 | ERROR | 非法 tag |
| C10 | 若含 `same_label_disambiguation`：scene 内**真实 label**（排除 unknown）同名 node ≥ 2 | WARN | tag 与事实不符（修订 1） |
| C11 | 若含 `geometry_aware`：`target_node_id` 在 geometry JSON 中有 bbox | WARN | 缺 bbox |
| C12 | 若含 `long_range`：文件名必须是 `long_range_stress_queries_v1.jsonl` | ERROR | long_range 不能放 pilot |
| **C13** | 若 `scene_id == "421380"` 且含 `geometry_aware`：`geometry_cues` 不得含 upper/lower/top/bottom/highest/lowest | WARN | 修订 2：低 z-range scene 禁用垂直几何 |

> C10 实现要点：validator 统计 scene 内同 label 节点时，**必须先过滤掉 `label in {"unknown", "", null}` 的节点**，
> 再判断 target_label 的同名计数是否 ≥ 2。`num_same_label_distractors` 字段也按此口径核对。

### validation_report.md 格式

```markdown
## Validation Report — YYYY-MM-DD HH:MM

Input file: pilot_20_queries.jsonl
Total queries checked: 20

Results:
  PASS (no errors): N
  FAIL (>=1 error): N
  WARN only:        N

Errors by type:
  invalid_node_id:    N
  invalid_edge_id:    N
  direction_mismatch: N
  invalid_tag:        N

Warnings by type:
  same_label_tag_without_real_distractor: N
  geometry_tag_without_bbox:              N
  vertical_geometry_in_low_z_scene:       N

Needs human review:
  - human_func_v1_000005: [reason]

Hard-slice counts (pilot):
  simple_functional:         N
  functional_relation:       N
  same_label_disambiguation: N
  endpoint_ambiguity:        N
  geometry_aware:            N
  hard_negative:             N
```

---

## Step 7：输出文件规格

### 7.1 `pilot_20_queries.jsonl`

路径：`benchmark_clean_v0/human_annotations/functional_queries_v1/pilot_20_queries.jsonl`

- 每行一条 JSON（无空行）
- 行顺序按 `human_func_v1_000001` → `000020` 排列
- 文件编码 UTF-8（无 BOM）

快速验证命令：

```powershell
python -c "
import json
from pathlib import Path
p = Path('benchmark_clean_v0/human_annotations/functional_queries_v1/pilot_20_queries.jsonl')
lines = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
ids = [q['query_id'] for q in lines]
print(f'Loaded {len(lines)} queries, dup IDs: {len(ids)-len(set(ids))}')
"
```

### 7.2 `annotation_notes.md`（末尾追加）

```markdown
## Phase 1 progress — YYYY-MM-DD

Did:
- 运行 phase1_scene_explorer.py，生成 scene_graph_summary_v1.txt
  （same-label group 已排除 unknown；edge 列表来自真实 scene graph）
- 写了 scripts/validate_functional_queries.py（13 项检查）
- 写了 20 条 pilot queries，分布：
    simple_functional=4, functional_relation=6,
    same_label_disambiguation=3, endpoint_ambiguity=2,
    geometry_aware=3, hard_negative=2

Counts:
- pilot_20_queries.jsonl: 20 条
- scenes covered: 6（全部）
- validator 通过率: N/20（0 ERROR，N WARN）

Scene breakdown:
- 469011: N 条  421254: N 条  421380: N 条
- 421602: N 条  421013: N 条  420683: N 条

修订口径执行情况:
- distractor 计数已排除 unknown label（修订 1）
- 421380 的 geometry query 只用水平方向词（修订 2）
- 所有 supporting_edge_id 已对照 scene_graph_summary_v1.txt 核实存在（修订 3）

Potential issues:
  [issue] ...

Files ready for review:
- pilot_20_queries.jsonl
- scripts/validate_functional_queries.py
- scripts/phase1_scene_explorer.py
- scene_graph_summary_v1.txt
- validation_report.md
```

---

## 全流程 Sanity Checks（提交前全部打勾）

```
□ scene_graph_summary_v1.txt 存在，包含全部 6 个 scene，same-label group 已排除 unknown
□ pilot_20_queries.jsonl 存在，正好 20 行，每行合法 JSON
□ 20 条 query 的 query_id 互不重复
□ query_id 均不与 all_queries_index.jsonl 里已有 ID 冲突（见查重命令）
□ 每条 supporting_edge_id 都能在 scene_graph_summary_v1.txt 的 EDGES 段找到（修订 3）
□ validator 运行时 0 条 ERROR（WARN 允许，需在 notes 解释）
□ 20 条 query 覆盖全部 6 个 scene（每个 scene >= 2 条）
□ difficulty_tag 分布符合计划：simple<=4，hard_negative=2，geometry_aware=3
□ geometry_aware 的 3 条覆盖垂直 + 水平两种方向；421380 那条不含 upper/lower（修订 2）
□ num_same_label_distractors 均按"真实 label、排除 unknown"口径填写（修订 1）
□ 没有任何 long_range tag；is_long_range 全部为 false
□ annotation_notes.md 末尾有 Phase 1 progress 段落
□ validation_report.md 存在，hard-slice 计数正确
□ scripts/phase1_scene_explorer.py 和 validate_functional_queries.py 均存在
□ 冻结目录（queries/graphs/geometry/annotations/）未被修改
```

**查重命令：**

```powershell
python -c "
import json
from pathlib import Path
existing = {json.loads(l)['query_id']
            for l in Path('benchmark_clean_v0/queries/all_queries_index.jsonl')
                .read_text(encoding='utf-8').splitlines() if l.strip()}
pilot = [json.loads(l)['query_id']
         for l in Path('benchmark_clean_v0/human_annotations/functional_queries_v1/pilot_20_queries.jsonl')
             .read_text(encoding='utf-8').splitlines() if l.strip()]
conflicts = [p for p in pilot if p in existing]
print(f'Pilot: {len(pilot)}, ID conflicts: {len(conflicts)}')
"
```

---

## Escalation Gate（硬性停止点）

```
================================================================================
  STOP HERE
  Phase 1 完成后必须等 Mingqian 审核，绝对不能直接进 Phase 2
================================================================================
```

**向 Mingqian 汇报模板：**

```
Phase 1 pilot 已完成，请审核：

文件：
  functional_queries_v1/pilot_20_queries.jsonl
  functional_queries_v1/validation_report.md
  functional_queries_v1/annotation_notes.md

概要：
  - 20 条 pilot query，覆盖 6 个 scene
  - difficulty tag 分布：[填实际数字]
  - validator 通过率：N/20 PASS，0 ERROR，N WARN
  - 三处修订已执行：unknown 不计 distractor / 421380 只写水平几何 / edge 基于真实 supporting_edge_id
  - 发现 issue：[列出，或"无"]

等 review 通过后再开始 Phase 2（扩展到 80 条）。
```

---

## 关键文件清单

**Phase 1 新建文件：**

| 文件 | 动作 | 说明 |
|------|------|------|
| `scripts/phase1_scene_explorer.py` | 新建 | 读取 scene graph，生成 UUID 查找手册（排除 unknown，真实 edge 列表） |
| `scene_graph_summary_v1.txt` | 新建（脚本生成） | 标注时查找 node_id / edge_id 的唯一权威来源 |
| `pilot_20_queries.jsonl` | 新建（手动写） | 20 条 pilot queries |
| `scripts/validate_functional_queries.py` | 新建 | 13 项一致性检查 |
| `validation_report.md` | 新建（脚本生成） | validator 报告 |
| `annotation_notes.md` | **追加写**（已存在） | 追加 Phase 1 progress 段落 |

**只读引用（绝对不修改）：**

| 文件 | 用途 |
|------|------|
| `benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json` | 获取 node/edge 真实 UUID 和 edge 列表 |
| `benchmark_clean_v0/geometry/scenefun3d_node_geom.json` | 验证 geometry_aware tag |
| `benchmark_clean_v0/queries/all_queries_index.jsonl` | query_id 查重 |

---

## 完成定义

```
□ pilot_20_queries.jsonl 存在，20 条，全部 validator PASS（0 ERROR）
□ scene_graph_summary_v1.txt 存在，覆盖 6 个 scene
□ validate_functional_queries.py 存在，独立运行（无 pip 依赖），含 13 项检查
□ validation_report.md 存在，hard-slice 计数正确
□ annotation_notes.md 追加了 Phase 1 progress 段落，记录三处修订的执行情况
□ 冻结目录未被修改（git diff 确认）
□ ==等 Mingqian review 通过后，才可以进入 Phase 2==
```

---

## Out of Scope（Phase 1 明确不做）

- 不写 long-range query（Phase 4）
- 不写 minimal pairs（Phase 3）
- 不做现有 query 质量审计（Phase 5）
- 不扩展到 80 条（Phase 2，需 review gate 通过后）
- 不修改任何 frozen 文件
- 不生成 `functional_queries_v1.jsonl`、`hard_slice_summary_v1.json`（Phase 2/7）
