"""Phase 3 minimal-pair validator (C14-C18).

Separate from validate_functional_queries.py (which owns C1-C13 main query
validation, unchanged). This script validates minimal_pairs_v1.jsonl and the
optional minimal_pair_queries_v1.jsonl (Phase 3 supplemental queries; empty
in current Phase 3 since mining yielded enough pairs).

Checks (phase3.md "Validator Extension" section):
  C14  pair_id format `minpair_v1_\\d{6}` and unique
  C15  query_a_id / query_b_id exist in known query pool
        (pilot + main + phase3 supplemental, if any)
  C16  target_a_node_id != target_b_node_id
  C17  changed_factor in {anchor_object, spatial_qualifier,
        functional_relation, geometry_direction}
  C18  changed_factor consistency (WARN-level):
       - anchor_object: scene/target_label/relation same, anchor different
       - spatial_qualifier / geometry_direction: anchor/relation/target_label
         same; geom diff >= 0.05m (else WARN)
       - functional_relation: anchor/target_label same, relation different

Writes validation_report_phase3.md and exits 1 on any ERROR.
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
QUERY_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"

PILOT_PATH = QUERY_DIR / "pilot_20_queries.jsonl"
MAIN_PATH = QUERY_DIR / "functional_queries_v1.jsonl"
SUPPL_PATH = QUERY_DIR / "minimal_pair_queries_v1.jsonl"  # may not exist
PAIRS_PATH = QUERY_DIR / "minimal_pairs_v1.jsonl"
REPORT_PATH = QUERY_DIR / "validation_report_phase3.md"

PAIR_ID_RE = re.compile(r"^minpair_v1_\d{6}$")

VALID_CHANGED_FACTOR = {
    "anchor_object",
    "spatial_qualifier",
    "functional_relation",
    "geometry_direction",
}

GEOM_DIFF_WARN_THRESHOLD_M = 0.05


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def build_query_index(paths: list[Path]) -> dict[str, dict]:
    """{query_id -> query dict} from all provided JSONL files."""
    idx = {}
    for p in paths:
        for q in load_jsonl(p):
            idx[q["query_id"]] = q
    return idx


def edge_relation(q: dict) -> str:
    edges = q.get("supporting_edge_ids") or []
    if not edges:
        return ""
    parts = edges[0].split("|", 2)
    return parts[1] if len(parts) >= 2 else ""


def validate_pair(pair: dict, idx: dict, all_pair_ids: list[str]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single pair."""
    errors: list[str] = []
    warnings: list[str] = []
    pid = pair.get("pair_id", "<no pair_id>")

    # C14: pair_id format + uniqueness
    if not PAIR_ID_RE.match(pid):
        errors.append(f"C14 invalid pair_id format: {pid!r}")
    if all_pair_ids.count(pid) > 1:
        errors.append(f"C14 duplicate pair_id: {pid}")

    # C15: query_a/b_id exist in pool
    a_id = pair.get("query_a_id")
    b_id = pair.get("query_b_id")
    qa = idx.get(a_id) if a_id else None
    qb = idx.get(b_id) if b_id else None
    if qa is None:
        errors.append(f"C15 query_a_id not in pool: {a_id}")
    if qb is None:
        errors.append(f"C15 query_b_id not in pool: {b_id}")
    if qa is None or qb is None:
        return errors, warnings  # can't proceed with cross-field checks

    # C16: target_node_id distinct
    ta = pair.get("target_a_node_id")
    tb = pair.get("target_b_node_id")
    if ta == tb:
        errors.append(f"C16 target_a == target_b: {ta}")
    # Also verify pair fields match the referenced query
    if ta != qa.get("target_node_id"):
        errors.append(f"C16 target_a_node_id mismatch with query_a: pair={ta} qa={qa.get('target_node_id')}")
    if tb != qb.get("target_node_id"):
        errors.append(f"C16 target_b_node_id mismatch with query_b: pair={tb} qb={qb.get('target_node_id')}")

    # C17: changed_factor valid
    cf = pair.get("changed_factor")
    if cf not in VALID_CHANGED_FACTOR:
        errors.append(f"C17 invalid changed_factor: {cf!r}")
        return errors, warnings

    # C18: changed_factor consistency
    qa_scene = qa.get("scene_id")
    qb_scene = qb.get("scene_id")
    if qa_scene != qb_scene:
        errors.append(f"C18 scene mismatch between query_a ({qa_scene}) and query_b ({qb_scene})")
    if pair.get("scene_id") != qa_scene:
        errors.append(f"C18 pair scene_id {pair.get('scene_id')} != query_a scene {qa_scene}")

    qa_tgt_lbl = qa.get("target_label")
    qb_tgt_lbl = qb.get("target_label")
    rel_a = edge_relation(qa)
    rel_b = edge_relation(qb)
    anchor_a = qa.get("anchor_node_id")
    anchor_b = qb.get("anchor_node_id")

    if cf == "anchor_object":
        if qa_tgt_lbl != qb_tgt_lbl:
            errors.append(f"C18[anchor_object] target_label differs: {qa_tgt_lbl!r} vs {qb_tgt_lbl!r}")
        if rel_a != rel_b:
            errors.append(f"C18[anchor_object] relation differs: {rel_a!r} vs {rel_b!r}")
        if anchor_a == anchor_b:
            errors.append(f"C18[anchor_object] anchor_node_id should differ but both are {anchor_a}")
    elif cf in ("spatial_qualifier", "geometry_direction"):
        if anchor_a != anchor_b:
            errors.append(f"C18[{cf}] anchor should match but differ: {anchor_a} vs {anchor_b}")
        if rel_a != rel_b:
            errors.append(f"C18[{cf}] relation should match but differ: {rel_a!r} vs {rel_b!r}")
        if qa_tgt_lbl != qb_tgt_lbl:
            errors.append(f"C18[{cf}] target_label differs: {qa_tgt_lbl!r} vs {qb_tgt_lbl!r}")
        # Geom diff warning
        d = pair.get("target_geom_diff_m")
        if d is not None and d < GEOM_DIFF_WARN_THRESHOLD_M:
            warnings.append(f"C18[{cf}] geom_diff_below_threshold: {d:.3f}m < {GEOM_DIFF_WARN_THRESHOLD_M}m")
    elif cf == "functional_relation":
        if anchor_a != anchor_b:
            errors.append(f"C18[functional_relation] anchor should match but differ: {anchor_a} vs {anchor_b}")
        if qa_tgt_lbl != qb_tgt_lbl:
            errors.append(f"C18[functional_relation] target_label differs: {qa_tgt_lbl!r} vs {qb_tgt_lbl!r}")
        if rel_a == rel_b:
            errors.append(f"C18[functional_relation] relation should differ but both are {rel_a!r}")

    return errors, warnings


