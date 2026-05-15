"""Validator for human functional queries.

Checks 13 validation rules + Phase 1 distribution analysis on pilot_20_queries.jsonl.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

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
        """Load enriched JSON and geometry."""
        try:
            with ENRICH_PATH.open(encoding="utf-8") as f:
                data = json.load(f)
            for item in data["data"]:
                sid = item["scene_id"]
                if sid in SELECTED_SCENES and sid not in self.scene_graphs:
                    if item.get("scene_graph"):
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

            # C13: duplicate instance check (same target+anchor+edge tuple)
            inst_key = (q.get("target_node_id"), q.get("anchor_node_id"),
                        tuple(q.get("supporting_edge_ids", [])))
            if inst_key in instance_keys:
                self.errors.append(
                    f"C13 {query_id}: duplicate instance of {instance_keys[inst_key]} "
                    f"(identical target+anchor+edge)")
            else:
                instance_keys[inst_key] = query_id

            # C1: query_id format
            if not query_id.startswith("human_func_v1_") or not query_id[-6:].isdigit():
                self.errors.append(f"C1 {query_id}: invalid format")
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
            edge_valid = True
            for eid in edge_ids:
                if eid not in edges_by_id:
                    self.errors.append(f"C6 {query_id}: edge_id not found: {eid}")
                    edge_valid = False
                    break
                e = edges_by_id[eid]
                # C7: source = target_node_id
                if e.get("source_node_id") != target_nid and e["edge_id"].split("|")[0] != target_nid:
                    # Try to extract source from edge_id format
                    parts = e["edge_id"].split("|")
                    if len(parts) == 3 and parts[0] != target_nid:
                        self.errors.append(f"C7 {query_id}: edge source mismatch")
                        edge_valid = False
                        break
                # C8: target = anchor_node_id
                if anchor_nid and e.get("target_node_id") != anchor_nid and e["edge_id"].split("|")[2] != anchor_nid:
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

            self.pass_count += 1

        # C2: query_id uniqueness
        if len(query_ids) != len(set(query_ids)):
            dups = [qid for qid in query_ids if query_ids.count(qid) > 1]
            self.errors.append(f"C2: duplicate query_ids: {set(dups)}")

        # Report
        self.write_report(scene_dist)
        return 0 if not self.errors else 1

    def write_report(self, scene_dist: dict) -> None:
        """Write validation_report.md."""
        report_path = self.queries_path.parent / "validation_report.md"

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

        # Phase 1 category distribution (mutually exclusive, per TASK_PLAN Section 8)
        cat = {"local_functional": 0, "same_or_endpoint": 0,
               "geometry_aware": 0, "hard_negative": 0}
        for q in self.queries:
            qtags = set(q.get("difficulty_tags", []))
            if "hard_negative" in qtags:
                cat["hard_negative"] += 1
            elif "geometry_aware" in qtags:
                cat["geometry_aware"] += 1
            elif "same_label_disambiguation" in qtags or "endpoint_ambiguity" in qtags:
                cat["same_or_endpoint"] += 1
            else:
                cat["local_functional"] += 1
        expected = {"local_functional": 10, "same_or_endpoint": 5,
                    "geometry_aware": 3, "hard_negative": 2}
        lines.extend([
            f"",
            f"Phase 1 category distribution (TASK_PLAN Section 8 requires 10/5/3/2):",
        ])
        for k in ["local_functional", "same_or_endpoint", "geometry_aware", "hard_negative"]:
            mark = "OK" if cat[k] == expected[k] else "MISMATCH"
            lines.append(f"  {k}: {cat[k]} (expected {expected[k]}) [{mark}]")

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
