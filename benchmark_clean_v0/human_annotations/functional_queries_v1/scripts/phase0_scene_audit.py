"""Phase 0: Scene & Edge Selection Audit for Human Annotation Task.

Scans all SceneFun3D functional queries to identify which scenes are most
suitable for human annotation in Phase 1+. Outputs per-scene statistics
and a recommendation score (0-4) based on 4 selection criteria.

Outputs:
    scene_audit_v1.csv  - per-scene statistics
    (stdout)             - top scenes summary + sanity checks
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Script location:
#   benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/phase0_scene_audit.py
# parents[0]=scripts/, parents[1]=functional_queries_v1/,
# parents[2]=human_annotations/, parents[3]=benchmark_clean_v0/
BENCH_ROOT = Path(__file__).resolve().parents[3]
QUERY_INDEX = BENCH_ROOT / "queries" / "all_queries_index.jsonl"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
OUT_CSV = OUT_DIR / "scene_audit_v1.csv"

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

CSV_COLUMNS = [
    "scene_id",
    "n_functional_queries",
    "n_unique_edges",
    "n_actionable_targets",
    "n_same_label_groups",
    "max_same_label_count",
    "same_label_groups_detail",
    "n_endpoint_ambig_edges",
    "endpoint_ambig_edge_descs",
    "n_target_nodes",
    "n_anchor_nodes",
    "n_target_with_bbox",
    "target_bbox_rate",
    "n_anchor_with_bbox",
    "anchor_bbox_rate",
    "z_axis_range",
    "action_verb_dist",
    "top_edge_descs",
    "recommendation_score",
]


def load_functional_queries(path: Path) -> list[dict]:
    queries = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if q.get("dataset") == "scenefun3d" and q.get("query_type") == "functional":
                queries.append(q)
    return queries


def load_geometry(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def has_bbox(geom: dict, scene_id: str, node_id: str) -> bool:
    return scene_id in geom and node_id in geom[scene_id]


def parse_edge(edge_id: str | None):
    if not edge_id or "|" not in edge_id:
        return None
    parts = edge_id.split("|", 2)
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def compute_scene_stats(queries: list[dict], geom: dict) -> list[dict]:
    scenes: dict[str, dict] = {}

    def _init_scene():
        return {
            "queries": set(),
            "edges": {},
            "target_nodes": {},
            "anchor_nodes": {},
            "label_to_nodes": defaultdict(set),
            "action_counts": defaultdict(int),
            "edge_desc_counts": defaultdict(int),
        }

    for q in queries:
        sid = q["scene_id"]
        if sid not in scenes:
            scenes[sid] = _init_scene()
        s = scenes[sid]
        s["queries"].add(q["query_id"])

        if q.get("action_verb"):
            s["action_counts"][q["action_verb"]] += 1

        for edge_id in q.get("supporting_edge_ids") or []:
            parsed = parse_edge(edge_id)
            if parsed is None:
                continue
            _src, desc, _tgt = parsed
            s["edges"][edge_id] = desc
            s["edge_desc_counts"][desc] += 1

        for nid, lbl in zip(q.get("target_node_ids") or [], q.get("target_labels") or []):
            s["target_nodes"][nid] = lbl
            s["label_to_nodes"][lbl].add(nid)

        anchor_id = q.get("anchor_node_id")
        if anchor_id:
            anchor_lbl = ((q.get("anchor_labels") or [None])[0]) or "unknown"
            s["anchor_nodes"][anchor_id] = anchor_lbl
            s["label_to_nodes"][anchor_lbl].add(anchor_id)

    rows = []
    for scene_id, s in scenes.items():
        n_queries = len(s["queries"])
        n_unique_edges = len(s["edges"])

        actionable_targets = {
            nid: lbl for nid, lbl in s["target_nodes"].items()
            if lbl in ACTIONABLE_LABELS
        }
        n_actionable_targets = len(actionable_targets)

        same_label_groups = {
            lbl: len(nids) for lbl, nids in s["label_to_nodes"].items() if len(nids) >= 2
        }
        max_same_label_count = max(same_label_groups.values(), default=0)
        n_same_label_groups = len(same_label_groups)

        endpoint_ambig_edges = {
            eid: desc for eid, desc in s["edges"].items()
            if any(pat in desc for pat in ENDPOINT_AMBIG_EDGE_PATTERNS)
        }
        n_endpoint_ambig = len(endpoint_ambig_edges)

        n_target_total = len(s["target_nodes"])
        n_anchor_total = len(s["anchor_nodes"])
        n_target_with_bbox = sum(1 for nid in s["target_nodes"] if has_bbox(geom, scene_id, nid))
        n_anchor_with_bbox = sum(1 for nid in s["anchor_nodes"] if has_bbox(geom, scene_id, nid))
        target_bbox_rate = n_target_with_bbox / n_target_total if n_target_total else 0.0
        anchor_bbox_rate = n_anchor_with_bbox / n_anchor_total if n_anchor_total else 0.0

        z_vals = []
        if scene_id in geom:
            z_vals = [v["bbox_center"][2] for v in geom[scene_id].values()]
        z_range = max(z_vals) - min(z_vals) if len(z_vals) >= 2 else 0.0

        score = 0
        if n_unique_edges >= 5:
            score += 1
        if max_same_label_count >= 3:
            score += 1
        if n_endpoint_ambig >= 2:
            score += 1
        if target_bbox_rate >= 0.8:
            score += 1

        same_label_detail = "; ".join(
            f"{lbl}={cnt}" for lbl, cnt in sorted(same_label_groups.items(), key=lambda x: -x[1])
        )
        endpoint_descs = "; ".join(sorted(set(endpoint_ambig_edges.values())))
        action_dist = "; ".join(
            f"{k}={v}" for k, v in sorted(s["action_counts"].items(), key=lambda x: -x[1])
        )
        top_edges = "; ".join(
            f"{d}x{c}" for d, c in sorted(s["edge_desc_counts"].items(), key=lambda x: -x[1])[:3]
        )

        rows.append({
            "scene_id": scene_id,
            "n_functional_queries": n_queries,
            "n_unique_edges": n_unique_edges,
            "n_actionable_targets": n_actionable_targets,
            "n_same_label_groups": n_same_label_groups,
            "max_same_label_count": max_same_label_count,
            "same_label_groups_detail": same_label_detail,
            "n_endpoint_ambig_edges": n_endpoint_ambig,
            "endpoint_ambig_edge_descs": endpoint_descs,
            "n_target_nodes": n_target_total,
            "n_anchor_nodes": n_anchor_total,
            "n_target_with_bbox": n_target_with_bbox,
            "target_bbox_rate": round(target_bbox_rate, 3),
            "n_anchor_with_bbox": n_anchor_with_bbox,
            "anchor_bbox_rate": round(anchor_bbox_rate, 3),
            "z_axis_range": round(z_range, 3),
            "action_verb_dist": action_dist,
            "top_edge_descs": top_edges,
            "recommendation_score": score,
        })

    return rows


def write_scene_audit_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def print_summary(rows: list[dict]) -> None:
    n_total = len(rows)
    n_score4 = sum(1 for r in rows if r["recommendation_score"] == 4)
    n_score3 = sum(1 for r in rows if r["recommendation_score"] == 3)
    n_score2 = sum(1 for r in rows if r["recommendation_score"] == 2)
    n_score_lt2 = sum(1 for r in rows if r["recommendation_score"] < 2)

    print("=" * 88)
    print("Scene selection summary")
    print("=" * 88)
    print(f"  Total scenes with functional queries: {n_total}")
    print(f"  Scenes with score == 4 (perfect)    : {n_score4}")
    print(f"  Scenes with score == 3 (high)       : {n_score3}")
    print(f"  Scenes with score == 2 (medium)     : {n_score2}")
    print(f"  Scenes with score <  2 (low)        : {n_score_lt2}")
    print()
    print("Top scenes by recommendation_score (desc), then n_unique_edges (desc):")
    print()
    print(f"  {'scene_id':>10} | {'score':>5} | {'edges':>5} | {'queries':>7} | "
          f"{'max_sl':>6} | {'amb':>3} | {'tgt_bbox':>8} | {'z_range':>7}")
    print(f"  {'-'*10:>10} | {'-'*5:>5} | {'-'*5:>5} | {'-'*7:>7} | "
          f"{'-'*6:>6} | {'-'*3:>3} | {'-'*8:>8} | {'-'*7:>7}")
    for r in rows:
        print(f"  {r['scene_id']:>10} | {r['recommendation_score']:>5} | "
              f"{r['n_unique_edges']:>5} | {r['n_functional_queries']:>7} | "
              f"{r['max_same_label_count']:>6} | {r['n_endpoint_ambig_edges']:>3} | "
              f"{r['target_bbox_rate']:>8.3f} | {r['z_axis_range']:>7.3f}")


def run_sanity_checks(queries: list[dict], rows: list[dict]) -> int:
    """Returns non-zero count of failed checks."""
    failed = 0
    print()
    print("=" * 88)
    print("Sanity checks")
    print("=" * 88)

    n = len(queries)
    ok = n == 870
    print(f"  [CHECK 1] functional query count == 870           : got {n:>4}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    bad_dataset = sum(1 for q in queries if q.get("dataset") != "scenefun3d")
    ok = bad_dataset == 0
    print(f"  [CHECK 2] all dataset == 'scenefun3d'             : bad={bad_dataset:>4}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    n_scenes = len(rows)
    ok = n_scenes <= 23
    print(f"  [CHECK 3] scene count <= 23 (annotated OpenFunGraph): got {n_scenes:>3}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    bad_edges = 0
    for q in queries:
        for eid in (q.get("supporting_edge_ids") or []):
            if eid and len(eid.split("|")) != 3:
                bad_edges += 1
    ok = bad_edges == 0
    print(f"  [CHECK 4] all supporting_edge_id have 3 parts     : bad={bad_edges:>4}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    bad_sid = sum(1 for r in rows if not r["scene_id"].isdigit())
    ok = bad_sid == 0
    print(f"  [CHECK 5] all scene_id are numeric strings        : bad={bad_sid:>4}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    bad_score = sum(1 for r in rows if not (0 <= r["recommendation_score"] <= 4))
    ok = bad_score == 0
    print(f"  [CHECK 6] recommendation_score in [0, 4]          : bad={bad_score:>4}  "
          f"{'pass' if ok else 'FAIL'}")
    failed += int(not ok)

    print()
    return failed


def main() -> int:
    print(f"Loading queries from: {QUERY_INDEX}")
    queries = load_functional_queries(QUERY_INDEX)
    print(f"  Loaded {len(queries)} SceneFun3D functional queries")

    print(f"Loading geometry from: {GEOM_PATH}")
    geom = load_geometry(GEOM_PATH)
    n_geom_nodes = sum(len(v) for v in geom.values())
    print(f"  Loaded {len(geom)} scenes, {n_geom_nodes} nodes with bbox")
    print()

    rows = compute_scene_stats(queries, geom)
    rows.sort(key=lambda r: (-r["recommendation_score"], -r["n_unique_edges"]))

    write_scene_audit_csv(rows, OUT_CSV)
    print(f"Wrote {len(rows)} rows to: {OUT_CSV}")
    print()

    print_summary(rows)
    failed = run_sanity_checks(queries, rows)
    print(f"Sanity checks failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
