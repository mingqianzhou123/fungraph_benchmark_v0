# Model-Specific Exports

This directory contains clean, model-facing export layers derived from the
frozen benchmark sources.

The frozen benchmark remains the source of truth:

```text
benchmark_clean_v0/queries/
benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/
benchmark_clean_v0/annotations/
benchmark_clean_v0/human_annotations/
benchmark_clean_v0/multimodal_extension/
```

Model-specific adapters should read from `exports/` instead of mixing source
files from multiple historical task tracks.
