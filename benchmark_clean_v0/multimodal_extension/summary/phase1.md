## 产出

```
benchmark_clean_v0/multimodal_extension/
├── scripts/
│   └── phase1_coverage_audit.py        # 412 行
├── geometry_coverage_report.csv        # 1485 行 query 明细 (369 KB)
├── target_anchor_geometry_coverage.csv # split×query_type 汇总表 (16 行)
└── coverage_summary.json               # gate-check + 高层 summary (4.7 KB)
```

## 核心数据

| 指标                           | functional           | spatial          | semantic         |
| ------------------------------ | -------------------- | ---------------- | ---------------- |
| **target coverage**            | 1.0000 (870/870)     | 1.0000 (405/405) | 1.0000 (210/210) |
| **anchor coverage**            | 1.0000 (870/870)     | 1.0000 (405/405) | n/a              |
| **support edge coverage**      | 1.0000 (870/870)     | n/a              | n/a              |
| **same-label distractor rate** | **0.8448** (735/870) | 0.0000           | 1.0000           |

**Gate**：`ready_for_phase_2 = true`（target=1.0 ≥ 0.70；edge=1.0 ≥ 0.65）

## 几个值得告诉学长的发现

1. **覆盖率全是 100%** — benchmark 在冻结时已经过滤过，只保留有 geometry 的 query。Phase 2 的 feature bank 不会有 NaN。
2. **84.5% 的 functional query 在场景里有同名干扰物**（中位数 3 个，最多 19 个），test functional 这一块 distractor 比例 84.3%，median 3，max 19。这正好说明 geometry 对 disambiguation 有价值。
3. **20 个 geometry scenes 都到位**：`{420683, 421013, 421015, 421063, 421254, 421267, 421380, 421602, 422007, 422391, 422813, 422826, 460417, 460419, 466183, 466192, 466803, 467293, 468076, 469011}`，没有 query 引用了不在 geom 里的 scene。
4. **总数对得上** `manifests/benchmark_summary.json`（1485 / 870 / 405 / 210），按 split 拆也对（456/111/918）。
5. 一个小坑：`scenefun3d_funrag_benchmark_enriched.json` 的顶层结构是 `{"metadata":..., "data":[...]}`，不是直接的 list；脚本里 `_iter_enriched_items` 已经正确处理。

## ==Output File Specifications==

### 1. `geometry_coverage_report.csv`

**每行一条 SceneFun3D query**。列顺序固定：

```
query_id, scene_id, split, query_type, dataset,
target_node_ids,                # join "|"
target_labels,                  # join "|"
anchor_node_id,                 # 空字符串表示 null
supporting_edge_id,             # 空字符串表示 null
target_count,                   # len(target_node_ids)
target_has_bbox,                # bool, all targets covered
target_any_has_bbox,            # bool
anchor_applicable,              # bool: anchor_node_id is not null
anchor_has_bbox,                # bool, anchor_applicable=false 时填 false
supporting_edge_applicable,     # bool
supporting_edge_src_has_bbox,   # bool
supporting_edge_tgt_has_bbox,   # bool
supporting_edge_both_have_bbox, # bool
target_and_anchor_both_covered, # bool
same_label_count,               # int
has_same_label_distractor,      # bool
same_label_with_bbox_count,     # int
missing_reason                  # str: "missing_target,missing_edge_tgt" 拼接，全覆盖填 "none"
```

**缺失原因编码**：

- `missing_target`        — 任何 target 缺 bbox
- `missing_anchor`        — anchor 适用且缺 bbox
- `missing_edge_src`      — supporting edge 适用且 src 缺 bbox
- `missing_edge_tgt`      — supporting edge 适用且 tgt 缺 bbox
- `scene_not_in_geom`     — scene 整个不在 geometry 文件里

### 2. `target_anchor_geometry_coverage.csv`

**汇总表**：按 `split × query_type` 分组的覆盖率。列：

```
split, query_type, n_queries,
n_target_covered, target_coverage_rate,
n_anchor_applicable, n_anchor_covered, anchor_coverage_rate,
n_edge_applicable, n_edge_both_covered, support_edge_endpoint_coverage_rate,
n_target_and_anchor_both_covered, target_and_anchor_coverage_rate,
n_same_label_distractor, same_label_distractor_rate
```

包含小计行：每个 split 一行 `query_type=ALL`，最后再来一行 `split=ALL, query_type=ALL`。

### 3. `coverage_summary.json`

**给学长一眼看完的高层 summary**。结构：

```json
{
  "generated_at": "2026-05-10T...",
  "input_files": {
    "queries":  "benchmark_clean_v0/queries/all_queries_index.jsonl",
    "geometry": "benchmark_clean_v0/geometry/scenefun3d_node_geom.json",
    "enriched": "benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json"
  },
  "geometry_inventory": {
    "n_scenes_in_geom": 20,
    "n_nodes_in_geom": 317,
    "scene_ids": ["420683", "421013", ...]
  },
  "totals": {
    "n_scenefun3d_queries": 1485,
    "n_functional": 870, "n_spatial": 405, "n_semantic": 210
  },
  "coverage": {
    "ALL": {
      "ALL":        {"target": 0.xx, "anchor": 0.xx, "edge": 0.xx, "n": 1485},
      "functional": {"target": 0.xx, "anchor": 0.xx, "edge": 0.xx, "n": 870},
      "spatial":    {...},
      "semantic":   {...}
    },
    "train": {"functional": {...}, "spatial": {...}, "semantic": {...}, "ALL": {...}},
    "val":   {...},
    "test":  {...}
  },
  "missing_breakdown": {
    "scenefun3d_functional_test":  {"n_total": __, "n_missing_target": __, "n_missing_anchor": __, "n_missing_edge_src": __, "n_missing_edge_tgt": __, "n_scene_not_in_geom": __},
    "scenefun3d_functional_train": {...},
    "scenefun3d_functional_val":   {...}
  },
  "same_label_distractor": {
    "scenefun3d_functional_test": {
      "n_with_distractor": __,
      "distractor_rate": 0.xx,
      "median_same_label_count": __,
      "max_same_label_count": __
    }
  },
  "gate_check": {
    "scenefun3d_functional_test_target_coverage": 0.xx,
    "scenefun3d_functional_test_support_edge_coverage": 0.xx,
    "passes_target_threshold_0.70": true,
    "passes_edge_threshold_0.65":   true,
    "ready_for_phase_2": true
  },
  "scenes_missing_from_geom": []
}
```

`gate_check` 是关键：学长打开文件直接看这一段。