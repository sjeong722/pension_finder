"""
v2 파이프라인: v1 결과 중 상위 후보에 대해
- TourAPI에서 가져온 시설 정보(객실수/취사/바비큐)
- 수동으로 조사해 채워넣는 가격/인원/예약가능여부/후기 (data/manual_overrides.csv)
를 더해 최종 추천 점수를 계산하고 지도를 만듭니다.

가격·실시간 예약가능여부·후기는 공식 오픈API로 제공되지 않아 자동 수집이 불가능합니다.
(야놀자/여기어때 등은 공개 API가 없고 스크래핑은 이용약관 위반 소지가 있어 이 파이프라인에서는 다루지 않습니다.)
그래서 상위 후보만 추려 수동으로 확인해 채우는 방식을 씁니다.

실행 순서:
  1. python pipeline_v1.py 를 먼저 실행해 data/v1_candidates_*.json을 만드세요.
  2. python pipeline_v2.py 를 실행하면 data/manual_overrides.csv 템플릿이 생성됩니다.
  3. 템플릿을 열어 가격/인원/예약가능여부/후기를 채운 뒤 다시 python pipeline_v2.py 를 실행하세요.
"""

import csv
import json
import os

from config import CANDIDATE_WEEKENDS
from visualize import build_map

TOP_N_PER_WEEKEND = 8  # 각 주말에서 수동 검토 대상으로 뽑을 상위 후보 수
MANUAL_CSV_PATH = "data/manual_overrides.csv"
MANUAL_FIELDS = ["name", "price_per_night", "capacity", "availability_note", "review_score", "reservation_url"]


def load_v1_candidates() -> list[dict]:
    """두 주말 각각의 v1 결과를 불러와 이름 기준으로 합칩니다 (중복 이름은 한 번만)."""
    seen_names = set()
    shortlist = []

    for weekend in CANDIDATE_WEEKENDS:
        path = f"data/v1_candidates_{weekend['date']}.json"
        if not os.path.exists(path):
            print(f"[v2] {path} 가 없습니다. 먼저 pipeline_v1.py를 실행하세요.")
            continue

        with open(path, encoding="utf-8") as f:
            ranked = json.load(f)

        for pension in ranked[:TOP_N_PER_WEEKEND]:
            if pension["name"] not in seen_names:
                seen_names.add(pension["name"])
                shortlist.append(pension)

    return shortlist


def ensure_manual_csv_template(shortlist: list[dict]) -> bool:
    """
    manual_overrides.csv가 없으면 shortlist 이름으로 빈 템플릿을 만들고 True를 반환합니다.
    (True면 아직 채워야 할 파일이 새로 생성됐다는 뜻이라 파이프라인을 여기서 멈추는 게 자연스럽습니다.)
    """
    if os.path.exists(MANUAL_CSV_PATH):
        return False  # 이미 있으면 새로 만들지 않음

    with open(MANUAL_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANUAL_FIELDS)
        writer.writeheader()
        for pension in shortlist:
            writer.writerow({"name": pension["name"], "price_per_night": "", "capacity": "",
                              "availability_note": "", "review_score": "", "reservation_url": ""})

    print(f"[v2] {MANUAL_CSV_PATH} 템플릿을 만들었습니다. 가격/인원/예약가능여부/후기를 채운 뒤 다시 실행하세요.")
    return True


def load_manual_overrides() -> dict:
    """manual_overrides.csv를 읽어 {업체명: 수동입력값} 딕셔너리로 반환합니다."""
    overrides = {}
    with open(MANUAL_CSV_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            overrides[row["name"]] = row
    return overrides


def compute_comfort_score(pension: dict) -> float:
    """
    시설 정보(TourAPI) + 수동 입력 후기 점수를 조합해 0~100 스케일의 '쾌적함' 점수를 계산합니다.
    가중치는 예시값이므로 팀 취향에 맞게 조정하세요.
    """
    score = 0.0
    if pension.get("barbecue") == "가능":
        score += 25
    if pension.get("chkcooking") == "가능":
        score += 25

    review_score = pension.get("review_score")
    if review_score:
        try:
            score += float(review_score) * 10  # 0~5점 후기를 0~50점으로 환산
        except ValueError:
            pass

    return min(100.0, score)


def run_pipeline():
    shortlist = load_v1_candidates()
    if not shortlist:
        print("[v2] 처리할 후보가 없습니다.")
        return

    if ensure_manual_csv_template(shortlist):
        return  # 방금 템플릿을 새로 만들었으면 채운 뒤 재실행하도록 여기서 종료

    overrides = load_manual_overrides()

    for pension in shortlist:
        manual = overrides.get(pension["name"], {})
        pension["price"] = manual.get("price_per_night") or None
        pension["capacity"] = manual.get("capacity") or None
        pension["availability"] = manual.get("availability_note") or None
        pension["review_score"] = manual.get("review_score") or None
        pension["reservation_url"] = manual.get("reservation_url") or None

        pension["access_score"] = pension.get("score", 0)               # v1에서 계산된 역 접근성 점수 (0~100), 별도 보관
        comfort_score = compute_comfort_score(pension)                    # 방금 계산한 쾌적함 점수 (0~100)
        pension["comfort_score"] = comfort_score
        pension["final_score"] = round(0.6 * pension["access_score"] + 0.4 * comfort_score, 1)  # 최종 가중합
        pension["score"] = pension["final_score"]  # 지도 마커 색상 로직이 score 필드를 사용하므로 갱신

    ranked = sorted(shortlist, key=lambda p: p["final_score"], reverse=True)

    with open("data/v2_final_candidates.json", "w", encoding="utf-8") as f:
        json.dump(ranked, f, ensure_ascii=False, indent=2)

    build_map(ranked, output_path="data/v2_final_map.html")

    print("\n=== v2 최종 추천 순위 ===")
    for p in ranked:
        print(f"  {p['final_score']:5.1f}점  {p['name']}  (역접근성 {p['access_score']}, 쾌적함 {p['comfort_score']}, 가격 {p.get('price') or '미확인'})")

    print("\n완료! data/v2_final_map.html 을 열어 확인하세요.")


if __name__ == "__main__":
    run_pipeline()
