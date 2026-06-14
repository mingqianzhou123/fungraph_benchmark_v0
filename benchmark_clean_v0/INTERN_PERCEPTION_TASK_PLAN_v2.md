# 本科生任务书 v2.1：Relation-Conditioned Perceptual Extension for Functional 3D Scene Graph Grounding

## 0. 任务定位

不是重做 grounding 方法，不是跑主实验，不是调模型。

你的任务：

```text
为现有 benchmark 构建一个干净、可复现、可加载的
relation-conditioned 部件级感知证据 (perceptual evidence) data extension。
```

Mingqian 负责：方法实现 / 3DGraphLLM 基线 / 编码器选择 / 主实验 / 消融 / paper 写作；充分性分层 taxonomy 的定义；co-visible 视图选择标准的精确定义（Phase 2 留空待填）。

你负责：把感知证据按“目标候选 × 它和特定 anchor 的关系”为条件整理好，让 Mingqian 直接接入。

**成功标准不是模型分数**，而是：给定任一 functional query，Mingqian 能可靠拿到“目标部件与其 anchor 同时可见的图像证据 + 部件点云”，并能做“符号 vs 粗几何 vs 感知”三档对照。

---

## 1. 为什么要做这个任务？（必读，决定你不会做偏）

论文核心主张：

```text
当场景里有很多同标签功能部件（多个一样的 knob / handle / switch）时，
“该选哪一个”所需的判别信息，本质上不在符号场景图里、也不在粗几何 (bbox) 里，
而在「目标部件 × 它与特定 anchor 的关系」的部件级感知证据里。
```

benchmark 必须能展示：**存在一批 query，符号解不了、bbox 也解不了，只有 relation-conditioned 部件级感知能解。**

### 为什么不是 bbox geometry（v1 的错误优先级）

- bbox 的 geometry / same-label rank 已部分在现有先验里，再做是重复劳动。
- 最难的同标签 case 恰恰是 bbox 失效处：15 个一样的 knob 对 15 个一样的 drawer，size 一样、height 几乎一样、distance-to-anchor 因 anchor 同标签而无法定义。
- “gray handle” 这类查询，颜色/材质不是 bbox 能表达的。

bbox 工作在本任务里降级为“筛子”（Phase 1），用来定位“粗几何分不开、必须靠感知”的子集。

### 一个会反复出现的坑（务必记住）

要的不是“给每个部件配几张好看的图”（= instance-level 视图，现有方法已做，加了没区别）。
要的是 **relation-conditioned 视图**：图里必须**同时包含目标部件和它的 anchor**，能看出两者关系。
产出“部件特写” = 任务失败。

---

## 2. 要加哪些模态：两种，只有两种

1. **Relation-conditioned 2D 视图（主）**：每个 (部件, anchor) 对，选“两者同时可见”的 top-K 帧，裁出**同时含两者**的 crop，存相机位姿与投影框。
2. **部件级 3D 点云 segment（主）**：每个功能件及其 anchor 的实际点云子集。

**明确不要做：** 不把 bbox 当模态再加深；不做 instance-level pooled 特征；现在不跑 CLIP/DINOv2/Uni3D/point transformer 全量特征（编码器选择是方法决策，benchmark 只存 raw crop + 点云，保持 encoder-agnostic）。

你交付的是**原始感知证据 + 投影元数据**，不是深度特征。

---

## 3. 工作目录和重要规则

起点：`benchmark_clean_v0/`

**不要修改**已冻结文件：`queries/ graphs/ geometry/ annotations/`，也**不要覆盖**已有的 `multimodal_extension/` geometry 文件。

新产出全部写到新子目录：

```text
benchmark_clean_v0/multimodal_extension/perception/
```

接口若需改，新建 `benchmark_clean_v1/`，不要静默改 v0。

### 3.1 关键 ID 约定（贯穿所有输出，务必遵守）

relation-conditioned 证据**必须按 (part, anchor, query) 三元组**组织，不能只用 scene/node：

```text
relation_key = f"{query_id}|{target_node_id}|{anchor_node_id}"
```

原因：同一个部件（如 oven/stove 间共享的 knob）对**不同 anchor** 的证据完全不同，只用 node_id 会把它们混在一起，破坏 relation-conditioned 的全部意义。

- **多 anchor**（query 带 `anchor_node_ids` 列表 / 多条 supporting edge）：对每个 (target, anchor) 各产出一行证据，并额外产出一个 query 级聚合条目。
- **缺 anchor**（无 anchor）：`anchor_node_id = "NONE"`，置 `anchor_missing=true`；这类只能产出 part-only 视图，**不算 relation-conditioned 证据**，单独归类。

