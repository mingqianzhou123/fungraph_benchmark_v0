# Auto-generated FunGraph native 3DGraphLLM eval config.
# This inherits the local reproduced 3DGraphLLM config and only overrides the
# dataset-facing fields. Use from the 3DGraphLLM repository root:
# python tasks/train.py /home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm/config_fungraph_eval.py evaluate True pretrained_path ./demo/3dgraphllm.pth val_tag fungraph_functional_500

_base_ = "/home/mz560/3D scene graph project/3DGraphLLM/scripts/config.py"

anno_root = "/home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm"
pc_encoder = "uni3d"
segmentor = "fungraph_geometry_fallback"
version = ""

seg_feat_file = f"{anno_root}/fungraph_scene3d_uni3d_feats.pt"
seg_img_feat_file = f"{anno_root}/fungraph_scene3d_videofeats.pt"
seg_val_attr_file = f"{anno_root}/fungraph_scene3d_attributes.pt"
seg_val_gnn_file = f"{anno_root}/fungraph_scene3d_gnn_feats.pt"

train_tag = "fungraph_functional_500"
val_tag = "fungraph_functional_500"

train_file_dict = {}
val_file_dict = {
    "fungraph_functional_500": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_functional_500_val.json", seg_val_gnn_file, "gt"],
    "fungraph_functional_500_objselect": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_functional_500_objselect_val.json", seg_val_gnn_file, "gt"],
    "fungraph_human_133": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_human_133_val.json", seg_val_gnn_file, "gt"],
    "fungraph_human_133_objselect": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_human_133_objselect_val.json", seg_val_gnn_file, "gt"],
    "fungraph_long_range_50": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_long_range_50_val.json", seg_val_gnn_file, "gt"],
    "fungraph_long_range_50_objselect": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_long_range_50_objselect_val.json", seg_val_gnn_file, "gt"],
    "fungraph_smoke_1": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_smoke_1_val.json", seg_val_gnn_file, "gt"],
    "fungraph_objselect_smoke_1": [seg_feat_file, seg_img_feat_file, seg_val_attr_file, f"{anno_root}/fungraph_objselect_smoke_1_val.json", seg_val_gnn_file, "gt"],
}

num_workers = 0
batch_size = 4
evaluate = True
wandb = dict(enable=False)
do_save = False
model = dict(knn=2, max_knn=2)
