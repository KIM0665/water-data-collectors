# water-data-collectors

환경 데이터 플랫폼 [Water Explorer](https://gqx.co.kr)의 수집 파이프라인 중 두 개를 떼어 낸 공개본입니다.
Water Explorer는 국내외 10곳 이상 출처의 데이터를 15종 이상의 수집기로 모으는데, 그중 **공공 API를 그대로 믿으면 데이터가 빠지는** 두 사례를 골랐습니다.

> 자세한 배경: [kky.ai.kr — 기관마다 흩어져 있던 환경 데이터](https://kky.ai.kr/case/water-explorer)

| 파일 | 다루는 문제 | 해결 |
|---|---|---|
| `water_quality_incremental.py` | 수질 자동측정망 데이터는 **1~2개월 늦게 확정**되어, "최근 N일" 수집으로는 늦게 확정된 값을 계속 놓침 | 지점별 **마지막 저장일(워터마크)** 다음부터 오늘까지 요청 + 최근 3일 겹쳐 재수집 |
| `wamis_flow.py` | WAMIS 유량 API가 **날짜 범위를 무시하고 항상 올해 데이터만** 돌려줌 (같은 API의 수위는 정상) | 동작하지 않는 과거 백필을 제거하고, 매일 수집 + `UNIQUE` 키로 새 날짜만 누적 |

## 실행

```bash
pip install -r requirements.txt

# 수질 자동측정망 (공공데이터포털 서비스 키 필요)
export DATA_GO_KR_SERVICE_KEY=...        # Windows: set DATA_GO_KR_SERVICE_KEY=...
python water_quality_incremental.py --sites S04001

# WAMIS 유량 (키 불필요)
python wamis_flow.py --stations
python wamis_flow.py --obscd 1001602

# 테스트 (네트워크 없이 동작)
python -m unittest -v
```

## 공개본에서 바꾼 점

- 원본은 MySQL을 쓰지만, 설치 없이 돌려볼 수 있게 **SQLite**로 옮겼습니다.
- API 키는 코드에 두지 않고 **환경변수**로 읽습니다.
- 수집 대상 지점은 원본에서는 DB의 지점 테이블에서 읽고, 공개본에서는 명령줄 인자로 받습니다.

로직과 주석(실측으로 확인한 API 동작)은 원본 그대로입니다.
