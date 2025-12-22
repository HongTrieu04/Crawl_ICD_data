import json
import os
from collections import OrderedDict

def build_description_map(data_list):
    """
    Hàm đệ quy để quét toàn bộ file nguồn và tạo từ điển {code: description}
    """
    desc_map = {}
    for item in data_list:
        # Lấy code và description nếu tồn tại
        if 'code' in item:
            # Nếu có description thì lưu, nếu không thì lưu chuỗi rỗng
            desc_map[item['code']] = item.get('description', '')
        
        # Nếu có con (children), tiếp tục đệ quy để lấy hết các nhóm con
        if 'children' in item and isinstance(item['children'], list):
            child_map = build_description_map(item['children'])
            desc_map.update(child_map)
    return desc_map

def reorder_item_fields(item, desc_map):
    """
    Sắp xếp lại thứ tự các trường theo format:
    type -> code -> name -> description -> children
    """
    ordered = OrderedDict()
    
    # Thứ tự cố định
    if 'type' in item:
        ordered['type'] = item['type']
    if 'code' in item:
        ordered['code'] = item['code']
    if 'name' in item:
        ordered['name'] = item['name']
    
    # Thêm description (từ map hoặc giữ nguyên chuỗi rỗng)
    if 'code' in item and item['code'] in desc_map:
        ordered['description'] = desc_map[item['code']]
    else:
        # Nếu không có trong map, giữ description cũ hoặc tạo rỗng
        ordered['description'] = item.get('description', '')
    
    # Thêm children nếu có
    if 'children' in item:
        ordered['children'] = item['children']
    
    # Thêm các trường khác (nếu có)
    for key in item:
        if key not in ordered:
            ordered[key] = item[key]
    
    return ordered

def update_descriptions_recursive(target_list, desc_map, stats):
    """
    Hàm đệ quy để duyệt file đích, cập nhật description và sắp xếp lại thứ tự
    """
    result = []
    
    for item in target_list:
        # Sắp xếp lại thứ tự trường và cập nhật description
        ordered_item = reorder_item_fields(item, desc_map)
        
        # Thống kê
        if 'code' in item:
            code = item['code']
            if code in desc_map:
                source_desc = desc_map[code]
                old_desc = item.get('description', '')
                
                if not source_desc or source_desc.strip() == '':
                    # Description nguồn rỗng -> giữ rỗng
                    stats['kept_empty'] += 1
                elif not old_desc or old_desc.strip() == '':
                    # Tạo mới description
                    stats['created'] += 1
                    desc_preview = source_desc[:50] + '...' if len(source_desc) > 50 else source_desc
                    print(f"  [CREATED] {code}: {desc_preview}")
                else:
                    # Cập nhật description đã tồn tại
                    stats['updated'] += 1
                    desc_preview = source_desc[:50] + '...' if len(source_desc) > 50 else source_desc
                    print(f"  [UPDATED] {code}: {desc_preview}")
            else:
                # Code không tìm thấy trong nguồn
                stats['not_found'] += 1
        
        # Xử lý đệ quy children
        if 'children' in ordered_item and isinstance(ordered_item['children'], list):
            ordered_item['children'] = update_descriptions_recursive(
                ordered_item['children'], desc_map, stats
            )
        
        result.append(dict(ordered_item))
    
    return result

def main():
    # --- CẤU HÌNH ĐƯỜNG DẪN FILE ---
    file_nguon = '../../data/icd10_structure.json'       # File chứa mô tả chuẩn
    file_dich = '../../data/icd10_diseases_raw.json'     # File dữ liệu cần update
    file_xuat = '../../data/icd10_data_v1.json'   # File kết quả

    # 1. Kiểm tra tồn tại file
    if not os.path.exists(file_nguon):
        print(f"❌ Lỗi: Không tìm thấy file nguồn tại {file_nguon}")
        return
    if not os.path.exists(file_dich):
        print(f"❌ Lỗi: Không tìm thấy file đích tại {file_dich}")
        return

    # 2. Đọc dữ liệu
    try:
        with open(file_nguon, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        print("✅ Đã đọc file nguồn.")

        with open(file_dich, 'r', encoding='utf-8') as f:
            target_data = json.load(f)
        print("✅ Đã đọc file đích.\n")

    except json.JSONDecodeError as e:
        print(f"❌ Lỗi định dạng JSON: {e}")
        return

    # 3. Tạo bản đồ dữ liệu (Mapping) từ file nguồn
    description_map = build_description_map(source_data)
    print(f"📋 Đã tìm thấy {len(description_map)} mục mô tả trong file nguồn.")
    
    # Đếm số description không rỗng
    valid_descriptions = sum(1 for desc in description_map.values() if desc and desc.strip())
    print(f"📝 Trong đó có {valid_descriptions} mô tả hợp lệ (không rỗng).\n")

    # 4. Thực hiện cập nhật trên dữ liệu đích
    print("🔄 Bắt đầu cập nhật descriptions...\n")
    stats = {
        'created': 0,      # Tạo mới description
        'updated': 0,      # Cập nhật description đã tồn tại
        'kept_empty': 0,   # Giữ description rỗng (nguồn cũng rỗng)
        'not_found': 0     # Code không tìm thấy trong nguồn
    }
    
    result_data = update_descriptions_recursive(target_data, description_map, stats)
    
    print("\n" + "="*60)
    print("📊 KẾT QUẢ MAPPING:")
    print("="*60)
    print(f"✨ Tạo mới description:         {stats['created']} mục")
    print(f"🔄 Cập nhật description:        {stats['updated']} mục")
    print(f"📝 Giữ description rỗng:        {stats['kept_empty']} mục")
    print(f"⚠️  Không tìm thấy trong nguồn:  {stats['not_found']} mục")
    print(f"✅ Tổng xử lý thành công:       {stats['created'] + stats['updated']} mục")
    print("="*60 + "\n")

    # 5. Xuất ra file mới
    output_dir = os.path.dirname(file_xuat)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(file_xuat, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"💾 THÀNH CÔNG! File kết quả đã được lưu tại:")
        print(f"   {os.path.abspath(file_xuat)}")
    except Exception as e:
        print(f"❌ Có lỗi khi ghi file: {e}")

if __name__ == "__main__":
    main()