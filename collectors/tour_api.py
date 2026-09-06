"""
한국관광공사 TourAPI 4.0 - 숙박정보(contentTypeId=32) 수집 모듈
- 키워드 검색(searchKeyword2) + 페이지네이션
- 소개정보(detailIntro2)로 객실수/바비큐/취사 가능 여부 등 부가 필드 보강
- 키가 없을 때는 샘플 데이터로 대체(USE_MOCK_DATA)
"""

import json       # 샘플 데이터 로드용
import time       # 호출 간격 조절
import requests   # HTTP 요청

from config import TOUR_API_KEY, USE_MOCK_DATA  # 설정값 불러오기

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"  # TourAPI 4.0 기본 엔드포인트
CONTENT_TYPE_PENSION = 32   # 숙박 카테고리 contentTypeId
SAMPLE_PATH = "data/sample/tour_api_sample.json"  # 목 데이터 경로


def _request_with_retry(url: str, params: dict, retries: int = 2) -> dict | None:
    """
    API 호출 공통 함수: 타임아웃/일시적 오류에 대해 재시도하고,
    최종 실패 시 None을 반환해 호출부가 빈 리스트로 처리할 수 있게 합니다.
    """
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=10)  # 실제 호출
            response.raise_for_status()  # 4xx/5xx면 예외 발생
            return response.json()       # 정상이면 JSON 반환
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"[TourAPI] 호출 실패 (시도 {attempt + 1}/{retries + 1}): {e}")
            time.sleep(0.5 * (attempt + 1))  # 재시도 전 짧게 대기 (점점 늘어나는 백오프)

    return None  # 모든 재시도가 실패한 경우


def search_stays_by_keyword(keyword: str, rows_per_page: int = 50, max_pages: int = 5) -> list[dict]:
    """
    키워드로 숙박시설을 검색하고, totalCount를 보며 필요한 만큼 페이지네이션합니다.
    """
    url = f"{BASE_URL}/searchKeyword2"
    all_items = []  # 모든 페이지 결과를 모을 리스트

    for page in range(1, max_pages + 1):
        params = {
            "serviceKey": TOUR_API_KEY,
            "MobileOS": "ETC",
            "MobileApp": "PensionFinder",
            "_type": "json",
            "keyword": keyword,
            "contentTypeId": CONTENT_TYPE_PENSION,
            "numOfRows": rows_per_page,
            "pageNo": page,  # 페이지 번호 (1부터 시작)
        }

        data = _request_with_retry(url, params)
        if data is None:
            break  # 재시도까지 실패하면 이번 키워드는 여기서 중단하고 지금까지 모은 것만 반환

        body = data.get("response", {}).get("body", {})
        items = body.get("items", "")

        if not items:  # 결과가 아예 없는 페이지 (빈 문자열로 옴)
            break

        item_list = items.get("item", [])
        if isinstance(item_list, dict):  # 1건이면 dict로 오므로 리스트로 통일
            item_list = [item_list]

        all_items.extend(item_list)

        total_count = int(body.get("totalCount", 0))  # 전체 검색 결과 수
        if page * rows_per_page >= total_count:  # 이미 전체를 다 가져왔으면 반복 종료
            break

        time.sleep(0.2)  # 페이지 간 짧은 대기 (과호출 방지)

    return all_items


def fetch_detail_intro(content_id: str) -> dict:
    """
    detailIntro2로 숙박시설의 부가정보(객실수/취사/바비큐 가능여부 등)를 가져옵니다.
    실패하거나 필드가 없으면 빈 값으로 채워 파이프라인이 끊기지 않게 합니다.
    """
    url = f"{BASE_URL}/detailIntro2"
    params = {
        "serviceKey": TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "PensionFinder",
        "_type": "json",
        "contentId": content_id,
        "contentTypeId": CONTENT_TYPE_PENSION,
    }

    data = _request_with_retry(url, params, retries=1)
    if data is None:
        return {}

    items = data.get("response", {}).get("body", {}).get("items", "")
    if not items:
        return {}

    item = items.get("item", [{}])
    if isinstance(item, list):
        item = item[0] if item else {}

    # 필드명은 TourAPI 공식 문서 기준 명칭입니다. 실제 응답에서 다를 경우 조정이 필요할 수 있습니다.
    return {
        "roomcount": item.get("roomcount"),      # 객실 수
        "chkcooking": item.get("chkcooking"),      # 취사 가능 여부
        "barbecue": item.get("barbecue"),          # 바비큐 가능 여부
    }


def _normalize_item(item: dict) -> dict:
    """
    searchKeyword2 결과 1건을 파이프라인 공통 포맷으로 정리합니다.
    """
    return {
        "source": "tourapi",
        "content_id": item.get("contentid"),          # detailIntro2 조회에 필요한 식별자
        "name": item.get("title"),
        "address": item.get("addr1"),
        "lat": float(item.get("mapy") or 0),
        "lng": float(item.get("mapx") or 0),
        "image": item.get("firstimage"),
        "tel": item.get("tel"),
    }


def collect_all(area_keywords: list[str], fetch_amenities: bool = True) -> list[dict]:
    """
    여러 지역 키워드에 대해 검색하고, 필요하면 amenities(부가정보)까지 채워 반환합니다.
    USE_MOCK_DATA가 True면 실제 호출 대신 샘플 데이터를 반환합니다.
    """
    if USE_MOCK_DATA:
        print("[TourAPI] API 키 미설정 -> 샘플 데이터 사용")
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)

    all_results = []
    for keyword in area_keywords:
        raw_items = search_stays_by_keyword(keyword)
        print(f"[TourAPI] '{keyword}' 검색 결과 {len(raw_items)}건")

        for raw in raw_items:
            pension = _normalize_item(raw)

            if fetch_amenities and pension["content_id"]:
                amenities = fetch_detail_intro(pension["content_id"])  # 부가정보 추가 조회
                pension.update(amenities)
                time.sleep(0.15)  # 상세조회는 건당 호출이라 더 신경써서 대기

            all_results.append(pension)

        time.sleep(0.3)  # 지역 간 대기

    return all_results
