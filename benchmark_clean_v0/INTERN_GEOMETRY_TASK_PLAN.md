# 本科生任务书：Geometry-Grounded Benchmark Extension for FCGP

## 0. 任务定位

这个任务不是让你重做 FCGP 方法，也不是让你跑主实验。

你的任务是：

```text
为现有 benchmark 构建一个干净、可复现、可加载的 geometry-grounded data extension。
```

Mingqian 会继续负责：

```text
FCGP / L-FCGP 方法实现
reranker integration
main ablation
paper table
paper writing
```

你负责把 geometry 数据整理好，让 Mingqian 可以直接接入方法。

## 1. 为什么要做这个任务？

目前我们的 benchmark 已经支持 text-level functional 3D scene graph grounding。

也就是说，给定 query：

```text
press the switch that controls the desk lamp
```

benchmark 已经知道：

```text
target node
anchor node
supporting functional edge
scene graph nodes
scene graph edges
```

但是为了让 paper 更像 robotics / embodied AI，我们还希望知道：

```text
target object 在 3D 空间中的哪里？
它有多大？
它和 anchor object 的距离是多少？
supporting edge 两端是否都有 3D grounding？
如果场景里有多个同名 object，geometry 是否能帮助区分？
```

==这里的 geometry 指的是 object-level 3D bounding box 信息，例如==：

```text
bbox_center
bbox_min
bbox_max
bbox_size
height
distance_to_anchor
relative_position_to_anchor
```

不是 RGB 图像，也不是 point-cloud deep feature。

这个 extension 的意义是把项目从：

```text
query + textual functional scene graph
```

增强成：

```text
query + textual functional scene graph + object-level 3D geometry
```

## 2. 工作目录和重要规则

你应该从这个目录开始：

```text
benchmark_clean_v0/
```

这是当前 CoRL deadline 前的 frozen benchmark interface。

重要规则：

```text
不要修改 benchmark_clean_v0/queries/
不要修改 benchmark_clean_v0/graphs/
不要修改 benchmark_clean_v0/geometry/
不要修改 benchmark_clean_v0/annotations/
```

你所有新产生的文件都写到：

```text
benchmark_clean_v0/multimodal_extension/
```

## 3. 主要输入文件

### 3.1 轻量 query index

优先使用：

```text
benchmark_clean_v0/queries/all_queries_index.jsonl
benchmark_clean_v0/queries/train_queries_index.jsonl
benchmark_clean_v0/queries/val_queries_index.jsonl
benchmark_clean_v0/queries/test_queries_index.jsonl
```

这些文件每一行是一条 query，包含：

```text
query_id
dataset
scene_id
split
query
query_type
target_node_ids
target_labels
anchor_node_id
anchor_node_ids
supporting_edge_id
supporting_edge_ids
action_verb
```

### 3.2 SceneFun3D 完整 benchmark

```text
benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json
```

如果你需要完整 scene graph，可以读这个文件。

### 3.3 SceneFun3D geometry 文件

```text
benchmark_clean_v0/geometry/scenefun3d_node_geom.json
```

格式是：

```text
scene_id -> node_id -> bbox_center / bbox_min / bbox_max
```

==这是本任务最重要的 geometry 输入==。

### 3.4 OpenFunGraph annotations

```text
benchmark_clean_v0/annotations/openfungraph/
```

这些文件可用于追溯原始 annotations、relations 和 label vocabulary。

### 3.5 原始资产指针

```text
benchmark_clean_v0/raw_assets/scenefun3d_raw_asset_manifest.csv
```

这个文件只记录 raw point cloud / metadata 的路径。

不要移动或复制原始 `.ply` 文件。

## 4. 总体交付目标

你最终要交付的是一个 geometry extension data package，包括：

```text
coverage report
node-level geometry features
query-level geometry features
feature index
sanity-check examples
handoff documentation
optional raw modality availability audit
```

Mingqian 拿到这些文件后，应该可以快速把 geometry features 接入 L-FCGP reranker。

## Phase 1 — Geometry Coverage Audit

### 目标

统计当前 benchmark 中有多少 SceneFun3D query 可以使用 geometry。

### 具体任务

读取：

```text
benchmark_clean_v0/queries/all_queries_index.jsonl
benchmark_clean_v0/geometry/scenefun3d_node_geom.json
```

只统计 SceneFun3D 的 query。

对每条 query 检查：

```text
target_node_ids 是否有 bbox
anchor_node_id 是否有 bbox
supporting_edge_id / supporting_edge_ids 的 endpoint 是否有 bbox
```

==需要统计：==