### 3.2 不提交大文件（执行规则）

- **可以 commit**：所有 manifest（`*.csv` / `*.jsonl`）、README、handoff、sample loader、小规模 QC HTML（< 5 MB）。
- **不要 commit**：`crops/**.jpg`、`pointclouds/**.ply` 等大资产，本地保存即可，是否入库等 Mingqian 确认。
- `perception/.gitignore` 已预留忽略规则。

---

## 4. 主要输入文件

```text
queries/all_queries_index.jsonl 及 train/val/test_queries_index.jsonl   # 轻量 query 索引
queries/scenefun3d_funrag_benchmark_enriched.json                       # 完整 scene graph
geometry/scenefun3d_node_geom.json                                      # canonical bbox fallback
multimodal_extension/node_geometry_features.csv                         # 已生成 geometry sidecar（Phase 1 优先用）
multimodal_extension/feature_index.json                                 # geometry sidecar index
annotations/openfungraph/{SceneFun3D.annotations.json, *.relations.json, all_labels.json, all_edges.json}
raw_assets/scenefun3d_raw_asset_manifest.csv                            # 原始资产指针（勿移动原文件）
human_annotations/functional_queries_v1/                                # 已填充的人类 query / minimal pair / stress query
    functional_queries_v1.jsonl
    minimal_pairs_v1.jsonl
    long_range_stress_queries_v1.jsonl
```

**输入状态规则：**

- 若 `node_geometry_features.csv` 缺少某个 node，Phase 1 对该 node fallback 到 `geometry/scenefun3d_node_geom.json`，并在报告中记录 `geometry_source`。
- `human_annotations/functional_queries_v1/*.jsonl` 在当前 benchmark 仓库中已经存在；Phase 2 pilot 应优先使用 minimal pairs，但仍要先验证字段完整性和 query/node IDs 是否能对齐。

---

## 5. 总体交付目标

```text
P0 raw modality availability report（分级：image_projection / point_segment / bbox_only）
P1 same-label 分层清单（连续 separation + 多 epsilon flag，placeholder）
P2 relation-conditioned crop 资产 + 元数据（优先 human minimal-pair + P1 同标签子集）
P3 部件 / anchor 点云 segment
P4 sanity-check（必须用 GT 部件）
P5 handoff documentation + sample loader
```

Mingqian 拿到后，应能用 relation_key 取到对应感知证据，不碰原始数据。

---

## Phase 0 — Raw Modality Availability Audit（最先做，硬阻塞）

### 目标

确认本地数据是否足够做感知扩展。SceneFun3D 功能件标注在激光扫描上，图像在单独 RGB-D 序列，投影需要完整“激光扫描 → 相机”变换链。缺一环即 data-block。

### 分级

逐 scene（mask 部分逐 node）判定三档，**互相独立**：

```text
image_projection_ready : RGB + depth + intrinsics + poses + laser_to_camera transform  全部可读
point_segment_ready    : 激光扫描 .ply + part/anchor 的 mask 或 point indices          全部可读
bbox_only              : 仅有 bbox（只能做粗几何，做不了真正 perception evidence）
```

这样缺数据时能立刻分清是 **crop-blocked** 还是 **point-segment-blocked**。

### 输出文件与必填列

`perception/p0_raw_modality_availability.csv`，每行一个 scene（mask 列可细到 node）：

```text
scene_id,
rgb_exists, depth_exists, intrinsics_exists, poses_exists, laser_to_camera_exists,
laser_scan_exists, part_mask_exists, anchor_mask_exists,
image_projection_ready, point_segment_ready, bbox_only,
failure_reason,
source_raw_path
```

`perception/p0_availability_summary.md`：三档各有多少 scene、缺失各缺什么、是否需额外下载。

### Escalation gate（必须停）

跑完先停，把两个文件发 Mingqian。**确认前不要进 Phase 1。** 若 image_projection_ready 的 functional scene 比例低，先一起排查是真缺数据还是路径/对齐问题，不要先裁图。

---

## Phase 1 — Same-Label 分层（复用 geometry，作筛子）

### 目标

标出“哪些同标签 case 粗几何分不开”，也就是感知必须救的战场。

### 占位定义（连续量，避免单一阈值被误用）

对每条 functional query 的同标签候选集，沿最佳区分轴计算最小间隔，并在多档打 flag：

