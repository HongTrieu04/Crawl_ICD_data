import pandas as pd
from neo4j import GraphDatabase
import random
from tqdm import tqdm
import time
import os
import re

# ================= CẤU HÌNH =================
URI = "bolt://20.249.211.169:7687"
AUTH = ("neo4j", "neo4j123")
OUTPUT_DIR = "../../data/raw_sentences"
OUTPUT_PREFIX = "raw_sentences"
SENTENCES_PER_FILE = 3000

# MỤC TIÊU SỐ LƯỢNG (90k triplets)
TOTAL_TARGET = 90000
QUOTA = {
    "1-hop": int(TOTAL_TARGET * 0.35), # ~31,500
    "2-hop": int(TOTAL_TARGET * 0.50), # ~45,000
    "3-hop": int(TOTAL_TARGET * 0.15)  # ~13,500
}

MAX_PATHS_PER_DISEASE = {
    "1-hop": 5,   
    "2-hop": 8,
    "3-hop": 3
}

class AdvancedDataGenerator:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self.collected_data = []
        self.counters = {"1-hop": 0, "2-hop": 0, "3-hop": 0}
        self.file_counter = 1

    def close(self):
        self.driver.close()

    def get_all_diseases(self):
        """Lấy danh sách ID tất cả các bệnh"""
        print("📋 Đang lấy danh sách Index các bệnh...")
        query = "MATCH (d:Disease) RETURN d.ID as id, d.name as name"
        with self.driver.session() as session:
            result = session.run(query).data()
            random.shuffle(result)
            return result

    # ================= HÀM HỖ TRỢ XỬ LÝ TEXT =================
    def clean_text(self, text):
        """
        Làm sạch và trích xuất ý chính từ mô tả.
        - Loại bỏ ký tự xuống dòng.
        - Lấy câu đầu tiên trước dấu chấm.
        """
        if not text or not isinstance(text, str):
            return None
        
        # Xóa các ký tự đặc biệt đầu dòng như •, -, *
        cleaned = re.sub(r'^[\s•\-\*]+', '', text.strip())
        
        # Lấy câu đầu tiên (tách bởi dấu chấm hoặc xuống dòng)
        first_sentence = re.split(r'[.\n]', cleaned)[0]
        
        # Nếu câu quá ngắn (dưới 10 ký tự) hoặc rỗng thì bỏ qua
        if len(first_sentence) < 10:
            return None
            
        return first_sentence.strip()

    # ================= QUERY BUILDERS (ĐÃ CẬP NHẬT DESCRIPTION) =================
    
    def query_1_hop(self, disease_id, limit):
        """
        1-Hop: Lấy thêm mô tả của Bệnh, Thuốc, Nhóm
        """
        query = """
        MATCH (d:Disease {ID: $id})
        
        OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
        OPTIONAL MATCH (dr:Drug)-[:TREATS]->(d)
        OPTIONAL MATCH (d)-[:BELONGS_TO]->(g:Group)
        
        RETURN 
            d.name as disease,
            d.description as disease_desc,      // <--- Thêm mô tả bệnh
            s.name as symptom,
            dr.name as drug,
            dr.description as drug_desc,        // <--- Thêm mô tả thuốc
            g.name as group_name,
            g.description as group_desc         // <--- Thêm mô tả nhóm
        LIMIT $limit
        """
        return query

    def query_2_hop(self, disease_id, limit):
        """
        2-Hop: Lấy mô tả thuốc, bệnh cha, bệnh con
        """
        query = """
        MATCH (d:Disease {ID: $id})
        
        // Path 1: Thuốc -> Bệnh -> Triệu chứng
        OPTIONAL MATCH (dr:Drug)-[:TREATS]->(d)-[:HAS_SYMPTOM]->(s:Symptom)
        
        // Path 2: Bệnh con -> Bệnh cha -> Nhóm
        OPTIONAL MATCH (sub:Disease)-[:IS_A]->(d)-[:BELONGS_TO]->(g:Group)
        
        WITH d, dr, s, sub, g
        WHERE dr IS NOT NULL OR sub IS NOT NULL 

        RETURN 
            d.name as disease,
            d.description as disease_desc,      // <---
            dr.name as drug,
            dr.description as drug_desc,        // <---
            s.name as symptom,
            sub.name as sub_disease,
            sub.description as sub_desc,        // <---
            g.name as group_name
        LIMIT $limit
        """
        return query

    def query_3_hop(self, disease_id, limit):
        """
        3-Hop: Lấy mô tả Nhóm và Chương
        """
        query = """
        MATCH (d:Disease {ID: $id})
        MATCH (dr:Drug)-[:TREATS]->(d)-[:BELONGS_TO]->(g:Group)-[:BELONGS_TO]->(c:Chapter)
        
        RETURN 
            d.name as disease,
            dr.name as drug,
            g.name as group_name,
            g.description as group_desc,        // <---
            c.name as chapter_name,
            c.description as chapter_desc       // <---
        LIMIT $limit
        """
        return query

    # ================= TEMPLATE APPLIER (ĐÃ NÂNG CẤP) =================
    
    def process_result_to_text(self, record, hop_type):
        """Chuyển kết quả DB thành câu văn (Kết hợp mô tả)"""
        items = []
        
        # Lấy dữ liệu cơ bản
        d = record.get('disease')
        d_desc = self.clean_text(record.get('disease_desc'))
        
        if hop_type == "1-hop":
            # --- Xử lý Thuốc ---
            if record.get('drug'):
                dr = record['drug']
                dr_desc = self.clean_text(record.get('drug_desc'))
                
                # Template cơ bản
                base = f"{dr} là thuốc được chỉ định cho {d}."
                items.append(base)
                
                # Template nâng cao (nếu có mô tả thuốc)
                if dr_desc:
                    items.append(f"Thuốc {dr} ({dr_desc.lower()}) được sử dụng để điều trị {d}.")
            
            # --- Xử lý Nhóm ---
            if record.get('group_name'):
                grp = record['group_name']
                grp_desc = self.clean_text(record.get('group_desc'))
                
                items.append(f"{d} được phân loại thuộc nhóm {grp}.")
                if grp_desc:
                    items.append(f"Nhóm bệnh {grp}, bao gồm {grp_desc.lower()}, chứa các bệnh lý như {d}.")

            # --- Xử lý Mô tả Bệnh (Rất quan trọng) ---
            if d_desc:
                items.append(f"Về mặt lâm sàng, {d} là tình trạng {d_desc.lower()}.")
                items.append(f"Định nghĩa: {d_desc}.")

            # --- Xử lý Triệu chứng ---
            if record.get('symptom'):
                items.append(f"Một trong những dấu hiệu của {d} là {record['symptom']}.")

        elif hop_type == "2-hop":
            # --- Path: Thuốc -> Bệnh -> Triệu chứng ---
            if record.get('drug') and record.get('symptom'):
                dr = record['drug']
                s = record['symptom']
                dr_desc = self.clean_text(record.get('drug_desc'))
                
                # Template ngữ cảnh điều trị triệu chứng
                if d_desc:
                    items.append(f"Đối với {d} ({d_desc.lower()}), thuốc {dr} có thể được dùng khi bệnh nhân có biểu hiện {s}.")
                else:
                    items.append(f"Bệnh nhân {d} có triệu chứng {s} thường được điều trị bằng {dr}.")
            
            # --- Path: Bệnh con -> Bệnh cha -> Nhóm ---
            if record.get('sub_disease') and record.get('group_name'):
                sub = record['sub_disease']
                sub_desc = self.clean_text(record.get('sub_desc'))
                grp = record['group_name']
                
                base = f"{sub} là một biến thể của {d}, nằm trong nhóm {grp}."
                items.append(base)
                
                if sub_desc:
                    items.append(f"{sub} ({sub_desc.lower()}) được xếp vào nhóm {grp} cùng với {d}.")

        elif hop_type == "3-hop":
            # --- Path: Drug -> Disease -> Group -> Chapter ---
            if record.get('drug') and record.get('group_name') and record.get('chapter_name'):
                dr = record['drug']
                grp = record['group_name']
                chap = record['chapter_name']
                chap_desc = self.clean_text(record.get('chapter_desc'))
                
                items.append(f"Thuốc {dr} điều trị {d} (nhóm {grp}), thuộc chương {chap}.")
                
                if chap_desc:
                    items.append(f"Trong chương {chap} ({chap_desc.lower()}), {d} thuộc nhóm {grp} và có thể điều trị bằng {dr}.")

        return items

    # ================= FILE SAVING =================
    
    def save_batch(self):
        if not self.collected_data: return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"{OUTPUT_PREFIX}_part{self.file_counter:03d}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        df = pd.DataFrame(self.collected_data)
        df = df.sample(frac=1).reset_index(drop=True)
        df['label'] = True
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"💾 Đã lưu {len(self.collected_data)} câu vào: {filename}")
        
        self.collected_data = []
        self.file_counter += 1

    # ================= MAIN GENERATOR =================

    def generate(self):
        all_diseases = self.get_all_diseases()
        total_diseases = len(all_diseases)
        print(f"✅ Tìm thấy {total_diseases} bệnh. Bắt đầu sampling...")

        with self.driver.session() as session:
            pbar = tqdm(total=TOTAL_TARGET)
            
            for idx, disease_info in enumerate(all_diseases):
                d_id = disease_info['id']
                if all(self.counters[k] >= QUOTA[k] for k in QUOTA):
                    print("\n🎉 Đã đạt đủ chỉ tiêu số lượng!")
                    break

                # 1-HOP
                if self.counters["1-hop"] < QUOTA["1-hop"]:
                    res = session.run(self.query_1_hop(d_id, MAX_PATHS_PER_DISEASE["1-hop"]), id=d_id, limit=MAX_PATHS_PER_DISEASE["1-hop"]).data()
                    for r in res:
                        sentences = self.process_result_to_text(r, "1-hop")
                        for s in sentences:
                            self.collected_data.append({"text": s, "hop": "1-hop", "source_id": d_id})
                            self.counters["1-hop"] += 1
                            pbar.update(1)
                            if len(self.collected_data) >= SENTENCES_PER_FILE: self.save_batch()

                # 2-HOP
                if self.counters["2-hop"] < QUOTA["2-hop"]:
                    res = session.run(self.query_2_hop(d_id, MAX_PATHS_PER_DISEASE["2-hop"]), id=d_id, limit=MAX_PATHS_PER_DISEASE["2-hop"]).data()
                    for r in res:
                        sentences = self.process_result_to_text(r, "2-hop")
                        for s in sentences:
                            self.collected_data.append({"text": s, "hop": "2-hop", "source_id": d_id})
                            self.counters["2-hop"] += 1
                            pbar.update(1)
                            if len(self.collected_data) >= SENTENCES_PER_FILE: self.save_batch()

                # 3-HOP
                if self.counters["3-hop"] < QUOTA["3-hop"]:
                    res = session.run(self.query_3_hop(d_id, MAX_PATHS_PER_DISEASE["3-hop"]), id=d_id, limit=MAX_PATHS_PER_DISEASE["3-hop"]).data()
                    for r in res:
                        sentences = self.process_result_to_text(r, "3-hop")
                        for s in sentences:
                            self.collected_data.append({"text": s, "hop": "3-hop", "source_id": d_id})
                            self.counters["3-hop"] += 1
                            pbar.update(1)
                            if len(self.collected_data) >= SENTENCES_PER_FILE: self.save_batch()

            pbar.close()

        if self.collected_data:
            self.save_batch()

        print("\n📊 Thống kê kết quả:")
        print(f"   - 1-hop: {self.counters['1-hop']} câu")
        print(f"   - 2-hop: {self.counters['2-hop']} câu")
        print(f"   - 3-hop: {self.counters['3-hop']} câu")
        print(f"   - Tổng số file: {self.file_counter - 1} files")
        print(f"✅ Các file đã được lưu tại thư mục: {OUTPUT_DIR}")