```text
all SceneFun3D queries
functional queries
train / val / test
target node coverage
anchor node coverage
supporting-edge endpoint coverage
target + anchor both covered
same-label distractor cases coverage
missing geometry cases
```

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/geometry_coverage_report.csv
benchmark_clean_v0/multimodal_extension/target_anchor_geometry_coverage.csv
benchmark_clean_v0/multimodal_extension/coverage_summary.json
```

### 成功标准

我们应该能清楚知道：

```text
多少 examples 可以使用 geometry
缺 geometry 的 query 是哪些
缺的是 target、anchor，还是 supporting edge endpoint
```

### Escalation gate

跑完 Phase 1 后先停下来，不要直接进入 Phase 2。

请把以下文件发给 Mingqian 检查：

```text
benchmark_clean_v0/multimodal_extension/coverage_summary.json
benchmark_clean_v0/multimodal_extension/geometry_coverage_report.csv
```

如果 SceneFun3D functional test split 上出现以下任一情况：

```text
target_geometry_coverage < 0.70
support_edge_endpoint_coverage < 0.65
```

不要继续 Phase 2。先找 Mingqian 一起检查 geometry 文件、node id 对齐和 coverage 统计逻辑。

## Phase 2 — Node-Level Geometry Feature Bank

### 目标

把已有 bbox 信息转换成每个 node 的 feature。

### 输入

```text
benchmark_clean_v0/geometry/scenefun3d_node_geom.json
```

### 对每个 node 计算

```text
scene_id
node_id
has_bbox

bbox_center_x
bbox_center_y
bbox_center_z

bbox_min_x
bbox_min_y
bbox_min_z

bbox_max_x
bbox_max_y
bbox_max_z

bbox_size_x
bbox_size_y
bbox_size_z

bbox_volume
bbox_diagonal
height

scene_normalized_center_x
scene_normalized_center_y
scene_normalized_center_z

scene_normalized_size_x
scene_normalized_size_y
scene_normalized_size_z
```

其中：

```text
bbox_size = bbox_max - bbox_min
bbox_volume = size_x * size_y * size_z
bbox_diagonal = sqrt(size_x^2 + size_y^2 + size_z^2)
height = size_z
```

### 缺失值约定

当 `has_bbox=false` 时，所有数值列统一填：

```text
CSV: nan
PT: float("nan")
```

下游代码必须使用 `has_bbox` mask 过滤缺失 geometry，不要通过数值本身判断缺失。

### Feature columns 契约

`node_geometry_features.csv` 的列顺序就是 node-level feature 顺序，必须在：

```text
benchmark_clean_v0/multimodal_extension/geometry_feature_readme.md
```

顶部用如下格式写死：

```python
NODE_FEATURE_COLUMNS = [
    ...
]
```

后续如果要加新列，只能 append 到末尾，不能插入、删除或重排已有列。

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/node_geometry_features.csv
benchmark_clean_v0/multimodal_extension/node_geometry_features.pt
benchmark_clean_v0/multimodal_extension/feature_index.json
```

### feature_index.json 示例

```json
{
  "420683/e0047d50-015b-40d0-8910-f0c4b1fb5b7a": {
    "scene_id": "420683",
    "node_id": "e0047d50-015b-40d0-8910-f0c4b1fb5b7a",
    "feature_row": 0,
    "has_bbox": true
  }
}
```

### 成功标准

给定：

```text
scene_id + node_id
```

我们可以稳定找到它的 geometry feature row。

## Phase 3 — Query-Level Geometry Feature Bank

### 目标

为每条 query 计算 target / anchor / supporting edge 相关的 geometry feature。

### 输入

```text
benchmark_clean_v0/queries/all_queries_index.jsonl
benchmark_clean_v0/multimodal_extension/node_geometry_features.csv
benchmark_clean_v0/multimodal_extension/feature_index.json
```

### 对每条 SceneFun3D query 计算

```text
query_id
scene_id
split
query_type

target_node_id
target_label
target_has_bbox

anchor_node_id
anchor_has_bbox

target_anchor_both_have_bbox

distance_to_anchor
relative_x_to_anchor
relative_y_to_anchor
relative_z_to_anchor
relative_height_to_anchor

target_larger_than_anchor
target_higher_than_anchor

supporting_edge_id
supporting_edge_source_has_bbox
supporting_edge_target_has_bbox
supporting_edge_both_have_bbox
```

### same-label disambiguation features

如果同一 scene 里有多个相同 label 的 node，计算：

```text
same_label_count
same_label_has_distractor
same_label_distance_rank_to_anchor
same_label_height_rank
same_label_volume_rank
```

例如 scene 里有多个 `switch`、`knob`、`remote`，这些 feature 可以帮助之后分析 geometry 是否帮助区分同名物体。

