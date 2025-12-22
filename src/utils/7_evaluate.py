import torch
import pandas as pd
import torch.nn.functional as F
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# ================= CẤU HÌNH =================
# Đường dẫn folder chứa Adapter (kết quả sau khi train xong)
ADAPTER_PATH = "../../models/qwen3_slm_batch6/checkpoint-3800" 
# Tên hoặc đường dẫn model gốc (Bắt buộc phải có để làm nền)
BASE_MODEL_PATH = "../../models/qwen3-0.6b/models--Qwen--Qwen3-0.6B" 

INPUT_FILE = "../../data/data_test_normalize.csv"
OUTPUT_FILE = "../../data/Result_Vector_Injection.xlsx"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ================= CORE LOGIC =================
class VectorInference:
    def __init__(self):
        print(f"🚀 Đang khởi tạo trên thiết bị: {DEVICE}")
        
        # 1. Load Tokenizer (Ưu tiên load từ Adapter nếu có, không thì lấy từ Base)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH, trust_remote_code=True)
        except:
            self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH, trust_remote_code=True)
            
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # 2. Load Base Model (Model nền)
        print(f"📦 Loading Base Model: {BASE_MODEL_PATH}...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_PATH,
            device_map=DEVICE,
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            trust_remote_code=True
        )
        
        # Resize token embeddings nếu lúc train bạn có resize (Quan trọng!)
        self.base_model.resize_token_embeddings(len(self.tokenizer))

        # 3. Load & Gắn Adapter (LoRA)
        print(f"🔗 Loading Adapter từ: {ADAPTER_PATH}...")
        self.model = PeftModel.from_pretrained(self.base_model, ADAPTER_PATH)
        self.model.eval()
        
        # 4. Xác định Token ID của nhãn "Đúng"/"Sai"
        # Tokenizer đôi khi thêm khoảng trắng (vd: "_Đúng"), nên ta encode và lấy token cuối cùng cho chắc
        self.true_token_id = self.get_single_token_id("Đúng")
        self.false_token_id = self.get_single_token_id("Sai")
        
        print(f"ℹ️ Token Map: 'Đúng' -> ID {self.true_token_id} | 'Sai' -> ID {self.false_token_id}")

    def get_single_token_id(self, word):
        """Hàm helper để lấy ID của 1 từ đơn"""
        ids = self.tokenizer.encode(word, add_special_tokens=False)
        return ids[-1] if ids else -1

    def predict_from_vector(self, context, statement):
        """
        Quy trình Vector Injection:
        Text -> Token IDs -> Embeddings Layer (Base Model) -> Vectors -> Transformer Layers -> Logits
        """
        
        # Format Prompt: PHẢI GIỐNG HỆT LÚC TRAIN để đạt hiệu quả cao nhất
        display_context = context if pd.notna(context) and str(context).strip() else statement
        display_statement = statement if pd.notna(statement) and str(statement).strip() else display_context
        
        prompt_text = (
            f"Ngữ cảnh: {display_context}\n"
            f"Mệnh đề: {display_statement}\n"
            "Hãy phân loại mệnh đề trên là 'Đúng' hoặc 'Sai'. "
            "Chỉ trả lời đúng một từ: Đúng hoặc Sai.\n"
            "Câu trả lời:" # Thêm gợi ý để model điền tiếp
        )
        
        # B1: Tokenize
        inputs = self.tokenizer(prompt_text, return_tensors="pt").to(self.model.device)
        input_ids = inputs.input_ids
        
        # B2: VECTOR EMBEDDING (Đây là bước bạn yêu cầu)
        # Lấy lớp Embedding đầu tiên của model gốc
        # Qwen/Llama thường có thuộc tính .model.embed_tokens hoặc .get_input_embeddings()
        with torch.no_grad():
            # Biến đổi Token IDs (số nguyên) thành Vectors (số thực float16)
            # input_vectors shape: [1, seq_len, hidden_size]
            input_vectors = self.model.get_input_embeddings()(input_ids)
        
        # B3: FORWARD PASS BẰNG VECTOR
        with torch.no_grad():
            # Thay vì truyền input_ids, ta truyền inputs_embeds
            outputs = self.model(
                inputs_embeds=input_vectors,
                # Vẫn cần attention_mask để model biết đâu là padding
                attention_mask=inputs.attention_mask 
            )
            
            # Lấy Logits của token cuối cùng (token dự đoán tiếp theo)
            next_token_logits = outputs.logits[0, -1, :]
            
            # So sánh điểm số (Logits) giữa token "Đúng" và "Sai"
            score_true = next_token_logits[self.true_token_id].item()
            score_false = next_token_logits[self.false_token_id].item()
            
            # Chuyển sang xác suất (Softmax cục bộ giữa 2 token này)
            probs = F.softmax(torch.tensor([score_true, score_false], dtype=torch.float32), dim=0)
            prob_true = probs[0].item()
            prob_false = probs[1].item()

        # Kết luận
        if prob_true > prob_false:
            return "Đúng", prob_true
        else:
            return "Sai", prob_false

# ================= MAIN =================
def run():
    # Khởi tạo Engine
    try:
        engine = VectorInference()
    except Exception as e:
        print(f"❌ Lỗi khởi tạo model: {e}")
        return

    # Đọc dữ liệu
    print(f"📂 Đang đọc file {INPUT_FILE}...")
    try:
        if INPUT_FILE.endswith('.csv'):
            df = pd.read_csv(INPUT_FILE)
        else:
            df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print("❌ Không tìm thấy file input!")
        return

    # Tự động tìm tên cột
    col_stmt = next((c for c in df.columns if "statement" in c.lower() or "mệnh đề" in c.lower()), "statement")
    col_ctx = next((c for c in df.columns if "context" in c.lower() or "ngữ cảnh" in c.lower()), "context")
    
    results = []
    print(f"▶️ Bắt đầu chạy Inference trên {len(df)} dòng...")
    
    # Dùng tqdm để hiện thanh tiến trình
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        stmt = row.get(col_stmt, "")
        ctx = row.get(col_ctx, "")
        
        # Gọi hàm xử lý vector
        decision, confidence = engine.predict_from_vector(ctx, stmt)
        
        results.append({
            "Context": ctx,
            "Statement": stmt,
            "Prediction": decision,
            "Confidence": round(confidence, 4)
        })
        
    # Lưu kết quả
    out_df = pd.DataFrame(results)
    out_df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✅ Đã xong! Kết quả lưu tại: {OUTPUT_FILE}")
    print(out_df[['Statement', 'Prediction', 'Confidence']].head())

if __name__ == "__main__":
    run()