"""
설정 파일: API 키는 .env 파일에서 읽어옵니다.
1) .env.example을 복사해 .env로 이름을 바꾸고 실제 키 값을 채우세요.
2) .env는 .gitignore에 포함돼 있어 git에는 올라가지 않습니다.
"""

import os               # 환경변수 접근용
from dotenv import load_dotenv  # .env 파일을 읽어 os.environ에 채워주는 라이브러리

load_dotenv()  # 현재 디렉터리의 .env 파일을 읽어 환경변수로 등록

# ---- API 키 (.env 파일에서 로드, 없으면 빈 문자열) ----
TOUR_API_KEY = os.getenv("TOUR_API_KEY", "")        # 한국관광공사 TourAPI
NAVER_HUB_KEY_ID = os.getenv("NAVER_HUB_KEY_ID", "")  # 네이버 API HUB Key ID
NAVER_HUB_KEY = os.getenv("NAVER_HUB_KEY", "")        # 네이버 API HUB Secret
KORAIL_API_KEY = os.getenv("KORAIL_API_KEY", "")      # 한국철도공사 열차운행정보

# 키가 하나라도 비어있으면 실제 API 대신 샘플 데이터로 파이프라인을 테스트할 수 있게 하는 플래그
USE_MOCK_DATA = not all([TOUR_API_KEY, NAVER_HUB_KEY_ID, NAVER_HUB_KEY, KORAIL_API_KEY])

# ---- 검색 대상 지역 (서울 근교, 전철/기차로 갈 수 있는 권역) ----
SEARCH_AREAS = [
    {"name": "가평", "line": "경춘선"},
    {"name": "청평", "line": "경춘선"},
    {"name": "강촌", "line": "경춘선"},
    {"name": "대성리", "line": "경춘선"},   # 추가: 경춘선
    {"name": "상천", "line": "경춘선"},     # 추가: 경춘선
    {"name": "굴봉산", "line": "경춘선"},   # 추가: 경춘선
    {"name": "백양리", "line": "경춘선"},   # 추가: 경춘선
    {"name": "양평", "line": "중앙선"},
    {"name": "용문", "line": "중앙선"},
]

# ---- 네이버 지역검색용 추가 키워드 (지역명 + 숙소 유형) ----
NAVER_KEYWORDS_SUFFIX = ["독채 펜션", "단체 펜션", "풀빌라"]

# ---- 필터 조건 ----
MAX_STATION_DISTANCE_KM = 3.0   # 1차 필터: 이 거리 내에서만 후보로 인정 (최종 판단은 실제 접근성으로 보완)
SEOUL_SIDE_STATIONS = ["청량리", "상봉"]  # 서울 방향 기준역 (경춘선/중앙선 공용 환승역)

# ---- 다음달 후보 주말 (투표 결과 반영) ----
CANDIDATE_WEEKENDS = [
    {"label": "10월 둘째주", "date": "20261010"},
    {"label": "10월 넷째주", "date": "20261024"},
]
