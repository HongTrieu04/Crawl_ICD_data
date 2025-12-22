import json
import re

def parse_disease_description(disease):
    """
    Phân tích và tách description của bệnh thành các bệnh con
    """
    if disease.get('type') != 'disease':
        return disease
    
    description = disease.get('description', '')
    if not description:
        return disease
    
    # Pattern để tìm các bệnh con (code dạng A00.0, A00.1, etc.)
    # Tìm các dòng bắt đầu bằng mã bệnh (có dấu • hoặc không)
    pattern = r'(?:^|\n)(?:•\s*)?([A-Z]\d{2}\.\d+)\n([^\n]+)'
    
    matches = list(re.finditer(pattern, description, re.MULTILINE))
    
    if not matches:
        # Không có bệnh con, giữ nguyên description
        return disease
    
    # Tách phần mô tả chung (trước bệnh con đầu tiên)
    first_match_start = matches[0].start()
    general_description = description[:first_match_start].strip()
    
    # Tạo danh sách children
    children = []
    for i, match in enumerate(matches):
        sub_code = match.group(1)
        sub_name = match.group(2).strip()
        
        # Làm sạch tên bệnh (loại bỏ các ký tự đặc biệt đầu dòng)
        sub_name = re.sub(r'^[•\s]+', '', sub_name)
        
        # Lấy description của bệnh con
        # Bắt đầu từ sau tên bệnh con, kết thúc trước bệnh con tiếp theo
        start_pos = match.end()
        
        if i < len(matches) - 1:
            # Có bệnh con tiếp theo
            end_pos = matches[i + 1].start()
        else:
            # Là bệnh con cuối cùng
            end_pos = len(description)
        
        sub_desc = description[start_pos:end_pos].strip()
        
        # Loại bỏ các dòng trắng thừa và các ký tự xuống dòng không cần thiết ở đầu/cuối
        sub_desc = re.sub(r'^\n+', '', sub_desc)
        sub_desc = re.sub(r'\n+$', '', sub_desc)
        
        # Nếu không có description, để trống
        if not sub_desc:
            sub_desc = ""
        
        child = {
            "type": "sub_disease",
            "code": sub_code,
            "name": sub_name,
            "description": sub_desc
        }
        children.append(child)
    
    # Cập nhật disease
    disease['description'] = general_description
    disease['children'] = children
    
    return disease

def process_data_recursive(data):
    """
    Xử lý đệ quy toàn bộ cấu trúc dữ liệu
    """
    if isinstance(data, dict):
        # Xử lý disease
        if data.get('type') == 'disease':
            data = parse_disease_description(data)
        
        # Xử lý children nếu có
        if 'children' in data and isinstance(data['children'], list):
            data['children'] = [process_data_recursive(child) for child in data['children']]
    
    elif isinstance(data, list):
        data = [process_data_recursive(item) for item in data]
    
    return data

# Đọc file JSON
def main(input_file, output_file):
    """
    Hàm chính để xử lý file
    """
    # Đọc dữ liệu
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Xử lý dữ liệu
    processed_data = process_data_recursive(data)
    
    # Ghi kết quả
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)
    
    print(f"Đã xử lý xong! Kết quả được lưu tại: {output_file}")

# Sử dụng
if __name__ == "__main__":
    input_file = "../../data/icd10_diseases_data_v1.json"
    output_file = "../../data/icd10_data.json" 
    
    main(input_file, output_file)