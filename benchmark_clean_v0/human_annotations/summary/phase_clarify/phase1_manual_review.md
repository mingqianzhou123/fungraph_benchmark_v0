# Phase 1 人工核查工作流

## 核查准备：打开两个文件并排

- **左侧**：`pilot_20_queries.jsonl`（每行一条 query）
- **右侧**：`scene_graph_summary_v1.txt`（对应 scene 的节点/边/同名组）

---

## 对每条 query 执行的 3 个核查步骤

### Step 1：对照 scene_graph_summary 验证 node/edge 真实存在

在 `scene_graph_summary_v1.txt` 中找到对应的 `SCENE XXXXXX`，然后核查：

```
target_node_id  在 NODES 列表中出现？ → 记录 label 和 z/x 坐标
anchor_node_id  在 NODES 列表中出现？ → 记录 label 和 z/x 坐标
supporting_edge_ids 的那条 edge_id 在 EDGES 列表中出现？
edge_id 格式 = target_node_id | relation | anchor_node_id？（方向是否正确）
```

### Step 2：判断 query_text 是否语义正确

用自己的话回答：

> Q: 如果我是机器人，只看 query_text，我的任务是找什么物体？  
> A: 应该找 **target_label**，而不是 anchor_label

检查点：
- query 是否模糊到多义（能找到多个不同的 target）？
- 若 `is_label_only_solvable=false`，query 不应该直接说出 target label
- `evidence_chain` 是否和 `query_text` 语义一致？

### Step 3：按 difficulty_tags 做针对性核查

| tag | 针对性核查 |
|---|---|
| `simple_functional` | anchor 是否在场景中唯一？`num_same_label_distractors` 是否 = SAME-LABEL count - 1？ |
| `functional_relation` | 不看 anchor，仅靠 label 能猜对吗？若 `is_label_only_solvable=false`，答案应不唯一 |
| `same_label_disambiguation` | SAME-LABEL GROUPS 中，target label 的 count 是否 ≥ 2？ |
| `endpoint_ambiguity` | edge 两端是否都是可交互对象？query 是否不显式区分哪端是答案？ |
| `geometry_aware` | `geometry_cues` 中的词（lowest/leftmost 等）是否在 z/x 坐标排序中对应 target？ |
| `hard_negative` | query_text 是否完全不提 target label？`is_label_only_solvable` 是否为 false？ |

---

## 20 条 Query 逐条核查表

> 核查时在 `结论` 列写 ✅ 或填写发现的问题

### Scene 420683（4条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000001` | "Turn the radiator knob..." | target=`e0047d50`(knob,z=381.827), anchor=`8a1b9af6`(radiator)。scene 有 9 个 knob，radiator 唯一 → `is_label_only_solvable=true` 合理。edge 在 EDGES 中存在 ✓ | |
| `000004` | "Which drawer knob...storage chest" | target=`465347e8`(knob), anchor=`34ef21f3`(chest of drawers/dresser)。edge 存在 ✓。注意 anchor label 是 `chest of drawers / dresser`，query 说 "storage chest"，语义是否可接受？ | |
| `000013` | "Use the electric box...ceiling light" | target=`560e4272`(switch panel/electric outlet), anchor=`7a6d5c52`(ceiling light)。edge 存在 ✓。endpoint_ambiguity：两端都可交互，query 问控制器(switch)而非被控物(light)。scene 中 switch panel 只有 1 个 → `num_same_label_distractors=0` ✓ | |
| `000020` | "Turn the handle to open the window" | target=`1bcde871`(handle,z=383.090), anchor=`74f9d3c4`(window)。edge 存在 ✓。scene 有 2 个 handle，window 唯一，anchor 唯一确定 target | |

### Scene 421013（4条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000002` | "Which handle opens the door to exit the bedroom" | target=`5c383fa1`(handle,z=215.723), anchor=`2b27ebab`(door)。edge 存在 ✓。scene 有 9 个 handle，door 唯一。"exit the bedroom"：scene 是否确实是卧室？ | |
| `000012` | "Press the switch...ceiling light above the bed" | target=`eab8ec36`(light switch), anchor=`38486241`(ceiling light)。edge 存在 ✓。endpoint_ambiguity ✓。**注意**："above the bed" 是几何提示但无 `geometry_aware` tag，且 scene_graph_summary 里没有 "bed" 节点——这个描述能否唯一定位？ | |
| `000014` | "Grasp the **lowest** handle on the tall wardrobe" | target=`217402c7`(handle,z=**214.915**), anchor=`a00be285`(wardrobe)。4 个 handle 连到 wardrobe，z 排序：214.915 < 215.139 < 215.456 < 215.704 → target 确实 z 最小(最低) ✓ | |
| `000017` | "I need to rest...which furniture do I open to get pillows" | target=`7f13ad67`(handle), anchor=`600ca2b3`(dresser/nightstand)。edge 存在 ✓。hard_negative：query 不提 handle，靠语义推理。注意：scene 里有两个 nightstand 相关 anchor，答案用的是 `600ca2b3` 还是 `e810c10f`？ | |

