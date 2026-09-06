"""
한국철도공사_열차운행정보 API 수집 모듈 (공공데이터포털)
- '여객열차 운행계획'으로 특정 역의 정차 열차 목록을 가져옵니다.
- 서울방향 소요시간 계산을 위해 서울측 기준역(청량리/상봉)의 같은 열차 정차시각도 함께 조회합니다.
- 키가 없을 때는 샘플 데이터로 대체(USE_MOCK_DATA)

주의: 아래 엔드포인트 경로(getCommCode, trainStopInfo)와 파라미터/필드명은
      활용신청 승인 후 마이페이지에서 제공되는 공식 문서로 반드시 재확인하세요.
      승인 전에는 공개 문서만으로 정확한 스펙을 확인할 방법이 없습니다.
"""

import json       # 샘플 데이터 로드/파싱용
import requests   # HTTP 요청

from config import KORAIL_API_KEY, USE_MOCK_DATA, SEOUL_SIDE_STATIONS  # 설정값

BASE_URL = "https://apis.data.go.kr/B551457/run/v2"  # 열차운행정보 v2 엔드포인트
SAMPLE_PATH = "data/sample/korail_sample.json"  # 목 데이터 경로

# 역코드는 코드정보 API(getCommCode)로 확인 후 채워야 합니다. 지금은 자리표시자입니다.
STATION_CODE_MAP = {
    "가평": "PLACEHOLDER_STN_CD",
    "청평": "PLACEHOLDER_STN_CD",
    "강촌": "PLACEHOLDER_STN_CD",
    "대성리": "PLACEHOLDER_STN_CD",
    "상천": "PLACEHOLDER_STN_CD",
    "굴봉산": "PLACEHOLDER_STN_CD",
    "백양리": "PLACEHOLDER_STN_CD",
    "양평": "PLACEHOLDER_STN_CD",
    "용문": "PLACEHOLDER_STN_CD",
    "청량리": "PLACEHOLDER_STN_CD",  # 서울측 기준역 1
    "상봉": "PLACEHOLDER_STN_CD",    # 서울측 기준역 2
}


def fetch_station_codes() -> list[dict]:
    """
    코드정보 API로 역코드(stn_cd) 목록을 가져옵니다. STATION_CODE_MAP을 채우는 용도입니다.
    """
    url = f"{BASE_URL}/getCommCode"
    params = {"serviceKey": KORAIL_API_KEY, "_type": "json", "type": "stn_cd"}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("response", {}).get("body", {}).get("items", [])


def fetch_stop_trains(station_code: str, run_date: str) -> list[dict]:
    """
    특정 역(station_code)에 특정 날짜(run_date, YYYYMMDD)에 정차하는 열차 목록을 가져옵니다.
    """
    url = f"{BASE_URL}/trainStopInfo"
    params = {
        "serviceKey": KORAIL_API_KEY,
        "_type": "json",
        "stnCd": station_code,
        "runDate": run_date,
        "numOfRows": 200,
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    items = data.get("response", {}).get("body", {}).get("items", "")
    if not items:
        return []

    item_list = items.get("item", [])
    if isinstance(item_list, dict):
        item_list = [item_list]

    return item_list


def collect_all(station_name_to_code: dict, run_date: str) -> dict:
    """
    지역역 + 서울측 기준역까지 포함해 역별 정차 열차 목록을 한 번에 수집합니다.
    반환값은 {역이름: [열차목록]} 형태입니다.
    USE_MOCK_DATA가 True면 샘플 데이터를 반환합니다 (샘플에는 '가평'과 '청량리'만 들어있습니다).
    """
    if USE_MOCK_DATA:
        print("[KORAIL] API 키 미설정 -> 샘플 데이터 사용")
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)

    result = {}
    for name, code in station_name_to_code.items():
        try:
            trains = fetch_stop_trains(code, run_date)
            result[name] = trains
            print(f"[KORAIL] '{name}' 정차 열차 {len(trains)}건")
        except requests.RequestException as e:
            print(f"[KORAIL] '{name}' 조회 실패: {e}")
            result[name] = []

    return result
