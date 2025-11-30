import streamlit as st
import csv
import folium
import math
import requests
from pathlib import Path

st.set_page_config(page_title="지하철 만남 지점 추천 서비스", layout="wide")
# =========================
# 커스텀 CSS 스타일
# =========================
st.markdown("""
<style>
    /* 메인 컨테이너 스타일 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* 타이틀 스타일 */
    h1 {
        color: #1f77b4;
        text-align: center;
        padding-bottom: 1rem;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    
    /* 서브헤더 스타일 */
    h2, h3 {
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* 정보 박스 스타일 */
    .stSuccess, .stInfo {
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* 입력 필드 스타일 */
    .stSelectbox, .stTextInput, .stNumberInput {
        margin-bottom: 1rem;
    }
    
    /* 카드 스타일 */
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .path-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
        color: #000000;
    }
    
    .path-card * {
        color: #000000 !important;
    }
    
    /* 지도 컨테이너 */
    .map-container {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Dijkstra 알고리즘 클래스
# =========================
class Dijkstra:
    def __init__(self, nodes):
        self.nodes = nodes
        self.visits = set()
        self.graph = []
        self.cost = {}
        for node in self.nodes:
            # [해당 노드까지의 최소 비용, 부모 노드]
            self.cost[node] = [float("inf"), None]

    def setEdge(self, a, b, w):
        # a, b: 노드 ID, w: 가중치(여기서는 "시간(분)")
        self.graph.append((a, b, w))

    def getPath(self, start, end):
        # nodes를 복사하여 사용 (원본을 변경하지 않기 위해)
        remaining_nodes = self.nodes.copy()
        curNode = start
        self.cost[curNode][0] = 0

        while True:
            self.visits.add(curNode)
            remaining_nodes.discard(curNode)
            neighbors = self._neighbor(curNode)

            # 인접 노드까지의 비용 갱신
            for node in neighbors:
                new_cost = self.cost[curNode][0] + self._getWeight(curNode, node)
                if new_cost < self.cost[node][0]:
                    self.cost[node][0] = new_cost
                    self.cost[node][1] = curNode

            if len(remaining_nodes) > 0:
                curNode = self._dicFilter(remaining_nodes)
                if curNode is None:
                    break
            else:
                break

        # start -> end 경로 복원
        if self.cost[end][0] == float("inf"):
            return []  # 도달 불가

        path = [end]
        temp_end = end
        while temp_end != start:
            parent = self.cost[temp_end][1]
            if parent is None:
                break
            path.append(parent)
            temp_end = parent

        return path[::-1]

    def _neighbor(self, curNode):
        neighbor = {}
        for node in self.graph:
            if node[0] == curNode:
                neighbor[node[1]] = node[2]
            elif node[1] == curNode:
                neighbor[node[0]] = node[2]
        return neighbor

    def _getWeight(self, n1, n2):
        for node in self.graph:
            if node[0] == n1 and node[1] == n2:
                return node[2]
            elif node[0] == n2 and node[1] == n1:
                return node[2]
        return None

    def _dicFilter(self, remaining_nodes):
        import sys
        mini = sys.maxsize
        curNode = None
        for key, value in self.cost.items():
            if key in remaining_nodes and value[0] < mini:
                mini = value[0]
                curNode = key
        return curNode

    def reset(self):
        self.visits = set()
        for node in self.nodes:
            self.cost[node] = [float("inf"), None]


# =========================
# 전역 상수 및 설정
# =========================

BASE_DIR = Path(__file__).resolve().parent
SUBWAY_LOCATION_CSV = BASE_DIR / "subwayLocation.csv"
SUBWAY_CSV = BASE_DIR / "subway_merged.csv"


# 지하철 평균 속도(km/h)
AVG_SPEED_KMH = 34

# Edge 별 거리/시간 저장용 전역 딕셔너리
edge_distance = {}  # (n1, n2) -> 거리(km)
edge_time = {}      # (n1, n2) -> 시간(분)

# 카카오 REST API 키 
KAKAO_REST_API_KEY = "2d03da2d8820fb8b46997aa45603523c"



# =========================
# 데이터 로딩
# =========================


@st.cache_data
def load_subway_data():
    """지하철역 위치 및 연결 정보를 로드"""
    global edge_distance, edge_time
    edge_distance = {}
    edge_time = {}

    subwayLoc = {}
    nodes = set()
    
    # 지하철역 위치 정보 로드
    with open(SUBWAY_LOCATION_CSV, 'r', encoding='utf-8-sig') as f:
        rdr = csv.reader(f)
        for line in rdr:
            # line[0]: 역 이름, line[1]: 위도, line[2]: 경도
            if line[0] not in subwayLoc:
                subwayLoc[line[0]] = [float(line[1]), float(line[2])]
    
    # 지하철역 간 연결 정보 로드 (노드 집합 구성)
    with open(SUBWAY_CSV, 'r', encoding='utf-8-sig') as f:
        rdr = csv.reader(f)
        for line in rdr:
            temp1 = line[0]
            temp2 = line[1]
            nodes.add(temp1)
            nodes.add(temp2)
    
    # Dijkstra 그래프 구성 (weight = 시간(분))
    d = Dijkstra(nodes)
    with open(SUBWAY_CSV, 'r', encoding='utf-8-sig') as f:
        rdr = csv.reader(f)
        for line in rdr:
            n1, n2 = line[0], line[1]
            dist_km = float(line[2])  # 3번째 컬럼이 거리(km)라고 가정

            # 거리(km) -> 시간(분) 환산
            time_min = dist_km * 60.0 / AVG_SPEED_KMH

            edge_distance[(n1, n2)] = dist_km
            edge_distance[(n2, n1)] = dist_km
            edge_time[(n1, n2)] = time_min
            edge_time[(n2, n1)] = time_min

            d.setEdge(n1, n2, time_min)
    
    return subwayLoc, nodes, d, edge_distance, edge_time


# =========================
# 유틸 함수들
# =========================

def kakao_keyword_search(query):
    """
    '인하대병원', '서울역' 같은 키워드를 카카오 로컬 API로 검색해서
    첫 번째 결과의 (lat, lng, place_name)을 반환
    """
    if not KAKAO_REST_API_KEY:
        st.error("카카오 REST API 키가 설정되어 있지 않습니다.")
        return None
    
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query, "size": 5}

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        st.error(f"카카오 API 요청 실패: {resp.status_code}")
        st.write(resp.text)
        return None

    data = resp.json()
    docs = data.get("documents", [])
    if not docs:
        st.warning("검색 결과가 없습니다.")
        return None
    
    first = docs[0]
    lat = float(first["y"])
    lng = float(first["x"])
    place_name = first["place_name"]
    return lat, lng, place_name


def find_nearest_station(subwayLoc, user_lat, user_lng):
    """
    사용자 위도/경도와 가장 가까운 지하철역(subwayLoc key)을 찾는다.
    """
    min_dist = float("inf")
    nearest_name = None

    for name, (lat, lng) in subwayLoc.items():
        d = math.hypot(lat - user_lat, lng - user_lng)
        if d < min_dist:
            min_dist = d
            nearest_name = name

    return nearest_name


def normalize_station_name(name: str) -> str:
    # 역 이름 비교용: 괄호 앞까지만, '역', 공백 제거
    if not name:
        return ""
    # 예: "홍대입구(2)" -> "홍대입구"
    base = name.split("(")[0]
    base = base.replace("역", "").replace(" ", "").strip()
    return base

def find_station_id_by_name(station_name, nodes):
    """
    subwayLoc에서 온 station_name과 subway.csv의 노드ID(예: '홍대입구(2)')를
    최대한 유연하게 매칭
    """
    target = normalize_station_name(station_name)

    for n in nodes:
        node_base = normalize_station_name(n)
        if node_base == target:
            return n
    return None



def kakao_search_hotplaces(lat, lng, radius=1000, category_group_code="FD6"):
    """
    특정 좌표 주변의 맛집/카페 등 핫플 추천
      - FD6: 음식점
      - CE7: 카페
      - AT4: 관광명소
    """
    if not KAKAO_REST_API_KEY:
        return []

    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "category_group_code": category_group_code,
        "x": lng,
        "y": lat,
        "radius": radius,
        "size": 10,
        "sort": "distance"
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        st.write("카카오 카테고리 검색 실패", resp.status_code, resp.text)
        return []

    data = resp.json()
    docs = data.get("documents", [])
    results = []
    for d in docs:
        results.append({
            "name": d["place_name"],
            "address": d.get("road_address_name") or d.get("address_name"),
            "lat": float(d["y"]),
            "lng": float(d["x"]),
            "distance": int(d.get("distance", 0))
        })
    return results


def compute_all_costs_from(start_station_id, nodes, dijkstra: Dijkstra):
    """
    한 출발역에서 모든 역까지의 최단 소요 시간을 계산해서 dict로 반환
    """
    dijkstra.reset()
    _ = dijkstra.getPath(start_station_id, start_station_id)
    return {node: dijkstra.cost[node][0] for node in nodes}


def find_best_meeting_station(start_station_ids, nodes, dijkstra: Dijkstra):
    """
    여러 출발역(start_station_ids)에서 출발할 때
    총 소요 시간이 최소가 되는 만남역을 찾는다.
    """
    all_costs = {}
    for s in start_station_ids:
        all_costs[s] = compute_all_costs_from(s, nodes, dijkstra)

    best_station = None
    best_total_time = float("inf")

    for candidate in nodes:
        total_time = 0
        unreachable = False
        for s in start_station_ids:
            t = all_costs[s].get(candidate, float("inf"))
            if t == float("inf"):
                unreachable = True
                break
            total_time += t
        
        if unreachable:
            continue

        if total_time < best_total_time:
            best_total_time = total_time
            best_station = candidate

    return best_station, best_total_time, all_costs


def get_path_distance_and_time(pathList, edge_distance, edge_time):
    """
    pathList(노드ID 리스트)에 대해
    총 거리(km)와 총 시간(분)을 계산
    """
    total_dist = 0.0
    total_time = 0.0
    for i in range(len(pathList) - 1):
        a = pathList[i]
        b = pathList[i+1]
        d = edge_distance.get((a, b), 0.0)
        t = edge_time.get((a, b), 0.0)
        total_dist += d
        total_time += t
    return total_dist, total_time


# =========================
# 메인 앱 로직
# =========================

# 메인 타이틀
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem;">🚇 지하철 기반 최적 만남 지점 & 경로 추천 서비스</h1>
    <p style="color: #666; font-size: 1.1rem;">최단 경로 찾기와 다중 인원 만남 지점 추천</p>
</div>
""", unsafe_allow_html=True)

