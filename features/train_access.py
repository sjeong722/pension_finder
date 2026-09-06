"""
철도공사 API로 받은 역별 정차 열차 목록을 가공해
'열차 접근성' 피처(운행 편수, 첫차/막차, 서울역 기준 실제 소요시간, ITX 정차 여부)를 계산하는 모듈
"""

from datetime import datetime  # 시각 문자열 파싱 및 시간차 계산

ITX_CHEONGCHUN_KEYWORD = "ITX-청춘"  # 열차종류명에서 ITX-청춘을 구분하는 키워드


def _parse_time(dt_str: str) -> datetime:
    """API가 주는 열차출발일시 문자열(YYYYMMDDHHMMSS)을 datetime으로 변환합니다."""
    return datetime.strptime(dt_str, "%Y%m%d%H%M%S")


def _trains_by_direction(trains: list[dict], direction: str) -> list[dict]:
    """정차 열차 목록에서 특정 방향(상행/하행)만 필터링합니다."""
    return [t for t in trains if t.get("upplnDnSeNm") == direction]


def compute_travel_time_min(local_trains: list[dict], seoul_trains: list[dict]) -> float | None:
    """
    같은 열차번호(trainNo)를 기준으로 지역역과 서울측 기준역의 정차시각 차이를 계산해
    평균 소요시간(분)을 반환합니다. 매칭되는 열차가 없으면 None을 반환합니다.
    """
    seoul_by_train_no = {t["trainNo"]: t for t in seoul_trains if t.get("trainNo")}  # 열차번호로 조회하기 쉽게 인덱싱

    diffs_min = []  # 소요시간(분)들을 모을 리스트
    for local_train in local_trains:
        train_no = local_train.get("trainNo")
        seoul_train = seoul_by_train_no.get(train_no)  # 같은 열차의 서울측 정차 기록 찾기
        if not seoul_train:
            continue  # 서울측 기록이 없으면(예: 해당 열차가 청량리를 안 지나면) 건너뜀

        local_time = _parse_time(local_train["dptrDt"])
        seoul_time = _parse_time(seoul_train["dptrDt"])
        diffs_min.append(abs((local_time - seoul_time).total_seconds()) / 60)

    if not diffs_min:
        return None

    return round(sum(diffs_min) / len(diffs_min), 1)  # 평균 소요시간(분)


def compute_station_features(local_trains: list[dict], seoul_trains: list[dict]) -> dict:
    """
    한 역의 정차 열차 목록(local_trains)과 서울측 기준역 정차 목록(seoul_trains)으로
    '서울 -> 지역역(하행)', '지역역 -> 서울(상행)' 양방향 접근성 피처를 계산합니다.
    """
    if not local_trains:
        return {
            "daily_train_count": 0,
            "first_train_to_seoul": None,
            "last_train_to_seoul": None,
            "first_train_from_seoul": None,
            "avg_travel_time_min": None,
            "is_itx_stop": False,
        }

    up_trains = _trains_by_direction(local_trains, "상행")     # 지역역 -> 서울 방향
    down_trains = _trains_by_direction(local_trains, "하행")   # 서울 -> 지역역 방향

    is_itx_stop = any(ITX_CHEONGCHUN_KEYWORD in (t.get("trainKndNm") or "") for t in local_trains)

    up_times = sorted(_parse_time(t["dptrDt"]) for t in up_trains if t.get("dptrDt"))
    down_times = sorted(_parse_time(t["dptrDt"]) for t in down_trains if t.get("dptrDt"))

    travel_time = compute_travel_time_min(local_trains, seoul_trains)  # 서울-지역역 실제 소요시간(분)

    return {
        "daily_train_count": len(up_trains),                                     # 상행 기준 하루 운행 횟수
        "first_train_to_seoul": up_times[0].strftime("%H:%M") if up_times else None,   # 서울행 첫차
        "last_train_to_seoul": up_times[-1].strftime("%H:%M") if up_times else None,   # 서울행 막차
        "first_train_from_seoul": down_times[0].strftime("%H:%M") if down_times else None,  # 서울발 첫차 (도착 기준 참고용)
        "avg_travel_time_min": travel_time,                                       # 서울측 기준역 대비 평균 소요시간(분)
        "is_itx_stop": is_itx_stop,                                               # ITX-청춘 정차 여부
    }


def build_all_station_features(raw_by_station: dict, seoul_side_stations: list[str]) -> dict:
    """
    korail.collect_all()의 결과(raw_by_station)를 받아 지역역별 피처를 계산합니다.
    서울측 기준역(청량리/상봉) 중 데이터가 있는 첫 번째 역을 기준으로 소요시간을 계산합니다.
    """
    # 서울측 기준역 중 실제로 데이터가 있는 역 하나를 선택 (없으면 빈 리스트로 처리)
    seoul_trains = []
    for station in seoul_side_stations:
        if raw_by_station.get(station):
            seoul_trains = raw_by_station[station]
            break

    station_features = {}
    for station_name, trains in raw_by_station.items():
        if station_name in seoul_side_stations:
            continue  # 서울측 기준역 자체는 후보 지역역이 아니므로 결과에서 제외
        station_features[station_name] = compute_station_features(trains, seoul_trains)

    return station_features


def add_train_access_features(pensions: list[dict], station_features: dict) -> list[dict]:
    """각 펜션의 nearest_station 값을 기준으로 station_features의 피처를 매칭해 붙입니다."""
    for pension in pensions:
        station = pension.get("nearest_station")
        feats = station_features.get(station, {})

        pension["daily_train_count"] = feats.get("daily_train_count")
        pension["first_train_to_seoul"] = feats.get("first_train_to_seoul")
        pension["last_train_to_seoul"] = feats.get("last_train_to_seoul")
        pension["avg_travel_time_min"] = feats.get("avg_travel_time_min")
        pension["is_itx_stop"] = feats.get("is_itx_stop", False)

    return pensions
