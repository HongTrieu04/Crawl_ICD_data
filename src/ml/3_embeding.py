import json
import torch
import os
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm # Thư viện tạo thanh tiến độ (pip install tqdm)

# ================= CẤU HÌNH =================
MODEL_PATH = "../../models/vietnamese-embedding" # Đường dẫn model local
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 32

# File đầu vào
INPUT_FILES = {
    "icd10": "../../data/icd10_data.json",
    "drugs": "../../data/drug_data_grouped_translated.json",
    "symptoms": "../../data/symptoms_extracted_data_translated.json"
}

# File đầu ra
OUTPUT_FILES = {
    "icd10": "../../data/icd10_embedded.json",
    "drugs": "../../data/drugs_embedded.json",
    "symptoms": "../../data/symptoms_embedded.json"
}

class EmbeddingGenerator:
    def __init__(self, model_path):
        print(f"⚙️ Đang tải model trên thiết bị: {DEVICE}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(model_path, trust_remote_code=True, torch_dtype=torch.float16 if DEVICE=="cuda" else torch.float32)
        self.model.to(DEVICE)
        self.model.eval()

    def get_embedding(self, text):
        """Hàm tính vector cho 1 câu text đơn lẻ"""
        if not text or not isinstance(text, str) or text.strip() == "":
            return [] # Trả về mảng rỗng nếu không có text
        
        # Giới hạn độ dài text trước khi tokenize (để tránh lỗi position embedding)
        text = text.strip()[:5000]  # Giới hạn ký tự trước khi tokenize
        
        with torch.no_grad():
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=256  # Giảm xuống 256 thay vì 512 để an toàn hơn
            )
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            # Thêm kiểm tra để đảm bảo input_ids không vượt quá giới hạn
            if inputs['input_ids'].shape[1] > 512:
                print(f"⚠️ Cảnh báo: Text quá dài ({inputs['input_ids'].shape[1]} tokens), đang cắt bớt...")
                inputs['input_ids'] = inputs['input_ids'][:, :512]
                inputs['attention_mask'] = inputs['attention_mask'][:, :512]
            
            outputs = self.model(**inputs)
            
            # Mean Pooling
            last_hidden_states = outputs.last_hidden_state
            attention_mask = inputs['attention_mask'].unsqueeze(-1).expand(last_hidden_states.size()).float()
            sum_embeddings = torch.sum(last_hidden_states * attention_mask, 1)
            sum_mask = torch.clamp(attention_mask.sum(1), min=1e-9)
            mean_embeddings = sum_embeddings / sum_mask
            
            return mean_embeddings.cpu().numpy()[0].tolist()

    def process_icd10_recursive(self, items):
        """Duyệt đệ quy cấu trúc cây ICD-10 để thêm vector"""
        for item in tqdm(items, desc="Xử lý node ICD-10", leave=False):
            # Xử lý vector dựa trên type
            item['name_vector'] = self.get_embedding(item.get('name', ''))
            item['desc_vector'] = self.get_embedding(item.get('description', ''))
            
            # Riêng Group có thêm code_vector
            if item.get('type') == 'group':
                item['code_vector'] = self.get_embedding(item.get('code', '')) # Dùng code làm ID vector
            
            # Đệ quy xuống con (children)
            if 'children' in item and isinstance(item['children'], list):
                self.process_icd10_recursive(item['children'])
        return items

    def process_flat_list(self, items, type_label):
        """Xử lý danh sách phẳng (Thuốc, Triệu chứng)"""
        for item in tqdm(items, desc=f"Xử lý {type_label}"):
            # Mapping dữ liệu dựa trên loại file
            if type_label == "Drug":
                # Thuốc
                item['name_vector'] = self.get_embedding(item.get('tên thuốc', ''))
                item['desc_vector'] = self.get_embedding(item.get('mô tả', ''))
            elif type_label == "Symptom":
                # Triệu chứng
                item['name_vector'] = self.get_embedding(item.get('tên', ''))
                item['desc_vector'] = self.get_embedding(item.get('mô tả', '')) # Nếu file gốc không có thì trả về []
                # Triệu chứng code chưa có nên bỏ qua code_vector
            
        return items

    def run(self):
        # 1. Xử lý ICD-10 (Cấu trúc phân cấp)
        if os.path.exists(INPUT_FILES['icd10']):
            print("\n📥 Đang xử lý file ICD-10...")
            with open(INPUT_FILES['icd10'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Gọi hàm đệ quy
            processed_data = self.process_icd10_recursive(data)
            
            with open(OUTPUT_FILES['icd10'], 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Đã xuất file: {OUTPUT_FILES['icd10']}")

        # 2. Xử lý Thuốc (Danh sách phẳng)
        if os.path.exists(INPUT_FILES['drugs']):
            print("\n📥 Đang xử lý file Thuốc...")
            with open(INPUT_FILES['drugs'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            processed_data = self.process_flat_list(data, "Drug")
            
            with open(OUTPUT_FILES['drugs'], 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Đã xuất file: {OUTPUT_FILES['drugs']}")

        # 3. Xử lý Triệu chứng (Danh sách phẳng)
        if os.path.exists(INPUT_FILES['symptoms']):
            print("\n📥 Đang xử lý file Triệu chứng...")
            with open(INPUT_FILES['symptoms'], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            processed_data = self.process_flat_list(data, "Symptom")
            
            with open(OUTPUT_FILES['symptoms'], 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Đã xuất file: {OUTPUT_FILES['symptoms']}")

if __name__ == "__main__":
    generator = EmbeddingGenerator(MODEL_PATH)
    generator.run()