```text
min_geom_separation_m          # 同标签候选间，在 {distance_to_anchor, z(height), volume} 上的最小可区分间隔（取最易分的轴）
geom_sep_at_1cm  (bool)
geom_sep_at_5cm  (bool)
geom_sep_at_10cm (bool)
is_placeholder_rule = true     # 强制 true：这些 flag 只用于排序/采样，不得进任何论文结论
```

报告中给出三档 flag 的敏感性（1/5/10cm 各有多少 query 翻转）。**不要**自己定一个“最终阈值”。

### 输出文件与必填列

`perception/p1_same_label_strata.csv`：

```text
query_id, split, scene_id, target_node_id, anchor_node_id,
same_label_count, min_geom_separation_m,
geom_sep_at_1cm, geom_sep_at_5cm, geom_sep_at_10cm,
is_placeholder_rule, geometry_source
```

`perception/p1_strata_summary.md`：functional 同标签 query 总数 / 各档“分不开”的数量与占比。

---

## Phase 2 — Relation-Conditioned Crop（主线；标准冻结前只能 dry-run）

### 目标

为 (部件, anchor) 对产出 relation-conditioned 视图。**首批优先做：human_annotations 的 minimal pair + `p1` 里粗几何分不开的同标签 query**，规模压到 3–5 scene / 20–50 个 (part,anchor) 对。

> 为什么先做这批：minimal pair 带 anchor、带 expected_failure_modes，是 relation_key 和 pair-accuracy 最锋利的落点；这批也正好够 Mingqian 跑 go/pivot 判定实验，最早解锁论文方向决策。

### 模式开关（强制）

```text
在 Mingqian 填好下方“co-visible 视图选择标准”之前，Phase 2 只能 DRY-RUN：
  - 只在少量 part 上验证投影管线、产出 debug overlay 图（看 part/anchor 是否都落在框里）
  - 不得批量产出“实验级” crop
  - 所有此阶段产物：selection_rule_version = "placeholder_dryrun"，is_placeholder_rule = true
标准冻结后才切到正式模式，重跑并产出 selection_rule_version = "<version>" 的正式 crop。
```

### 待 Mingqian 填：Co-Visible 视图选择标准（本科生勿自定义）

```text
[ TODO — Mingqian 填写 ]
- anchor 判定为“可见”的条件：________
- 投影面积 / 可见点比例阈值：________
- part 与 anchor 必须同帧可见？是否允许仅 part 可见的回退：________
- K（每对保留几帧）：________
- 遮挡处理：是否用 depth 做 z-test：________
- crop 框如何包住 part + anchor（联合 bbox + margin）：________
```

### 管线（与标准解耦，dry-run 即可跑通）

```text
1. 取部件 3D 点（激光扫描坐标系）
2. transform + 位姿 + 内参 → 投影到每帧
3. （可选）depth z-test 排除遮挡帧
4. 对 part 与 anchor 各算可见性得分
5. 按 co-visible 标准选 top-K（dry-run 用占位规则）
6. 裁出含 part+anchor 的 crop，存图
7. 记录元数据
```

### 输出文件与必填列

```text
perception/crops/<scene_id>/<relation_dir>/view_*.jpg
perception/p2_crop_index.jsonl
```

`p2_crop_index.jsonl` 每行必含：

```text
relation_key, relation_dir, query_id, split, scene_id, target_node_id, anchor_node_id, supporting_edge_id,
anchor_missing,
view_paths, camera_pose_per_view,
part_proj_box_per_view, anchor_proj_box_per_view, visibility_score_per_view,
coordinate_frame,
selection_rule_version,
is_placeholder_rule,
failure_reason
```

`relation_dir` 用 `sha1(relation_key)[:12]` 或等价稳定 hash，避免把 `|` 直接放进路径导致 shell/script 问题。`relation_key` 仍是语义主键，必须保留在 index 里。

`perception/p2_crop_pilot_report.md`：覆盖率、失败分布、几张正/反例。

---

## Phase 3 — 部件 / Anchor 点云 Segment（同子集）

### 输出文件与必填列

```text
perception/pointclouds/<scene_id>/<node_id>.ply
perception/p3_pointcloud_index.jsonl
```

`p3_pointcloud_index.jsonl` 每行必含：

```text
node_id, scene_id, role(part|anchor), relation_keys(引用到的 relation_key 列表),
ply_path, num_points, coordinate_frame, source_raw_path, failure_reason
```

