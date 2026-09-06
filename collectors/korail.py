"""
한국철도공사_열차운행정보 API 수집 모듈 (공공데이터포털)
'여객열차 운행계획' 서비스를 사용해 특정 역의 정차 열차 목록을 가져옵니다.
2024년 개편으로 엔드포인트가 v2로 바뀌었습니다.
"""

import requests  # HTTP 요청 라이브러리
from config import KORAIL_API_KEY  # 설정 파일에서 API 키 불러오기

BASE_URL = "https://apis.data.go.kr/B551457/run/v2"  # 열차운행정보 v2 엔드포인트

# 경춘선·중앙선 주요 역의 역코드는 코드정보 API로 미리 확인해서 채워두는 것을 추천합니다.
# 아래는 자리표시자이므로, 실제 코드정보 API 응답으로 반드시 교체하세요.
STATION_CODE_MAP = {
    "가평": "PLACEHOLDER_STN_CD",
    "청평": "PLACEHOLDER_STN_CD",
    "강촌": "PLACEHOLDER_STN_CD",
    "양평": "PLACEHOLDER_STN_CD",
    "용문": "PLACEHOLDER_STN_CD",
}


def fetch_station_codes(mrnt_cd: str = None) -> list[dict]:
    """
    코드정보 API를 호출해 역코드(stn_cd) 목록을 가져옵니다.
    처음 한 번 실행해서 STATION_CODE_MAP을 채우는 용도로 사용하세요.
    """
    url = f"{BASE_URL}/getCommCode"  # 코드정보 조회 엔드포인트 (실제 경로는 발급받은 가이드 문서 기준으로 확인 필요)
    params = {
        "serviceKey": KORAIL_API_KEY,  # 인증키
        "_type": "json",               # JSON 응답
        "type": "stn_cd",              # 역코드 타입 조회
    }
    response = requests.get(url, params=params, timeout=10)  # API 호출
    response.raise_for_status()  # 오류 시 예외 발생
    data = response.json()  # JSON 파싱
    return data.get("response", {}).get("body", {}).get("items", [])  # 코드 목록 반환


def fetch_stop_trains(station_code: str, run_date: str) -> list[dict]:
    """
    특정 역(station_code)에 특정 날짜(run_date, YYYYMMDD)에 정차하는 열차 목록을 가져옵니다.
    """
    url = f"{BASE_URL}/trainStopInfo"  # 여객열차 운행정보(역별 정차) 엔드포인트 (실제 경로는 가이드 문서로 확인)
    params = {
        "serviceKey": KORAIL_API_KEY,  # 인증키
        "_type": "json",               # JSON 응답
        "stnCd": station_code,          # 조회할 역코드
        "runDate": run_date,            # 조회할 운행일자
        "numOfRows": 200,               # 하루 정차 열차가 많을 수 있어 넉넉히 설정
    }
    response = requests.get(url, params=params, timeout=10)  # API 호출
    response.raise_for_status()  # 오류 시 예외 발생
    data = response.json()  # JSON 파싱

    items = data.get("response", {}).get("body", {}).get("items", "")  # 결과 목록
    if not items:
        return []  # 결과 없으면 빈 리스트

    item_list = items.get("item", [])  # 실제 열차 목록
    if isinstance(item_list, dict):     # 1건이면 dict로 오므로 리스트로 통일
        item_list = [item_list]

    return item_list


def collect_all(station_name_to_code: dict, run_date: str) -> dict:
    """
    여러 역에 대해 정차 열차 목록을 한 번에 수집합니다.
    반환값은 {역이름: [열차목록]} 형태입니다.
    """
    result = {}  # 역별 결과를 담을 딕셔너리
    for name, code in station_name_to_code.items():
        try:
            trains = fetch_stop_trains(code, run_date)  # 역별 정차 열차 조회
            result[name] = trains                        # 결과 저장
            print(f"[KORAIL] '{name}' 정차 열차 {len(trains)}건")  # 진행상황 출력
        except requests.RequestException as e:
            print(f"[KORAIL] '{name}' 조회 실패: {e}")  # 실패해도 계속 진행
            result[name] = []  # 실패 시 빈 리스트로 채워 파이프라인이 끊기지 않게 함

    return result
