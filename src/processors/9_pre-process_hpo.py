import pandas as pd
import re
import json

# ================= CẤU HÌNH ĐƯỜNG DẪN FILE =================
OBO_FILE = "../../data/hp.obo"
HPOA_FILE = "../../data/phenotype.hpoa"
OUTPUT_FILE = "../../data/hpo_processed_english.jsonl"

# ================= 1. HÀM ĐỌC FILE OBO (TỪ ĐIỂN) =================
def parse_obo(file_path):
    print("📖 Đang đọc file hp.obo...")
    id2name = {}
    id2def = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tách các block [Term]
    terms = content.split("[Term]")
    
    for term in terms[1:]: # Bỏ phần header đầu
        term_id = ""
        term_name = ""
        term_def = ""
        
        lines = term.strip().split("\n")
        for line in lines:
            if line.startswith("id: HP:"):
                term_id = line.split("id: ")[1].strip()
            elif line.startswith("name: "):
                term_name = line.split("name: ")[1].strip()
            elif line.startswith("def: "):
                # Lấy nội dung trong dấu ngoặc kép
                match = re.search(r'"(.*?)"', line)
                if match:
                    term_def = match.group(1)
        
        if term_id and term_name:
            id2name[term_id] = term_name
            if term_def:
                id2def[term_id] = term_def
                
    print(f"✅ Đã load {len(id2name)} định nghĩa triệu chứng.")
    return id2name, id2def

# ================= 2. XỬ LÝ FILE HPOA (LIÊN KẾT) =================
def process_hpoa(hpoa_path, id2name, output_path):
    print("📖 Đang đọc file phenotype.hpoa...")
    
    # File HPOA thường có comment ở đầu, cần skip
    # Cấu trúc cột thường là: database_id, disease_name, qualifier, hpo_id, ...
    df = pd.read_csv(hpoa_path, sep='\t', comment='#')
    
    # Chuẩn hóa tên cột (đôi khi tên cột có thể khác nhau tùy phiên bản file)
    # Ta cần các cột: 'database_id', 'disease_name', 'hpo_id'
    df.columns = [c.strip().lower() for c in df.columns] 
    
    # Group by Disease
    print("🔄 Đang gom nhóm triệu chứng theo bệnh...")
    grouped = df.groupby(['database_id', 'disease_name'])
    
    results = []
    
    for (db_id, disease_name), group in grouped:
        symptoms = []
        
        for _, row in group.iterrows():
            hpo_id = row.get('hpo_id')
            # Lấy tên triệu chứng từ từ điển OBO
            symptom_name = id2name.get(hpo_id, hpo_id) # Nếu không thấy thì dùng ID
            
            # (Tùy chọn) Bạn có thể lấy thêm Frequency nếu muốn
            # freq = row.get('frequency', '')
            
            if symptom_name:
                symptoms.append(symptom_name)
        
        # Loại bỏ trùng lặp và nối chuỗi
        symptoms = list(set(symptoms))
        symptoms_str = ", ".join(symptoms)
        
        # --- TẠO CÂU VĂN (TIẾNG ANH) ---
        # Format 1: Bệnh -> Triệu chứng
        text_content = f"Disease {disease_name} (ID: {db_id}) is characterized by the following phenotypes: {symptoms_str}."
        
        results.append({
            "source": "HPO",
            "type": "disease_phenotype",
            "text": text_content,
            "original_id": db_id
        })

    # ================= 3. LƯU KẾT QUẢ =================
    print(f"💾 Đang lưu {len(results)} mẫu dữ liệu vào {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("✅ Hoàn tất!")

# ================= CHẠY QUY TRÌNH =================
# 1. Load từ điển
hpo_id_map, hpo_def_map = parse_obo(OBO_FILE)

# 2. Xử lý và ghép nối
process_hpoa(HPOA_FILE, hpo_id_map, OUTPUT_FILE)