点云按 node 存一次即可，再用 relation_keys 关联到具体 query，避免重复存储。

---

## Phase 4 — Sanity Check & QC（必须用 GT 部件）

### 目标

确认证据可信，并把“检测/投影失败”与“信息天花板”隔开。**一律用 GT 标注的部件抽证据**，先排除感知质量问题，否则会把感知模块烂误读成符号天花板。

### 内容

选 20–50 例生成可读页面，每例展示：query / scene_id / relation_key / target_label / anchor_label、relation-conditioned crop 缩略图（验证 part+anchor 是否真都在框里）、part/anchor 点云点数、same_label_count、min_geom_separation_m + 各档 flag、投影成功/失败原因。

并统计：多少 (part,anchor) 对投不出合格 co-visible 帧；同标签簇里 crop 肉眼可分/不可分比例。

### 输出

```text
perception/p4_sanity_examples.html
perception/p4_qc_report.csv
```

---

## Phase 5 — Handoff Documentation

### 输出

```text
perception/README.md
perception/handoff_notes.md
perception/sample_load_perception.py
```

文档须讲清：每个文件/目录是什么；各字段含义；点云坐标系与来源；缺失/失败如何编码；**relation_key 格式**、多/缺 anchor 如何表示；如何用 relation_key 取 crop+点云；如何用 query_id 取关联证据；哪些 query 无感知证据及原因；哪些属“粗几何分不开”（适合做感知 vs 符号对照）。

`sample_load_perception.py` 演示：输入 relation_key 返回 view 路径 + 点云路径；输入 query_id 返回其全部 relation_key 与证据。

---

## Optional Phase 6 — 扩到全量 + 其余 split（前 5 phase 验收后再做）

Mingqian 确认 pilot 与 go/pivot 通过后再扩到完整 SF3D-functional，及（若有图像与位姿的）3DSSG / SF3D-other。

**deadline 前不要做**：任何全量深度特征提取、3DGraphLLM 适配（方法侧）。

---

## 6. 最终必须交付

```text
perception/p0_raw_modality_availability.csv + p0_availability_summary.md
perception/p1_same_label_strata.csv + p1_strata_summary.md
perception/crops/... (本地) + p2_crop_index.jsonl + p2_crop_pilot_report.md
perception/pointclouds/... (本地) + p3_pointcloud_index.jsonl + p3_pointcloud_report.md
perception/p4_sanity_examples.html + p4_qc_report.csv
perception/README.md + handoff_notes.md + sample_load_perception.py
perception/.gitignore
```

---

## 7. 最重要的原则

1. **不改 frozen benchmark**，不覆盖已有 geometry 产出，只写 `perception/`。
2. **模态是 relation-conditioned 的**：crop 必须同时含 part 和 anchor；产出特写 = 失败。
3. **按 relation_key 组织**（query_id|target|anchor），显式处理多/缺 anchor。
4. **你负责数据，不负责方法与 framing**：不跑方法实验；不自定义 co-visible 标准；不自定义任何分层 taxonomy；卡住的定义标占位并继续跑通管线。
5. **标准冻结前 Phase 2 只 dry-run**，crop 标 placeholder_dryrun。
6. **先解锁决策再求全**：P0 → P1 → P2/P3 最小子集（minimal pair + P1 同标签子集）→ QC → handoff，全量最后做。
7. **QC 用 GT 部件**，隔开感知质量与信息天花板。
8. **不 commit 大文件**：只入库 manifest/README/loader/小 QC HTML。
9. **汇报节奏**：每 phase 当天发 <200 字 progress note；**P0 结束必须先 sync**；卡住超半天立刻找 Mingqian。

---

## 8. 这个任务对 paper 的价值

完成后论文能讲：每个功能件在“与其 anchor 同时可见”的图像里有 relation-conditioned 证据 + 点云 segment，使同一 query 可在符号 / 粗几何 / relation-conditioned 感知三档下被尝试，从而隔离出“只有感知能突破符号天花板”的同标签 case。即把项目从 text-level functional grounding 升级为能**实证“符号天花板 + 感知突破”**的多模态 benchmark——论文 novelty 的承载体。

> 待 Mingqian + Dennis 决策（不在本任务书内）：是否把 human_annotations 按“实际需要哪一层（符号/几何/感知/信息不足）”重新分层，以区分“符号<几何”与“几何<感知”两类 hard case。这步决定论文立的是弱命题还是强命题，属 framing，需 Dennis 签字。
