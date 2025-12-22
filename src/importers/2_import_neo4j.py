import json
from neo4j import GraphDatabase

# ================= CẤU HÌNH =================
URI = "neo4j://127.0.0.1:7687" 
AUTH = ("neo4j", "neo4j123") 
DRUG_FILE = "../../data/drug_data_grouped_translated.json"
SYMPTOM_FILE = "../../data/symptoms_extracted_data_translated.json"

class DetailImporter:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def create_constraints(self):
        """Tạo ràng buộc duy nhất cho ID của Thuốc và Triệu chứng"""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Drug) REQUIRE d.ID IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom) REQUIRE s.ID IS UNIQUE"
        ]
        with self.driver.session() as session:
            for q in queries:
                session.run(q)
            print("✅ Đã tạo Constraints cho Drug và Symptom.")

    def import_drugs(self, file_path):
        print(f"💊 Đang đọc file thuốc: {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {file_path}")
            return

        query = """
        UNWIND $batch AS item
        // 1. Tạo Node Thuốc
        MERGE (d:Drug {ID: item.id})
        SET d.code = item.code,
            d.name = item.name,
            d.scientific_name = item.scientific_name,
            d.description = item.description,
            d.name_vector = [],
            d.desc_vector = []
        
        // 2. Tạo quan hệ với Bệnh (Lookup các bệnh trong danh sách)
        WITH d, item
        UNWIND item.diseases AS disease_code
        // MATCH để chỉ nối với các bệnh ĐÃ CÓ trong DB
        MATCH (dis:Disease {ID: disease_code})
        MERGE (d)-[:TREATS]->(dis)
        """

        # Batching: Xử lý từng nhóm 1000 item để không quá tải
        batch_size = 1000
        with self.driver.session() as session:
            total = len(data)
            for i in range(0, total, batch_size):
                batch = []
                for item in data[i:i+batch_size]:
                    # Map các trường JSON sang cấu trúc Python dict chuẩn
                    batch.append({
                        "id": item.get("id"),
                        "code": item.get("mã thuốc", ""),
                        "name": item.get("tên thuốc", ""),
                        "scientific_name": item.get("tên y sinh", ""),
                        "description": item.get("mô tả", ""),
                        "diseases": item.get("danh sách bệnh", [])
                    })
                
                print(f"   ↳ Đang import batch thuốc {i} - {min(i+batch_size, total)}...")
                session.run(query, batch=batch)
        print("✅ Hoàn tất import Thuốc!")

    def import_symptoms(self, file_path):
        print(f"🌡️ Đang đọc file triệu chứng: {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {file_path}")
            return

        query = """
        UNWIND $batch AS item
        // 1. Tạo Node Triệu chứng
        MERGE (s:Symptom {ID: item.id})
        SET s.code = "",          // Dữ liệu trống theo yêu cầu
            s.name = item.name,
            s.description = "",   // Dữ liệu trống theo yêu cầu
            s.name_vector = [],
            s.desc_vector = []
        
        // 2. Tạo quan hệ Bệnh -> Có Triệu chứng
        WITH s, item
        UNWIND item.diseases AS disease_code
        MATCH (dis:Disease {ID: disease_code})
        MERGE (dis)-[:HAS_SYMPTOM]->(s)
        """

        batch_size = 1000
        with self.driver.session() as session:
            total = len(data)
            for i in range(0, total, batch_size):
                batch = []
                for item in data[i:i+batch_size]:
                    batch.append({
                        "id": item.get("id"),
                        "name": item.get("tên", ""),
                        "diseases": item.get("bệnh", [])
                    })
                
                print(f"   ↳ Đang import batch triệu chứng {i} - {min(i+batch_size, total)}...")
                session.run(query, batch=batch)
        print("✅ Hoàn tất import Triệu chứng!")

if __name__ == "__main__":
    importer = DetailImporter(URI, AUTH)
    try:
        importer.create_constraints()
        # Chạy lần lượt
        importer.import_drugs(DRUG_FILE)
        print("-" * 30)
        importer.import_symptoms(SYMPTOM_FILE)
    finally:
        importer.close()