if __name__ == "__main__":
    generator = AdvancedDataGenerator(URI, AUTH)
    try:
        generator.generate()
    finally:
        generator.close()


# import pandas as pd
# from neo4j import GraphDatabase
# import random
# from tqdm import tqdm
# import time
# import os

# # CẤU HÌNH NEO4J - THAY ĐỔI THÔNG TIN CỦA BẠN Ở ĐÂY
# URI = "bolt://20.249.211.169:7687" 
# AUTH = ("neo4j", "neo4j123")     

# # CẤU HÌNH OUTPUT - Lưu vào Google Drive
# OUTPUT_DIR = "Data/raw_sentences"
# OUTPUT_PREFIX = "raw_sentences"
# SENTENCES_PER_FILE = 3000

# # MỤC TIÊU SỐ LƯỢNG (90k câu)
# TOTAL_TARGET = 90000
# QUOTA = {
#     "1-hop": int(TOTAL_TARGET * 0.35), # ~31,500
#     "2-hop": int(TOTAL_TARGET * 0.50), # ~45,000
#     "3-hop": int(TOTAL_TARGET * 0.15)  # ~13,500
# }

# # GIỚI HẠN ĐỂ ĐẢM BẢO ĐA DẠNG
# MAX_PATHS_PER_DISEASE = {
#     "1-hop": 5,   
#     "2-hop": 8,
#     "3-hop": 3
# }

