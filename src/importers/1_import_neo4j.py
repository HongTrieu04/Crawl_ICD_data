import json
from neo4j import GraphDatabase

# ================= CẤU HÌNH KẾT NỐI NEO4J =================
# URI = "neo4j://20.249.211.169:7687" 
# AUTH = ("neo4j", "neo4j123") 
# FILE_PATH = "icd10_data.json" 

URI = "neo4j://127.0.0.1:7687" 
AUTH = ("neo4j", "neo4j123") 
FILE_PATH = "../../data/icd10_data.json" 

class ICDImporter:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Xóa toàn bộ dữ liệu cũ trong Database"""
        print("🗑️ Đang xóa dữ liệu cũ...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✅ Đã xóa sạch dữ liệu.")

    def create_constraints(self):
        """Tạo ràng buộc duy nhất (Unique Constraints) cho các ID để tối ưu hóa"""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chapter) REQUIRE c.ID IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (g:Group) REQUIRE g.ID IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.ID IS UNIQUE"
        ]
        with self.driver.session() as session:
            for q in queries:
                session.run(q)
            print("✅ Đã tạo các ràng buộc (Constraints) thành công.")

    def import_data(self, file_path):
        """Đọc file JSON và import vào Neo4j"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {file_path}")
            return

        with self.driver.session() as session:
            # Duyệt qua từng chương trong file JSON
            # start=1 để ID chương bắt đầu từ 1 thay vì 0
            for index, chapter_data in enumerate(data, start=1):
                
                # Gán ID chương bằng số thứ tự (1, 2, 3...)
                chapter_id = str(index) 
                
                print(f"⏳ Đang import Chương {chapter_id}: {chapter_data.get('name')}...")
                
                # Gọi hàm thực thi Cypher cho từng Chương (Batching theo chương)
                session.execute_write(self._create_chapter_structure, chapter_data, chapter_id)
                
            print("🎉 Hoàn tất import dữ liệu!")

    @staticmethod
    def _create_chapter_structure(tx, chapter_data, chapter_id):
        """
        Câu lệnh Cypher phức hợp để tạo Chương -> Nhóm -> Bệnh -> Bệnh con
        trong cùng một transaction để đảm bảo tính toàn vẹn.
        """
        query = """
        // 1. Tạo Node Chương (Chapter)
        MERGE (c:Chapter {ID: $chapter_id})
        SET c.name = $c_name,
            c.description = $c_desc,
            c.name_vector = [], 
            c.desc_vector = []

        // 2. Xử lý các Nhóm bệnh (Group) con của Chương này
        WITH c
        UNWIND $groups AS group_data
        MERGE (g:Group {ID: group_data.code})
        SET g.name = group_data.name,
            g.description = group_data.description,
            g.name_vector = [],
            g.code_vector = [] // Đã sửa dấu # thành // tại đây
        MERGE (g)-[:BELONGS_TO]->(c)

        // 3. Xử lý Bệnh chính (Disease) con của Nhóm
        WITH g, group_data
        UNWIND group_data.children AS disease_data
        // Chỉ lọc lấy những node là bệnh chính (đề phòng dữ liệu lạ)
        WITH g, disease_data WHERE disease_data.type = 'disease'
        MERGE (d:Disease {ID: disease_data.code})
        SET d.name = disease_data.name,
            d.description = disease_data.description,
            d.type = 'disease',
            d.synonym = "",         // Để trống
            d.desc_vector = []      // Để trống
        MERGE (d)-[:BELONGS_TO]->(g)

        // 4. Xử lý Bệnh con (Sub_disease) con của Bệnh chính
        WITH d, disease_data
        UNWIND disease_data.children AS sub_data
        WITH d, sub_data WHERE sub_data.type = 'sub_disease'
        MERGE (sd:Disease {ID: sub_data.code})
        SET sd.name = sub_data.name,
            sd.description = sub_data.description,
            sd.type = 'sub_disease',
            sd.synonym = "",
            sd.desc_vector = []
        MERGE (sd)-[:IS_A]->(d)
        """
        
        # Truyền tham số vào câu lệnh Cypher
        tx.run(query, 
               chapter_id=chapter_id,
               c_name=chapter_data.get('name', ''),
               c_desc=chapter_data.get('description', ''),
               groups=chapter_data.get('children', []) 
        )

if __name__ == "__main__":
    # Khởi tạo và chạy import
    importer = ICDImporter(URI, AUTH)
    try:
        importer.clear_database()
        
        importer.create_constraints()
        importer.import_data(FILE_PATH)
    finally:
        importer.close()