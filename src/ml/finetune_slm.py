import argparse
import json
import os
import random
from typing import List, Dict, Optional

import torch
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    default_data_collator,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def load_jsonl(path: str, fallback_label: Optional[str] = None) -> List[Dict]:
    """Load JSONL file từ Google Drive"""
    data = []
    if not path or not os.path.exists(path):
        print(f"⚠️ File không tồn tại: {path}")
        return data
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            answer = obj.get("answer") or fallback_label
            if answer is None:
                continue
            obj["answer"] = answer
            data.append(obj)
    
    print(f"✅ Đã load {len(data)} mẫu từ {path}")
    return data


def normalize_answer(ans: str) -> str:
    """Chuẩn hóa câu trả lời về Đúng/Sai"""
    ans = ans.strip().lower()
    if ans.startswith("đ"):
        return "Đúng"
    if ans.startswith("s"):
        return "Sai"
    return "Sai"


def build_messages(context: str, statement: str, answer: str) -> List[Dict[str, str]]:
    """Tạo format chat messages cho Qwen"""
    display_context = context.strip() or statement.strip()
    display_statement = statement.strip() or context.strip()

    user_prompt = (
        "Ngữ cảnh: {context}\n"
        "Mệnh đề: {statement}\n"
        "Hãy phân loại mệnh đề trên là 'Đúng' hoặc 'Sai'. "
        "Chỉ trả lời đúng một từ: Đúng hoặc Sai."
    ).format(context=display_context, statement=display_statement)

    return [
        {
            "role": "system",
            "content": "Bạn là chuyên gia y tế, chỉ trả lời 'Đúng' hoặc 'Sai'.",
        },
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": answer},
    ]


def tokenize_example(example, tokenizer, max_len, text_field: Optional[str] = None):
    """Tokenize một mẫu dữ liệu"""
    single_text = ""
    if text_field:
        single_text = example.get(text_field, "") or ""
    if not single_text:
        single_text = (
            example.get("text")
            or example.get("sentence")
            or example.get("content")
            or ""
        )

    context = example.get("context", "") or single_text
    statement = example.get("statement", "") or single_text
    answer = normalize_answer(example.get("answer", "Sai"))

    messages = build_messages(context, statement, answer)
    prompt_text = tokenizer.apply_chat_template(
        messages[:-1], tokenize=False, add_generation_prompt=True
    )
    full_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )

    prompt_ids = tokenizer(
        prompt_text, add_special_tokens=True, truncation=True, max_length=max_len
    )["input_ids"]
    enc = tokenizer(
        full_text,
        add_special_tokens=True,
        truncation=True,
        max_length=max_len,
        padding="max_length",
        return_tensors="pt",
    )

    labels = enc["input_ids"][0].clone()
    labels[: len(prompt_ids)] = -100

    return {
        "input_ids": enc["input_ids"][0],
        "attention_mask": enc["attention_mask"][0],
        "labels": labels,
    }


class QwenSLMDataset(Dataset):
    """Dataset class cho Qwen fine-tuning"""
    def __init__(self, examples: List[Dict], tokenizer, max_len: int, text_field: Optional[str]):
        self.features = [
            tokenize_example(e, tokenizer, max_len, text_field) for e in examples
        ]

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return {k: v.clone() for k, v in self.features[idx].items()}