### Scene 421254（3条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000009` | "Which remote controls the television" | target=`560f1e2c`(remote), anchor=`8bd6869b`(television)。**⚠️ 潜在问题**：scene 中 2 个 remote 都连到同一 TV。query 没有区分两个 remote 的方式，两个都可以是正确答案。 | ⚠️ |
| `000010` | "Pull the knob to open the nightstand drawer **on the left side**" | target=`ba0e4f26`(knob,x=**-0.446**), anchor=`762c6ae7`(dresser/nightstand)。edge 存在 ✓。"left side" 对应 x=-0.446，需确认坐标系中 x 小 = 左边。 | |
| `000019` | "Which electric outlet powers the bedside lamp" | target=`51097855`(electric outlet), anchor=`0ea8a987`(lamp)。edge 存在 ✓。scene 里 electric outlet 只有 1 个 → `is_label_only_solvable=true`，`num_same_label_distractors=0` ✓ | |

### Scene 421380（2条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000007` | "Find the knob that rotates to adjust the temperature on the radiator" | target=`44d68daa`(knob), anchor=`f422e864`(radiator)。edge 存在 ✓。scene 有 15 个 knob，只有 1 个连到 radiator → `num_same_label_distractors=14` ✓。**注意**：只有 `functional_relation` tag，但有 14 个同名 distractor——是否也应加 `same_label_disambiguation`？ | |
| `000016` | "Pull the **leftmost** knob on the television stand" | target=`bc40c514`(knob,x=**0.652**), anchor=`6e39c1ea`(television stand)。连到该 anchor 的 4 个 knob 的 x 坐标：0.652, 0.690, 1.848, 1.885 → target x=0.652 确实最小(leftmost) ✓。z_range=0.802 → 不用 upper/lower，用 leftmost 合适 ✓ | |

### Scene 421602（3条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000003` | "Rotate the handle to open the **top drawer** of the dresser" | target=`cde51d66`(handle,z=**170.741**), anchor=`f4e41b55`(dresser)。5 个 handle 连到该 anchor，z 排序：170.932 > **170.741** > 170.553 > 170.360 > 170.175。**⚠️ target z=170.741 不是最大**！"top drawer"→z 最大应是 `9fcd23c1`(z=170.932)，target 选的是第 2 高的 handle。**可能选错了！** | ⚠️ |
| `000008` | "Which handle opens the wooden cabinet near the window" | target=`31afb664`(handle,z=170.962), anchor=`631559ce`(cabinet/closet)。edge 存在 ✓。"near the window" 在 scene_graph_summary 里无法验证（需要可视化），暂时可接受 | |
| `000015` | "Pull the **bottom** handle of the dresser...lowest drawer" | target=`90e6a8bd`(handle,z=**170.191**), anchor=`340b66f3`(dresser)。3 个 handle 连到该 anchor：170.567 > 170.379 > **170.191** → target z=170.191 确实最小(lowest/bottom) ✓ | |

### Scene 469011（4条）

| 编号 | 简要 query | 核查要点 | 结论 |
|---|---|---|---|
| `000005` | "Locate the faucet handle that controls the water flow to the kitchen sink" | target=`4af16074`(faucet/handle), anchor=`19d41c11`(kitchen sink)。edge 存在 ✓。endpoint_ambiguity：faucet 和 sink 都可交互，query 问 faucet(控制器) ✓ | |
| `000006` | "Which electric outlet provides power to the **exhaust hood** above the stove" | target=`0146b63e`(electric outlet,z=-26.325), anchor=`3d0352ee`(exhaust hood)。edge 存在 ✓。scene 有 6 个 outlet，只有 1 个连到 exhaust hood。query 提到 "above the stove" 但无 `geometry_aware` tag——是否需要补充？ | |
| `000011` | "Find the knob that operates the dishwasher" | target=`ba5246d7`(knob), anchor=`af49702a`(dishwasher)。edge 存在 ✓。scene 有 19 个 knob，18 个干扰项。**⚠️ 只有 `functional_relation` tag，但有 18 个同名 distractor**——应否加 `same_label_disambiguation`？ | ⚠️ |
| `000018` | "To keep my food fresh, find the power source that keeps the refrigerator running" | target=`548a6569`(electric outlet), anchor=`7fddf637`(fridge)。edge 存在 ✓。hard_negative：完全不提 outlet，靠语义推理 ✓ | |