# 데이터 로드
with st.spinner("지하철 데이터를 불러오는 중..."):
    subwayLoc, nodes, dijkstra, edge_distance, edge_time = load_subway_data()
    station_list = sorted(list(nodes))

st.markdown("<br>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.5], gap="large")

# -------------------------
# 왼쪽: 컨트롤/입력
# -------------------------
with col1:
    tab1, tab2 = st.tabs(["단일 경로 찾기", "다중 인원 만남 지점"])

    # -------------------------
    # 탭 1: 단일 경로 (기본 기능)
    # -------------------------
    with tab1:
        st.markdown("### 🎯 단일 출발-도착 최단경로")
        st.markdown("출발역과 도착역을 선택하여 최단 경로를 찾아보세요.")

        start_station = st.selectbox(
            "📍 출발역",
            options=[""] + station_list,
            index=0,
            key="single_start"
        )

        destination_station = st.selectbox(
            "🎯 도착역",
            options=[""] + station_list,
            index=0,
            key="single_destination"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        find_path_button = st.button(
            "🔍 경로 찾기", type="primary",
            use_container_width=True, key="single_btn"
        )

        if find_path_button:
            if not start_station or not destination_station:
                st.error("출발역과 도착역을 모두 선택해주세요.")
            elif start_station == destination_station:
                st.warning("출발역과 도착역이 같습니다.")
            else:
                dijkstra.reset()
                pathList = dijkstra.getPath(start_station, destination_station)

                if pathList:
                    pathNames = []
                    pathLine = []
                    for item in pathList:
                        # 괄호 앞까지만 역 이름 추출 (예: "원인재(B)" -> "원인재", "원인재(I1)" -> "원인재")
                        if "(" in item:
                            station_name = item.split("(")[0]
                            line_part = item.split("(")[1].rstrip(")")
                            # 호선 번호만 추출 (예: "I1" -> "I1", "B" -> "B")
                            line_num = line_part
                        else:
                            station_name = item
                            line_num = ""
                        pathNames.append(station_name)
                        pathLine.append(line_num)

                    total_dist, total_time = get_path_distance_and_time(pathList, edge_distance, edge_time)

                    st.success(f"✅ 경로를 찾았습니다! (총 {len(pathList)}개 역 경유)")
                    st.markdown("---")
                    
                    st.markdown("### 📍 경로 정보")
                    path_text = " → ".join(
                        [f"{name}({line})" for name, line in zip(pathNames, pathLine)]
                    )
                    st.markdown(f'<div class="path-card">{path_text}</div>', unsafe_allow_html=True)

                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.metric("📏 총 거리", f"{total_dist:.2f} km", delta=None)
                    with col_info2:
                        st.metric("⏱️ 예상 소요 시간", f"{total_time:.1f} 분", delta=f"평균 시속 {AVG_SPEED_KMH} km/h")

                    st.session_state["mode"] = "single"
                    st.session_state["single_pathList"] = pathList
                    st.session_state["single_pathNames"] = pathNames
                    st.session_state["single_pathLine"] = pathLine
                else:
                    st.error("경로를 찾을 수 없습니다.")

    # -------------------------
    # 탭 2: 다중 인원 최적 만남 지점
    # -------------------------
    with tab2:
        st.markdown("### 👥 다중 인원 최적 만남 지점 찾기")
        st.markdown("여러 사람이 만나기 가장 좋은 지하철역을 찾아드립니다.")

        # 세션 상태에 인원 수 저장 (초기값 설정)
        if "num_people" not in st.session_state:
            st.session_state["num_people"] = 3
        
        num_people = st.number_input(
            "👤 인원 수 선택",
            min_value=2,
            max_value=5,
            value=st.session_state["num_people"],
            step=1,
            key="num_people",
            help="2명부터 5명까지 선택 가능합니다."
        )

        location_mode = st.radio(
            "📍 출발 위치 입력 방식",
            ["직접 역 선택", "장소 검색(예: 인하대병원)"],
            index=1,
            horizontal=True
        )

        start_station_ids = []

        start_station_ids = []

        for i in range(num_people):
            st.markdown(f"#### 👤 {i+1}번 사람 출발지")
            with st.container():
                if location_mode == "직접 역 선택":
                    # key를 person_{i}_station으로 통일 (검색 모드와 동일한 세션키)
                    st.selectbox(
                        f"{i+1}번 사람 출발역",
                        options=[""] + station_list,
                        key=f"person_{i}_station",
                        label_visibility="visible"
                    )
                    # 즉시 append하지 않고 아래에서 session_state로 한 번만 읽습니다.

                elif location_mode == "장소 검색(예: 인하대병원)":
                    query = st.text_input(
                        f"{i+1}번 사람 출발 위치 검색",
                        key=f"person_{i}_query",
                        placeholder="예: 인하대병원, 서울역, 잠실 롯데월드...",
                        help="장소명을 입력하고 검색 버튼을 클릭하세요."
                    )

                    col_search1, col_search2 = st.columns([3, 1])
                    with col_search1:
                        search_clicked = st.button(f"🔍 검색", key=f"person_{i}_search_btn", use_container_width=True)
                    with col_search2:
                        if st.session_state.get(f"person_{i}_station"):
                            st.success("✓")
                    
                    # 검색 결과 표시 (이미 검색된 경우)
                    if st.session_state.get(f"person_{i}_search_result") and not search_clicked:
                        result_info = st.session_state[f"person_{i}_search_result"]
                        st.success(f"✅ '{result_info['place_name']}' 위치를 사용합니다.")
                        st.info(f"🚇 가장 가까운 지하철역: **{result_info['nearest_name']}**")
                    
                    if search_clicked:
                        if not query:
                            st.warning("⚠️ 검색어를 입력해주세요.")
                        else:
                            with st.spinner("검색 중..."):
                                result = kakao_keyword_search(query)
                            if result is not None:
                                lat, lng, place_name = result
                                
                                nearest_name = find_nearest_station(subwayLoc, lat, lng)
                                station_id = find_station_id_by_name(nearest_name, nodes)
                                if station_id:
                                    st.session_state[f"person_{i}_station"] = station_id
                                    st.session_state[f"person_{i}_search_result"] = {
                                        "place_name": place_name,
                                        "nearest_name": nearest_name
                                    }
                                    st.success(f"✅ '{place_name}' 위치를 사용합니다.")
                                    st.info(f"🚇 가장 가까운 지하철역: **{nearest_name}**")
                                else:
                                    st.error("❌ 해당 역 이름에 해당하는 노드를 찾지 못했습니다.")
                                    st.session_state[f"person_{i}_search_result"] = None

                # 루프 밖에서 한 번만 세션에서 읽어 append
                station_id = st.session_state.get(f"person_{i}_station", "")
                start_station_ids.append(station_id)
            st.markdown("<br>", unsafe_allow_html=True)
# ...existing code...

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(
            "🎯 최적 만남역 찾기",
            type="primary", use_container_width=True,
            key="meeting_btn"
        ):
            if any(not s for s in start_station_ids):
                st.error("모든 사람의 출발역(또는 검색 결과)을 설정해주세요.")
            else:
                best_station, best_total_time, all_costs = find_best_meeting_station(
                    start_station_ids, nodes, dijkstra
                )
                if best_station is None:
                    st.error("❌ 모든 사람이 도달 가능한 공통 역을 찾지 못했습니다.")
                else:
                    # 괄호 앞까지만 역 이름 추출
                    if "(" in best_station:
                        best_station_name = best_station.split("(")[0]
                    else:
                        best_station_name = best_station
                    st.markdown("---")
                    st.markdown(f"""
                    <div class="info-card">
                        <h2 style="color: white; margin: 0 ;">⭐ 최적 만남역</h2>
                        <h1 style="color: white; margin: 0.5rem 0;">{best_station_name}</h1>
                        <p style="color: white; font-size: 1.1rem; margin: 0;">총 예상 소요시간 합계: <strong>{best_total_time:.1f}분</strong></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # 각 사람별 경로 복원 및 시간 계산
                    meeting_paths = []
                    for idx, s in enumerate(start_station_ids):
                        dijkstra.reset()
                        p = dijkstra.getPath(s, best_station)
                        if not p:
                            continue

                        pathNames = []
                        pathLine = []
                        for item in p:
                            # 괄호 앞까지만 역 이름 추출 (예: "원인재(B)" -> "원인재", "원인재(I1)" -> "원인재")
                            if "(" in item:
                                station_name = item.split("(")[0]
                                line_part = item.split("(")[1].rstrip(")")
                                # 호선 번호만 추출 (예: "I1" -> "I1", "B" -> "B")
                                line_num = line_part
                            else:
                                station_name = item
                                line_num = ""
                            pathNames.append(station_name)
                            pathLine.append(line_num)

                        # 시간은 all_costs에서 직접 사용 (가장 정확)
                        t = all_costs[s][best_station]
                        # 거리는 대략 계산 (필요 없으면 제거 가능)
                        dist, _ = get_path_distance_and_time(p, edge_distance, edge_time)

                        meeting_paths.append({
                            "person_idx": idx + 1,
                            "start_station": s,
                            "pathList": p,
                            "pathNames": pathNames,
                            "pathLine": pathLine,
                            "total_dist": dist,
                            "total_time": t
                        })

                    st.markdown("### 📊 인원별 이동 요약")
                    for mp in meeting_paths:
                        col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
                        with col_p1:
                            st.metric(f"👤 {mp['person_idx']}번 사람", f"{mp['total_time']:.1f}분")
                        with col_p2:
                            dist_value = mp['total_dist'] if mp['total_dist'] > 0 else 0.0
                            st.metric("📏 거리", f"{dist_value:.2f} km")
                        with col_p3:
                            path_display = " → ".join([f"{name}({line})" for name, line in zip(mp['pathNames'], mp['pathLine'])])
                            st.caption(f"경로: {path_display}")
                        st.markdown("<br>", unsafe_allow_html=True)

                    # 만남역 주변 핫플 (맛집 기준)
                    center_lat, center_lng = subwayLoc.get(best_station_name, (None, None))
                    hotplaces = []
                    if center_lat is not None:
                        with st.spinner("주변 맛집 정보를 검색하는 중..."):
                            hotplaces = kakao_search_hotplaces(
                                center_lat, center_lng, radius=1000, category_group_code="FD6"
                            )
                        if hotplaces:
                            st.markdown("### 🍽 만남역 주변 맛집/핫플")
                            for idx, hp in enumerate(hotplaces[:5], 1):  # 상위 5개만 표시
                                with st.container():
                                    st.markdown(f"""
                                    <div style="border-radius: 8px; margin: 1.0rem 0; background: #fff3cd; padding: 1rem; border-left: 4px solid #ffc107;">
                                        <strong style="color:black;">🍴 {hp['name']}</strong><br>
                                        <small style="color: black;">📍 {hp['address']}</small><br>
                                        <small style="color: black;">📏 거리: {hp['distance']}m</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.info("ℹ️ 주변 맛집 정보를 찾지 못했습니다.")
                    else:
                        st.warning("⚠️ 만남역 좌표 정보를 찾지 못했습니다.")

                    # 세션 상태 저장 (지도 표시용)
                    st.session_state["mode"] = "meeting"
                    st.session_state["meeting_station"] = best_station
                    st.session_state["meeting_station_name"] = best_station_name
                    st.session_state["meeting_paths"] = meeting_paths
                    st.session_state["meeting_hotplaces"] = hotplaces


# -------------------------
# 오른쪽: 지도 시각화
# -------------------------
with col2:
    st.markdown("### 🗺️ 경로 지도")

    mode = st.session_state.get("mode", None)

    # 1) 단일 경로 모드
    if mode == "single" and "single_pathNames" in st.session_state:
        pathNames = st.session_state["single_pathNames"]
        pathLine = st.session_state["single_pathLine"]

        # 위치 정보가 있는 역만 사용하여 중심점 계산
        valid_locs = [subwayLoc[name] for name in pathNames if name in subwayLoc]
        if valid_locs:
            xbar = sum([loc[0] for loc in valid_locs]) / len(valid_locs)
            ybar = sum([loc[1] for loc in valid_locs]) / len(valid_locs)
        else:
            # 기본값 (서울 중심)
            xbar, ybar = 37.5665, 126.9780

        map_osm = folium.Map(location=[xbar, ybar], zoom_start=12)

        paths = []
        for idx, name in enumerate(pathNames):
            loc = subwayLoc.get(name)
            if loc is None:
                continue
            line_num = pathLine[idx]

            if line_num == '1':
                color = 'blue'
            elif line_num == '2':
                color = 'green'
            elif line_num == '3':
                color = 'orange'
            elif line_num == '4':
                color = 'cyan'
            else:
                color = 'gray'

            folium.CircleMarker(
                loc,
                radius=8,
                popup=f"{name}({line_num})",
                tooltip=f"{name}({line_num})",
                color=color,
                fill=True,
                fill_color=color,
                fillOpacity=0.7
            ).add_to(map_osm)

            paths.append(loc)

        if paths:
            folium.PolyLine(paths, color="red", weight=4, opacity=0.8).add_to(map_osm)

            folium.Marker(
                paths[0],
                popup=f"출발: {pathNames[0]}",
                tooltip=f"출발: {pathNames[0]}",
                icon=folium.Icon(color='green', icon='play', prefix='fa')
            ).add_to(map_osm)
            folium.Marker(
                paths[-1],
                popup=f"도착: {pathNames[-1]}",
                tooltip=f"도착: {pathNames[-1]}",
                icon=folium.Icon(color='red', icon='stop', prefix='fa')
            ).add_to(map_osm)

        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.components.v1.html(map_osm._repr_html_(), width=700, height=550)
        st.markdown('</div>', unsafe_allow_html=True)

    # 2) 다중 인원 만남 모드
    elif mode == "meeting" and "meeting_paths" in st.session_state:
        meeting_station_name = st.session_state.get("meeting_station_name")
        meeting_paths = st.session_state.get("meeting_paths", [])
        hotplaces = st.session_state.get("meeting_hotplaces", [])

        if meeting_station_name and meeting_station_name in subwayLoc:
            center_lat, center_lng = subwayLoc[meeting_station_name]
        else:
            center_lat, center_lng = 37.5665, 126.9780

        map_osm = folium.Map(location=[center_lat, center_lng], zoom_start=12)

        colors = ["red", "blue", "green", "purple", "orange"]
        for idx, mp in enumerate(meeting_paths):
            color = colors[idx % len(colors)]
            coords = []
            for station_name in mp["pathNames"]:
                if station_name in subwayLoc:
                    coords.append(subwayLoc[station_name])

            if coords:
                folium.PolyLine(
                    coords, color=color, weight=4, opacity=0.7,
                    popup=f"{mp['person_idx']}번 사람 경로"
                ).add_to(map_osm)

                start_loc = coords[0]
                folium.Marker(
                    start_loc,
                    popup=f"{mp['person_idx']}번 출발",
                    tooltip=f"{mp['person_idx']}번 출발",
                    icon=folium.Icon(color=color, icon='user', prefix='fa')
                ).add_to(map_osm)

        if meeting_station_name in subwayLoc:
            folium.Marker(
                subwayLoc[meeting_station_name],
                popup=f"만남역: {meeting_station_name}",
                tooltip=f"만남역: {meeting_station_name}",
                icon=folium.Icon(color='darkgreen', icon='star', prefix='fa')
            ).add_to(map_osm)

        for hp in hotplaces:
            folium.Marker(
                [hp["lat"], hp["lng"]],
                popup=f"{hp['name']} ({hp['distance']}m)",
                tooltip=hp["name"],
                icon=folium.Icon(color='pink', icon='cutlery', prefix='fa')
            ).add_to(map_osm)

        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.components.v1.html(map_osm._repr_html_(), width=700, height=550)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        default_map = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.components.v1.html(default_map._repr_html_(), width=700, height=550)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: #e3f2fd; border-radius: 12px; margin-top: 1rem;">
            <h3 style="color: #1976d2;">📍 경로를 찾아보세요!</h3>
            <p style="color: #666;">좌측에서 경로를 찾거나, 다중 인원 만남 지점을 계산해보세요.</p>
        </div>
        """, unsafe_allow_html=True)