所有 rank 类 feature 使用 dense rank：

```text
same_label_distance_rank_to_anchor
same_label_height_rank
same_label_volume_rank
```

同分共享名次。平手时按 `node_id` 字典序作为次级排序键，保证结果可复现。可以使用：

```python
pandas.DataFrame.rank(method="dense")
```

### 缺失值约定

当相关 node 没有 bbox，或者 anchor 不存在时，所有无法计算的数值列统一填：

```text
CSV: nan
JSONL: NaN 或 null，但需要在 README 中明确说明
```

布尔列必须显式写：

```text
true / false
```

不要用空字符串表示缺失。

### Feature columns 契约

`query_geometry_features.csv` 的列顺序就是 query-level feature 顺序，必须在：

```text
benchmark_clean_v0/multimodal_extension/geometry_feature_readme.md
```

顶部用如下格式写死：

```python
QUERY_FEATURE_COLUMNS = [
    ...
]
```

后续如果要加新列，只能 append 到末尾，不能插入、删除或重排已有列。

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/query_geometry_features.csv
benchmark_clean_v0/multimodal_extension/query_geometry_features.jsonl
```

### 成功标准

给定：

```text
query_id
```

我们能查到这条 query 的 target / anchor / supporting edge geometry 状态和相关 feature。

## Phase 4 — Sanity Check and Visualization

### 目标

确认 geometry extension 是可信的，而不是只有数字文件。

### 具体任务

从 functional queries 中选 20-50 个例子，生成一个人能看懂的页面或表格。

每个例子展示：

```text
query
scene_id
target_node_id
target_label
anchor_node_id
supporting_edge_id

target bbox_center
target bbox_size
anchor bbox_center
anchor bbox_size

distance_to_anchor
relative_position_to_anchor

same_label_count
same_label candidate ids
coverage status
```

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/geometry_sanity_examples.html
benchmark_clean_v0/multimodal_extension/manual_check_report.csv
```

### 成功标准

Mingqian 可以人工检查这些例子，并判断：

```text
target 是否有 3D geometry
anchor 是否有 3D geometry
same-label cases 是否被正确标记
feature 数值是否明显异常
```

## Phase 5 — Handoff Documentation

### 目标

把你生成的 dataset extension 整理成 Mingqian 可以快速接入方法的格式。

你不需要实现 reranker。

你不需要跑主实验。

你不需要修改 FCGP 代码。

你需要说明清楚：

```text
每个输出文件是什么
每一列 feature 是什么意思
缺失值如何编码
node key 格式是什么
query key 格式是什么
如何通过 scene_id + node_id 找到 node feature
如何通过 query_id 找到 query feature
哪些 examples 没有 geometry
哪些 examples 适合做 geometry ablation
```

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/geometry_feature_readme.md
benchmark_clean_v0/multimodal_extension/handoff_notes.md
benchmark_clean_v0/multimodal_extension/sample_load_geometry_features.py
```

### sample_load_geometry_features.py 需要展示

```text
1. 如何读取 node_geometry_features.csv
2. 如何读取 query_geometry_features.csv
3. 如何读取 feature_index.json
4. 输入 scene_id + node_id，返回 node geometry feature
5. 输入 query_id，返回 query geometry feature
```

`sample_load_geometry_features.py` 必须从：

```text
geometry_feature_readme.md
```

读取 `NODE_FEATURE_COLUMNS` 和 `QUERY_FEATURE_COLUMNS`，不要在脚本里 hardcode feature 顺序。

### 成功标准

Mingqian 拿到这些文件后，可以在 10 分钟内写 loader 接入 L-FCGP。

## Optional Phase 6 — Raw Modality Availability Audit

这一阶段是可选的。

只有 Phase 1-5 都完成后再做。

### 目标

检查本地是否有进一步做 RGB / point cloud extension 的条件。

### 具体任务

检查每个 SceneFun3D scene 是否有：

```text
RGB images
depth images
camera intrinsics
camera trajectory / poses
point cloud .ply
metadata.csv
transform matrix
instance masks
```

注意：不要直接开始 DINOv2、CLIP、Uni3D。

先只做 availability audit。

### 输出文件

```text
benchmark_clean_v0/multimodal_extension/raw_modality_availability_report.csv
benchmark_clean_v0/multimodal_extension/raw_modality_availability_summary.md
```

### 成功标准

我们能清楚知道：

```text
当前本地数据是否足够支持 RGB crop
当前本地数据是否足够支持 point-cloud crop
缺哪些文件
是否需要额外下载 SceneFun3D raw assets
```

## Optional Phase 7 — Small RGB / Point-Cloud Pilot

这一阶段也是可选的。

只有 raw modality availability audit 显示文件齐全时才做。

### RGB pilot

只做小规模：

```text
3-5 scenes
20-50 target / anchor nodes
```

输出：

```text
benchmark_clean_v0/multimodal_extension/rgb_pilot/
benchmark_clean_v0/multimodal_extension/rgb_pilot_report.md
```

### Point-cloud pilot

如果 bbox 和 `.ply` 足够，可以尝试裁出 bbox 内点云。

输出：

```text
benchmark_clean_v0/multimodal_extension/pointcloud_pilot/
benchmark_clean_v0/multimodal_extension/pointcloud_pilot_report.md
```

### 不要在 deadline 前做

```text
full DINOv2 feature extraction
full CLIP feature extraction
full Uni3D feature extraction
full 3DGraphLLM adaptation
```

## 最终必须交付

```text
benchmark_clean_v0/multimodal_extension/geometry_coverage_report.csv
benchmark_clean_v0/multimodal_extension/target_anchor_geometry_coverage.csv
benchmark_clean_v0/multimodal_extension/coverage_summary.json

