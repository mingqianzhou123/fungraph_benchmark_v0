# Model-Specific Exports

This directory contains clean, model-facing export layers derived from the frozen benchmark sources.

The current mainline export is:

```text
3dgraphllm_functional_eval_v1/
```

Use it for 3DGraphLLM reproduction, functional-query evaluation, full raw multimodal manifests, relation-conditioned evidence, and official crop/QC metadata.

The frozen benchmark source of truth remains:

```text
benchmark_clean_v0/queries/
benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/
benchmark_clean_v0/annotations/
benchmark_clean_v0/human_annotations/
benchmark_clean_v0/raw_assets/
```

Do not mix files directly from older task tracks when running model experiments. Read through the export README and validate with:

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/validate_export.py
```
