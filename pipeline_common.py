"""
v1/v2 파이프라인이 공통으로 쓰는 수집·정제 단계 모듈
"""

import difflib  # 문자열 유사도 비교 (이름 중복 판단용)

from config import SEARCH_AREAS, NAVER_KEYWORDS_SUFFIX
from collectors import tour_api, naver_local
from features.distance import haversine_km


def collect_pensions() -> list[dict]:
    """TourAPI와 네이버 지역검색에서 숙박 후보를 모두 모아 하나의 리스트로 반환합니다."""
    area_names = [area["name"] for area in SEARCH_AREAS]

    tour_keywords = [f"{name} 펜션" for name in area_names]
    tour_results = tour_api.collect_all(tour_keywords)

    naver_results = naver_local.collect_all(area_names, NAVER_KEYWORDS_SUFFIX)

    return tour_results + naver_results


def _is_same_place(a: dict, b: dict, distance_m_threshold: float = 150, name_sim_threshold: float = 0.6) -> bool:
    """
    두 항목이 같은 업체인지 판단합니다.
    조건: 좌표 거리가 threshold(m) 이내 AND 이름 유사도가 threshold 이상.
    거리만 보면 우연히 가까운 다른 업체를 합칠 수 있고, 이름만 보면 지점이 여러 곳인 프랜차이즈를 잘못 합칠 수 있어
    두 조건을 함께 봅니다.
    """
    if not (a.get("lat") and a.get("lng") and b.get("lat") and b.get("lng")):
        return False  # 좌표가 없는 항목은 비교 불가

    dist_km = haversine_km(a["lat"], a["lng"], b["lat"], b["lng"])
    if dist_km * 1000 > distance_m_threshold:
        return False  # 거리 조건 불충족

    name_a = (a.get("name") or "").replace(" ", "")
    name_b = (b.get("name") or "").replace(" ", "")
    similarity = difflib.SequenceMatcher(None, name_a, name_b).ratio()

    return similarity >= name_sim_threshold


def _merge_records(primary: dict, secondary: dict) -> dict:
    """
    같은 업체로 판단된 두 레코드를 병합합니다. primary(TourAPI 우선)의 값을 기본으로 하되
    비어있는 필드는 secondary(네이버) 값으로 채웁니다.
    """
    merged = dict(primary)  # primary를 기본으로 복사
    for key, value in secondary.items():
        if not merged.get(key) and value:  # primary에 없는 값만 secondary로 보강
            merged[key] = value
    merged["sources"] = sorted(set([primary.get("source"), secondary.get("source")]))  # 두 출처 모두 기록
    return merged


def deduplicate_and_merge(pensions: list[dict]) -> list[dict]:
    """
    이름 유사도 + 주소/좌표 근접도를 함께 봐서 중복을 판단하고,
    TourAPI 항목을 우선으로 네이버 항목의 정보를 병합합니다.
    """
    # 좌표가 없는 항목은 지도에 표시 불가하므로 먼저 제외
    valid = [p for p in pensions if p.get("lat") and p.get("lng")]

    # TourAPI 결과를 먼저 배치해 병합 시 우선순위를 갖게 함
    tour_items = [p for p in valid if p["source"] == "tourapi"]
    naver_items = [p for p in valid if p["source"] == "naver_local"]

    merged_list = list(tour_items)  # 결과 리스트를 TourAPI 항목으로 시작
    used_naver_idx = set()          # 이미 병합에 사용된 네이버 항목 인덱스

    for i, naver_item in enumerate(naver_items):
        matched = False
        for j, tour_item in enumerate(merged_list):
            if tour_item["source"] != "tourapi":
                continue
            if _is_same_place(tour_item, naver_item):
                merged_list[j] = _merge_records(tour_item, naver_item)  # 병합해서 교체
                used_naver_idx.add(i)
                matched = True
                break
        if not matched:
            naver_item["sources"] = [naver_item["source"]]
            merged_list.append(naver_item)  # 매칭 안 되면 별도 항목으로 추가

    return merged_list
