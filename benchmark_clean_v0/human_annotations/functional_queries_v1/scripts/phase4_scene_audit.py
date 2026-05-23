"""Phase 4: Junction Audit for Long-Range Stress Set.

Scans all 20 SceneFun3D scenes for junction patterns suitable for Phase 4
junction-2hop queries. A *strong junction* is an appliance/container node v
with incoming-degree >= 2, where at least one pair of incoming edges has
distinct (source_label, relation) — i.e., not two knobs doing the same
"pull to open" on the same cabinet (that would be paraphrase灌水).

Per phase4.md:
  - Default pattern: target -> shared_anchor <- reference (junction_2hop)
  - 3+ hop chains: rare in bipartite topology; still scanned for completeness
    (e.g., 421267/466803 power strip reverse-direction edges)

Outputs:
    phase4_junction_audit.csv     - one row per (scene, anchor, edge_a, edge_b)
    phase4_audit_summary.txt      - per-scene summary + chain detection
    (stdout)                       - top junctions and sanity checks
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
ENRICH_PATH = BENCH_ROOT / "queries" / "scenefun3d_funrag_benchmark_enriched.json"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
OUT_CSV = OUT_DIR / "phase4_junction_audit.csv"
OUT_TXT = OUT_DIR / "phase4_audit_summary.txt"

CSV_COLUMNS = [
    "scene_id",
    "anchor_node_id",
    "anchor_label",
    "n_incoming",
    "n_distinct_source_labels",
    "n_distinct_relations",
    "edge_a_id",
    "edge_a_source_label",
    "edge_a_relation",
    "edge_a_source_node_id",
    "edge_b_id",
    "edge_b_source_label",
    "edge_b_relation",
    "edge_b_source_node_id",
    "pair_distinct_kind",  # "src+rel" / "src" / "rel"
    "target_3d_distance_m",  # distance(edge_a_source, edge_b_source)
    "anchor_target_distance_m",  # distance(anchor, edge_a_source)
    "writable_score",  # 1=strong (src+rel both differ); 0.5=partial
]


def load_scene_graphs(path: Path) -> dict[str, dict]:
    """Load enriched JSON, dedup by scene_id. Returns {scene_id: scene_graph}."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    scene_graphs: dict[str, dict] = {}
    for item in data["data"]:
        sid = item["scene_id"]
        if sid not in scene_graphs and item.get("scene_graph"):
            scene_graphs[sid] = item["scene_graph"]
    return scene_graphs


def load_geometry(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_edge_id(edge_id: str) -> tuple[str, str, str]:
    """edge_id format: '<src_uuid>|<relation>|<tgt_uuid>' — relation may contain commas/spaces."""
    parts = edge_id.split("|")
    if len(parts) != 3:
        raise ValueError(f"Unexpected edge_id format: {edge_id}")
    return parts[0], parts[1], parts[2]


def euclidean(p1: list, p2: list) -> float:
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2) ** 0.5


