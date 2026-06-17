# 3DGraphLLM Adapter Smoke Test

Date: 2026-06-18

## Command

Run from the local 3DGraphLLM repository root:

```bash
PYTHONPATH=. CUDA_VISIBLE_DEVICES=7 /home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python tasks/train.py \
  /home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm/config_fungraph_eval.py \
  output_dir /home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1 \
  evaluate True \
  pretrained_path ./demo/3dgraphllm.pth \
  model.llama_model_path ./Meta-Llama-3-8B-Instruct \
  model.low_resource True \
  wandb.enable False \
  gpu_num 1 \
  batch_size 1 \
  val_tag fungraph_smoke_1 \
  train_tag fungraph_smoke_1 \
  do_save False
```

## Result

The run completed full model loading and one-sample generation.

Output files:

```text
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/config.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/preds_fungraph_smoke_1.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/scores_fungraph_smoke_1.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/train.log
```

The generated prediction confirms that the FunGraph native packet can pass
through the original 3DGraphLLM model entrypoint.

## Scientific Status

This is an integration smoke test only. The current native packet uses
geometry-aligned attributes plus zero fallback Uni3D/video/GNN tensors. Do not
use these predictions as evidence for a multimodal performance claim. Replace
the fallback tensor files with real SceneFun3D-native 3DGraphLLM features before
running Gate 1.

## Real Modality Adapter Smoke Test

After replacing the zero fallback tensors with real SceneFun3D point/color,
RGB-D/camera, and relative-geometry adapter features, the one-query full-model
smoke test completed again.

Output directory:

```text
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1_real_modalities
```

This confirms that the modality-complete native packet passes through the
original 3DGraphLLM model entrypoint. The features are real SceneFun3D modality
features but not pretrained Uni3D/video-network embeddings.
