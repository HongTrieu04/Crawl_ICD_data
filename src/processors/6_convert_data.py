import pandas as pd
import os

def process_test_file(input_path, output_path):
    print(f"📂 Đang đọc file: {input_path}")
    
    # 1. Đọc file (hỗ trợ cả CSV và Excel)
    if input_path.endswith('.csv'):
        df = pd.read_csv(input_path)
    elif input_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(input_path)
    else:
        raise ValueError("❌ Chỉ hỗ trợ file .csv hoặc .xlsx")

    # 2. Map tên cột từ file của bạn sang chuẩn của Model
    # Cấu trúc: 'Tên Cột Trong File Của Bạn': 'Tên Cột Chuẩn'
    column_mapping = {
        'Mệnh đề Câu hỏi (VIETNAMESE TEXT ONLY)': 'statement',
        'Đáp án (TRUE/FALSE)': 'answer'
    }
    
    # Kiểm tra xem file có đúng cột không
    for col in column_mapping.keys():
        if col not in df.columns:
            print(f"⚠️ Cảnh báo: Không tìm thấy cột '{col}' trong file.")
            print(f"   Các cột hiện có: {list(df.columns)}")
            return

    # Đổi tên cột
    df = df.rename(columns=column_mapping)

    # 3. Tạo cột context (Ngữ cảnh)
    # Vì dữ liệu test chỉ có câu hỏi đơn, ta để context là rỗng
    if 'context' not in df.columns:
        df['context'] = "" 

    # 4. Chuẩn hóa cột answer (True/False -> Đúng/Sai)
    def normalize_label(val):
        s = str(val).strip().lower()
        if s in ['true', '1', 't', 'yes', 'đúng']: return 'Đúng'
        if s in ['false', '0', 'f', 'no', 'sai']: return 'Sai'
        return 'Sai' # Mặc định

    if 'answer' in df.columns:
        df['answer'] = df['answer'].apply(normalize_label)

    # 5. Chọn và sắp xếp lại các cột cần thiết
    final_df = df[['context', 'statement', 'answer']]

    # 6. Lưu ra file mới
    final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✅ Xử lý xong! File đã được lưu tại: {output_path}")
    print(final_df.head())

# --- CÁCH SỬ DỤNG ---
# Thay đường dẫn file của bạn vào đây
INPUT_FILE = '../../data/data_test/Test_sample.v1.0.xlsx' 
OUTPUT_FILE = '../../data/data_test/data_test_normalize.csv'

# Chạy hàm
try:
    process_test_file(INPUT_FILE, OUTPUT_FILE)
except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")