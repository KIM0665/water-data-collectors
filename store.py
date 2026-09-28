"""SQLite 저장소.

원본(Water Explorer)은 MySQL을 쓰지만, 공개본은 설치 없이 바로 돌려볼 수 있게 SQLite로 옮겼다.
UNIQUE 키 + INSERT OR IGNORE 조합으로 같은 수집을 여러 번 돌려도 중복이 쌓이지 않는다.
"""
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS auto_measurement (
    site_id  TEXT NOT NULL,
    msr_date TEXT NOT NULL,          -- 'YYYY-MM-DD HH:MM:SS'
    items    TEXT NOT NULL,          -- 측정 항목(M01, M02, ...) 원본 JSON
    UNIQUE (site_id, msr_date)
);
CREATE TABLE IF NOT EXISTS flow_station (
    obscd TEXT PRIMARY KEY,
    obsnm TEXT, bbsnnm TEXT, mngorg TEXT, minyear TEXT, maxyear TEXT
);
CREATE TABLE IF NOT EXISTS flow (
    obscd TEXT NOT NULL,
    ymd   TEXT NOT NULL,             -- 'YYYY-MM-DD'
    fw    REAL,                      -- 유량
    UNIQUE (obscd, ymd)
);
"""


def connect(path="water.db"):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def last_dates_by_site(conn):
    """{site_id: 마지막으로 저장된 날짜(str 'YYYY-MM-DD')} -- 한 번도 수집 안 된 지점은 키 자체가 없음."""
    rows = conn.execute("SELECT site_id, MAX(DATE(msr_date)) FROM auto_measurement GROUP BY site_id")
    return dict(rows.fetchall())


def save_auto_measurements(conn, items):
    conn.executemany(
        "INSERT OR IGNORE INTO auto_measurement (site_id, msr_date, items) VALUES (?, ?, ?)",
        [(it["SITE_ID"], it["MSR_DATE"], json.dumps(it, ensure_ascii=False)) for it in items])
    conn.commit()


def save_flow_stations(conn, stations):
    conn.executemany(
        "INSERT OR IGNORE INTO flow_station (obscd, obsnm, bbsnnm, mngorg, minyear, maxyear) "
        "VALUES (:obscd, :obsnm, :bbsnnm, :mngorg, :minyear, :maxyear)",
        [{k: s.get(k) for k in ("obscd", "obsnm", "bbsnnm", "mngorg", "minyear", "maxyear")} for s in stations])
    conn.commit()


def load_flow_stations(conn):
    return [r[0] for r in conn.execute("SELECT obscd FROM flow_station")]


def save_flows(conn, rows):
    """새로 추가된 행 수를 돌려준다(이미 있던 날짜는 무시)."""
    before = conn.total_changes
    conn.executemany("INSERT OR IGNORE INTO flow (obscd, ymd, fw) VALUES (:obscd, :ymd, :fw)", rows)
    conn.commit()
    return conn.total_changes - before
