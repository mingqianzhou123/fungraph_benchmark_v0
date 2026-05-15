"""Phase 1: Scene Graph Explorer for Human Annotation.

读取 scenefun3d_funrag_benchmark_enriched.json，对 6 个选中 scene 输出：
  - 所有节点（node_id, label, bbox_center）
  - 所有功能边（edge_id, source_label, relation, target_label）
  - 同名节点分组（用于 same_label_disambiguation，过滤掉 unknown 标签）

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

    lines.append(f"{'='*80}")
    lines.append(f"SCENE {scene_id}  ({len(nodes)} nodes, {len(edges)} edges)")
    lines.append(f"{'='*80}")

    # ---- 节点表 ----
    lines.append("")
    lines.append("NODES:")
    lines.append(f"  {'node_id':38s}  {'label':30s}  {'z':>10}  {'x':>10}  {'y':>10}")
    lines.append(f"  {'-'*38}  {'-'*30}  {'-'*10}  {'-'*10}  {'-'*10}")
    for n in sorted(nodes, key=lambda x: (x["label"], x["node_id"])):
        nid = n["node_id"]
        lbl = n["label"]
        g = scene_geom.get(nid, {})
        cx, cy, cz = g.get("bbox_center", [None, None, None])
        z_str = f"{cz:10.3f}" if cz is not None else f"{'NO_GEOM':>10}"
        x_str = f"{cx:10.3f}" if cx is not None else f"{'':>10}"
        y_str = f"{cy:10.3f}" if cy is not None else f"{'':>10}"
        lines.append(f"  {nid:38s}  {lbl:30s}  {z_str}  {x_str}  {y_str}")

    # ---- 同名节点分组（过滤掉 unknown）----
    label_to_nodes: dict[str, list] = defaultdict(list)
    for n in nodes:
        lbl = n["label"]
        if lbl != "unknown":  # 关键修正：过滤 unknown 标签
            label_to_nodes[lbl].append(n["node_id"])

    same_label = {lbl: nids for lbl, nids in label_to_nodes.items() if len(nids) >= 2}
    if same_label:
        lines.append("")
        lines.append("SAME-LABEL GROUPS (distractor candidates, unknown excluded):")
        for lbl, nids in sorted(same_label.items(), key=lambda x: -len(x[1])):
            lines.append(f"  [{lbl}]  count={len(nids)}")
            for nid in sorted(nids):
                g = scene_geom.get(nid, {})
                cx, cy, cz = g.get("bbox_center", [None, None, None])
                z_str = f"z={cz:.3f}" if cz is not None else "z=NO_GEOM"
                x_str = f"x={cx:.3f}" if cx is not None else ""
                lines.append(f"    {nid}  {z_str}  {x_str}")

    # ---- 边表（按 relation 排序）----
    lines.append("")
    lines.append("EDGES:")
    lines.append(f"  {'source_label':30s}  {'relation':45s}  {'target_label':30s}")
    lines.append(f"  {'-'*30}  {'-'*45}  {'-'*30}")
    for e in sorted(edges, key=lambda x: (x["relation"], x.get("source_label", "?"))):
        lines.append(
            f"  {e.get('source_label', '?'):30s}  {e['relation']:45s}  {e.get('target_label', '?'):30s}"
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
