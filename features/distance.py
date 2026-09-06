"""
펜션 좌표와 가장 가까운 전철/기차역 사이의 거리를 계산하는 모듈
직선거리(Haversine) 기준이며, 최종 후보 3~5개로 좁힌 뒤에는
카카오맵 길찾기 API로 실제 도보/대중교통 시간까지 검증하는 걸 추천합니다.
"""

import math  # 삼각함수 계산에 사용

# 경춘선·중앙선 주요 역의 위경도 (공개된 지리 정보 기준, 필요 시 최신 좌표로 업데이트하세요)
STATION_COORDS = {
    "가평": (37.8317, 127.5097),
    "청평": (37.7423, 127.4437),
    "강촌": (37.7967, 127.5808),
    "대성리": (37.7053, 127.4880),   # 추가: 경춘선
    "상천": (37.8047, 127.4970),     # 추가: 경춘선
    "굴봉산": (37.8123, 127.6030),   # 추가: 경춘선
    "백양리": (37.8320, 127.6470),   # 추가: 경춘선
    "양평": (37.4917, 127.4878),
    "용문": (37.4993, 127.5497),
}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    두 좌표(위도/경도) 사이의 직선거리를 km 단위로 계산합니다.
    """
    R = 6371.0  # 지구 반지름 (km)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)  # 위도를 라디안으로 변환
    d_phi = math.radians(lat2 - lat1)   # 위도 차이
    d_lambda = math.radians(lng2 - lng1)  # 경도 차이

    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)  # Haversine 공식 핵심 항
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  # 중심각 계산

    return R * c  # 거리(km) 반환


def find_nearest_station(lat: float, lng: float) -> tuple[str, float]:
    """
    주어진 좌표에서 가장 가까운 역 이름과 거리(km)를 반환합니다.
    """
    nearest_name = None   # 가장 가까운 역 이름을 담을 변수
    nearest_dist = float("inf")  # 최소 거리를 담을 변수 (초기값은 무한대)

    for station_name, (s_lat, s_lng) in STATION_COORDS.items():
        dist = haversine_km(lat, lng, s_lat, s_lng)  # 각 역까지의 거리 계산
        if dist < nearest_dist:  # 더 가까운 역을 발견하면 갱신
            nearest_dist = dist
            nearest_name = station_name

    return nearest_name, round(nearest_dist, 2)  # (역이름, 거리km) 반환


def add_distance_features(pensions: list[dict]) -> list[dict]:
    """
    펜션 리스트 각각에 nearest_station, station_distance_km 필드를 추가합니다.
    """
    for pension in pensions:
        lat, lng = pension.get("lat"), pension.get("lng")  # 펜션 좌표 꺼내기
        if not lat or not lng:  # 좌표가 없는 데이터는 건너뜀 (예: API 응답 누락)
            pension["nearest_station"] = None
            pension["station_distance_km"] = None
            continue

        station, dist = find_nearest_station(lat, lng)  # 최근접 역 계산
        pension["nearest_station"] = station         # 최근접 역 이름 저장
        pension["station_distance_km"] = dist          # 최근접 역까지 거리 저장

    return pensions