def set_seed(seed: int):
    """Set random seed cho reproducibility"""
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def main():
    # ===== CẤU HÌNH - CHỈNH SỬA PHẦN NÀY =====
    
    # Đường dẫn file dữ liệu trên Google Drive
    TRAIN_FILE = "./data/checkpoint_results.jsonl"
    EXTRA_FILE = "./data/checkpoint_results_sai.jsonl"

    # Thư mục output trên Google Drive
    OUTPUT_DIR = "./checkpoint/qwen3_slm"
    
    # Model từ Hugging Face
    MODEL_ID = "Qwen/Qwen3-0.6B"
    
    # Hyperparameters
    config = {
        "seed": 42,
        "max_seq_length": 512,
        "per_device_train_batch_size": 4,  # Giảm batch size cho Kaggle
        "per_device_eval_batch_size": 4,
        "gradient_accumulation_steps": 4,  # Tăng để compensate batch size nhỏ
        "learning_rate": 2e-4,
        "weight_decay": 0.01,
        "num_train_epochs": 3,
        "warmup_ratio": 0.05,
        "logging_steps": 50,
        "save_steps": 500,
        "eval_steps": 500,
    }
    
    # ===== KẾT THÚC CẤU HÌNH =====
    
    set_seed(config["seed"])
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🚀 Bắt đầu fine-tuning Qwen3-0.6B")
    print(f"📁 Train file: {TRAIN_FILE}")
    print(f"📁 Extra file: {EXTRA_FILE}")
    print(f"💾 Output dir: {OUTPUT_DIR}")
    
    # ===== Load dữ liệu =====
    print("\n📊 Đang load dữ liệu...")
    train_data = load_jsonl(TRAIN_FILE)
    extra = load_jsonl(EXTRA_FILE) if EXTRA_FILE else []
    all_data = train_data + extra
    random.shuffle(all_data)

    if len(all_data) == 0:
        raise ValueError("❌ Không có dữ liệu để huấn luyện. Kiểm tra đường dẫn file!")

    split_idx = int(0.95 * len(all_data))
    train_examples = all_data[:split_idx]
    eval_examples = all_data[split_idx:]
    
    print(f"✅ Tổng số mẫu: {len(all_data)}")
    print(f"   - Train: {len(train_examples)}")
    print(f"   - Eval: {len(eval_examples)}")

    # ===== Load Tokenizer & Model từ Hugging Face =====
    print(f"\n🤖 Đang tải model {MODEL_ID} từ Hugging Face...")
    print("⚠️ Lưu ý: Qwen3-0.6B yêu cầu transformers>=4.51.0")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, 
        trust_remote_code=True,
        use_fast=False,
        padding_side="right"
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    
    print("✅ Model đã được tải và quantize thành công!")
    
    # ===== Cấu hình LoRA =====
    lora_config = LoraConfig(
        r=64,
        lora_alpha=128,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
            "lm_head",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.config.use_cache = False
    
    print("✅ LoRA adapter đã được thêm vào model!")
    print(f"   Trainable params: {model.print_trainable_parameters()}")

    # ===== Tạo Dataset =====
    print("\n📦 Đang chuẩn bị dataset...")
    train_dataset = QwenSLMDataset(
        train_examples, tokenizer, config["max_seq_length"], None
    )
    eval_dataset = QwenSLMDataset(
        eval_examples, tokenizer, config["max_seq_length"], None
    )

    # ===== Training Arguments =====
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=config["per_device_train_batch_size"],
        per_device_eval_batch_size=config["per_device_eval_batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation_steps"],
        learning_rate=config["learning_rate"],
        weight_decay=config["weight_decay"],
        num_train_epochs=config["num_train_epochs"],
        warmup_ratio=config["warmup_ratio"],
        logging_steps=config["logging_steps"],
        save_steps=config["save_steps"],
        eval_strategy="steps",
        eval_steps=config["eval_steps"],
        save_total_limit=3,
        load_best_model_at_end=True,
        bf16=False,
        fp16=True,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        report_to="none",
    )

    # ===== Start Training =====
    print("\n🏋️ Bắt đầu training...")
    trainer = Trainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=default_data_collator,
    )

    trainer.train()
    
    # ===== Save Model =====
    print("\n💾 Đang lưu model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    if hasattr(model, "save_pretrained"):
        model.save_pretrained(os.path.join(OUTPUT_DIR, "lora_adapter"))
    
    print(f"\n✅ Hoàn thành! Model đã được lưu tại: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()