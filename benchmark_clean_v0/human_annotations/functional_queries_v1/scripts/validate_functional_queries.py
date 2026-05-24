"""Validator for human functional queries.

Checks 13 validation rules + Phase 1 distribution analysis on pilot_20_queries.jsonl.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

_COORD_PAT = re.compile(
    r'\b[xyz]=[-−]?\d+(\.\d+)?|\b[xyz]≈[-−]?\d+(\.\d+)?',
    re.IGNORECASE)

BENCH_ROOT = Path(__file__).resolve().parents[3]
ENRICH_PATH = BENCH_ROOT / "queries" / "scenefun3d_funrag_benchmark_enriched.json"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"

VALID_TAGS = {
    "simple_functional",
    "functional_relation",
    "same_label_disambiguation",
    "endpoint_ambiguity",
    "geometry_aware",
    "hard_negative",
    "long_range",
    "multi_anchor",
    "minimal_pair",
}

SELECTED_SCENES = {"469011", "421254", "421380", "421602", "421013", "420683"}


class Validator:
    def __init__(self, queries_path: Path):
        self.queries_path = queries_path
        self.queries = []
        self.scene_graphs = {}
        self.geometry = {}
        self.errors = []
        self.warnings = []
        self.pass_count = 0

    def load_data(self) -> bool:
        """Load enriched JSON and geometry.

        Loads ALL SceneFun3D scenes (not just SELECTED_SCENES) so Phase 4
        long_range queries on new scenes (460417, 421063, 422813, 422391,
        466192, 466803, etc.) can be validated. SELECTED_SCENES is retained
        as documentation for the Phase 1-3 6-scene scope.
        """
        try:
            with ENRICH_PATH.open(encoding="utf-8") as f:
                data = json.load(f)
            for item in data["data"]:
                sid = item["scene_id"]
                if sid not in self.scene_graphs and item.get("scene_graph"):
                    self.scene_graphs[sid] = item["scene_graph"]
            print(f"Loaded {len(self.scene_graphs)} scene graphs")

            with GEOM_PATH.open(encoding="utf-8") as f:
                self.geometry = json.load(f)
            print(f"Loaded geometry data")
            return True
        except Exception as e:
            print(f"ERROR loading data: {e}")
            return False

    def load_queries(self) -> bool:
        """Load queries from JSONL."""
        try:
            with self.queries_path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.queries.append(json.loads(line))
            print(f"Loaded {len(self.queries)} queries")
            return True
        except Exception as e:
            print(f"ERROR loading queries: {e}")
            return False

    def validate_all(self) -> int:
        """Run all 12 checks."""
        if not self.load_data() or not self.load_queries():
            return 1

        # Track query_ids and scene distribution
        query_ids = []
        scene_dist = defaultdict(int)
        instance_keys = {}  # (target, anchor, edges) -> first query_id seen

        for q_idx, q in enumerate(self.queries):
            query_id = q.get("query_id", f"MISSING_{q_idx}")
            query_ids.append(query_id)
            scene_id = q.get("scene_id")
            if scene_id:
                scene_dist[scene_id] += 1

            # C13: duplicate instance check (same target+anchor+edge tuple).
            # Phase 3 allows duplicates when at least one query is in a minimal_pair
            # (language-variant pairs intentionally reuse instance keys; see
            # phase3.md Revision 1).
            inst_key = (q.get("target_node_id"), q.get("anchor_node_id"),
                        tuple(q.get("supporting_edge_ids", [])))
            if inst_key in instance_keys:
                first_q = instance_keys[inst_key]
                current_in_pair = q.get("minimal_pair_id") is not None
                first_in_pair = first_q.get("minimal_pair_id") is not None
                if not (current_in_pair or first_in_pair):
                    self.errors.append(
                        f"C13 {query_id}: duplicate instance of {first_q.get('query_id')} "
                        f"(identical target+anchor+edge, neither in minimal_pair)")
            else:
                instance_keys[inst_key] = q

            # C1: query_id format — accept human_func_v1_NNNNNN or lr_v1_NNNNNN
            is_human = query_id.startswith("human_func_v1_") and query_id[-6:].isdigit()
            is_lr_id = query_id.startswith("lr_v1_") and query_id[-6:].isdigit()
            if not (is_human or is_lr_id):
                self.errors.append(f"C1 {query_id}: invalid format (expected human_func_v1_NNNNNN or lr_v1_NNNNNN)")
                continue

            # C3: scene_id valid
            if scene_id not in self.scene_graphs:
                self.errors.append(f"C3 {query_id}: scene {scene_id} not found")
                continue

            sg = self.scene_graphs[scene_id]
            node_ids = {n["node_id"] for n in sg.get("nodes", [])}
            edge_data = {(e["edge_id"], (e.get("source_label"), e.get("target_label")))
                         for e in sg.get("edges", [])}
            edges_by_id = {e["edge_id"]: e for e in sg.get("edges", [])}

            # C4: target_node_id valid
            target_nid = q.get("target_node_id")
            if target_nid not in node_ids:
                self.errors.append(f"C4 {query_id}: target_node_id {target_nid} not found")
                continue

            # C5: anchor_node_id valid (if not null)
            anchor_nid = q.get("anchor_node_id")
            if anchor_nid and anchor_nid not in node_ids:
                self.errors.append(f"C5 {query_id}: anchor_node_id {anchor_nid} not found")
                continue

            # C6 & C7 & C8: supporting_edge_ids
            edge_ids = q.get("supporting_edge_ids", [])
            is_long_range_q = bool(q.get("is_long_range", False))
            edge_valid = True
            for e_idx, eid in enumerate(edge_ids):
                if eid not in edges_by_id:
                    self.errors.append(f"C6 {query_id}: edge_id not found: {eid}")
                    edge_valid = False
                    break
                e = edges_by_id[eid]
                # C7: source = target_node_id
                # For long_range junction queries, only the first edge's source is target;
                # the second edge's source is reference_node_id (different node). Skip C7
                # for subsequent edges of long_range queries.
                if e_idx == 0 or not is_long_range_q:
                    if e.get("source_node_id") != target_nid and e["edge_id"].split("|")[0] != target_nid:
                        parts = e["edge_id"].split("|")
                        if len(parts) == 3 and parts[0] != target_nid:
                            self.errors.append(f"C7 {query_id}: edge source mismatch")
                            edge_valid = False
                            break
                # C8: target = anchor_node_id (skip for long_range — C26 covers junction anchor)
                if not is_long_range_q and anchor_nid and e.get("target_node_id") != anchor_nid and e["edge_id"].split("|")[2] != anchor_nid:
                    parts = e["edge_id"].split("|")
                    if len(parts) == 3 and parts[2] != anchor_nid:
                        self.errors.append(f"C8 {query_id}: edge target mismatch")
                        edge_valid = False
                        break
            if not edge_valid:
                continue

            # C9: difficulty_tags valid
            tags = q.get("difficulty_tags", [])
            for tag in tags:
                if tag not in VALID_TAGS:
                    self.errors.append(f"C9 {query_id}: invalid tag '{tag}'")
                    continue

            # C10: same_label_disambiguation check
            if "same_label_disambiguation" in tags:
                target_label = q.get("target_label")
                same_label_count = sum(1 for n in sg.get("nodes", [])
                                       if n["label"] == target_label and n["label"] != "unknown")
                if same_label_count < 2:
                    self.warnings.append(f"C10 {query_id}: same_label tag but ≤1 same-label node")

            # C11: geometry_aware check
            if "geometry_aware" in tags:
                if target_nid not in self.geometry.get(scene_id, {}):
                    self.warnings.append(f"C11 {query_id}: geometry_aware tag but no bbox")

            # C12: long_range check — covers BOTH the tag and the is_long_range flag
            is_lr = ("long_range" in tags) or bool(q.get("is_long_range", False))
            if is_lr and not self.queries_path.name.startswith("long_range"):
                self.errors.append(
                    f"C12 {query_id}: long_range query (tag or is_long_range=true) "
                    f"must live in long_range_stress_queries_v1.jsonl, not {self.queries_path.name}")

            # C14: no naked coordinate in query_text (x=1.23, y=-0.85, z=293, x≈1.07)
            if _COORD_PAT.search(q.get("query_text", "")):
                self.errors.append(
                    f"C14 {query_id}: naked coordinate in query_text: "
                    f"{q['query_text'][:80]!r}")

            # C19: self-describing minimal_pair fields all-or-nothing + format
            mp_id = q.get("minimal_pair_id")
            mp_role = q.get("minimal_pair_role")
            mp_partner = q.get("minimal_pair_partner_id")
            mp_fields_set = sum(1 for v in (mp_id, mp_role, mp_partner) if v is not None)
            if mp_fields_set not in (0, 3):
                self.errors.append(
                    f"C19 {query_id}: minimal_pair fields must be all-or-nothing "
                    f"(id={mp_id!r}, role={mp_role!r}, partner={mp_partner!r})")
            elif mp_id is not None:
                if not (isinstance(mp_id, str) and mp_id.startswith("minpair_v1_")
                        and len(mp_id) == len("minpair_v1_000000") and mp_id[-6:].isdigit()):
                    self.errors.append(f"C19 {query_id}: invalid minimal_pair_id format: {mp_id!r}")
                if mp_role not in ("a", "b"):
                    self.errors.append(
                        f"C19 {query_id}: minimal_pair_role must be 'a' or 'b', got {mp_role!r}")
                if not (isinstance(mp_partner, str) and mp_partner.startswith("human_func_v1_")):
                    self.errors.append(
                        f"C19 {query_id}: invalid minimal_pair_partner_id: {mp_partner!r}")

            # C20: minimal_pair tag iff minimal_pair_id present
            has_mp_tag = "minimal_pair" in tags
            has_mp_id = mp_id is not None
            if has_mp_tag != has_mp_id:
                self.errors.append(
                    f"C20 {query_id}: minimal_pair tag={has_mp_tag} but "
                    f"minimal_pair_id present={has_mp_id} (must match)")

            # C24-C29: Phase 4 long_range checks (only when is_long_range=true)
            if is_long_range_q:
                edge_ids_lr = q.get("supporting_edge_ids", [])
                ev_chain = q.get("evidence_chain", [])

                # C24: supporting_edge_ids and evidence_chain both length ≥ 2 and equal
                if len(edge_ids_lr) < 2:
                    self.errors.append(
                        f"C24 {query_id}: is_long_range=true but supporting_edge_ids "
                        f"length={len(edge_ids_lr)} (must be ≥ 2)")
                if len(ev_chain) < 2:
                    self.errors.append(
                        f"C24 {query_id}: is_long_range=true but evidence_chain "
                        f"length={len(ev_chain)} (must be ≥ 2)")
                if len(edge_ids_lr) != len(ev_chain):
                    self.errors.append(
                        f"C24 {query_id}: supporting_edge_ids length={len(edge_ids_lr)} "
                        f"≠ evidence_chain length={len(ev_chain)} (must match)")

                # C25: all supporting edges exist (already covered by C6 above; skip re-check)

                # C26: junction_2hop — all edge targets ("|" right-end) must be identical
                # (= shared_anchor). Only applies when long_range_pattern == "junction_2hop".
                lr_pattern = q.get("long_range_pattern")
                if lr_pattern == "junction_2hop" and len(edge_ids_lr) >= 2:
                    tgt_ends = []
                    for eid in edge_ids_lr:
                        parts = eid.split("|")
                        if len(parts) == 3:
                            tgt_ends.append(parts[2])
                    if len(set(tgt_ends)) > 1:
                        self.errors.append(
                            f"C26 {query_id}: junction_2hop but edge target UUIDs differ "
                            f"({tgt_ends}) — all must share the same anchor")
                    # Also cross-check shared_anchor_node_id field if present
                    shared_anchor = q.get("shared_anchor_node_id")
                    if shared_anchor and tgt_ends and tgt_ends[0] != shared_anchor:
                        self.errors.append(
                            f"C26 {query_id}: shared_anchor_node_id={shared_anchor!r} does not "
                            f"match edge target {tgt_ends[0]!r}")

                # C27: target ≠ shared_anchor ≠ reference (3 distinct UUIDs)
                shared_anc = q.get("shared_anchor_node_id")
                ref_nid = q.get("reference_node_id")
                if shared_anc and ref_nid:
                    uuids = [target_nid, shared_anc, ref_nid]
                    if len(set(uuids)) < 3:
                        self.errors.append(
                            f"C27 {query_id}: target/shared_anchor/reference not all distinct "
                            f"({target_nid!r}, {shared_anc!r}, {ref_nid!r})")

                # C28: long_range tag must be present in difficulty_tags
                if "long_range" not in tags:
                    self.errors.append(
                        f"C28 {query_id}: is_long_range=true but 'long_range' tag missing "
                        f"from difficulty_tags")

                # C29: reference_necessity must be "strict" or "contextual"
                ref_nec = q.get("reference_necessity")
                if ref_nec not in ("strict", "contextual"):
                    self.errors.append(
                        f"C29 {query_id}: reference_necessity={ref_nec!r} (must be "
                        f"'strict' or 'contextual')")

            self.pass_count += 1

        # C2: query_id uniqueness
        if len(query_ids) != len(set(query_ids)):
            dups = [qid for qid in query_ids if query_ids.count(qid) > 1]
            self.errors.append(f"C2: duplicate query_ids: {set(dups)}")

        # C21-C23: cross-query checks for minimal_pair bidirectional consistency
        query_by_id = {q.get("query_id"): q for q in self.queries}
        for q in self.queries:
            qid = q.get("query_id")
            mp_id = q.get("minimal_pair_id")
            mp_role = q.get("minimal_pair_role")
            mp_partner = q.get("minimal_pair_partner_id")
            if mp_id is None:
                continue
            # C21: partner exists in same file
            partner = query_by_id.get(mp_partner)
            if partner is None:
                self.errors.append(
                    f"C21 {qid}: minimal_pair_partner_id {mp_partner!r} not in same file")
                continue
            # C22: bidirectional consistency
            if partner.get("minimal_pair_partner_id") != qid:
                self.errors.append(
                    f"C22 {qid}: partner.minimal_pair_partner_id="
                    f"{partner.get('minimal_pair_partner_id')!r}, expected {qid!r}")
            if partner.get("minimal_pair_id") != mp_id:
                self.errors.append(
                    f"C22 {qid}: partner.minimal_pair_id="
                    f"{partner.get('minimal_pair_id')!r}, expected {mp_id!r}")
            # C23: partner role is the opposite letter
            partner_role = partner.get("minimal_pair_role")
            if mp_role == "a" and partner_role != "b":
                self.errors.append(
                    f"C23 {qid}: role='a' but partner role={partner_role!r}, expected 'b'")
            elif mp_role == "b" and partner_role != "a":
                self.errors.append(
                    f"C23 {qid}: role='b' but partner role={partner_role!r}, expected 'a'")

        # Report
        self.write_report(scene_dist)
        return 0 if not self.errors else 1

    def write_report(self, scene_dist: dict) -> None:
        """Write validation_report.md."""
        report_stem = self.queries_path.stem
        report_name = "validation_report.md" if report_stem == "functional_queries_v1" else f"validation_report_{report_stem}.md"
        report_path = self.queries_path.parent / report_name

        lines = [
            f"## Validation Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"Input file: {self.queries_path.name}",
            f"Total queries checked: {len(self.queries)}",
            f"",
            f"Results:",
            f"  PASS (no errors): {self.pass_count}",
            f"  FAIL (≥1 error):  {len(self.queries) - self.pass_count}",
            f"  WARN only:        {len(self.warnings)}",
            f"",
        ]

        if self.errors:
            lines.extend([
                f"Errors found ({len(self.errors)}):",
            ])
            for err in self.errors:
                lines.append(f"  - {err}")
            lines.append("")

        if self.warnings:
            lines.extend([
                f"Warnings found ({len(self.warnings)}):",
            ])
            for warn in self.warnings:
                lines.append(f"  - {warn}")
            lines.append("")

        lines.extend([
            f"Scene distribution:",
        ])
        for sid in sorted(scene_dist.keys()):
            lines.append(f"  {sid}: {scene_dist[sid]} queries")

        lines.extend([
            f"",
            f"Difficulty tags distribution:",
        ])
        tag_counts = defaultdict(int)
        for q in self.queries:
            for tag in q.get("difficulty_tags", []):
                tag_counts[tag] += 1
        for tag in sorted(tag_counts.keys()):
            lines.append(f"  {tag}: {tag_counts[tag]}")

        ref_nec_counts = defaultdict(int)
        for q in self.queries:
            rn = q.get("reference_necessity")
            if rn is not None:
                ref_nec_counts[rn] += 1
        if ref_nec_counts:
            lines.extend([f"", f"reference_necessity distribution (Phase 4 long_range):"])
            for rn in sorted(ref_nec_counts.keys()):
                lines.append(f"  {rn}: {ref_nec_counts[rn]}")

        report_text = "\n".join(lines)
        report_path.write_text(report_text, encoding="utf-8")
        print(f"\nWrote validation report to: {report_path}")
        print(report_text)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python validate_functional_queries.py <path_to_queries.jsonl>")
        return 1

    queries_path = Path(sys.argv[1])
    validator = Validator(queries_path)
    return validator.validate_all()


if __name__ == "__main__":
    sys.exit(main())
