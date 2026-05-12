## 产出

```
benchmark_clean_v0/multimodal_extension/
├── scripts/
│   └── phase2_node_geometry_features.py   # 378 行
├── node_geometry_features.csv             # 317 行 × 24 列 (142 KB)
├── node_geometry_features.pt              # tensor (317, 22) float32 (70 KB)
└── feature_index.json                     # 317 keys, scene_id/node_id → row (58 KB)
```

## 核心数据

| 维度 | 值 |
|---|---|
| scenes | 20 |
| nodes | 317（6~43 nodes/scene，均值 15.8） |
| has_bbox | 100%（0 个 NaN） |
| CSV 列数 | 24（NODE_FEATURE_COLUMNS，freeze） |
| PT tensor shape | (317, 22) float32 |
| feature_row 连续 | 0~316，无重复 |

### 关键列数值范围

| 列 | 最小值 | 最大值 | 均值 |
|---|---|---|---|
| `height_from_floor_m` | 0.022 m | 7.962 m | 1.853 m |
| `height`（物体本身高，=size_y） | 0.011 m | 5.069 m | 0.231 m |
| `bbox_volume` | 2.9e-6 m³ | 42.0 m³ | 0.253 m³ |
| `bbox_diagonal` | 0.030 m | 9.315 m | 0.515 m |
| `scene_normalized_center_x` | 0.005 | 0.996 | 0.498 |
| `scene_normalized_center_z` | 0.011 | 0.985 | 0.381 |
| `scene_normalized_size_x` | 0.001 | 0.718 | 0.074 |
| `scene_normalized_size_z` | 0.004 | 1.000 | 0.149 |

## 设计决策（已与 Mingqian 确认，2026-05-11）

1. **高度轴 = y**：`height = bbox_size_y`（非 size_z）。  
   依据：z 有 100–380m 全局偏移（点云注册帧），y 以 0 为中心范围 2–8m，符合室内高度。

2. **归一化方案 C（重力对齐分层）**：
   - 水平轴 (x, z)：scene AABB min-max 归一化 → [0, 1]，跨 scene 可比
   - 垂直轴 (y)：保留米制绝对尺度
     - `height_from_floor_m = center_y - scene_min_y`（scene 内最低 node 为地板基准）
     - `bbox_size_y_m = size_y`（米，替换 `scene_normalized_size_y` 槽位）

3. **PT 文件格式**：self-contained dict，含 features tensor + columns + scene_ids + node_ids + feature_row_index，无需额外文件即可使用。

## NODE_FEATURE_COLUMNS（24 列，freeze，只能末尾 append）

```python
NODE_FEATURE_COLUMNS = [
    "scene_id", "node_id",                                     # 标识符 (2)
    "has_bbox",                                                 # 覆盖标志 (1)
    "bbox_center_x", "bbox_center_y", "bbox_center_z",         # 原始 bbox (9)
    "bbox_min_x",    "bbox_min_y",    "bbox_min_z",
    "bbox_max_x",    "bbox_max_y",    "bbox_max_z",
    "bbox_size_x",   "bbox_size_y",   "bbox_size_z",           # 尺寸衍生 (6)
    "bbox_volume", "bbox_diagonal", "height",
    "scene_normalized_center_x",                               # scene 内归一化 (6)
    "height_from_floor_m",                                     # 方案 C：垂直保留米制
    "scene_normalized_center_z",
    "scene_normalized_size_x",
    "bbox_size_y_m",                                           # 方案 C：垂直保留米制
    "scene_normalized_size_z",
]
```

## 输出文件访问方式

```python
# 已知 scene_id + node_id，取出 geometry feature
import pandas as pd, torch, json

df  = pd.read_csv("node_geometry_features.csv")
pt  = torch.load("node_geometry_features.pt", weights_only=False)
idx = json.load(open("feature_index.json"))

key = "420683/465347e8-606a-4807-b89e-085cf8c578f3"  # knob
row = idx[key]["feature_row"]                         # → 5

csv_feat = df.iloc[row]                               # pandas Series，含全部 24 列
pt_feat  = pt["features"][row]                        # tensor shape (22,)，直接送模型
```

## 验证结果（13 项全部通过）

| 检查项 | 结果 |
|---|---|
| CSV 行数 == 317 | pass |
| CSV 列数 == 24 | pass |
| has_bbox 全 True | pass |
| NaN 数 == 0 | pass |
| scene_normalized_center_x ∈ [0,1] | pass |
| scene_normalized_center_z ∈ [0,1] | pass |
| height_from_floor_m ≥ 0 | pass |
| scene_normalized_size_x ≥ 0 | pass |
| scene_normalized_size_z ≥ 0 | pass |
| bbox_size_y_m ≥ 0 | pass |
| bbox_volume ≥ 0 | pass |
| feature_index key 数 == 317 | pass |
| feature_row 连续集合 0~316 | pass |
| 5 个抽样 node 手算 vs CSV diff | max_diff = 0.00e+00，pass |

## 值得告诉学长的发现

1. **无 NaN**：317 个 node 全部有 bbox，Phase 3 可直接计算所有 query 的 target/anchor 距离，无需 has_bbox mask 的特殊分支（但代码已预留）。

2. **`height_from_floor_m` 物理合理**：均值 1.85m，最大 7.96m（某 scene 内最高与最低 node 的相对高度差），与室内 2–8m 层高一致。小物体（旋钮、开关）离地 0.3–1.5m，灯具类 1.5–3m，符合直觉。

3. **`bbox_volume` 跨度大**：最小 2.9e-6 m³（约 3cm 小旋钮）到最大 42 m³（整面墙或大型家具节点），相差 7 个数量级。Phase 3 的 same-label volume rank 会直接利用这个差异做 disambiguation。

4. **水平位置均匀覆盖 [0,1]**：x 均值 0.50、z 均值 0.38，节点在 scene 内分布合理，scene_normalized 坐标有区分度。

5. **一个注意事项**：`scene_normalized_center_y` 槽位已改名为 `height_from_floor_m`，`scene_normalized_size_y` 槽位改为 `bbox_size_y_m`，二者保留米制绝对尺度（方案 C），与 phase.md 原始列名不同。列顺序位置不变，下游按列名读取不受影响。

## 下一步

进入 Phase 3：query-level geometry feature bank  
输入：`all_queries_index.jsonl` + `node_geometry_features.csv` + `feature_index.json`  
输出：`query_geometry_features.csv` + `query_geometry_features.jsonl`
