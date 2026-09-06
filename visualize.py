"""
최종 펜션 후보를 지도 위에 시각화하는 모듈
folium 라이브러리로 인터랙티브 HTML 지도를 생성해 팀원들에게 링크/파일로 공유할 수 있습니다.
설치: pip install folium
"""

import folium  # 인터랙티브 지도 생성 라이브러리
from folium.plugins import MarkerCluster  # 마커가 많을 때 겹치지 않게 묶어주는 플러그인

from features.distance import STATION_COORDS  # 역 위치도 함께 표시하기 위해 불러오기


def score_to_color(score: float) -> str:
    """
    점수 구간에 따라 마커 색상을 다르게 지정합니다. (한눈에 우선순위 파악용)
    """
    if score >= 70:
        return "darkgreen"   # 접근성 매우 좋음
    elif score >= 50:
        return "green"       # 접근성 좋음
    elif score >= 30:
        return "orange"      # 보통
    else:
        return "lightgray"   # 낮음 (참고용)


def build_map(pensions: list[dict], output_path: str = "data/pension_map.html") -> None:
    """
    펜션 후보 리스트를 받아 folium 지도를 생성하고 HTML 파일로 저장합니다.
    """
    if not pensions:  # 후보가 하나도 없으면 빈 지도만 생성하고 종료
        print("시각화할 후보가 없습니다. 필터 조건을 확인하세요.")
        return

    # 지도 중심점은 모든 후보 좌표의 평균으로 계산 (경춘선/중앙선 권역 중심 근처로 자동 설정됨)
    avg_lat = sum(p["lat"] for p in pensions) / len(pensions)
    avg_lng = sum(p["lng"] for p in pensions) / len(pensions)

    m = folium.Map(location=[avg_lat, avg_lng], zoom_start=11, tiles="OpenStreetMap")  # 기본 지도 생성

    cluster = MarkerCluster().add_to(m)  # 마커 클러스터 레이어 추가

    for pension in pensions:
        popup_html = f"""
        <b>{pension.get('name')}</b><br>
        점수: {pension.get('score')}점<br>
        최근접역: {pension.get('nearest_station')} ({pension.get('station_distance_km')}km)<br>
        ITX-청춘 정차: {'O' if pension.get('is_itx_stop') else 'X'}<br>
        하루 운행: {pension.get('daily_train_count')}회 / 막차 {pension.get('last_train_time')}<br>
        출처: {pension.get('source')}
        """  # 마커 클릭 시 보여줄 상세 정보 HTML

        folium.Marker(
            location=[pension["lat"], pension["lng"]],           # 펜션 좌표
            popup=folium.Popup(popup_html, max_width=250),         # 상세정보 팝업
            tooltip=pension.get("name"),                            # 마우스 오버 시 이름 표시
            icon=folium.Icon(color=score_to_color(pension["score"]), icon="home"),  # 점수별 색상 아이콘
        ).add_to(cluster)

    # 참고용으로 역 위치도 별도 마커(파란 기차 아이콘)로 함께 표시
    for station_name, (lat, lng) in STATION_COORDS.items():
        folium.Marker(
            location=[lat, lng],
            tooltip=f"{station_name}역",
            icon=folium.Icon(color="blue", icon="train", prefix="fa"),
        ).add_to(m)

    m.save(output_path)  # HTML 파일로 저장 (더블클릭하면 브라우저에서 바로 열림)
    print(f"지도 저장 완료: {output_path}")
