import csv
import pandas as pd
from pathlib import Path

# 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent
SHINBUNDANG_CSV = BASE_DIR / "국가철도공단_신분당선_역간거리_20250630 (1).csv"
OUTPUT_CSV = BASE_DIR / "subway_shinbundang.csv"

# =========================
# 신분당선 처리
# =========================
print("신분당선 데이터 처리 중...")
df_shinbundang = pd.read_csv(SHINBUNDANG_CSV, encoding="cp949")

shinbundang_edges = []
line_name = "D"  # 신분당선은 D로 표시

# 연속된 역들끼리 엣지 만들기
# "후행역간거리"를 우선 사용, 없으면 다음 행의 "역간거리" 사용
prev_name = None
prev_dist = None

for idx, row in df_shinbundang.iterrows():
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
    if idx + 1 < len(df_shinbundang):
        next_row = df_shinbundang.iloc[idx + 1]
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
        shinbundang_edges.append((a, b, prev_dist))
    
    prev_name = name
    prev_dist = dist

print(f"신분당선 엣지 개수: {len(shinbundang_edges)}")

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
for a, b, _ in shinbundang_edges:
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
all_edges = shinbundang_edges + transfer_edges

with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f)
    for a, b, d in all_edges:
        wr.writerow([a, b, f"{d:.3f}"])

print(f"\n완료! {OUTPUT_CSV} 파일을 생성했습니다.")
print(f"총 엣지 개수: {len(all_edges)}")
print(f"  - 신분당선: {len(shinbundang_edges)}개")
print(f"  - 환승 엣지: {len(transfer_edges)}개")

