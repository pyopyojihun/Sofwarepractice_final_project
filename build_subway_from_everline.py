import csv
import pandas as pd
from pathlib import Path

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
EVERLINE_CSV = BASE_DIR / "국가철도공단_에버라인 역간거리_20230425.csv"
OUTPUT_CSV = BASE_DIR / "subway_everline.csv"

# =========================
# 에버라인 처리
# =========================
print("에버라인 데이터 처리 중...")
df_everline = pd.read_csv(EVERLINE_CSV, encoding="cp949")

everline_edges = []
line_name = "E"  # 에버라인은 E로 표시

# 연속된 역들끼리 엣지 만들기
# "역간거리" 컬럼만 있으므로 다음 행의 역간거리를 사용
# 마지막 행의 경우 현재 행의 역간거리를 사용
prev_name = None

for idx, row in df_everline.iterrows():
    name = str(row["역명"]).strip()
    
    # 다음 행의 역간거리 확인 (현재 역에서 다음 역까지의 거리)
    dist = None
    if idx + 1 < len(df_everline):
        next_row = df_everline.iloc[idx + 1]
        dist = next_row["역간거리"]
    else:
        # 마지막 행의 경우 현재 행의 역간거리 사용
        dist = row["역간거리"]
    
    try:
        if pd.isna(dist) or dist == "" or dist == 0:
            dist = None
        else:
            dist = float(dist)
    except (TypeError, ValueError):
        dist = None
    
    # 이전 역이 있고 거리가 있으면 엣지 추가
    if prev_name is not None and dist is not None and dist > 0:
        a = f"{prev_name}({line_name})"
        b = f"{name}({line_name})"
        everline_edges.append((a, b, dist))
    
    prev_name = name

print(f"에버라인 엣지 개수: {len(everline_edges)}")

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
for a, b, _ in everline_edges:
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
all_edges = everline_edges + transfer_edges

with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f)
    for a, b, d in all_edges:
        wr.writerow([a, b, f"{d:.3f}"])

print(f"\n완료! {OUTPUT_CSV} 파일을 생성했습니다.")
print(f"총 엣지 개수: {len(all_edges)}")
print(f"  - 에버라인: {len(everline_edges)}개")
print(f"  - 환승 엣지: {len(transfer_edges)}개")