benchmark_clean_v0/multimodal_extension/node_geometry_features.csv
benchmark_clean_v0/multimodal_extension/node_geometry_features.pt
benchmark_clean_v0/multimodal_extension/feature_index.json

benchmark_clean_v0/multimodal_extension/query_geometry_features.csv
benchmark_clean_v0/multimodal_extension/query_geometry_features.jsonl

benchmark_clean_v0/multimodal_extension/geometry_sanity_examples.html
benchmark_clean_v0/multimodal_extension/manual_check_report.csv

benchmark_clean_v0/multimodal_extension/geometry_feature_readme.md
benchmark_clean_v0/multimodal_extension/handoff_notes.md
benchmark_clean_v0/multimodal_extension/sample_load_geometry_features.py
```

可选交付：

```text
benchmark_clean_v0/multimodal_extension/raw_modality_availability_report.csv
benchmark_clean_v0/multimodal_extension/raw_modality_availability_summary.md

benchmark_clean_v0/multimodal_extension/rgb_pilot/
benchmark_clean_v0/multimodal_extension/rgb_pilot_report.md

benchmark_clean_v0/multimodal_extension/pointcloud_pilot/
benchmark_clean_v0/multimodal_extension/pointcloud_pilot_report.md
```

## 时间安排

### May 8-10

理解 `benchmark_clean_v0`。

完成 Phase 1 coverage audit。

### May 11-13

完成 Phase 2 node-level geometry feature bank。

### May 14-16

完成 Phase 3 query-level geometry feature bank。

### May 17-18

完成 Phase 4 sanity check / visualization。

### May 19-20

完成 Phase 5 handoff documentation。

### May 21 之后

如果前面都完成，再做 Optional Phase 6 / 7。

否则不要扩展 RGB / point cloud。

## 最重要的原则

### 1. 不改 frozen benchmark

不要改：

```text
benchmark_clean_v0/queries/
benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/
benchmark_clean_v0/annotations/
```

只写：

```text
benchmark_clean_v0/multimodal_extension/
```

### 2. 你负责数据，不负责方法实验

你不需要跑：

```text
FCGP
L-FCGP
LLM grounding
main ablation
paper table
```

Mingqian 会负责这些。

### 3. 先把 geometry 做扎实

优先级：

```text
coverage audit
node features
query features
sanity examples
handoff docs
```

RGB / point cloud 是可选，不是必须。

### 4. 成功标准

这个任务成功的标志不是模型分数提升多少。

成功的标志是：

```text
Mingqian 可以可靠地把每个 SceneFun3D query / node 映射到 geometry features，
并能用这些 features 做后续 FCGP geometry ablation。
```

### 5. 汇报节奏

每个 phase 结束当天发一个少于 200 字的 progress note，包含：

```text
做了什么
卡在哪里
下一步做什么
```

Phase 1 结束后必须先 sync 一次，等 Mingqian 确认 coverage summary 后再进入 Phase 2。

任何卡住超过半天的问题，立刻找 Mingqian，不要自己耗。

## 这个任务对 paper 的价值

如果完成，我们可以在 paper 里说：

```text
The benchmark is not purely textual: SceneFun3D object nodes are linked to 3D geometry,
allowing grounded object instances to be localized by bbox center and size.
```

也可以讲：

```text
Functional graph retrieval explains why an object is the correct target.
Geometry grounding tells us where the object is in 3D space and helps analyze same-label disambiguation.
```

这会把项目从：

```text
textual functional graph grounding
```

增强成：

```text
geometry-grounded functional 3D scene graph grounding
```
