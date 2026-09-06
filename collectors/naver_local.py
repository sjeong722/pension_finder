"""
네이버 지역검색 API - NAVER API HUB 버전 수집 모듈
2026년 6월부터 기존 개발자센터 방식에서 API HUB 방식으로 이관됐습니다.
네이버클라우드플랫폼 콘솔에서 HUB용 Client ID / Secret을 새로 발급받아야 합니다.
(기존 개발자센터 키는 이 코드와 호환되지 않습니다.)
"""

import requests  # HTTP 요청 라이브러리
import time      # 호출 간격 조절용
from config import NAVER_HUB_KEY_ID, NAVER_HUB_KEY  # HUB 인증 정보 불러오기

HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/local"  # HUB 지역검색 엔드포인트


def search_local(query: str, display: int = 5) -> list[dict]:
    """
    query(예: '가평 독채 펜션')로 지역검색을 수행하고 결과 리스트를 반환합니다.
    네이버 지역검색은 트래픽 이슈로 display 최대값이 5로 제한되어 있습니다.
    """
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_HUB_KEY_ID,  # HUB 인증 헤더 (기존 X-Naver-Client-Id 대체)
        "X-NCP-APIGW-API-KEY": NAVER_HUB_KEY,        # HUB 인증 헤더 (기존 X-Naver-Client-Secret 대체)
    }
    params = {
        "query": query,      # 검색어
        "display": display,  # 결과 개수 (최대 5)
        "sort": "random",    # 정확도순 정렬 (random이 기본 정확도 정렬 옵션)
    }

    response = requests.get(HUB_URL, headers=headers, params=params, timeout=10)  # API 호출
    response.raise_for_status()  # 401/403/429 등 오류 시 예외로 즉시 확인
    data = response.json()  # JSON 파싱

    results = []  # 정리된 결과를 담을 리스트
    for item in data.get("items", []):
        results.append({
            "source": "naver_local",                          # 데이터 출처 표시
            "name": item.get("title", "").replace("<b>", "").replace("</b>", ""),  # 굵게 태그 제거
            "address": item.get("roadAddress") or item.get("address"),  # 도로명 주소 우선
            "lat": float(item.get("mapy", 0)) / 1e7,           # 네이버는 좌표를 10^7배 정수로 줌 → 환산
            "lng": float(item.get("mapx", 0)) / 1e7,           # 위와 동일하게 환산
            "category": item.get("category"),                  # 업종 카테고리
            "tel": item.get("telephone"),                       # 전화번호
        })

    return results


def collect_all(area_names: list[str], keyword_suffixes: list[str]) -> list[dict]:
    """
    지역명 x 숙소유형 키워드 조합으로 여러 번 검색해 결과를 합칩니다.
    예: '가평' x ['독채 펜션', '단체 펜션'] -> '가평 독채 펜션', '가평 단체 펜션'
    """
    all_results = []  # 전체 결과를 모을 리스트
    for area in area_names:
        for suffix in keyword_suffixes:
            query = f"{area} {suffix}"  # 지역명과 숙소유형을 조합한 검색어 생성
            try:
                results = search_local(query)          # 검색 실행
                all_results.extend(results)             # 결과 누적
                print(f"[Naver] '{query}' 검색 결과 {len(results)}건")  # 진행상황 출력
            except requests.RequestException as e:
                print(f"[Naver] '{query}' 검색 실패: {e}")  # 실패해도 계속 진행
            time.sleep(0.3)  # 과호출 방지를 위한 짧은 대기

    return all_results
