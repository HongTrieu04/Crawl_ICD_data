import ijson
import os
from neo4j import GraphDatabase

# ================= CẤU HÌNH =================
URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "neo4j123")
FILES = {
    "icd10": "../../data/icd10_embedded.json",
    "drugs": "../../data/drugs_embedded.json",
    "symptoms": "../../data/symptoms_embedded.json"
}
BATCH_SIZE = 500 

class VectorImporterStream:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    # Hàm hỗ trợ chuyển Decimal -> float
    def to_float_list(self, vector):
        if not vector:
            return []
        # Ép kiểu từng phần tử trong mảng sang float
        return [float(x) for x in vector]

    def update_icd10_vectors(self, file_path):
        print(f"🔄 Đang xử lý file {file_path} theo luồng...")
        
        query_normal = """
        MATCH (n) WHERE n.ID = $id
        SET n.name_vector = $nv, n.desc_vector = $dv
        """
        query_group = """
        MATCH (n:Group) WHERE n.ID = $id
        SET n.name_vector = $nv, n.desc_vector = $dv, n.code_vector = $cv
        """

        def process_node_recursive(item, session, index=None):
            node_type = item.get('type')
            node_id = item.get('code')
            
            if node_type == 'chapter' and index is not None:
                node_id = str(index)

            # --- SỬA LỖI TẠI ĐÂY: Ép kiểu sang float ---
            nv = self.to_float_list(item.get('name_vector', []))
            dv = self.to_float_list(item.get('desc_vector', []))
            
            params = {
                "id": node_id,
                "nv": nv,
                "dv": dv
            }

            if node_type == 'group':
                # Ép kiểu code_vector
                cv = self.to_float_list(item.get('code_vector', []))
                params["cv"] = cv
                session.run(query_group, **params)
            else:
                session.run(query_normal, **params)

            if 'children' in item:
                for child in item['children']:
                    process_node_recursive(child, session)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                with self.driver.session() as session:
                    chapters = ijson.items(f, 'item')
                    for i, chapter in enumerate(chapters, start=1):
                        print(f"   ↳ Đang update Chapter {i}...")
                        process_node_recursive(chapter, session, index=i)
            print("✅ Xong ICD-10.")
        except FileNotFoundError:
            print(f"⚠️ Không tìm thấy file {file_path}")

    def update_flat_vectors(self, file_path, label):
        print(f"🔄 Đang xử lý file {file_path} cho nhãn {label}...")
        
        query = f"""
        UNWIND $batch as row
        MATCH (n:{label} {{ID: row.id}})
        SET n.name_vector = row.name_vector,
            n.desc_vector = row.desc_vector
        """
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                with self.driver.session() as session:
                    items = ijson.items(f, 'item')
                    batch = []
                    count = 0
                    for item in items:
                        # --- SỬA LỖI TẠI ĐÂY: Ép kiểu sang float ---
                        nv = self.to_float_list(item.get('name_vector', []))
                        dv = self.to_float_list(item.get('desc_vector', []))

                        batch.append({
                            "id": item.get('id'),
                            "name_vector": nv,
                            "desc_vector": dv
                        })
                        
                        if len(batch) >= BATCH_SIZE:
                            session.run(query, batch=batch)
                            count += len(batch)
                            print(f"   ...Đã update {count} node {label}")
                            batch = [] 
                    
                    if batch:
                        session.run(query, batch=batch)
                        print(f"   ...Đã update {count + len(batch)} node {label}")
                        
            print(f"✅ Xong {label}.")
        except FileNotFoundError:
            print(f"⚠️ Không tìm thấy file {file_path}")

    def run(self):
        if os.path.exists(FILES['icd10']):
            self.update_icd10_vectors(FILES['icd10'])
        
        if os.path.exists(FILES['drugs']):
            self.update_flat_vectors(FILES['drugs'], "Drug")
            
        if os.path.exists(FILES['symptoms']):
            self.update_flat_vectors(FILES['symptoms'], "Symptom")

if __name__ == "__main__":
    importer = VectorImporterStream(URI, AUTH)
    try:
        importer.run()
    finally:
        importer.close()