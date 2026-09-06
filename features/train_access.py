"""
철도공사 API로 받은 역별 정차 열차 목록을 가공해
'열차 접근성' 피처(배차간격, 막차시간, ITX-청춘 정차 여부)를 계산하는 모듈
"""

from datetime import datetime  # 시각 문자열을 파싱하고 차이를 계산하기 위해 사용

ITX_CHEONGCHUN_KEYWORD = "ITX-청춘"  # 열차 종류 필드에서 ITX-청춘을 구분하기 위한 키워드


def _parse_time(dt_str: str) -> datetime:
    """
    API가 주는 열차출발일시 문자열(예: '20261010143000')을 datetime 객체로 변환합니다.
    """
    return datetime.strptime(dt_str, "%Y%m%d%H%M%S")  # 초 단위까지 있는 포맷 기준 파싱


def compute_station_features(trains: list[dict], direction_code_to_seoul: str = "상행") -> dict:
    """
    한 역의 정차 열차 목록(trains)으로부터 접근성 피처를 계산합니다.
    trains의 각 항목은 열차종류명, 상행하행구분명, 열차출발일시 등을 포함한다고 가정합니다.
    """
    if not trains:  # 정차 열차가 아예 없으면 접근성 최하로 처리
        return {
            "daily_train_count": 0,
            "avg_interval_min": None,
            "last_train_time": None,
            "is_itx_stop": False,
        }

    # 서울 방향(상행)으로 가는 열차만 필터링 (당일치기/귀가 기준으로 중요한 피처이기 때문)
    up_trains = [t for t in trains if t.get("uppln_dn_se_nm") == direction_code_to_seoul]

    # 열차종류명 필드에 ITX-청춘이 하나라도 있는지 확인
    is_itx_stop = any(ITX_CHEONGCHUN_KEYWORD in (t.get("train_knd_nm") or "") for t in trains)

    if not up_trains:  # 상행 열차가 없으면 배차간격/막차시간 계산 불가
        return {
            "daily_train_count": len(trains),
            "avg_interval_min": None,
            "last_train_time": None,
            "is_itx_stop": is_itx_stop,
        }

    # 출발시각 기준으로 정렬해야 배차간격을 순서대로 계산할 수 있음
    departure_times = sorted(_parse_time(t["dptr_dt"]) for t in up_trains if t.get("dptr_dt"))

    # 연속된 열차들 사이의 시간 간격(분)을 모두 계산
    intervals_min = [
        (departure_times[i + 1] - departure_times[i]).total_seconds() / 60
        for i in range(len(departure_times) - 1)
    ]
    avg_interval = round(sum(intervals_min) / len(intervals_min), 1) if intervals_min else None

    last_train = departure_times[-1].strftime("%H:%M")  # 막차 출발시각을 HH:MM 형태로 저장

    return {
        "daily_train_count": len(up_trains),   # 상행 기준 하루 운행 횟수
        "avg_interval_min": avg_interval,        # 평균 배차간격(분)
        "last_train_time": last_train,           # 막차 출발시각
        "is_itx_stop": is_itx_stop,              # ITX-청춘 정차 여부
    }


def add_train_access_features(pensions: list[dict], station_features: dict) -> list[dict]:
    """
    각 펜션의 nearest_station 값을 기준으로 station_features에서 접근성 피처를 매칭해 붙입니다.
    station_features는 {역이름: compute_station_features 결과} 형태입니다.
    """
    for pension in pensions:
        station = pension.get("nearest_station")  # distance.py에서 계산해둔 최근접 역
        feats = station_features.get(station, {})  # 해당 역의 접근성 피처 (없으면 빈 딕셔너리)

        pension["daily_train_count"] = feats.get("daily_train_count")  # 하루 운행 횟수
        pension["avg_interval_min"] = feats.get("avg_interval_min")     # 평균 배차간격
        pension["last_train_time"] = feats.get("last_train_time")       # 막차시간
        pension["is_itx_stop"] = feats.get("is_itx_stop", False)        # ITX-청춘 정차 여부

    return pensions
