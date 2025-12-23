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

***Drive data:*** https://drive.google.com/drive/folders/1crWnVrS8N8EnB9uCnGX54rZbgkRwqRiR?usp=sharing

## 🚀 Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- Node.js 14+ (cho crawlers)
- Neo4j Database

### Cài đặt dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies
cd src/crawlers
npm install puppeteer
```

## 📋 Các thành phần chính

### 1. Crawlers (`src/crawlers/`)
- `3_crawler_chapter_group.js`: Crawl cấu trúc ICD-10 (chương và nhóm)
- `4_crawler_disease.js`: Crawl chi tiết bệnh từ ICD-10

### 2. Importers (`src/importers/`)
- `1_import_neo4j.py`: Import cấu trúc ICD-10 vào Neo4j
- `2_import_neo4j.py`: Import thuốc và triệu chứng vào Neo4j
- `4_import_vector.py`: Import vector embeddings vào Neo4j

### 3. ML/Embedding (`src/ml/`)
- `3_embeding.py`: Tạo embeddings cho dữ liệu
- `rag_embedding.py`: RAG embedding và query
- `finetune_slm.py`: Fine-tune model ngôn ngữ nhỏ
- `download_model.py`: Download models từ HuggingFace

### 4. Processors (`src/processors/`)
- `5_generate_sentences.py`: Tạo câu từ graph Neo4j
- `6_convert_data.py`: Chuyển đổi format dữ liệu test
- `9_pre-process_hpo.py`: Xử lý dữ liệu HPO
- `extract_disease_wiki.py`: Trích xuất dữ liệu bệnh từ Wikipedia
- `sort_disease_wiki.py`: Sắp xếp dữ liệu bệnh
- `icd10_parser.py`: Parse dữ liệu ICD-10
- `map_data.py`: Map và merge dữ liệu
- `translate.py`: Dịch dữ liệu

### 5. Utils (`src/utils/`)
- `7_evaluate.py`: Đánh giá model với vector injection
- `8_query_triplet.py`: Query triplets từ Neo4j

### 6. Notebooks (`notebooks/`)
- `slm-finetune.ipynb`: Jupyter notebook cho fine-tuning Small Language Model (Qwen3-0.6B)

## 🔧 Cấu hình

Các file cấu hình chính nằm trong từng script. Cần cập nhật:
- Neo4j connection (URI, username, password)
- Đường dẫn file dữ liệu
- Model paths

## 📝 Quy trình sử dụng

### 1. Crawl dữ liệu
```bash
cd src/crawlers
node 3_crawler_chapter_group.js
node 4_crawler_disease.js
```

### 2. Import vào Neo4j
```bash
cd src/importers
python 1_import_neo4j.py
python 2_import_neo4j.py
```

### 3. Tạo embeddings
```bash
cd src/ml
python 3_embeding.py
```

### 4. Import vectors
```bash
cd src/importers
python 4_import_vector.py
```

## 📊 Dữ liệu

### Nguồn dữ liệu
- **ICD-10**: [Hệ thống quản lý mã hóa lâm sàng khám chữa bệnh](https://icd.kcb.vn/icd-10/icd10)
- **Thuốc**: [Drugs, Active Ingredients and Diseases database](https://doi.org/10.6084/m9.figshare.7722062)

### Dữ liệu đã xử lý
Tất cả dữ liệu được lưu trong thư mục `data/`:
- `icd10_structure.json`: Cấu trúc ICD-10
- `icd10_diseases_raw.json`: Dữ liệu bệnh thô
- `icd10_data.json`: Dữ liệu ICD-10 đã xử lý
- `drug_data_grouped_translated.json`: Dữ liệu thuốc
- `symptoms_extracted_data_translated.json`: Dữ liệu triệu chứng


