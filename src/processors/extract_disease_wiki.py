import json
import glob
import os

# --- CẤU HÌNH ---
INPUT_FOLDER = '../../data/disease_details'  # Thư mục chứa các file json con
OUTPUT_FILE = '../../data/all_diseases_wiki.json'  # Tên file tổng hợp đầu ra

def process_details_field(raw_details):
    """
    Hàm xử lý riêng cho trường 'details':
    Chỉ lấy danh sách tên (name) của các mục con.
    """
    if not raw_details or not isinstance(raw_details, dict):
        return {}
    
    clean_details = {}
    
    # Duyệt qua từng nhóm (ví dụ: 'Subclass of', 'Possible treatment'...)
    for category_key, items_list in raw_details.items():
        if isinstance(items_list, list):
            # Chỉ lấy trường 'name' từ mỗi phần tử trong danh sách
            # Filter: chỉ lấy nếu phần tử có trường 'name'
            names_only = [item.get('name') for item in items_list if item.get('name')]
            
            # Chỉ thêm vào kết quả nếu danh sách không rỗng
            if names_only:
                clean_details[category_key] = names_only
                
    return clean_details

def main():
    print(f"🚀 Đang quét dữ liệu từ thư mục: {INPUT_FOLDER}...")
    
    # Lấy danh sách tất cả file .json
    json_files = glob.glob(os.path.join(INPUT_FOLDER, "*.json"))
    
    if not json_files:
        print("❌ Không tìm thấy file .json nào!")
        return

    master_list = []
    count = 0

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Tạo object mới chỉ chứa các trường yêu cầu
                entry = {}
                
                # 1. Mã bệnh ICD-10 (Bỏ qua nếu không có)
                if 'icd_10' in data and data['icd_10']:
                    entry['icd_10'] = data['icd_10']
                
                # 2. Tên bệnh
                if 'name' in data and data['name']:
                    entry['name'] = data['name']
                
                # 3. Description
                if 'description' in data and data['description']:
                    entry['description'] = data['description']
                
                # 4. Aliases (Lấy tất cả)
                if 'aliases' in data and data['aliases']:
                    entry['aliases'] = data['aliases']
                
                # 5. Detail (Chỉ lấy name của các mục con)
                if 'details' in data:
                    processed_detail = process_details_field(data['details'])
                    if processed_detail: # Chỉ thêm nếu có dữ liệu
                        entry['detail'] = processed_detail

                # Thêm vào danh sách tổng nếu object không rỗng
                if entry:
                    master_list.append(entry)
                    count += 1

        except Exception as e:
            print(f"⚠️ Lỗi khi đọc file {file_path}: {e}")

    # Lưu file tổng hợp
    print(f"💾 Đang lưu {count} bệnh vào file {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
            json.dump(master_list, f_out, ensure_ascii=False, indent=4)
        print("✅ Hoàn tất! File của bạn đã sẵn sàng.")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")

if __name__ == "__main__":
    main()