# import os
# from huggingface_hub import snapshot_download

# # Tên folder đích (Trùng với code của bạn)
# local_folder = "qwen2.5-0.5b_ner_fp16"

# print(f"--- Đang tải model Qwen2.5-0.5B-Instruct về: {local_folder} ---")
# print("Quá trình này có thể mất vài phút (khoảng 1GB)...")

# try:
#     path = snapshot_download(
#         repo_id="Qwen/Qwen2.5-0.5B-Instruct", # Dùng bản Instruct chuẩn để làm NER
#         local_dir=local_folder,
#         local_dir_use_symlinks=False,
#         resume_download=True
#     )
#     print(f"\n[THÀNH CÔNG] Model đã tải về tại: {path}")
#     print("Bây giờ bạn có thể chạy: python run_experiment.py")
    
# except Exception as e:
#     print(f"\n[LỖI] Không thể tải model: {e}")

# from huggingface_hub import snapshot_download
# import os

# # Chọn thư mục để lưu mô hình
# local_dir = "./vietnamese-embedding"

# print("Đang tải mô hình về máy...")
# print(f"Thư mục lưu: {local_dir}")

# # Tải toàn bộ mô hình về máy
# snapshot_download(
#     repo_id="dangvantuan/vietnamese-embedding",
#     local_dir=local_dir,
#     local_dir_use_symlinks=False
# )

# print(f"✓ Đã tải xong mô hình vào: {os.path.abspath(local_dir)}")

from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "Qwen/Qwen3-0.6B"
LOCAL_DIR = "../../models/qwen3-0.6b"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    cache_dir=LOCAL_DIR
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    cache_dir=LOCAL_DIR,
    device_map="auto"
)

print("Model downloaded to:", LOCAL_DIR)
