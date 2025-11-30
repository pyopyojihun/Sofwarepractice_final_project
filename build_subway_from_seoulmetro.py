import csv
import math
import pandas as pd

# 1. 원본 파일 / 출력 파일 이름 설정
SRC = "서울교통공사_역간거리 및 소요시간_240810.csv"   # 네가 받은 파일 이름 그대로
DST = "subway_from_seoulmetro.csv"                   # 새로 만들 subway.csv 역할

# 2. CSV 읽기 (서울교통공사 파일은 cp949 인코딩)
df = pd.read_csv("/Users/pyojihun/Desktop/softwarepractice/subway_project/서울교통공사_역간거리 및 소요시간_20230614.csv", encoding="cp949")

# 3. 연속된 역들끼리 엣지 만들기
edges = []  # (역1(호선), 역2(호선), 거리km)

for line_no, group in df.groupby("호선"):
    group_sorted = group.sort_values("연번")

    prev_name = None
    for _, row in group_sorted.iterrows():
        name = str(row["역명"]).strip()
        dist = row["역간거리(km)"]

        # NaN 방지
        try:
            dist = float(dist)
        except (TypeError, ValueError):
            dist = 0.0

        if prev_name is not None:
            # prev_name -- name 사이의 edge 추가
            a = f"{prev_name}({line_no})"
            b = f"{name}({line_no})"
            edges.append((a, b, dist))

        prev_name = name

# 4. 같은 역 이름 + 서로 다른 호선 = 환승 엣지 추가
def normalize_station_name(name: str) -> str:
    if not name:
        return ""
    base = name.split("(")[0]
    base = base.replace("역", "").replace(" ", "").strip()
    return base

# 역명별로 몇 개의 호선이 있는지 확인
multi = df.groupby("역명")["호선"].nunique()
transfer_edges = []
transfer_dist_km = 0.3  # 환승 페널티 거리(km) (원하면 0.2~0.5 사이로 조절 가능)

for station_name in multi[multi > 1].index:
    sub = df[df["역명"] == station_name]
    lines = sorted(sub["호선"].unique())

    # 예: 고속터미널: [3,7] → (3,7) 쌍
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a = f"{station_name}({lines[i]})"
            b = f"{station_name}({lines[j]})"
            transfer_edges.append((a, b, transfer_dist_km))

print(f"일반 엣지 개수: {len(edges)}")
print(f"환승 엣지 개수: {len(transfer_edges)}")

# 5. 최종 CSV 쓰기
with open(DST, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f)
    for a, b, d in edges + transfer_edges:
        wr.writerow([a, b, f"{d:.3f}"])

print(f"완료! {DST} 파일을 생성했습니다.")
