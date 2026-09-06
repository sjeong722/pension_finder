# 서울 근교 전철 접근 펜션 후보 파이프라인

TourAPI + 네이버 지역검색(HUB) + 철도공사 열차운행정보를 조합해
경춘선·중앙선 권역의 펜션 후보를 찾고, 열차 접근성 점수를 매겨 지도로 시각화합니다.

## 1. 설치

```bash
pip install -r requirements.txt
```

## 2. API 키 발급 (진행 전 필수)

| API | 발급처 | 소요 시간 |
|---|---|---|
| TourAPI | data.go.kr → '한국관광공사_국문 관광정보 서비스_GW' 활용신청 | 즉시~수시간 |
| 네이버 지역검색 | 네이버클라우드플랫폼 콘솔 → NAVER API HUB → Application 생성 | 즉시 |
| 철도공사 열차운행정보 | data.go.kr → '한국철도공사_열차운행정보' 활용신청 | 즉시~수시간 |

발급받은 키는 `config.py`에 직접 넣거나, 환경변수로 등록하세요.

```bash
export TOUR_API_KEY="발급받은_디코딩키"
export NAVER_HUB_KEY_ID="발급받은_HUB_Key_ID"
export NAVER_HUB_KEY="발급받은_HUB_Secret"
export KORAIL_API_KEY="발급받은_디코딩키"
```

## 3. 실행 전 반드시 확인해야 하는 것 (중요)

코드는 뼈대를 잡아둔 상태라, 실제 API 키를 받으신 후 아래 두 가지는 꼭 확인·수정하셔야 합니다.

1. **`collectors/korail.py`의 `STATION_CODE_MAP`** — 지금은 자리표시자(`PLACEHOLDER_STN_CD`)입니다.
   `fetch_station_codes()`를 한 번 실행해서 가평·청평·강촌·양평·용문의 실제 역코드를 확인한 뒤 채워 넣으세요.
2. **`collectors/korail.py`의 엔드포인트 경로** (`/getCommCode`, `/trainStopInfo`) — 실제 경로명은
   발급 승인 후 마이페이지에서 제공되는 '참고문서'를 보고 정확한 경로로 맞춰주세요. (API마다 세부 경로 표기가 조금씩 다를 수 있습니다.)

## 4. 실행

```bash
python pipeline.py
```

실행하면:
- `data/candidates.json` — 점수순으로 정렬된 후보 원본 데이터
- `data/pension_map.html` — 브라우저에서 여는 인터랙티브 지도 (팀원 공유용)

이 두 파일이 생성됩니다.

## 5. 점수 기준 조정하기

`pipeline.py`의 `score_pension()` 함수에서 가중치를 바꿀 수 있습니다.
지금은 거리(40점) + 배차횟수(30점) + ITX정차(20점) + 배차간격(10점) 구조입니다.

## 6. 알려진 제약

- 네이버 지역검색은 한 번 호출에 최대 5건까지만 반환됩니다 (네이버 정책).
- 철도공사 '운행계획' 데이터의 미래 시점 조회 가능 범위가 명확히 문서화되어 있지 않으니,
  10월 날짜로 먼저 테스트 호출해서 데이터가 나오는지 확인하세요. 안 나오면 날짜를 가깝게 당겨서 재시도하세요.
