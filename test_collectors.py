"""네트워크 없이 도는 핵심 로직 테스트: python -m unittest -v"""
import unittest
from datetime import date

import store
from water_quality_incremental import NEVER_COLLECTED_START, next_start
from wamis_flow import format_ymd


class NextStartTest(unittest.TestCase):
    def test_never_collected_starts_from_beginning(self):
        self.assertEqual(next_start(None, date(2026, 9, 28)), NEVER_COLLECTED_START)

    def test_resumes_from_watermark_with_overlap(self):
        # 늦게 확정되는 최근 3일은 다시 받는다
        self.assertEqual(next_start(date(2026, 9, 20), date(2026, 9, 28)), date(2026, 9, 17))

    def test_future_start_means_nothing_to_fetch(self):
        self.assertIsNone(next_start(date(2026, 10, 5), date(2026, 9, 28)))


class StoreIdempotencyTest(unittest.TestCase):
    def test_same_rows_twice_do_not_duplicate(self):
        conn = store.connect(":memory:")
        rows = [{"obscd": "1001602", "ymd": "2026-09-01", "fw": 1.2},
                {"obscd": "1001602", "ymd": "2026-09-02", "fw": 1.5}]
        self.assertEqual(store.save_flows(conn, rows), 2)
        # WAMIS는 매번 올해 전체를 돌려주지만, 이미 있는 날짜는 추가되지 않는다
        self.assertEqual(store.save_flows(conn, rows + [{"obscd": "1001602", "ymd": "2026-09-03", "fw": 2.0}]), 1)

    def test_watermark_is_latest_saved_date(self):
        conn = store.connect(":memory:")
        store.save_auto_measurements(conn, [{"SITE_ID": "S04001", "MSR_DATE": "2026-09-01 10:00:00"},
                                            {"SITE_ID": "S04001", "MSR_DATE": "2026-09-05 10:00:00"}])
        self.assertEqual(store.last_dates_by_site(conn), {"S04001": "2026-09-05"})


class FormatYmdTest(unittest.TestCase):
    def test_formats_and_keeps_unknown(self):
        self.assertEqual(format_ymd("20260915"), "2026-09-15")
        self.assertEqual(format_ymd("bad"), "bad")


if __name__ == "__main__":
    unittest.main()