def main() -> int:
    pairs = load_jsonl(PAIRS_PATH)
    if not pairs:
        print(f"ERROR: no pairs found at {PAIRS_PATH}", file=sys.stderr)
        return 1

    idx = build_query_index([PILOT_PATH, MAIN_PATH, SUPPL_PATH])
    all_pair_ids = [p.get("pair_id", "") for p in pairs]

    pair_results = []
    for pair in pairs:
        errs, warns = validate_pair(pair, idx, all_pair_ids)
        pair_results.append({
            "pair_id": pair.get("pair_id"),
            "errors": errs,
            "warnings": warns,
        })

    n_pass = sum(1 for r in pair_results if not r["errors"])
    n_fail = sum(1 for r in pair_results if r["errors"])
    n_warn_only = sum(1 for r in pair_results if r["warnings"] and not r["errors"])

    # Distributions
    cf_counts = Counter(p["changed_factor"] for p in pairs)
    scene_counts = Counter(p["scene_id"] for p in pairs)
    evidence_counts = Counter()
    for p in pairs:
        for ev in p.get("pair_evidence_used", []) or []:
            evidence_counts[ev] += 1

    # Build report
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append(f"## Phase 3 Validation Report -- {ts}")
    lines.append("")
    lines.append(f"Input files:")
    lines.append(f"  - {PAIRS_PATH.name} ({len(pairs)} pairs)")
    if SUPPL_PATH.exists():
        suppl = load_jsonl(SUPPL_PATH)
        lines.append(f"  - {SUPPL_PATH.name} ({len(suppl)} supplemental queries)")
    else:
        lines.append(f"  - {SUPPL_PATH.name}: not present (mining yielded enough pairs)")
    lines.append("")
    lines.append(f"Query pool size (pilot + main + supplemental): {len(idx)}")
    lines.append("")
    lines.append(f"Pair validator (C14-C18):")
    lines.append(f"  PASS (no errors): {n_pass} / {len(pairs)}")
    lines.append(f"  FAIL (>=1 error): {n_fail}")
    lines.append(f"  WARN only:        {n_warn_only}")
    lines.append("")

    # Error / warning details
    err_lines = [r for r in pair_results if r["errors"]]
    warn_lines = [r for r in pair_results if r["warnings"]]
    if err_lines:
        lines.append("Errors:")
        for r in err_lines:
            for e in r["errors"]:
                lines.append(f"  [{r['pair_id']}] {e}")
        lines.append("")
    if warn_lines:
        lines.append("Warnings:")
        for r in warn_lines:
            for w in r["warnings"]:
                lines.append(f"  [{r['pair_id']}] {w}")
        lines.append("")

    lines.append("changed_factor distribution:")
    for cf in sorted(cf_counts):
        lines.append(f"  {cf}: {cf_counts[cf]}")
    lines.append("")
    lines.append("scene distribution:")
    for s in sorted(scene_counts):
        lines.append(f"  {s}: {scene_counts[s]}")
    lines.append("")
    lines.append("pair_evidence_used distribution:")
    for ev in sorted(evidence_counts):
        lines.append(f"  {ev}: {evidence_counts[ev]}")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"PASS: {n_pass} / {len(pairs)}  FAIL: {n_fail}  WARN only: {n_warn_only}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
