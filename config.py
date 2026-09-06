"""
설정 파일: API 키와 검색 조건을 여기서만 관리합니다.
실제 값은 .env 파일이나 환경변수로 분리하는 걸 추천하지만,
빠르게 진행하기 위해 우선 여기서 직접 채워 넣는 구조로 만들었습니다.
"""

import os  # 환경변수에서 키를 읽어오기 위해 사용

# ---- API 키 (발급받으신 값으로 교체) ----
TOUR_API_KEY = os.getenv("TOUR_API_KEY", "여기에_공공데이터포털_디코딩키_입력")  # 한국관광공사 TourAPI
NAVER_HUB_KEY_ID = os.getenv("NAVER_HUB_KEY_ID", "여기에_HUB_클라이언트_ID_입력")  # 네이버 API HUB Key ID
NAVER_HUB_KEY = os.getenv("NAVER_HUB_KEY", "여기에_HUB_클라이언트_Secret_입력")  # 네이버 API HUB Secret
KORAIL_API_KEY = os.getenv("KORAIL_API_KEY", "여기에_공공데이터포털_디코딩키_입력")  # 한국철도공사 열차운행정보

# ---- 검색 대상 지역 (서울 근교, 전철/기차로 갈 수 있는 권역) ----
SEARCH_AREAS = [
    {"name": "가평", "line": "경춘선"},   # 경춘선, ITX-청춘 정차
    {"name": "청평", "line": "경춘선"},   # 경춘선, ITX-청춘 정차
    {"name": "강촌", "line": "경춘선"},   # 경춘선
    {"name": "양평", "line": "중앙선"},   # 중앙선, ITX-청춘 정차
    {"name": "용문", "line": "중앙선"},   # 중앙선
]

# ---- 네이버 지역검색용 추가 키워드 (지역명 + 숙소 유형) ----
NAVER_KEYWORDS_SUFFIX = ["독채 펜션", "단체 펜션", "풀빌라"]

# ---- 필터 조건 ----
MAX_STATION_DISTANCE_KM = 3.0   # 가장 가까운 역으로부터 이 거리(km) 이내만 후보로 인정
MIN_CAPACITY_HINT = None        # TourAPI 응답에 인원수 필드가 없는 경우가 많아 참고용으로만 사용

# ---- 다음달 후보 주말 (투표 결과 반영) ----
CANDIDATE_WEEKENDS = ["2026-10-10~2026-10-11", "2026-10-24~2026-10-25"]  # 둘째주 / 넷째주
