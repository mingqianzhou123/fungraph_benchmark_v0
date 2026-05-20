"""Phase 3 minimal-pair candidate miner.

Scan all human-authored queries (pilot_20_queries.jsonl + functional_queries_v1.jsonl)
and surface candidate minimal pairs for human review.

Outputs `pair_candidates_v1.csv` with one row per candidate pair. Each row marks the
candidate_type (spatial_qualifier / anchor_object / functional_relation) and the
fields that match/differ, so a human can filter to true minimal pairs (Step 1 in
phase3.md). The miner does NOT emit `geometry_direction` — that subclass is decided
during human review (phase3.md "geometry_direction is a subset of spatial_qualifier").

The miner is conservative: it enumerates every unordered pair within a group, even
when n is large. Step 1 human review prunes to ~20 pairs.
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
QUERY_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_CSV = QUERY_DIR / "pair_candidates_v1.csv"

QUERY_FILES = [
    "pilot_20_queries.jsonl",
    "functional_queries_v1.jsonl",
]

CSV_COLUMNS = [
    "candidate_type",
    "scene_id",
    "target_label",
    "shared_relation",
    "query_a_id",
    "query_b_id",
    "target_a_node_id",
    "target_b_node_id",
    "anchor_a_node_id",
    "anchor_b_node_id",
    "a_geometry_cues",
    "b_geometry_cues",
    "target_a_xyz",
    "target_b_xyz",
    "target_geom_diff_m",
    "review_status",
    "review_notes",
]


def load_queries() -> list[dict]:
    queries = []
    for fname in QUERY_FILES:
        path = QUERY_DIR / fname
        if not path.exists():
            print(f"WARN: {path} not found, skipping")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                queries.append(json.loads(line))
    return queries


def load_geometry() -> dict:
    with GEOM_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def edge_relation(q: dict) -> str:
    edges = q.get("supporting_edge_ids") or []
    if not edges:
        return ""
    parts = edges[0].split("|", 2)
    return parts[1] if len(parts) >= 2 else ""


def bbox_center(geom: dict, scene_id: str, node_id: str) -> tuple[float, float, float] | None:
    s = geom.get(scene_id, {})
    n = s.get(node_id, {})
    c = n.get("bbox_center")
    return tuple(c) if c else None


def fmt_xyz(c: tuple | None) -> str:
    if c is None:
        return ""
    return f"{c[0]:.3f},{c[1]:.3f},{c[2]:.3f}"


def euclid(a: tuple | None, b: tuple | None) -> float | None:
    if a is None or b is None:
        return None
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def mine_spatial_qualifier(queries: list[dict], geom: dict) -> list[dict]:
    """Same scene + target_label + anchor + relation, different target_node_id."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for q in queries:
        key = (
            q["scene_id"],
            q.get("target_label", ""),
            q.get("anchor_node_id", ""),
            edge_relation(q),
        )
        groups[key].append(q)

    rows: list[dict] = []
    for key, qs in sorted(groups.items()):
        if len(qs) < 2:
            continue
        # Only emit pairs with distinct target_node_id.
        for a, b in combinations(qs, 2):
            if a["target_node_id"] == b["target_node_id"]:
                continue
            ca = bbox_center(geom, key[0], a["target_node_id"])
            cb = bbox_center(geom, key[0], b["target_node_id"])
            d = euclid(ca, cb)
            rows.append({
                "candidate_type": "spatial_qualifier",
                "scene_id": key[0],
                "target_label": key[1],
                "shared_relation": key[3],
                "query_a_id": a["query_id"],
                "query_b_id": b["query_id"],
                "target_a_node_id": a["target_node_id"],
                "target_b_node_id": b["target_node_id"],
                "anchor_a_node_id": key[2],
                "anchor_b_node_id": key[2],
                "a_geometry_cues": ";".join(a.get("geometry_cues", []) or []),
                "b_geometry_cues": ";".join(b.get("geometry_cues", []) or []),
                "target_a_xyz": fmt_xyz(ca),
                "target_b_xyz": fmt_xyz(cb),
                "target_geom_diff_m": f"{d:.3f}" if d is not None else "",
                "review_status": "pending",
                "review_notes": "",
            })
    return rows


