"""WAMIS 유량 데이터 수집 (www.wamis.go.kr, 키 불필요).

알아낸 것 — 유량 API는 날짜 범위를 무시한다:
  flw_dtdata는 startdt/enddt를 완전히 무시하고 항상 "올해" 데이터만 돌려준다(실측 확인).
  2015~2026 범위로 요청해도, 2020년 한 해만 요청해도 결과는 늘 올해뿐이었다.
  같은 API의 수위(wl_dtdata)는 요청한 연도를 정상적으로 돌려줘서, 유량 엔드포인트만의 제약으로 확정했다.

그래서:
  과거 이력을 한 번에 채우는 백필은 이 API로 불가능하다. 동작하지 않는 백필 기능은 지우고,
  매일 수집해서 앞으로의 이력을 쌓는다. UNIQUE(obscd, ymd) + INSERT OR IGNORE라서
  매번 올해 전체가 돌아와도 새로 생긴 날짜만 추가된다.

Usage:
  python wamis_flow.py --stations          # 유량 관측소 목록 저장
  python wamis_flow.py                     # 전체 관측소 유량 수집 (일일 배치)
  python wamis_flow.py --obscd 1001602     # 일부 관측소만
"""
import argparse
import time
from datetime import datetime

import requests

import store

BASE = "http://www.wamis.go.kr:8080/wamis/openapi/wkw"


def format_ymd(value):
    """'20260915' -> '2026-09-15' (형식이 다르면 원본 유지)."""
    try:
        return datetime.strptime(value[:8], "%Y%m%d").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return value


def collect_stations(conn):
    stations = requests.get(f"{BASE}/flw_dubobsif", timeout=30).json()["list"]
    store.save_flow_stations(conn, stations)
    print(f"유량 관측소 {len(stations)}개 저장")


def collect(conn, obscds):
    today = datetime.now().strftime("%Y%m%d")
    for obscd in obscds:
        # startdt/enddt는 API가 무시하지만 파라미터 형식상 그대로 넣어 둔다.
        params = {"obscd": obscd, "startdt": "20150101", "enddt": today, "output": "json"}
        try:
            rows = requests.get(f"{BASE}/flw_dtdata", params=params, timeout=30).json().get("list") or []
        except (requests.RequestException, ValueError) as e:
            print(f"{obscd} 요청 실패: {e}")
            continue
        added = store.save_flows(conn, [{"obscd": obscd, "ymd": format_ymd(r["ymd"]), "fw": r.get("fw")} for r in rows])
        print(f"{obscd}: {len(rows)}건 수신, 새 날짜 {added}건 추가")
        time.sleep(0.1)  # 관측소 1,000개 이상 연속 호출 -- 서버 배려용 짧은 딜레이


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stations", action="store_true", help="관측소 목록만 저장")
    p.add_argument("--obscd", nargs="+", help="수집할 관측소 코드 (기본: 저장된 전체)")
    p.add_argument("--db", default="water.db")
    args = p.parse_args()
    conn = store.connect(args.db)
    if args.stations:
        collect_stations(conn)
    else:
        collect(conn, args.obscd or store.load_flow_stations(conn))
