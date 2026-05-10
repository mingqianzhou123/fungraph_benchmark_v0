"""Phase 1: Geometry Coverage Audit for SceneFun3D queries.

Reads (read-only):
  - benchmark_clean_v0/queries/all_queries_index.jsonl
  - benchmark_clean_v0/geometry/scenefun3d_node_geom.json
  - benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json

Writes:
  - benchmark_clean_v0/multimodal_extension/geometry_coverage_report.csv
  - benchmark_clean_v0/multimodal_extension/target_anchor_geometry_coverage.csv
  - benchmark_clean_v0/multimodal_extension/coverage_summary.json

Usage:
  python phase1_coverage_audit.py
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent       # multimodal_extension/scripts/
EXT_DIR    = SCRIPT_DIR.parent                      # multimodal_extension/
REPO_ROOT  = EXT_DIR.parent                         # benchmark_clean_v0/

QUERY_INDEX = REPO_ROOT / "queries"  / "all_queries_index.jsonl"
GEOM_PATH   = REPO_ROOT / "geometry" / "scenefun3d_node_geom.json"
ENRICHED    = REPO_ROOT / "queries"  / "scenefun3d_funrag_benchmark_enriched.json"

OUT_REPORT_CSV   = EXT_DIR / "geometry_coverage_report.csv"
OUT_SUMMARY_CSV  = EXT_DIR / "target_anchor_geometry_coverage.csv"
OUT_SUMMARY_JSON = EXT_DIR / "coverage_summary.json"

# --- Gate thresholds (from phase.md / phase1.md) ---
GATE_TARGET_THRESHOLD = 0.70
GATE_EDGE_THRESHOLD   = 0.65


# =============================================================================
# Loaders
# =============================================================================
def load_queries(path: Path) -> list[dict]:
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_geom(path: Path) -> dict[str, dict[str, dict]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _iter_enriched_items(enriched: Any) -> Iterable[dict]:
    """Yield query-like dicts from the enriched file.

    The actual top-level shape is ``{"metadata": {...}, "data": [...]}`` (the
    ``data`` list contains 1485 query dicts, each with a ``scene_graph`` field).
    Other shapes are tolerated for safety.
    """
    if isinstance(enriched, list):
        for item in enriched:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(enriched, dict):
        for key in ("data", "queries"):
            if key in enriched and isinstance(enriched[key], list):
                for item in enriched[key]:
                    if isinstance(item, dict):
                        yield item
                return
        # Fallback: dict-of-dicts
        for item in enriched.values():
            if isinstance(item, dict):
                yield item


def build_scene_label_map(enriched_path: Path) -> dict[str, dict[str, list[str]]]:
    """Return ``{scene_id: {label: [node_ids_sorted]}}``.

    The enriched file embeds ``scene_graph.nodes`` per query; the same node
    may be repeated across queries from the same scene. We deduplicate by
    node_id and keep the first label seen.
    """
    with open(enriched_path, "r", encoding="utf-8") as f:
        enriched = json.load(f)

    # scene_id -> {node_id: label}
    scene_to_nodes: dict[str, dict[str, str]] = defaultdict(dict)

    for item in _iter_enriched_items(enriched):
        scene_id = item.get("scene_id")
        if not scene_id:
            continue
        scene_graph = item.get("scene_graph") or {}
        nodes = scene_graph.get("nodes") or []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = node.get("node_id")
            label   = node.get("label")
            if node_id and label:
                scene_to_nodes[scene_id].setdefault(node_id, label)

    # Reorganize to scene_id -> {label: [node_ids]}; sort node_ids for reproducibility
    scene_label_to_nodes: dict[str, dict[str, list[str]]] = {}
    for scene_id, node_label_map in scene_to_nodes.items():
        per_label: dict[str, list[str]] = defaultdict(list)
        for node_id, label in node_label_map.items():
            per_label[label].append(node_id)
        scene_label_to_nodes[scene_id] = {
            label: sorted(nids) for label, nids in per_label.items()
        }
    return scene_label_to_nodes


# =============================================================================
# Helpers
# =============================================================================
def parse_supporting_edge(edge_id: str | None) -> tuple[str, str, str] | None:
    """Parse ``"src|relation|tgt"``. Returns None if input is empty/malformed."""
    if not edge_id:
        return None
    parts = edge_id.split("|", 2)
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def has_bbox(geom: dict, scene_id: str, node_id: str) -> bool:
    return (scene_id in geom) and (node_id in geom[scene_id])


# =============================================================================
# Per-query record
# =============================================================================
def compute_query_record(
    q: dict,
    geom: dict,
    scene_label_to_nodes: dict[str, dict[str, list[str]]],
) -> dict:
    scene_id           = q.get("scene_id", "")
    target_node_ids    = q.get("target_node_ids") or []
    target_labels      = q.get("target_labels") or []
    anchor_node_id     = q.get("anchor_node_id")
    supporting_edge_id = q.get("supporting_edge_id")

    scene_in_geom = scene_id in geom

    # Target coverage (multi-target: ALL must have bbox)
    target_count = len(target_node_ids)
    if target_count == 0:
        target_has_bbox = False
        target_any_has_bbox = False
    else:
        bbox_flags = [has_bbox(geom, scene_id, nid) for nid in target_node_ids]
        target_has_bbox     = all(bbox_flags)
        target_any_has_bbox = any(bbox_flags)

    # Anchor coverage (only the singular anchor_node_id)
    anchor_applicable = bool(anchor_node_id)
    anchor_covered    = bool(anchor_applicable and has_bbox(geom, scene_id, anchor_node_id))

    # Supporting edge endpoint coverage
    supporting_edge_applicable = bool(supporting_edge_id)
    edge_src_covered  = False
    edge_tgt_covered  = False
    edge_both_covered = False
    if supporting_edge_applicable:
        parsed = parse_supporting_edge(supporting_edge_id)
        if parsed is not None:
            src, _rel, tgt = parsed
            edge_src_covered  = has_bbox(geom, scene_id, src)
            edge_tgt_covered  = has_bbox(geom, scene_id, tgt)
            edge_both_covered = edge_src_covered and edge_tgt_covered

    target_and_anchor_both_covered = bool(target_has_bbox and anchor_applicable and anchor_covered)

    # Same-label distractor analysis (use first target_label)
    target_label = target_labels[0] if target_labels else None
    same_label_nodes = (
        scene_label_to_nodes.get(scene_id, {}).get(target_label, []) if target_label else []
    )
    same_label_count = len(same_label_nodes)
    has_same_label_distractor = same_label_count >= 2
    same_label_with_bbox_count = sum(
        1 for nid in same_label_nodes if has_bbox(geom, scene_id, nid)
    )

    # Missing reason (categories overlap; documented in handoff notes)
    reasons: list[str] = []
    if not scene_in_geom:
        reasons.append("scene_not_in_geom")
    if target_count > 0 and not target_has_bbox:
        reasons.append("missing_target")
    if anchor_applicable and not anchor_covered:
        reasons.append("missing_anchor")
    if supporting_edge_applicable:
        if not edge_src_covered:
            reasons.append("missing_edge_src")
        if not edge_tgt_covered:
            reasons.append("missing_edge_tgt")
    missing_reason = ",".join(reasons) if reasons else "none"

    return {
        "query_id":   q.get("query_id", ""),
        "scene_id":   scene_id,
        "split":      q.get("split", ""),
        "query_type": q.get("query_type", ""),
        "dataset":    q.get("dataset", ""),
        "target_node_ids":    "|".join(target_node_ids),
        "target_labels":      "|".join(target_labels),
        "anchor_node_id":     anchor_node_id or "",
        "supporting_edge_id": supporting_edge_id or "",
        "target_count":       target_count,
        "target_has_bbox":               target_has_bbox,
        "target_any_has_bbox":           target_any_has_bbox,
        "anchor_applicable":             anchor_applicable,
        "anchor_has_bbox":               anchor_covered,
        "supporting_edge_applicable":    supporting_edge_applicable,
        "supporting_edge_src_has_bbox":  edge_src_covered,
        "supporting_edge_tgt_has_bbox":  edge_tgt_covered,
        "supporting_edge_both_have_bbox": edge_both_covered,
        "target_and_anchor_both_covered": target_and_anchor_both_covered,
        "same_label_count":              same_label_count,
        "has_same_label_distractor":     has_same_label_distractor,
        "same_label_with_bbox_count":    same_label_with_bbox_count,
        "missing_reason":                missing_reason,
    }


# =============================================================================
# Aggregation
# =============================================================================
def aggregate(records: list[dict]) -> dict:
    """Compute split x query_type coverage matrix (with ALL totals)."""
    splits_present = sorted({r["split"] for r in records})
    qtypes_present = sorted({r["query_type"] for r in records})
    splits_full    = splits_present + ["ALL"]
    qtypes_full    = qtypes_present + ["ALL"]

    def matches(rec: dict, split: str, qtype: str) -> bool:
        ok_split = (split == "ALL") or (rec["split"] == split)
        ok_qtype = (qtype == "ALL") or (rec["query_type"] == qtype)
        return ok_split and ok_qtype

    agg: dict = {}
    for split in splits_full:
        agg[split] = {}
        for qtype in qtypes_full:
            subset = [r for r in records if matches(r, split, qtype)]
            n = len(subset)
            if n == 0:
                agg[split][qtype] = {
                    "n_queries": 0,
                    "n_target_covered": 0, "target_coverage_rate": None,
                    "n_anchor_applicable": 0, "n_anchor_covered": 0, "anchor_coverage_rate": None,
                    "n_edge_applicable": 0, "n_edge_both_covered": 0,
                    "support_edge_endpoint_coverage_rate": None,
                    "n_target_and_anchor_both_covered": 0,
                    "target_and_anchor_coverage_rate": None,
                    "n_same_label_distractor": 0,
                    "same_label_distractor_rate": None,
                }
                continue

            n_target_covered = sum(1 for r in subset if r["target_has_bbox"])
            n_anchor_app     = sum(1 for r in subset if r["anchor_applicable"])
            n_anchor_cov     = sum(1 for r in subset if r["anchor_applicable"] and r["anchor_has_bbox"])
            n_edge_app       = sum(1 for r in subset if r["supporting_edge_applicable"])
            n_edge_both      = sum(
                1 for r in subset
                if r["supporting_edge_applicable"] and r["supporting_edge_both_have_bbox"]
            )
            n_both_cov       = sum(1 for r in subset if r["target_and_anchor_both_covered"])
            n_distractor     = sum(1 for r in subset if r["has_same_label_distractor"])

            agg[split][qtype] = {
                "n_queries":                        n,
                "n_target_covered":                 n_target_covered,
                "target_coverage_rate":             n_target_covered / n,
                "n_anchor_applicable":              n_anchor_app,
                "n_anchor_covered":                 n_anchor_cov,
                "anchor_coverage_rate":             (n_anchor_cov / n_anchor_app) if n_anchor_app > 0 else None,
                "n_edge_applicable":                n_edge_app,
                "n_edge_both_covered":              n_edge_both,
                "support_edge_endpoint_coverage_rate": (n_edge_both / n_edge_app) if n_edge_app > 0 else None,
                "n_target_and_anchor_both_covered": n_both_cov,
                "target_and_anchor_coverage_rate":  n_both_cov / n,
                "n_same_label_distractor":          n_distractor,
                "same_label_distractor_rate":       n_distractor / n,
            }
    return agg


def compute_missing_breakdown(records: list[dict]) -> dict:
    """For each split, count missing-reason occurrences within functional queries."""
    out: dict = {}
    splits = sorted({r["split"] for r in records})
    for split in splits:
        subset = [r for r in records if r["split"] == split and r["query_type"] == "functional"]
        if not subset:
            continue
        out[f"scenefun3d_functional_{split}"] = {
            "n_total":             len(subset),
            "n_missing_target":    sum(1 for r in subset if "missing_target"    in r["missing_reason"]),
            "n_missing_anchor":    sum(1 for r in subset if "missing_anchor"    in r["missing_reason"]),
            "n_missing_edge_src":  sum(1 for r in subset if "missing_edge_src"  in r["missing_reason"]),
            "n_missing_edge_tgt":  sum(1 for r in subset if "missing_edge_tgt"  in r["missing_reason"]),
            "n_scene_not_in_geom": sum(1 for r in subset if "scene_not_in_geom" in r["missing_reason"]),
        }
    return out


def compute_distractor_stats(records: list[dict]) -> dict:
    out: dict = {}
    splits = sorted({r["split"] for r in records})
    for split in splits:
        subset = [r for r in records if r["split"] == split and r["query_type"] == "functional"]
        if not subset:
            continue
        with_distractor = [r for r in subset if r["has_same_label_distractor"]]
        counts = [r["same_label_count"] for r in subset]
        out[f"scenefun3d_functional_{split}"] = {
            "n_with_distractor":       len(with_distractor),
            "distractor_rate":         len(with_distractor) / len(subset),
            "median_same_label_count": float(statistics.median(counts)) if counts else 0.0,
            "max_same_label_count":    max(counts) if counts else 0,
        }
    return out


# =============================================================================
# Writers
# =============================================================================
REPORT_COLUMNS = [
    "query_id", "scene_id", "split", "query_type", "dataset",
    "target_node_ids", "target_labels", "anchor_node_id", "supporting_edge_id",
    "target_count",
    "target_has_bbox", "target_any_has_bbox",
    "anchor_applicable", "anchor_has_bbox",
    "supporting_edge_applicable",
    "supporting_edge_src_has_bbox", "supporting_edge_tgt_has_bbox",
    "supporting_edge_both_have_bbox",
    "target_and_anchor_both_covered",
    "same_label_count", "has_same_label_distractor", "same_label_with_bbox_count",
    "missing_reason",
]


def _bool_str(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def write_report_csv(records: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow({col: _bool_str(r[col]) for col in REPORT_COLUMNS})


SUMMARY_COLUMNS = [
    "split", "query_type", "n_queries",
    "n_target_covered", "target_coverage_rate",
    "n_anchor_applicable", "n_anchor_covered", "anchor_coverage_rate",
    "n_edge_applicable", "n_edge_both_covered", "support_edge_endpoint_coverage_rate",
    "n_target_and_anchor_both_covered", "target_and_anchor_coverage_rate",
    "n_same_label_distractor", "same_label_distractor_rate",
]


def _fmt_rate(v: float | None) -> str:
    return "" if v is None else f"{v:.4f}"


def write_summary_csv(agg: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        ordered_splits = [s for s in agg.keys() if s != "ALL"] + (["ALL"] if "ALL" in agg else [])
        for split in ordered_splits:
            qtypes = list(agg[split].keys())
            ordered_qtypes = [q for q in qtypes if q != "ALL"] + (["ALL"] if "ALL" in qtypes else [])
            for qtype in ordered_qtypes:
                m = agg[split][qtype]
                writer.writerow({
                    "split": split,
                    "query_type": qtype,
                    "n_queries": m["n_queries"],
                    "n_target_covered": m["n_target_covered"],
                    "target_coverage_rate": _fmt_rate(m["target_coverage_rate"]),
                    "n_anchor_applicable": m["n_anchor_applicable"],
                    "n_anchor_covered": m["n_anchor_covered"],
                    "anchor_coverage_rate": _fmt_rate(m["anchor_coverage_rate"]),
                    "n_edge_applicable": m["n_edge_applicable"],
                    "n_edge_both_covered": m["n_edge_both_covered"],
                    "support_edge_endpoint_coverage_rate": _fmt_rate(m["support_edge_endpoint_coverage_rate"]),
                    "n_target_and_anchor_both_covered": m["n_target_and_anchor_both_covered"],
                    "target_and_anchor_coverage_rate": _fmt_rate(m["target_and_anchor_coverage_rate"]),
                    "n_same_label_distractor": m["n_same_label_distractor"],
                    "same_label_distractor_rate": _fmt_rate(m["same_label_distractor_rate"]),
                })


def _rel_path(path: Path) -> str:
    """Express a path relative to the parent of REPO_ROOT (the git repo root), forward slashes."""
    try:
        rel = path.relative_to(REPO_ROOT.parent)
    except ValueError:
        rel = path
    return str(rel).replace("\\", "/")


def write_summary_json(
    agg: dict,
    geom: dict,
    queries: list[dict],
    missing_breakdown: dict,
    distractor_stats: dict,
    path: Path,
) -> dict:
    scene_ids_in_geom = sorted(geom.keys())
    n_nodes_in_geom   = sum(len(geom[sid]) for sid in scene_ids_in_geom)

    n_total = len(queries)
    counts_by_qtype = defaultdict(int)
    for q in queries:
        counts_by_qtype[q.get("query_type", "")] += 1

    referenced_scenes = sorted({q.get("scene_id", "") for q in queries if q.get("scene_id")})
    scenes_missing_from_geom = sorted(set(referenced_scenes) - set(scene_ids_in_geom))

    # Compact coverage view
    coverage_view: dict = {}
    for split, qtypes in agg.items():
        coverage_view[split] = {}
        for qtype, m in qtypes.items():
            coverage_view[split][qtype] = {
                "n":      m["n_queries"],
                "target": m["target_coverage_rate"],
                "anchor": m["anchor_coverage_rate"],
                "edge":   m["support_edge_endpoint_coverage_rate"],
            }

    # Gate check
    func_test = agg.get("test", {}).get("functional", {})
    func_test_n = func_test.get("n_queries", 0)
    target_cov_test = func_test.get("target_coverage_rate")
    edge_cov_test   = func_test.get("support_edge_endpoint_coverage_rate")

    # Fallback: if functional test is empty/sparse, use train+val functional
    fallback_used = False
    fallback_target = None
    fallback_edge = None
    if func_test_n == 0:
        fallback_used = True
        train_func = agg.get("train", {}).get("functional", {})
        val_func   = agg.get("val", {}).get("functional", {})
        n_total_fallback = train_func.get("n_queries", 0) + val_func.get("n_queries", 0)
        if n_total_fallback > 0:
            n_t = train_func.get("n_target_covered", 0) + val_func.get("n_target_covered", 0)
            fallback_target = n_t / n_total_fallback
            n_e_app = train_func.get("n_edge_applicable", 0) + val_func.get("n_edge_applicable", 0)
            n_e_cov = train_func.get("n_edge_both_covered", 0) + val_func.get("n_edge_both_covered", 0)
            fallback_edge = (n_e_cov / n_e_app) if n_e_app > 0 else None

    gate_target = fallback_target if fallback_used else target_cov_test
    gate_edge   = fallback_edge   if fallback_used else edge_cov_test

    pass_target = (gate_target is not None) and (gate_target >= GATE_TARGET_THRESHOLD)
    pass_edge   = (gate_edge   is not None) and (gate_edge   >= GATE_EDGE_THRESHOLD)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_files": {
            "queries":  _rel_path(QUERY_INDEX),
            "geometry": _rel_path(GEOM_PATH),
            "enriched": _rel_path(ENRICHED),
        },
        "geometry_inventory": {
            "n_scenes_in_geom": len(scene_ids_in_geom),
            "n_nodes_in_geom":  n_nodes_in_geom,
            "scene_ids":        scene_ids_in_geom,
        },
        "totals": {
            "n_scenefun3d_queries": n_total,
            "n_functional":         counts_by_qtype.get("functional", 0),
            "n_spatial":            counts_by_qtype.get("spatial", 0),
            "n_semantic":           counts_by_qtype.get("semantic", 0),
        },
        "coverage":              coverage_view,
        "missing_breakdown":     missing_breakdown,
        "same_label_distractor": distractor_stats,
        "gate_check": {
            "scenefun3d_functional_test_n_queries":             func_test_n,
            "scenefun3d_functional_test_target_coverage":       target_cov_test,
            "scenefun3d_functional_test_support_edge_coverage": edge_cov_test,
            "fallback_used_train_val_functional":               fallback_used,
            "fallback_target_coverage":                         fallback_target,
            "fallback_support_edge_coverage":                   fallback_edge,
            "gate_target_coverage_evaluated":                   gate_target,
            "gate_support_edge_coverage_evaluated":             gate_edge,
            "passes_target_threshold_0.70":                     bool(pass_target),
            "passes_edge_threshold_0.65":                       bool(pass_edge),
            "ready_for_phase_2":                                bool(pass_target and pass_edge),
        },
        "scenes_missing_from_geom": scenes_missing_from_geom,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


# =============================================================================
# Stdout summary
# =============================================================================
def _fmt_opt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.4f}"


def print_summary(summary: dict) -> None:
    gc = summary["gate_check"]
    print("=" * 70)
    print("Phase 1 Coverage Audit - Summary")
    print("=" * 70)
    t = summary["totals"]
    print(f"  Total SceneFun3D queries: {t['n_scenefun3d_queries']}")
    print(f"    functional: {t['n_functional']}")
    print(f"    spatial:    {t['n_spatial']}")
    print(f"    semantic:   {t['n_semantic']}")
    inv = summary["geometry_inventory"]
    print(f"  Geometry inventory: {inv['n_scenes_in_geom']} scenes, {inv['n_nodes_in_geom']} nodes")
    if summary["scenes_missing_from_geom"]:
        n_miss = len(summary["scenes_missing_from_geom"])
        print(f"  Scenes referenced but missing from geom file: {n_miss}")
    print()
    print("Coverage by split (functional only):")
    print(f"  {'split':6s} {'n':>5s}  {'target':>8s}  {'anchor':>8s}  {'edge':>8s}")
    for split in ("train", "val", "test", "ALL"):
        cov = summary["coverage"].get(split, {}).get("functional")
        if cov is None:
            continue
        print(f"  {split:6s} {cov['n']:5d}  {_fmt_opt(cov['target']):>8s}  "
              f"{_fmt_opt(cov['anchor']):>8s}  {_fmt_opt(cov['edge']):>8s}")
    print()
    print("Gate check:")
    print(f"  test functional n = {gc['scenefun3d_functional_test_n_queries']}")
    if gc.get("fallback_used_train_val_functional"):
        print("  [fallback] using train+val functional (test functional was empty)")
        print(f"    target = {_fmt_opt(gc['fallback_target_coverage'])}  "
              f"edge = {_fmt_opt(gc['fallback_support_edge_coverage'])}")
    else:
        print(f"    target = {_fmt_opt(gc['scenefun3d_functional_test_target_coverage'])}  "
              f"edge = {_fmt_opt(gc['scenefun3d_functional_test_support_edge_coverage'])}")
    print(f"  pass_target_>=0.70: {gc['passes_target_threshold_0.70']}")
    print(f"  pass_edge_>=0.65:   {gc['passes_edge_threshold_0.65']}")
    print()
    if gc["ready_for_phase_2"]:
        print("  [GATE PASSED] Ready for Phase 2 once Mingqian signs off.")
    else:
        print("  [GATE FAILED] Do not proceed to Phase 2 without sync.")
    print("=" * 70)


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    print(f"Loading queries from: {QUERY_INDEX}")
    all_queries = load_queries(QUERY_INDEX)
    queries = [q for q in all_queries if q.get("dataset") == "scenefun3d"]
    print(f"  Total {len(all_queries)} queries; {len(queries)} are SceneFun3D")

    print(f"Loading geometry from: {GEOM_PATH}")
    geom = load_geom(GEOM_PATH)

    print(f"Building scene->label map from: {ENRICHED}")
    scene_label_to_nodes = build_scene_label_map(ENRICHED)
    n_scene_label = sum(len(v) for v in scene_label_to_nodes.values())
    print(f"  Built mapping for {len(scene_label_to_nodes)} scenes "
          f"({n_scene_label} (scene, label) buckets)")

    print("Computing per-query records...")
    records = [compute_query_record(q, geom, scene_label_to_nodes) for q in queries]

    print("Aggregating...")
    agg = aggregate(records)
    missing_breakdown = compute_missing_breakdown(records)
    distractor_stats  = compute_distractor_stats(records)

    print(f"Writing {OUT_REPORT_CSV.name}...")
    write_report_csv(records, OUT_REPORT_CSV)
    print(f"Writing {OUT_SUMMARY_CSV.name}...")
    write_summary_csv(agg, OUT_SUMMARY_CSV)
    print(f"Writing {OUT_SUMMARY_JSON.name}...")
    summary = write_summary_json(
        agg, geom, queries, missing_breakdown, distractor_stats, OUT_SUMMARY_JSON
    )

    print()
    print_summary(summary)


if __name__ == "__main__":
    main()
