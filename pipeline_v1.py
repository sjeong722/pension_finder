"""
v1 파이프라인: TourAPI + 네이버 지역검색 기반 전체 후보와 역 접근성 지도
- 후보 주말 두 곳(CANDIDATE_WEEKENDS)을 각각 계산해 비교합니다.
- API 키가 없으면 샘플 데이터로 전체 흐름을 테스트합니다.

실행: python pipeline_v1.py
"""

import json

from config import CANDIDATE_WEEKENDS, MAX_STATION_DISTANCE_KM, SEOUL_SIDE_STATIONS
from collectors import korail
from pipeline_common import collect_pensions, deduplicate_and_merge
from features.distance import add_distance_features
from features.train_access import build_all_station_features, add_train_access_features
from visualize import build_map


def score_pension(pension: dict) -> float:
    """거리·운행횟수·ITX정차·소요시간을 종합해 0~100 사이의 역 접근성 점수를 계산합니다."""
    distance = pension.get("station_distance_km")
    if distance is None or distance > MAX_STATION_DISTANCE_KM:
        return 0.0  # 1차 필터: 기준 거리를 넘으면 후보에서 제외

    distance_score = max(0, 40 - distance * 10)          # 가까울수록 최대 40점

    train_count = pension.get("daily_train_count") or 0
    frequency_score = min(30, train_count * 2)             # 운행 횟수 기반 최대 30점

    itx_bonus = 20 if pension.get("is_itx_stop") else 0     # ITX-청춘 정차 가산점

    travel_time = pension.get("avg_travel_time_min")
    travel_score = max(0, 10 - (travel_time or 120) / 15)   # 소요시간 짧을수록 최대 10점

    return round(distance_score + frequency_score + itx_bonus + travel_score, 1)


def run_for_weekend(pensions_base: list[dict], weekend: dict) -> list[dict]:
    """공통 후보 리스트에 특정 주말 기준 열차 피처와 점수를 계산해 반환합니다."""
    pensions = [dict(p) for p in pensions_base]  # 원본 훼손 방지를 위해 복사

    station_names = list(korail.STATION_CODE_MAP.keys())
    raw_by_station = korail.collect_all(korail.STATION_CODE_MAP, weekend["date"])
    station_features = build_all_station_features(raw_by_station, SEOUL_SIDE_STATIONS)

    pensions = add_train_access_features(pensions, station_features)

    for pension in pensions:
        pension["score"] = score_pension(pension)

    return sorted([p for p in pensions if p["score"] > 0], key=lambda p: p["score"], reverse=True)


def run_pipeline():
    print("1단계: 숙박정보 수집 중...")
    raw_pensions = collect_pensions()

    print("2단계: 중복 제거·병합 중...")
    pensions = deduplicate_and_merge(raw_pensions)

    print("3단계: 역까지 거리 피처 계산 중... (날짜와 무관하므로 한 번만 계산)")
    pensions = add_distance_features(pensions)

    summary = {}  # 주말별 상위 후보 요약을 모을 딕셔너리

    for weekend in CANDIDATE_WEEKENDS:
        print(f"\n=== {weekend['label']} ({weekend['date']}) 처리 중 ===")
        ranked = run_for_weekend(pensions, weekend)
        print(f"후보 {len(ranked)}건 (전체 {len(pensions)}건 중 거리 기준 통과)")

        out_json = f"data/v1_candidates_{weekend['date']}.json"
        out_map = f"data/v1_map_{weekend['date']}.html"

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(ranked, f, ensure_ascii=False, indent=2)

        build_map(ranked, output_path=out_map)
        summary[weekend["label"]] = ranked[:5]  # 비교용으로 상위 5개만 저장

    print("\n=== 주말별 상위 5개 후보 비교 ===")
    for label, top5 in summary.items():
        print(f"\n[{label}]")
        for p in top5:
            print(f"  {p['score']:5.1f}점  {p['name']} ({p['nearest_station']}역, {p['station_distance_km']}km)")

    print("\n완료! data/v1_map_<날짜>.html 파일들을 열어 확인하세요.")


if __name__ == "__main__":
    run_pipeline()
