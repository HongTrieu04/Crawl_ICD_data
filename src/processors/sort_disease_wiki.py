import json
import re

# --- CẤU HÌNH ---
INPUT_FILE = '../../data/all_diseases_wiki.json'
OUTPUT_FILE = '../../data/diseases_wiki.json'

def natural_sort_key(s):
    """
    Hàm tạo key để sắp xếp tự nhiên (Natural Sort).
    Giúp máy tính hiểu A2 < A10 (thay vì A10 < A2 như mặc định string).
    Cấu trúc mã ICD thường là: Chữ cái + Số + (Dấu chấm + Số)
    """
    # Tách chuỗi thành danh sách các phần tử gồm số và không phải số
    # Ví dụ: "A01.1" -> ['A', 1, '.', 1]
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def main():
    print(f"📂 Đang đọc file: {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Kiểm tra xem dữ liệu có phải là danh sách không
        if not isinstance(data, list):
            print("❌ Lỗi: Cấu trúc file JSON không phải là một danh sách (list).")
            return

        print(f"📊 Tìm thấy {len(data)} bệnh. Đang sắp xếp...")

        # Sắp xếp danh sách dựa trên trường 'icd_10'
        # Sử dụng hàm natural_sort_key để xử lý mã ICD
        data.sort(key=lambda x: natural_sort_key(x.get('icd_10', '')))

        print(f"💾 Đang lưu kết quả vào: {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
            json.dump(data, f_out, ensure_ascii=False, indent=4)
            
        print("✅ Hoàn tất! Danh sách đã được sắp xếp gọn gàng.")

    except FileNotFoundError:
        print(f"❌ Không tìm thấy file '{INPUT_FILE}'. Hãy đảm bảo file nằm cùng thư mục với code.")
    except Exception as e:
        print(f"❌ Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()