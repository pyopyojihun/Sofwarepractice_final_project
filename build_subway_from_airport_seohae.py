import csv
import pandas as pd
from pathlib import Path

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
AIRPORT_CSV = BASE_DIR / "국가철도공단_공항철도_역간거리_20250630.csv"
OUTPUT_CSV = BASE_DIR / "subway_airport_seohae.csv"

# =========================
# 공항철도 처리
# =========================
print("공항철도 데이터 처리 중...")
df_airport = pd.read_csv(AIRPORT_CSV, encoding="cp949")

airport_edges = []
line_name = "A"  # 공항철도는 A로 표시

# 연속된 역들끼리 엣지 만들기
# "후행역간거리"를 우선 사용, 없으면 다음 행의 "역간거리" 사용
prev_name = None
prev_dist = None

for idx, row in df_airport.iterrows():
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
    if idx + 1 < len(df_airport):
        next_row = df_airport.iloc[idx + 1]
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
    
    # 이전 역이 있고 이전 역의 거리가 있으면 엣지 추가
    if prev_name is not None and prev_dist is not None and prev_dist > 0:
        a = f"{prev_name}({line_name})"
        b = f"{name}({line_name})"
        airport_edges.append((a, b, prev_dist))
    
    prev_name = name
    prev_dist = dist

print(f"공항철도 엣지 개수: {len(airport_edges)}")

# =========================
# 서해남부선 처리 (수동 입력)
# =========================
print("\n서해남부선 데이터 처리 중...")
seohae_edges = []
line_name_seohae = "S"  # 서해남부선은 S로 표시

# 사용자가 제공한 데이터
seohae_stations = [
    ("홍성", "내포", 10.5),
    ("내포", "합덕", 14.1),
    ("합덕", "인주", 8.8),
    ("인주", "안중", 17.5),
    ("안중", "향남", 19.1),
    ("향남", "화성시청", 11.4),
    ("화성시청", "서화성", 7.3),
    ("서화성", "서해남부선종점", 1.3),
]

for prev_station, next_station, dist in seohae_stations:
    a = f"{prev_station}({line_name_seohae})"
    b = f"{next_station}({line_name_seohae})"
    seohae_edges.append((a, b, dist))

print(f"서해남부선 엣지 개수: {len(seohae_edges)}")

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
for a, b, _ in airport_edges + seohae_edges:
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
all_edges = airport_edges + seohae_edges + transfer_edges

with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f)
    for a, b, d in all_edges:
        wr.writerow([a, b, f"{d:.3f}"])

print(f"\n완료! {OUTPUT_CSV} 파일을 생성했습니다.")
print(f"총 엣지 개수: {len(all_edges)}")
print(f"  - 공항철도: {len(airport_edges)}개")
print(f"  - 서해남부선: {len(seohae_edges)}개")
print(f"  - 환승 엣지: {len(transfer_edges)}개")