# print("⚙️ Cấu hình hoàn tất!")
# print(f"📍 Neo4j URI: {URI}")
# print(f"💾 Output folder: {OUTPUT_DIR}")
# class AdvancedDataGenerator:
#     def __init__(self, uri, auth):
#         self.driver = GraphDatabase.driver(uri, auth=auth)
#         self.collected_data = []
#         self.counters = {"1-hop": 0, "2-hop": 0, "3-hop": 0}
#         self.file_counter = 1

#     def close(self):
#         self.driver.close()

#     def get_all_diseases(self):
#         """Lấy danh sách ID tất cả các bệnh để sample ngẫu nhiên"""
#         print("📋 Đang lấy danh sách Index các bệnh...")
#         query = "MATCH (d:Disease) RETURN d.ID as id, d.name as name"
#         with self.driver.session() as session:
#             result = session.run(query).data()
#             random.shuffle(result)
#             return result

#     # ================= QUERY BUILDERS =================
    
#     def query_1_hop(self, disease_id, limit):
#         """1-Hop: Quan hệ trực tiếp."""
#         query = """
#         MATCH (d:Disease {ID: $id})
#         OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
#         OPTIONAL MATCH (dr:Drug)-[:TREATS]->(d)
#         OPTIONAL MATCH (d)-[:BELONGS_TO]->(g:Group)
        