def audit_scene(scene_id: str, sg: dict, geom: dict) -> tuple[list[dict], dict]:
    """Return (junction_rows, summary_dict) for one scene.

    junction_rows: list of CSV row dicts, one per (anchor, edge_a, edge_b) writable pair.
    summary_dict: {n_nodes, n_edges, n_junctions, n_writable_pairs, chain_candidates, top_anchors}
    """
    nodes = sg.get("nodes", [])
    edges = sg.get("edges", [])
    nid_to_label = {n["node_id"]: n["label"] for n in nodes}
    scene_geom = geom.get(scene_id, {})

    # Group edges by tgt_uuid (incoming-degree per anchor candidate)
    incoming: dict[str, list[dict]] = defaultdict(list)
    outgoing: dict[str, list[dict]] = defaultdict(list)
    for e in edges:
        src, rel, tgt = parse_edge_id(e["edge_id"])
        record = {
            "edge_id": e["edge_id"],
            "src_uuid": src,
            "src_label": e.get("source_label", nid_to_label.get(src, "unknown")),
            "relation": rel,
            "tgt_uuid": tgt,
            "tgt_label": e.get("target_label", nid_to_label.get(tgt, "unknown")),
        }
        incoming[tgt].append(record)
        outgoing[src].append(record)

    rows: list[dict] = []
    anchor_writable_counts: dict[str, int] = {}

    for anchor_uuid, in_edges in incoming.items():
        if len(in_edges) < 2:
            continue
        anchor_label = nid_to_label.get(anchor_uuid, "unknown")
        if anchor_label == "unknown":
            # unknown anchor label — query_text 无法自然描述，跳过
            continue

        # Compute distinct counts
        src_labels = {e["src_label"] for e in in_edges}
        relations = {e["relation"] for e in in_edges}

        # Enumerate writable pairs: (e1, e2) where (src_label, relation) tuple differs
        # Avoid two same (src_label, relation) edges (would be paraphrase灌水)
        n = len(in_edges)
        writable = 0
        for i in range(n):
            for j in range(i + 1, n):
                e1, e2 = in_edges[i], in_edges[j]
                src_diff = e1["src_label"] != e2["src_label"]
                rel_diff = e1["relation"] != e2["relation"]
                if not (src_diff or rel_diff):
                    continue  # same (src_label, relation) — paraphrase灌水
                # Distinct UUIDs check
                if e1["src_uuid"] == e2["src_uuid"]:
                    continue  # same source node (shouldn't happen in bipartite)
                writable += 1

                # Compute geometry distances if available
                t3d = None
                ata = None
                g_a = scene_geom.get(e1["src_uuid"], {}).get("bbox_center")
                g_b = scene_geom.get(e2["src_uuid"], {}).get("bbox_center")
                g_anchor = scene_geom.get(anchor_uuid, {}).get("bbox_center")
                if g_a and g_b:
                    t3d = round(euclidean(g_a, g_b), 3)
                if g_anchor and g_a:
                    ata = round(euclidean(g_anchor, g_a), 3)

                if src_diff and rel_diff:
                    kind, score = "src+rel", 1.0
                elif src_diff:
                    kind, score = "src", 0.7
                else:
                    kind, score = "rel", 0.7

                rows.append({
                    "scene_id": scene_id,
                    "anchor_node_id": anchor_uuid,
                    "anchor_label": anchor_label,
                    "n_incoming": len(in_edges),
                    "n_distinct_source_labels": len(src_labels),
                    "n_distinct_relations": len(relations),
                    "edge_a_id": e1["edge_id"],
                    "edge_a_source_label": e1["src_label"],
                    "edge_a_relation": e1["relation"],
                    "edge_a_source_node_id": e1["src_uuid"],
                    "edge_b_id": e2["edge_id"],
                    "edge_b_source_label": e2["src_label"],
                    "edge_b_relation": e2["relation"],
                    "edge_b_source_node_id": e2["src_uuid"],
                    "pair_distinct_kind": kind,
                    "target_3d_distance_m": t3d if t3d is not None else "",
                    "anchor_target_distance_m": ata if ata is not None else "",
                    "writable_score": score,
                })
        if writable > 0:
            anchor_writable_counts[anchor_uuid] = writable

    # Scan for 3+ hop chain candidates: any node v that has BOTH in-degree>=1 AND out-degree>=1
    chain_bridges: list[dict] = []
    all_nids = set(incoming.keys()) | set(outgoing.keys())
    for nid in all_nids:
        if nid in incoming and nid in outgoing:
            chain_bridges.append({
                "bridge_node_id": nid,
                "bridge_label": nid_to_label.get(nid, "unknown"),
                "in_edges": [e["edge_id"] for e in incoming[nid]],
                "out_edges": [e["edge_id"] for e in outgoing[nid]],
            })

    summary = {
        "scene_id": scene_id,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_junctions": len(anchor_writable_counts),
        "n_writable_pairs": sum(anchor_writable_counts.values()),
        "chain_candidates": chain_bridges,
        "top_anchors": sorted(
            [(nid_to_label.get(a, "?"), w) for a, w in anchor_writable_counts.items()],
            key=lambda x: -x[1],
        )[:5],
    }
    return rows, summary


