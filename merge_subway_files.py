import csv
from pathlib import Path

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
SEOULMETRO_CSV = BASE_DIR / "subway_from_seoulmetro.csv"
BUNDANG_INCHEON_CSV = BASE_DIR / "subway_bundang_incheon.csv"
AIRPORT_SEOHAE_CSV = BASE_DIR / "subway_airport_seohae.csv"
SHINBUNDANG_CSV = BASE_DIR / "subway_shinbundang.csv"
EVERLINE_CSV = BASE_DIR / "subway_everline.csv"
MERGED_CSV = BASE_DIR / "subway_merged.csv"

print("지하철 데이터 파일 병합 중...")

# 기존 서울교통공사 데이터 읽기
seoulmetro_edges = []
with open(SEOULMETRO_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 3:
            seoulmetro_edges.append((row[0], row[1], row[2]))

print(f"서울교통공사 엣지 개수: {len(seoulmetro_edges)}")

# 분당선/인천교통공사 데이터 읽기
bundang_incheon_edges = []
with open(BUNDANG_INCHEON_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 3:
            bundang_incheon_edges.append((row[0], row[1], row[2]))

print(f"분당선/인천교통공사 엣지 개수: {len(bundang_incheon_edges)}")

# 공항철도/서해남부선 데이터 읽기
airport_seohae_edges = []
with open(AIRPORT_SEOHAE_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 3:
            airport_seohae_edges.append((row[0], row[1], row[2]))

print(f"공항철도/서해남부선 엣지 개수: {len(airport_seohae_edges)}")

# 신분당선 데이터 읽기
shinbundang_edges = []
with open(SHINBUNDANG_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 3:
            shinbundang_edges.append((row[0], row[1], row[2]))

print(f"신분당선 엣지 개수: {len(shinbundang_edges)}")

# 에버라인 데이터 읽기
everline_edges = []
with open(EVERLINE_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) >= 3:
            everline_edges.append((row[0], row[1], row[2]))

print(f"에버라인 엣지 개수: {len(everline_edges)}")

# 병합
all_edges = seoulmetro_edges + bundang_incheon_edges + airport_seohae_edges + shinbundang_edges + everline_edges

# =========================
# 환승 엣지 생성 (모든 파일 간)
# =========================
def normalize_station_name(name: str) -> str:
    """역 이름 정규화 (괄호 앞까지만, '역', 공백 제거)"""
    if not name:
        return ""
    # 괄호가 여러 개 있을 수 있으므로 첫 번째 괄호 앞까지만 추출
    # 예: "기흥(백남준아트센터)(B)" -> "기흥"
    base = name.split("(")[0]
    base = base.replace("역", "").replace(" ", "").replace("·", "").strip()
    return base

# 모든 역 정보 수집 (역명 -> 호선 리스트)
all_stations = {}
for a, b, _ in all_edges:
    # 역 이름 추출 (첫 번째 괄호 앞까지)
    name_a = normalize_station_name(a.split("(")[0])
    name_b = normalize_station_name(b.split("(")[0])
    
    # 호선 추출 (마지막 괄호에서)
    # 예: "기흥(백남준아트센터)(B)" -> "B"
    if "(" in a and ")" in a:
        line_a = a.split("(")[-1].replace(")", "")
    else:
        line_a = ""
    
    if "(" in b and ")" in b:
        line_b = b.split("(")[-1].replace(")", "")
    else:
        line_b = ""
    
    if name_a not in all_stations:
        all_stations[name_a] = set()
    all_stations[name_a].add(line_a)
    
    if name_b not in all_stations:
        all_stations[name_b] = set()
    all_stations[name_b].add(line_b)

# 환승 엣지 생성 (같은 역 이름 + 서로 다른 호선)
transfer_edges = []
transfer_dist_km = 0.3  # 환승 페널티 거리(km)

for station_name, lines in all_stations.items():
    if len(lines) > 1:
        lines_list = sorted(list(lines))
        for i in range(len(lines_list)):
            for j in range(i + 1, len(lines_list)):
                a = f"{station_name}({lines_list[i]})"
                b = f"{station_name}({lines_list[j]})"
                transfer_edges.append((a, b, transfer_dist_km))

print(f"\n환승 엣지 개수: {len(transfer_edges)}")

# 환승 엣지를 all_edges에 추가
all_edges = all_edges + transfer_edges

# 중복 제거 (같은 (a, b) 쌍이 있으면 하나만 유지)
unique_edges = {}
for a, b, d in all_edges:
    key1 = (a, b)
    key2 = (b, a)
    if key1 not in unique_edges and key2 not in unique_edges:
        unique_edges[key1] = d
    elif key1 in unique_edges:
        # 이미 있으면 더 작은 거리 사용
        if float(d) < float(unique_edges[key1]):
            unique_edges[key1] = d
    elif key2 in unique_edges:
        # 역방향이 있으면 더 작은 거리 사용
        if float(d) < float(unique_edges[key2]):
            del unique_edges[key2]
            unique_edges[key1] = d

# 최종 엣지 리스트 생성
final_edges = [(a, b, d) for (a, b), d in unique_edges.items()]

print(f"병합 후 총 엣지 개수: {len(final_edges)}")

# 병합된 파일 저장
with open(MERGED_CSV, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    for a, b, d in final_edges:
        writer.writerow([a, b, d])

print(f"\n완료! {MERGED_CSV} 파일을 생성했습니다.")
print(f"서울교통공사: {len(seoulmetro_edges)}개")
print(f"분당선/인천교통공사: {len(bundang_incheon_edges)}개")
print(f"공항철도/서해남부선: {len(airport_seohae_edges)}개")
print(f"신분당선: {len(shinbundang_edges)}개")
print(f"에버라인: {len(everline_edges)}개")
print(f"병합 후: {len(final_edges)}개")