#         RETURN 
#             d.name as disease,
#             s.name as symptom,
#             dr.name as drug,
#             g.name as group_name,
#             d.description as description
#         LIMIT $limit
#         """
#         return query

#     def query_2_hop(self, disease_id, limit):
#         """2-Hop: Ngữ cảnh phong phú."""
#         query = """
#         MATCH (d:Disease {ID: $id})
        
#         OPTIONAL MATCH (dr:Drug)-[:TREATS]->(d)-[:HAS_SYMPTOM]->(s:Symptom)
#         OPTIONAL MATCH (sub:Disease)-[:IS_A]->(d)-[:BELONGS_TO]->(g:Group)
        
#         WITH d, dr, s, sub, g
#         WHERE dr IS NOT NULL OR sub IS NOT NULL

#         RETURN 
#             d.name as disease,
#             dr.name as drug,
#             s.name as symptom,
#             sub.name as sub_disease,
#             g.name as group_name
#         LIMIT $limit
#         """
#         return query

#     def query_3_hop(self, disease_id, limit):
#         """3-Hop: Ngữ cảnh sâu."""
#         query = """
#         MATCH (d:Disease {ID: $id})
#         MATCH (dr:Drug)-[:TREATS]->(d)-[:BELONGS_TO]->(g:Group)-[:BELONGS_TO]->(c:Chapter)
        