def main():
    if not ENRICH_PATH.exists():
        sys.exit(f"ERROR: enriched JSON not found: {ENRICH_PATH}")
    if not GEOM_PATH.exists():
        sys.exit(f"ERROR: geometry JSON not found: {GEOM_PATH}")

    scene_graphs = load_scene_graphs(ENRICH_PATH)
    geom = load_geometry(GEOM_PATH)
    print(f"Loaded {len(scene_graphs)} scene graphs from enriched JSON")
    print(f"Loaded geometry for {len(geom)} scenes")

    all_rows: list[dict] = []
    all_summaries: list[dict] = []

    for sid in sorted(scene_graphs):
        rows, summary = audit_scene(sid, scene_graphs[sid], geom)
        all_rows.extend(rows)
        all_summaries.append(summary)

    # Write CSV
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} junction candidate rows to {OUT_CSV.name}")

    # Write summary TXT
    summary_lines: list[str] = []
    summary_lines.append("=" * 80)
    summary_lines.append("Phase 4 Junction Audit Summary")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    summary_lines.append(f"Total scenes audited     : {len(all_summaries)}")
    summary_lines.append(f"Total junctions found    : {sum(s['n_junctions'] for s in all_summaries)}")
    summary_lines.append(f"Total writable pairs     : {sum(s['n_writable_pairs'] for s in all_summaries)}")
    summary_lines.append(
        f"Scenes with >=1 junction : "
        f"{sum(1 for s in all_summaries if s['n_junctions'] > 0)}"
    )
    summary_lines.append(
        f"Total chain bridges      : {sum(len(s['chain_candidates']) for s in all_summaries)}"
    )
    summary_lines.append("")

    # Per-scene table
    summary_lines.append("Per-scene summary:")
    summary_lines.append(
        f"  {'scene':>8}  {'nodes':>5}  {'edges':>5}  "
        f"{'n_junc':>6}  {'n_pairs':>7}  {'n_chain':>7}  top_anchors"
    )
    summary_lines.append(f"  {'-'*8}  {'-'*5}  {'-'*5}  {'-'*6}  {'-'*7}  {'-'*7}  ----")
    for s in sorted(all_summaries, key=lambda x: -x["n_writable_pairs"]):
        top = ", ".join(f"{lbl}({n})" for lbl, n in s["top_anchors"])
        summary_lines.append(
            f"  {s['scene_id']:>8}  "
            f"{s['n_nodes']:>5}  {s['n_edges']:>5}  "
            f"{s['n_junctions']:>6}  {s['n_writable_pairs']:>7}  "
            f"{len(s['chain_candidates']):>7}  {top}"
        )

    summary_lines.append("")

    # Chain candidates detail
    summary_lines.append("Chain candidates (nodes with both in-edge AND out-edge):")
    chain_total = 0
    for s in all_summaries:
        if s["chain_candidates"]:
            for cc in s["chain_candidates"]:
                chain_total += 1
                summary_lines.append(
                    f"  scene={s['scene_id']}  bridge_label={cc['bridge_label']}  "
                    f"node_id={cc['bridge_node_id']}  "
                    f"in={len(cc['in_edges'])}  out={len(cc['out_edges'])}"
                )
    if chain_total == 0:
        summary_lines.append("  (none — bipartite topology confirmed)")
    summary_lines.append("")

    # Strong-junction detail per scene (writable score = 1.0)
    summary_lines.append("Strong-junction detail (writable_score=1.0, src+rel both differ):")
    strong_by_scene: dict[str, list[dict]] = defaultdict(list)
    for r in all_rows:
        if r["writable_score"] == 1.0:
            strong_by_scene[r["scene_id"]].append(r)
    for sid in sorted(strong_by_scene):
        rows = strong_by_scene[sid]
        anchors = defaultdict(list)
        for r in rows:
            anchors[(r["anchor_node_id"], r["anchor_label"])].append(r)
        summary_lines.append(f"  scene={sid}  ({len(rows)} strong pairs)")
        for (anchor_uuid, anchor_label), arows in anchors.items():
            summary_lines.append(
                f"    anchor={anchor_label} ({anchor_uuid[:8]}..)  {len(arows)} pairs"
            )
            for r in arows[:3]:  # show first 3 per anchor
                summary_lines.append(
                    f"      {r['edge_a_source_label']} --{r['edge_a_relation']}--> _  "
                    f"vs  {r['edge_b_source_label']} --{r['edge_b_relation']}--> _  "
                    f"src_dist={r['target_3d_distance_m']}m"
                )
            if len(arows) > 3:
                summary_lines.append(f"      ... +{len(arows) - 3} more")
    summary_lines.append("")

    OUT_TXT.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote summary to {OUT_TXT.name}")

    # Stdout: print key sanity checks
    print()
    print("Sanity checks:")
    print(f"  - {sum(1 for s in all_summaries if s['n_junctions'] > 0)} / "
          f"{len(all_summaries)} scenes have >=1 junction")
    print(f"  - {sum(s['n_writable_pairs'] for s in all_summaries)} writable pairs total")
    strong_total = sum(1 for r in all_rows if r["writable_score"] == 1.0)
    print(f"  - {strong_total} strong pairs (writable_score=1.0)")
    print(f"  - {chain_total} chain bridges (3+ hop candidates)")

    expected_known_junctions = {
        "469011": ["oven", "fridge"],  # known strong junctions
        "421380": ["television stand / cabinet"],  # known partial junction
    }
    print()
    print("Spot-check known scenes:")
    for sid, expected_labels in expected_known_junctions.items():
        scene_rows = [r for r in all_rows if r["scene_id"] == sid]
        found_anchors = {r["anchor_label"] for r in scene_rows}
        for lbl in expected_labels:
            status = "OK" if lbl in found_anchors else "MISSING"
            print(f"  scene={sid}  expected anchor={lbl!r}  ->  {status}")


if __name__ == "__main__":
    main()
