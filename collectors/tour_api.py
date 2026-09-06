"""
한국관광공사 TourAPI 4.0 - 숙박정보(contentTypeId=32) 수집 모듈
공공데이터포털에서 '한국관광공사_국문 관광정보 서비스_GW' 활용신청 후 발급받은
디코딩 서비스키를 config.py의 TOUR_API_KEY에 넣고 사용하세요.
"""

import requests  # HTTP 요청을 보내기 위한 라이브러리
import time      # 호출 사이 간격을 두어 API 과호출을 방지하기 위해 사용
from config import TOUR_API_KEY  # 설정 파일에서 API 키 불러오기

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"  # TourAPI 4.0 기본 엔드포인트
CONTENT_TYPE_PENSION = 32  # TourAPI 분류체계상 '숙박' contentTypeId


def search_stays_by_keyword(keyword: str, num_of_rows: int = 50) -> list[dict]:
    """
    키워드(예: '가평 펜션')로 숙박시설을 검색해 결과 리스트를 반환합니다.
    반환 항목에는 title(업체명), mapx/mapy(경도/위도), addr1(주소) 등이 포함됩니다.
    """
    url = f"{BASE_URL}/searchKeyword2"  # 키워드 검색 엔드포인트
    params = {
        "serviceKey": TOUR_API_KEY,           # 발급받은 인증키
        "MobileOS": "ETC",                    # 필수 파라미터: OS 구분값
        "MobileApp": "PensionFinder",         # 필수 파라미터: 앱 이름(임의 지정 가능)
        "_type": "json",                      # 응답 형식을 JSON으로 지정
        "keyword": keyword,                   # 실제 검색 키워드
        "contentTypeId": CONTENT_TYPE_PENSION,  # 숙박 카테고리로 한정
        "numOfRows": num_of_rows,             # 한 번에 가져올 최대 건수
    }

    response = requests.get(url, params=params, timeout=10)  # API 호출 (10초 타임아웃)
    response.raise_for_status()  # 오류 응답이면 예외 발생시켜 즉시 확인 가능하게 함
    data = response.json()  # JSON 파싱

    # TourAPI는 결과가 없을 때 items가 빈 문자열("")로 오는 경우가 있어 별도 처리
    items = data.get("response", {}).get("body", {}).get("items", "")
    if not items:
        return []  # 결과 없으면 빈 리스트 반환

    item_list = items.get("item", [])  # 실제 업체 목록
    if isinstance(item_list, dict):     # 결과가 1건이면 dict로만 오므로 리스트로 통일
        item_list = [item_list]

    results = []  # 최종 정리된 결과를 담을 리스트
    for item in item_list:
        results.append({
            "source": "tourapi",                       # 데이터 출처 표시 (나중에 병합/디버깅용)
            "name": item.get("title"),                  # 업체명
            "address": item.get("addr1"),                # 주소
            "lat": float(item.get("mapy", 0)),           # 위도 (TourAPI는 mapy가 위도)
            "lng": float(item.get("mapx", 0)),           # 경도 (TourAPI는 mapx가 경도)
            "image": item.get("firstimage"),             # 대표 이미지 URL
            "tel": item.get("tel"),                      # 전화번호
        })

    return results


def collect_all(area_keywords: list[str]) -> list[dict]:
    """
    여러 지역 키워드에 대해 순차적으로 검색하고 결과를 하나의 리스트로 합칩니다.
    """
    all_results = []  # 전체 지역 결과를 모을 리스트
    for keyword in area_keywords:
        try:
            results = search_stays_by_keyword(keyword)  # 지역별 검색 실행
            all_results.extend(results)                  # 결과 누적
            print(f"[TourAPI] '{keyword}' 검색 결과 {len(results)}건")  # 진행상황 출력
        except requests.RequestException as e:
            print(f"[TourAPI] '{keyword}' 검색 실패: {e}")  # 실패해도 전체 파이프라인은 계속 진행
        time.sleep(0.3)  # 과호출 방지를 위한 짧은 대기

    return all_results