#         RETURN 
#             d.name as disease,
#             dr.name as drug,
#             g.name as group_name,
#             c.name as chapter_name
#         LIMIT $limit
#         """
#         return query

#     # ================= TEMPLATE APPLIER =================
    
#     def process_result_to_text(self, record, hop_type):
#         """Chuyển kết quả Raw DB thành câu thô"""
#         items = []
#         d = record.get('disease')
        
#         if hop_type == "1-hop":
#             if record.get('symptom'):
#                 items.append(f"Bệnh {d} có biểu hiện lâm sàng là {record['symptom']}.")
#             if record.get('drug'):
#                 items.append(f"{record['drug']} là thuốc được dùng cho {d}.")
#             if record.get('group_name'):
#                 items.append(f"{d} thuộc nhóm bệnh {record['group_name']}.")
#             if record.get('description'):
#                 desc = record['description'].split('.')[0]
#                 if len(desc) > 20:
#                     items.append(f"Về {d}: {desc}.")

#         elif hop_type == "2-hop":
#             if record.get('drug') and record.get('symptom'):
#                 items.append(f"Bệnh nhân {d} có triệu chứng {record['symptom']} có thể được điều trị bằng {record['drug']}.")
#             if record.get('sub_disease') and record.get('group_name'):
#                 items.append(f"{record['sub_disease']} là một biến thể của {d}, thuộc nhóm {record['group_name']}.")

#         elif hop_type == "3-hop":
#             if record.get('drug') and record.get('group_name') and record.get('chapter_name'):
#                  items.append(f"Thuốc {record['drug']} điều trị {d} (nhóm {record['group_name']}), thuộc chương {record['chapter_name']}.")

#         return items

#     # ================= FILE SAVING =================
    
#     def save_batch(self):
#         """Lưu batch hiện tại ra file và reset collected_data"""
#         if not self.collected_data:
#             return
        
#         # Tạo thư mục nếu chưa có
#         os.makedirs(OUTPUT_DIR, exist_ok=True)
        
#         # Tạo tên file với số thứ tự
#         filename = f"{OUTPUT_PREFIX}_part{self.file_counter:03d}.csv"
#         filepath = os.path.join(OUTPUT_DIR, filename)
        
#         # Shuffle trước khi lưu
#         df = pd.DataFrame(self.collected_data)
#         df = df.sample(frac=1).reset_index(drop=True)
#         df['label'] = True
        
#         # Lưu file
#         df.to_csv(filepath, index=False, encoding='utf-8-sig')
#         print(f"💾 Đã lưu {len(self.collected_data)} câu vào: {filename}")
        
#         # Reset và tăng counter
#         self.collected_data = []
#         self.file_counter += 1

#     # ================= MAIN GENERATOR =================

#     def generate(self):
#         all_diseases = self.get_all_diseases()
#         total_diseases = len(all_diseases)
#         print(f"✅ Tìm thấy {total_diseases} bệnh. Bắt đầu sampling...")

#         with self.driver.session() as session:
#             pbar = tqdm(total=TOTAL_TARGET)
            
#             for idx, disease_info in enumerate(all_diseases):
#                 d_id = disease_info['id']
                
#                 # Kiểm tra đã đủ quota chưa
#                 if all(self.counters[k] >= QUOTA[k] for k in QUOTA):
#                     print("\n🎉 Đã đạt đủ chỉ tiêu số lượng!")
#                     break

#                 # --- 1-HOP ---
#                 if self.counters["1-hop"] < QUOTA["1-hop"]:
#                     res = session.run(self.query_1_hop(d_id, MAX_PATHS_PER_DISEASE["1-hop"]), 
#                                      id=d_id, limit=MAX_PATHS_PER_DISEASE["1-hop"]).data()
#                     for r in res:
#                         sentences = self.process_result_to_text(r, "1-hop")
#                         for s in sentences:
#                             self.collected_data.append({"text": s, "hop": "1-hop", "source_id": d_id})
#                             self.counters["1-hop"] += 1
#                             pbar.update(1)
                            
