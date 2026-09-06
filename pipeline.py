"""
전체 파이프라인 실행 스크립트
순서: 데이터 수집 -> 통합/중복제거 -> 거리 피처 -> 열차 접근성 피처 -> 스코어링 -> 지도 시각화
실행: python pipeline.py
"""

import json  # 중간 결과를 파일로 저장/확인하기 위해 사용

from config import SEARCH_AREAS, NAVER_KEYWORDS_SUFFIX, MAX_STATION_DISTANCE_KM
from collectors import tour_api, naver_local, korail
from features.distance import add_distance_features
from features.train_access import compute_station_features, add_train_access_features
from visualize import build_map


def collect_pensions() -> list[dict]:
    """
    TourAPI와 네이버 지역검색에서 숙박 후보를 모두 모아 하나의 리스트로 반환합니다.
    """
    area_names = [area["name"] for area in SEARCH_AREAS]  # 설정 파일의 지역명만 추출

    tour_keywords = [f"{name} 펜션" for name in area_names]  # TourAPI용 검색어 생성
    tour_results = tour_api.collect_all(tour_keywords)         # TourAPI 수집 실행

    naver_results = naver_local.collect_all(area_names, NAVER_KEYWORDS_SUFFIX)  # 네이버 수집 실행

    return tour_results + naver_results  # 두 소스를 하나의 리스트로 합침


def deduplicate(pensions: list[dict]) -> list[dict]:
    """
    좌표를 소수점 3자리(약 100m 단위)로 반올림해 같은 위치로 판단되는 중복 항목을 제거합니다.
    TourAPI와 네이버 결과에 같은 업체가 중복 등록된 경우를 걸러내기 위함입니다.
    """
    seen = set()          # 이미 등록된 좌표를 기록하는 집합
    unique_pensions = []  # 중복 제거된 결과를 담을 리스트

    for pension in pensions:
        lat, lng = pension.get("lat"), pension.get("lng")  # 좌표 꺼내기
        if not lat or not lng:  # 좌표가 없는 데이터는 지도에 못 그리므로 제외
            continue

        key = (round(lat, 3), round(lng, 3))  # 약 100m 단위로 반올림한 좌표를 키로 사용
        if key in seen:  # 이미 같은 위치의 데이터가 있으면 건너뜀
            continue

        seen.add(key)               # 새 좌표를 등록
        unique_pensions.append(pension)  # 결과에 추가

    return unique_pensions


def collect_train_features(run_date: str) -> dict:
    """
    korail 모듈에서 STATION_CODE_MAP을 이용해 역별 열차 데이터를 가져오고
    train_access 모듈로 접근성 피처를 계산해 반환합니다.
    """
    raw_by_station = korail.collect_all(korail.STATION_CODE_MAP, run_date)  # 역별 원본 열차 데이터

    station_features = {}  # 역별 계산된 피처를 담을 딕셔너리
    for station_name, trains in raw_by_station.items():
        station_features[station_name] = compute_station_features(trains)  # 피처 계산

    return station_features


def score_pension(pension: dict) -> float:
    """
    거리·배차간격·ITX 정차 여부를 종합해 0~100 사이의 접근성 점수를 계산합니다.
    가중치는 임의 설정값이므로 실제 사용하면서 소정님 기준에 맞게 조정하시면 됩니다.
    """
    distance = pension.get("station_distance_km")
    if distance is None or distance > MAX_STATION_DISTANCE_KM:
        return 0.0  # 기준 거리를 넘으면 후보에서 사실상 탈락시키는 점수

    distance_score = max(0, 40 - distance * 10)  # 가까울수록 최대 40점 (거리 1km당 10점 감점)

    train_count = pension.get("daily_train_count") or 0
    frequency_score = min(30, train_count * 2)  # 하루 운행 횟수 기반, 최대 30점

    itx_bonus = 20 if pension.get("is_itx_stop") else 0  # ITX-청춘 정차역이면 20점 가산

    interval = pension.get("avg_interval_min")
    interval_score = max(0, 10 - (interval or 60) / 10)  # 배차간격이 촘촘할수록 최대 10점

    return round(distance_score + frequency_score + itx_bonus + interval_score, 1)  # 총점


def run_pipeline(run_date: str = "20261010"):
    """
    전체 파이프라인을 순서대로 실행하고 최종 지도를 생성합니다.
    run_date는 열차 스케줄을 조회할 기준 날짜(YYYYMMDD)로, 후보 주말 중 하루를 넣으세요.
    """
    print("1단계: 숙박정보 수집 중...")
    pensions = collect_pensions()

    print("2단계: 중복 제거 중...")
    pensions = deduplicate(pensions)

    print("3단계: 역까지 거리 피처 계산 중...")
    pensions = add_distance_features(pensions)

    print("4단계: 열차 접근성 피처 계산 중...")
    station_features = collect_train_features(run_date)
    pensions = add_train_access_features(pensions, station_features)

    print("5단계: 스코어링 중...")
    for pension in pensions:
        pension["score"] = score_pension(pension)  # 각 펜션에 접근성 점수 부여

    # 점수 높은 순으로 정렬하고, 최소 기준(거리 초과 등으로 0점) 후보는 제외
    ranked = sorted([p for p in pensions if p["score"] > 0], key=lambda p: p["score"], reverse=True)

    print(f"최종 후보 {len(ranked)}건 (전체 수집 {len(pensions)}건 중)")

    with open("data/candidates.json", "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)  # 중간 결과 저장 (검토/디버깅용)

    print("6단계: 지도 생성 중...")
    build_map(ranked, output_path="data/pension_map.html")  # 지도 HTML 생성

    print("완료! data/pension_map.html 파일을 열어 확인하세요.")


if __name__ == "__main__":
    run_pipeline()