---

## 汇总：核查中发现的 3 个问题

### ⚠️ 问题 1（严重）：`000003` target 可能选错了

> 如果要修复，我感觉可以在后面的difficulty_tags加上geometry_aware！

```
query: "Rotate the handle to open the top drawer of the dresser"
anchor: f4e41b55 (dresser/chest of drawers)

连到该 anchor 的 5 个 handle（z 从大到小）:
  9fcd23c1  z=170.932  ← "top"应选这个
  cde51d66  z=170.741  ← 当前 target（第 2 高）← ❌
  7f9d7574  z=170.553
  70b0480d  z=170.360
  1fff26d6  z=170.175

建议：将 target_node_id 改为 9fcd23c1，或将 query 改为不说"top"
```

### ⚠️ 问题 2（中等）：`000009` 两个 remote 都是正确答案

```
scene 421254 中：
  560f1e2c (remote) → control → 8bd6869b (television)  ← target
  9c06f662 (remote) → control → 8bd6869b (television)  ← 也是正确答案

query "Which remote controls the television" 没有给出区分两个 remote 的方式。
建议：
  A. 补充几何描述区分（如"the remote on the left side of the TV stand"），或
  B. 将两个 remote 都列为 target（multi-answer），或
  C. 将 query 改为 same_label hard case 的"minimal pair"形式
```

### ⚠️ 问题 3（轻微）：`000007` 和 `000011` 缺少 `same_label_disambiguation` tag

```
000007: scene 421380，15 个 knob，num_same_label_distractors=14 → 应加 same_label_disambiguation
000011: scene 469011，19 个 knob，num_same_label_distractors=18 → 应加 same_label_disambiguation

这两条的 tag 只有 functional_relation，但实际上 same_label_disambiguation 的条件完全满足。
建议：difficulty_tags 各补充 "same_label_disambiguation"
```

---

## 核查完成后的操作

**发现问题后**，在 `annotation_notes.md` 末尾追加（不要直接改 jsonl，等 Mingqian 确认）：

```markdown
## ==Phase 1 人工核查记录 — YYYY-MM-DD==

[issue] query_id=000003  problem=target z=170.741 不是最高，"top drawer"应选 z=170.932 的 9fcd23c1
        suggested_fix=target_node_id 改为 9fcd23c1，或去掉 query 中的 "top"
        status=PENDING_MINGQIAN

[issue] query_id=000009  problem=两个 remote 都连到同一 TV，query 无法唯一确定答案
        suggested_fix=补充几何描述区分，或改为 multi-answer
        status=PENDING_MINGQIAN

[issue] query_id=000007  problem=有 14 个 same-label knob 但缺少 same_label_disambiguation tag
        suggested_fix=difficulty_tags 补充 "same_label_disambiguation"
        status=PENDING_MINGQIAN

[issue] query_id=000011  problem=有 18 个 same-label knob 但缺少 same_label_disambiguation tag
        suggested_fix=difficulty_tags 补充 "same_label_disambiguation"
        status=PENDING_MINGQIAN
```

## 数据齐全。==修复==方案:

| Query      | 问题                                                         | 修复                                                         |
| ---------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **000003** | target=`cde51d66`(z=170.741,第2高),"top drawer" 应选 z 最大的 | target → `9fcd23c1`(z=170.932,真正最高);retag 为 `geometry_aware`+`same_label_disambiguation`,加 `geometry_cues=["top"]` |
| **000007** | 14 个 same-label knob 但缺 `same_label_disambiguation` tag   | 加 tag                                                       |
| **000009** | 2 个 remote 都连同一 TV,query 无唯一答案。两 remote 仅 x 差 0.113m | ==加 "on the right-hand side"(target x=-0.330 > 9c06f662 x=-0.443)==;加 `geometry_aware` tag + `geometry_cues=["right"]` |
| **000011** | 18 个 same-label knob 但缺 `same_label_disambiguation` tag   | 加 tag                                                       |
