import csv
import pandas as pd
from pathlib import Path

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
BUNDANG_CSV = BASE_DIR / "국가철도공단_분당선_역간거리_20250630.csv"
INCHEON_CSV = BASE_DIR / "국가철도공단_인천교통공사 역간거리_20230425.csv"
OUTPUT_CSV = BASE_DIR / "subway_bundang_incheon.csv"

# =========================
# 분당선 처리
# =========================
print("분당선 데이터 처리 중...")
df_bundang = pd.read_csv(BUNDANG_CSV, encoding="cp949")

bundang_edges = []
line_name = "B"  # 분당선은 B로 표시

# 연속된 역들끼리 엣지 만들기
# "후행역간거리"를 우선 사용, 없으면 다음 행의 "역간거리" 사용
prev_name = None

for idx, row in df_bundang.iterrows():
    name = str(row["역명"]).strip()
    
    # 현재 행의 후행역간거리 사용 (다음 역까지의 거리)
    dist_next = row["후행역간거리"]
    try:
        if pd.isna(dist_next) or dist_next == "":
            dist_next = None
        else:
            dist_next = float(dist_next)
    except (TypeError, ValueError):
        dist_next = None
    
    # 다음 행의 역간거리도 확인 (현재 역에서 다음 역까지의 거리)
    dist_current = None
    if idx + 1 < len(df_bundang):
        next_row = df_bundang.iloc[idx + 1]
        dist_current = next_row["역간거리"]
        try:
            if pd.isna(dist_current) or dist_current == "":
                dist_current = None
            else:
                dist_current = float(dist_current)
        except (TypeError, ValueError):
            dist_current = None
    
    # 거리 결정: 후행역간거리 우선, 없으면 다음 행의 역간거리 사용
    dist = dist_next if dist_next is not None else dist_current
    
    # 이전 역이 있고 거리가 있으면 엣지 추가
    if prev_name is not None and dist is not None and dist > 0:
        a = f"{prev_name}({line_name})"
        b = f"{name}({line_name})"
        bundang_edges.append((a, b, dist))
    
    prev_name = name

print(f"분당선 엣지 개수: {len(bundang_edges)}")

# =========================
# 인천교통공사 처리
# =========================
print("\n인천교통공사 데이터 처리 중...")
df_incheon = pd.read_csv(INCHEON_CSV, encoding="cp949")

incheon_edges = []

# 선명별로 그룹화
for line_name, group in df_incheon.groupby("선명"):
    # 선명을 호선 번호로 변환
    if "7호선" in str(line_name):
        line_code = "I7"  # 인천 7호선
    elif "1호선" in str(line_name) or "인천1호선" in str(line_name):
        line_code = "I1"  # 인천 1호선
    elif "2호선" in str(line_name) or "인천2호선" in str(line_name):
        line_code = "I2"  # 인천 2호선
    else:
        line_code = "I" + str(line_name).replace("호선", "").strip()
    
    # 연속된 역들끼리 엣지 만들기
    prev_name = None
    for _, row in group.iterrows():
        name = str(row["역명"]).strip()
        dist = row["역간거리"]
        
        # NaN 또는 빈 값 처리
        try:
            if pd.isna(dist) or dist == "" or dist == 0:
                dist = 0.0
            else:
                dist = float(dist)
        except (TypeError, ValueError):
            dist = 0.0
        
        # 첫 번째 역은 거리가 0일 수 있음 (시작점)
        if prev_name is not None and dist > 0:
            a = f"{prev_name}({line_code})"
            b = f"{name}({line_code})"
            incheon_edges.append((a, b, dist))
        
        prev_name = name
    
    print(f"  {line_name} 엣지 개수: {len([e for e in incheon_edges if f"({line_code})" in e[0]])}")

print(f"인천교통공사 총 엣지 개수: {len(incheon_edges)}")

# =========================
# 환승 엣지 추가 (같은 역 이름 + 서로 다른 호선)
# =========================
def normalize_station_name(name: str) -> str:
    """역 이름 정규화 (괄호 앞까지만, '역', 공백 제거)"""
    if not name:
        return ""
    base = name.split("(")[0]
    base = base.replace("역", "").replace(" ", "").strip()
    return base

# 모든 역 정보 수집
all_stations = {}
for a, b, _ in bundang_edges + incheon_edges:
    name_a = normalize_station_name(a.split("(")[0])
    name_b = normalize_station_name(b.split("(")[0])
    line_a = a.split("(")[1].replace(")", "")
    line_b = b.split("(")[1].replace(")", "")
    
    if name_a not in all_stations:
        all_stations[name_a] = set()
    all_stations[name_a].add(line_a)
    
    if name_b not in all_stations:
        all_stations[name_b] = set()
    all_stations[name_b].add(line_b)

# 환승 엣지 생성
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

# =========================
# 최종 CSV 쓰기
# =========================
all_edges = bundang_edges + incheon_edges + transfer_edges

with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f)
    for a, b, d in all_edges:
        wr.writerow([a, b, f"{d:.3f}"])

print(f"\n완료! {OUTPUT_CSV} 파일을 생성했습니다.")
print(f"총 엣지 개수: {len(all_edges)}")

