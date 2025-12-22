import json
import csv
import sys
import time
from neo4j import GraphDatabase

# --- 1. CẤU HÌNH KẾT NỐI LOCAL ---
# Chỉnh lại mật khẩu cho đúng với máy của bạn
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"

# File đầu ra
OUTPUT_FILE = "../../data/triplets.csv"

# --- 2. KẾT NỐI ---
try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print(f"✅ Đã kết nối Neo4j tại {NEO4J_URI}")
except Exception as e:
    print(f"❌ Lỗi kết nối: {e}")
    print("-> Hãy kiểm tra xem Neo4j Desktop/Service đã bật chưa.")
    sys.exit(1)

# --- 3. CÂU TRUY VẤN (CYPHER) ---
# Lưu ý: ORDER BY rand() trên 700k node ở máy local có thể hơi chậm. 
# Nếu thấy quá lâu, hãy xóa "ORDER BY rand()" đi.
num_total_triplets_to_retrieve = 685766

cypher_query = f"""
MATCH (s:Group)-[r:BELONGS_TO]->(t:Chapter)
RETURN labels(s) AS source_type, properties(s) AS source_props, type(r) AS rel_type, properties(r) AS rel_props, labels(t) AS target_type, properties(t) AS target_props
UNION ALL
MATCH (s:Disease)-[r:BELONGS_TO]->(t:Group)
RETURN labels(s) AS source_type, properties(s) AS source_props, type(r) AS rel_type, properties(r) AS rel_props, labels(t) AS target_type, properties(t) AS target_props
UNION ALL
MATCH (s:Disease)-[r:HAS_SYMPTOM]->(t:Symptom)
RETURN labels(s) AS source_type, properties(s) AS source_props, type(r) AS rel_type, properties(r) AS rel_props, labels(t) AS target_type, properties(t) AS target_props
UNION ALL
MATCH (s1:Disease)-[r:IS_A]->(s2:Disease)
RETURN labels(s1) AS source_type, properties(s1) AS source_props, type(r) AS rel_type, properties(r) AS rel_props, labels(s2) AS target_type, properties(s2) AS target_props
UNION ALL
MATCH (s:Drug)-[r:TREATS]->(t:Disease)
RETURN labels(s) AS source_type, properties(s) AS source_props, type(r) AS rel_type, properties(r) AS rel_props, labels(t) AS target_type, properties(t) AS target_props
ORDER BY rand() LIMIT {num_total_triplets_to_retrieve}
"""

# --- 4. THỰC THI VÀ GHI FILE (STREAMING) ---
print(f"🚀 Bắt đầu truy vấn và ghi vào {OUTPUT_FILE}...")
start_time = time.time()

# Định nghĩa header cho CSV
csv_headers = ['id', 'source_labels', 'source_props', 'rel_type', 'rel_props', 'target_labels', 'target_props']

count = 0

with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=csv_headers)
    writer.writeheader()

    with driver.session() as session:
        # stream=True là mặc định, dữ liệu sẽ chảy về từng dòng thay vì tải hết cục lớn
        result = session.run(cypher_query)
        
        for i, record in enumerate(result):
            # -- Xử lý lọc bỏ embedding/vector để giảm dung lượng file --
            source_props = record['source_props'].copy()
            target_props = record['target_props'].copy()
            
            # Xóa các trường vector (nếu có)
            for props in [source_props, target_props]:
                keys_to_del = [k for k in props if k.endswith('_vector') or k in ['embedding', 'vector']]
                for k in keys_to_del:
                    del props[k]

            # -- Tạo dòng dữ liệu --
            row = {
                'id': f'triplet_{i+1}',
                'source_labels': ', '.join(record['source_type']),
                'source_props': json.dumps(source_props, ensure_ascii=False),
                'rel_type': record['rel_type'],
                'rel_props': json.dumps(record['rel_props'], ensure_ascii=False),
                'target_labels': ', '.join(record['target_type']),
                'target_props': json.dumps(target_props, ensure_ascii=False)
            }
            
            # -- Ghi xuống đĩa ngay lập tức --
            writer.writerow(row)
            count += 1
            
            # In tiến độ để biết code không bị đơ
            if count % 2000 == 0:
                sys.stdout.write(f"\r-> Đã xử lý: {count} dòng...")
                sys.stdout.flush()

end_time = time.time()
print(f"\n\n✅ Hoàn thành! Tổng cộng {count} triplets.")
print(f"⏱️ Thời gian chạy: {round(end_time - start_time, 2)} giây.")
print(f"📂 File kết quả: {OUTPUT_FILE}")

driver.close()