#                             if len(self.collected_data) >= SENTENCES_PER_FILE:
#                                 self.save_batch()

#                 # --- 2-HOP ---
#                 if self.counters["2-hop"] < QUOTA["2-hop"]:
#                     res = session.run(self.query_2_hop(d_id, MAX_PATHS_PER_DISEASE["2-hop"]), 
#                                      id=d_id, limit=MAX_PATHS_PER_DISEASE["2-hop"]).data()
#                     for r in res:
#                         sentences = self.process_result_to_text(r, "2-hop")
#                         for s in sentences:
#                             self.collected_data.append({"text": s, "hop": "2-hop", "source_id": d_id})
#                             self.counters["2-hop"] += 1
#                             pbar.update(1)
                            
#                             if len(self.collected_data) >= SENTENCES_PER_FILE:
#                                 self.save_batch()

#                 # --- 3-HOP ---
#                 if self.counters["3-hop"] < QUOTA["3-hop"]:
#                     res = session.run(self.query_3_hop(d_id, MAX_PATHS_PER_DISEASE["3-hop"]), 
#                                      id=d_id, limit=MAX_PATHS_PER_DISEASE["3-hop"]).data()
#                     for r in res:
#                         sentences = self.process_result_to_text(r, "3-hop")
#                         for s in sentences:
#                             self.collected_data.append({"text": s, "hop": "3-hop", "source_id": d_id})
#                             self.counters["3-hop"] += 1
#                             pbar.update(1)
                            
#                             if len(self.collected_data) >= SENTENCES_PER_FILE:
#                                 self.save_batch()

#             pbar.close()

#         # Lưu phần còn lại
#         if self.collected_data:
#             self.save_batch()

#         # Thống kê
#         print("\n📊 Thống kê kết quả:")
#         print(f"   - 1-hop: {self.counters['1-hop']} câu")
#         print(f"   - 2-hop: {self.counters['2-hop']} câu")
#         print(f"   - 3-hop: {self.counters['3-hop']} câu")
#         print(f"   - Tổng số file: {self.file_counter - 1} files")
#         print(f"✅ Các file đã được lưu tại: {OUTPUT_DIR}")
# # ============= BƯỚC 5: Kiểm tra kết nối Neo4j =============
# print("\n🔌 Đang kiểm tra kết nối Neo4j...")
# try:
#     test_driver = GraphDatabase.driver(URI, auth=AUTH)
#     with test_driver.session() as session:
#         result = session.run("RETURN 1 as test")
#         result.single()
#     test_driver.close()
#     print("✅ Kết nối Neo4j thành công!")
# except Exception as e:
#     print(f"❌ Lỗi kết nối Neo4j: {e}")
#     print("⚠️ Vui lòng kiểm tra lại URI và AUTH")

# # ============= BƯỚC 6: Chạy Generator =============
# print("\n🚀 Bắt đầu generate data...")
# print("=" * 60)

# generator = AdvancedDataGenerator(URI, AUTH)
# try:
#     generator.generate()
# except Exception as e:
#     print(f"❌ Lỗi khi chạy: {e}")
#     import traceback
#     traceback.print_exc()
# finally:
#     generator.close()
#     print("\n✅ Hoàn tất! Kiểm tra Google Drive của bạn.")

# # ============= BƯỚC 7: Kiểm tra kết quả =============
# print("\n📂 Danh sách file đã tạo:")
# if os.path.exists(OUTPUT_DIR):
#     files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv')])
#     for i, f in enumerate(files, 1):
#         filepath = os.path.join(OUTPUT_DIR, f)
#         size_mb = os.path.getsize(filepath) / (1024 * 1024)
#         print(f"   {i}. {f} ({size_mb:.2f} MB)")
# else:
#     print("   ⚠️ Chưa có file nào được tạo")