def mine_anchor_object(queries: list[dict], geom: dict) -> list[dict]:
    """Same scene + target_label + relation, different anchor, different target."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for q in queries:
        key = (q["scene_id"], q.get("target_label", ""), edge_relation(q))
        groups[key].append(q)

    rows: list[dict] = []
    for key, qs in sorted(groups.items()):
        if len(qs) < 2:
            continue
        for a, b in combinations(qs, 2):
            anchor_a = a.get("anchor_node_id", "")
            anchor_b = b.get("anchor_node_id", "")
            # Must differ in anchor AND target.
            if anchor_a == anchor_b:
                continue
            if a["target_node_id"] == b["target_node_id"]:
                continue
            ca = bbox_center(geom, key[0], a["target_node_id"])
            cb = bbox_center(geom, key[0], b["target_node_id"])
            d = euclid(ca, cb)
            rows.append({
                "candidate_type": "anchor_object",
                "scene_id": key[0],
                "target_label": key[1],
                "shared_relation": key[2],
                "query_a_id": a["query_id"],
                "query_b_id": b["query_id"],
                "target_a_node_id": a["target_node_id"],
                "target_b_node_id": b["target_node_id"],
                "anchor_a_node_id": anchor_a,
                "anchor_b_node_id": anchor_b,
                "a_geometry_cues": ";".join(a.get("geometry_cues", []) or []),
                "b_geometry_cues": ";".join(b.get("geometry_cues", []) or []),
                "target_a_xyz": fmt_xyz(ca),
                "target_b_xyz": fmt_xyz(cb),
                "target_geom_diff_m": f"{d:.3f}" if d is not None else "",
                "review_status": "pending",
                "review_notes": "",
            })
    return rows


def mine_functional_relation(queries: list[dict], geom: dict) -> list[dict]:
    """Same scene + target_label + anchor, different relation, different target."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for q in queries:
        key = (q["scene_id"], q.get("target_label", ""), q.get("anchor_node_id", ""))
        groups[key].append(q)

    rows: list[dict] = []
    for key, qs in sorted(groups.items()):
        if len(qs) < 2:
            continue
        for a, b in combinations(qs, 2):
            rel_a = edge_relation(a)
            rel_b = edge_relation(b)
            if rel_a == rel_b:
                continue
            if a["target_node_id"] == b["target_node_id"]:
                continue
            ca = bbox_center(geom, key[0], a["target_node_id"])
            cb = bbox_center(geom, key[0], b["target_node_id"])
            d = euclid(ca, cb)
            rows.append({
                "candidate_type": "functional_relation",
                "scene_id": key[0],
                "target_label": key[1],
                "shared_relation": f"{rel_a} || {rel_b}",
                "query_a_id": a["query_id"],
                "query_b_id": b["query_id"],
                "target_a_node_id": a["target_node_id"],
                "target_b_node_id": b["target_node_id"],
                "anchor_a_node_id": key[2],
                "anchor_b_node_id": key[2],
                "a_geometry_cues": ";".join(a.get("geometry_cues", []) or []),
                "b_geometry_cues": ";".join(b.get("geometry_cues", []) or []),
                "target_a_xyz": fmt_xyz(ca),
                "target_b_xyz": fmt_xyz(cb),
                "target_geom_diff_m": f"{d:.3f}" if d is not None else "",
                "review_status": "pending",
                "review_notes": "",
            })
    return rows


def main() -> None:
    queries = load_queries()
    geom = load_geometry()
    print(f"Loaded {len(queries)} queries from {len(QUERY_FILES)} files")

    spatial = mine_spatial_qualifier(queries, geom)
    anchor = mine_anchor_object(queries, geom)
    func = mine_functional_relation(queries, geom)

    print(f"Candidates: spatial_qualifier={len(spatial)}, "
          f"anchor_object={len(anchor)}, functional_relation={len(func)}")

    # Pre-sort: smaller geom diff last (later candidates likely more nuanced);
    # group rows by type then scene then a_id.
    all_rows = spatial + anchor + func
    all_rows.sort(key=lambda r: (
        r["candidate_type"],
        r["scene_id"],
        r["query_a_id"],
        r["query_b_id"],
    ))

    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} candidates to {OUT_CSV}")

    # Stdout breakdown per scene + type
    bucket: dict[tuple, int] = defaultdict(int)
    for r in all_rows:
        bucket[(r["candidate_type"], r["scene_id"])] += 1
    print()
    print("Breakdown by (type, scene):")
    for (t, s), c in sorted(bucket.items()):
        print(f"  {t:22s} scene={s}  {c} pairs")


if __name__ == "__main__":
    main()
