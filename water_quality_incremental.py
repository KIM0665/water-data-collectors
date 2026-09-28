"""수질 자동측정망 실시간 데이터 — 지점별 워터마크 기반 증분 수집.

공공데이터포털 WaterQualityService(getRealTimeWaterQualityList)를 사용한다.

왜 증분인가:
  자동측정망 데이터는 실측 시점보다 1~2개월 늦게 "확정"된다(실측 확인).
  "최근 N일"처럼 고정 폭으로 수집하면 그보다 늦게 확정된 값을 구조적으로 계속 놓친다.
  그래서 지점별로 "이미 저장된 마지막 날짜(워터마크)"를 조회해 그다음부터 오늘까지만 요청한다.
  지연이 아무리 길어져도 놓치지 않고, 이미 확정된 옛 데이터를 매번 다시 받지도 않는다.

Usage:
  set DATA_GO_KR_SERVICE_KEY=...      (공공데이터포털 서비스 키)
  python water_quality_incremental.py --sites S04001 S04002
"""
import argparse
import os
from datetime import date, datetime, timedelta

import requests

import store

URL = "https://apis.data.go.kr/1480523/WaterQualityService/getRealTimeWaterQualityList"
NEVER_COLLECTED_START = date(2015, 1, 8)   # 한 번도 수집 안 된 지점의 시작일
OVERLAP_DAYS = 3                           # 확정 중이던 최근 며칠은 나중에 바뀔 수 있어 겹쳐서 다시 받는다


def next_start(last, today, overlap_days=OVERLAP_DAYS):
    """이번에 요청할 시작일. None이면 이미 최신이라 요청할 게 없다는 뜻."""
    start = (last - timedelta(days=overlap_days)) if last else NEVER_COLLECTED_START
    return None if start > today else start


def fetch(site_id, start, end, service_key):
    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "3653",
        "resultType": "json",
        "siteId": site_id,
        "startDate": start.strftime("%Y%m%d000000"),
        "endDate": end.strftime("%Y%m%d235959"),
    }
    resp = requests.get(URL, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json().get("getRealTimeWaterQualityList", {})
    return body.get("item") or []


def collect(site_ids, conn, service_key, today=None):
    today = today or date.today()
    watermarks = store.last_dates_by_site(conn)
    for site_id in site_ids:
        last = watermarks.get(site_id)
        start = next_start(datetime.strptime(last, "%Y-%m-%d").date() if last else None, today)
        if start is None:
            continue
        try:
            items = fetch(site_id, start, today, service_key)
        except (requests.RequestException, ValueError) as e:
            print(f"{site_id} 요청 실패: {e}")
            continue
        store.save_auto_measurements(conn, items)
        print(f"{site_id}: {start} ~ {today} 요청, {len(items)}건 수신")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sites", nargs="+", default=["S04001"], help="자동측정망 siteId 목록")
    p.add_argument("--db", default="water.db")
    args = p.parse_args()
    key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
    if not key:
        raise SystemExit("환경변수 DATA_GO_KR_SERVICE_KEY 를 설정하세요.")
    collect(args.sites, store.connect(args.db), key)
