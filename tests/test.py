import json

def check_structure(file_path):
    # Đọc file JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    inconsistencies = []

    # Hàm đệ quy để duyệt cây dữ liệu
    def traverse(node):
        current_code = node.get('code', '')
        current_type = node.get('type', '')
        children = node.get('children', [])

        # Kiểm tra logic: Nếu là 'disease', các con của nó phải có mã bắt đầu bằng mã cha
        # (Lưu ý: Bỏ qua nếu mã cha có ký tự đặc biệt như '*' nếu cần thiết, 
        # nhưng ở đây ta kiểm tra chặt chẽ theo chuỗi ký tự)
        if current_type == 'disease' and children:
            for child in children:
                child_code = child.get('code', '')
                # Nếu mã con không bắt đầu bằng mã cha => Ghi nhận lỗi
                if current_code and child_code and not child_code.startswith(current_code):
                    inconsistencies.append({
                        "Parent Code": current_code,
                        "Parent Name": node.get('name'),
                        "Mismatch Child Code": child_code,
                        "Child Name": child.get('name')
                    })

        # Tiếp tục duyệt xuống các cấp con (nếu có)
        if isinstance(children, list):
            for child in children:
                traverse(child)

    # Bắt đầu duyệt từ root
    if isinstance(data, list):
        for item in data:
            traverse(item)
    elif isinstance(data, dict):
        traverse(data)

    return inconsistencies

# Chạy hàm kiểm tra
file_name = 'Data/icd10_data.json' # Thay đường dẫn file của bạn vào đây
errors = check_structure(file_name)

# In kết quả
print(f"Tìm thấy {len(errors)} trường hợp không khớp mã:")
for err in errors:
    print(f"Cha: {err['Parent Code']} chứa con: {err['Mismatch Child Code']} ({err['Child Name']})")