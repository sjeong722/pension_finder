"""
최종 펜션 후보를 지도 위에 시각화하는 모듈
설치: pip install folium
"""

import folium
from folium.plugins import MarkerCluster

from features.distance import STATION_COORDS


def score_to_color(score: float) -> str:
    """점수 구간에 따라 마커 색상을 다르게 지정합니다."""
    if score >= 70:
        return "darkgreen"
    elif score >= 50:
        return "green"
    elif score >= 30:
        return "orange"
    else:
        return "lightgray"


def _fmt(value, suffix: str = "") -> str:
    """값이 없으면 '정보 없음'으로, 있으면 접미사를 붙여 표시합니다. (예: 3.0 -> '3.0km')"""
    return "정보 없음" if value in (None, "") else f"{value}{suffix}"


def _popup_html(pension: dict) -> str:
    """
    펜션 데이터에 있는 필드만 골라 팝업 HTML을 만듭니다.
    v1(역접근성만)에서도, v2(가격/시설 포함)에서도 같은 함수로 동작하도록
    없는 필드는 자동으로 건너뜁니다.
    """
    rows = [
        ("최근접역", f"{_fmt(pension.get('nearest_station'))} ({_fmt(pension.get('station_distance_km'), 'km')})"),
        ("ITX-청춘 정차", "O" if pension.get("is_itx_stop") else "X"),
        ("서울행 첫차/막차", f"{_fmt(pension.get('first_train_to_seoul'))} / {_fmt(pension.get('last_train_to_seoul'))}"),
        ("서울 기준 소요시간", _fmt(pension.get('avg_travel_time_min'), '분')),
        ("객실 수", _fmt(pension.get("roomcount"), "개")),
        ("취사/바비큐", f"{_fmt(pension.get('chkcooking'))} / {_fmt(pension.get('barbecue'))}"),
        ("가격(1박)", _fmt(pension.get("price"), "원")),       # v2에서 수동 입력으로 채워지는 필드
        ("예약 가능일", _fmt(pension.get("availability"))),      # v2에서 수동 입력으로 채워지는 필드
        ("역접근성 / 쾌적함", f"{_fmt(pension.get('access_score'))} / {_fmt(pension.get('comfort_score'))}"),
        ("종합 점수", pension.get("score")),
        ("출처", ", ".join(pension.get("sources", [pension.get("source", "")]))),
    ]

    rows_html = "".join(f"<tr><td><b>{label}</b></td><td>{value}</td></tr>" for label, value in rows)

    image_html = (
        f'<img src="{pension["image"]}" width="220"><br>' if pension.get("image") else ""
    )

    return f"""
    <b>{pension.get('name')}</b><br>
    {pension.get('address') or ''}<br>
    {image_html}
    <table>{rows_html}</table>
    """


def build_map(pensions: list[dict], output_path: str = "data/pension_map.html") -> None:
    """펜션 후보 리스트를 받아 folium 지도를 생성하고 HTML 파일로 저장합니다."""
    if not pensions:
        print("시각화할 후보가 없습니다. 필터 조건을 확인하세요.")
        return

    avg_lat = sum(p["lat"] for p in pensions) / len(pensions)
    avg_lng = sum(p["lng"] for p in pensions) / len(pensions)

    m = folium.Map(location=[avg_lat, avg_lng], zoom_start=11, tiles="OpenStreetMap")
    cluster = MarkerCluster().add_to(m)

    for pension in pensions:
        folium.Marker(
            location=[pension["lat"], pension["lng"]],
            popup=folium.Popup(_popup_html(pension), max_width=280),
            tooltip=pension.get("name"),
            icon=folium.Icon(color=score_to_color(pension.get("score", 0)), icon="home"),
        ).add_to(cluster)

    for station_name, (lat, lng) in STATION_COORDS.items():
        folium.Marker(
            location=[lat, lng],
            tooltip=f"{station_name}역",
            icon=folium.Icon(color="blue", icon="train", prefix="fa"),
        ).add_to(m)

    m.save(output_path)
    print(f"지도 저장 완료: {output_path}")
