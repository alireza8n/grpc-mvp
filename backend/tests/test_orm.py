"""Unit tests for server/orm.py."""

import io
import unittest
from unittest.mock import MagicMock, call, patch

from server.orm import _seed, get_readings, setup_db


def _make_cursor(fetchone_returns=None, fetchall_returns=None):
    cur = MagicMock()
    if fetchone_returns is not None:
        cur.fetchone.return_value = fetchone_returns
    if fetchall_returns is not None:
        cur.fetchall.return_value = fetchall_returns
    return cur


def _make_conn(cursor):
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


class TestGetReadings(unittest.TestCase):
    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_returns_all_rows(self, mock_get_conn, mock_put_conn):
        rows = [("2021-01-01 00:00:00+00", 1.5), ("2021-01-01 01:00:00+00", 2.0)]
        cur = _make_cursor(fetchall_returns=rows)
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        result = get_readings()

        self.assertEqual(result, rows)
        cur.execute.assert_called_once_with(
            "SELECT time, meterusage FROM meter_readings ORDER BY time;"
        )
        cur.close.assert_called_once()
        mock_put_conn.assert_called_once_with(conn)

    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_returns_empty_list_when_no_rows(self, mock_get_conn, mock_put_conn):
        cur = _make_cursor(fetchall_returns=[])
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        result = get_readings()

        self.assertEqual(result, [])

    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_always_returns_conn_on_exception(self, mock_get_conn, mock_put_conn):
        cur = MagicMock()
        cur.execute.side_effect = Exception("DB error")
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        with self.assertRaises(Exception):
            get_readings()

        mock_put_conn.assert_called_once_with(conn)


class TestSetupDb(unittest.TestCase):
    def _cur_for_setup(self, row_count):
        cur = MagicMock()
        cur.fetchone.return_value = (row_count,)
        return cur

    @patch("server.orm._seed")
    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_seeds_when_table_is_empty(self, mock_get_conn, mock_put_conn, mock_seed):
        cur = self._cur_for_setup(0)
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        setup_db()

        mock_seed.assert_called_once_with(cur)
        conn.commit.assert_called_once()
        cur.close.assert_called_once()
        mock_put_conn.assert_called_once_with(conn)

    @patch("server.orm._seed")
    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_skips_seed_when_table_populated(
        self, mock_get_conn, mock_put_conn, mock_seed
    ):
        cur = self._cur_for_setup(42)
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        setup_db()

        mock_seed.assert_not_called()
        conn.commit.assert_called_once()

    @patch("server.orm._seed")
    @patch("server.orm.put_conn")
    @patch("server.orm.get_conn")
    def test_rollback_on_exception(self, mock_get_conn, mock_put_conn, mock_seed):
        cur = MagicMock()
        cur.execute.side_effect = Exception("DB error")
        conn = _make_conn(cur)
        mock_get_conn.return_value = conn

        with self.assertRaises(Exception):
            setup_db()

        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        mock_put_conn.assert_called_once_with(conn)


class TestSeed(unittest.TestCase):
    CSV_CONTENT = "time,meterusage\n2021-01-01 00:00:00,1.5\n2021-01-01 01:00:00,2.0\n"

    @patch("builtins.open")
    def test_inserts_valid_rows(self, mock_open):
        mock_open.return_value.__enter__ = lambda s: io.StringIO(self.CSV_CONTENT)
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        cur = MagicMock()

        _seed(cur)

        cur.executemany.assert_called_once()
        args = cur.executemany.call_args[0]
        rows = args[1]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], ("2021-01-01 00:00:00", 1.5))
        self.assertEqual(rows[1], ("2021-01-01 01:00:00", 2.0))

    @patch("builtins.open")
    def test_skips_nan_values(self, mock_open):
        csv_with_nan = (
            "time,meterusage\n2021-01-01 00:00:00,nan\n2021-01-01 01:00:00,1.0\n"
        )
        mock_open.return_value.__enter__ = lambda s: io.StringIO(csv_with_nan)
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        cur = MagicMock()

        _seed(cur)

        args = cur.executemany.call_args[0]
        rows = args[1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 1.0)

    @patch("builtins.open")
    def test_skips_non_numeric_values(self, mock_open):
        csv_bad = "time,meterusage\n2021-01-01 00:00:00,not_a_number\n2021-01-01 01:00:00,3.0\n"
        mock_open.return_value.__enter__ = lambda s: io.StringIO(csv_bad)
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        cur = MagicMock()

        _seed(cur)

        args = cur.executemany.call_args[0]
        rows = args[1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 3.0)

    @patch("builtins.open")
    def test_empty_csv_inserts_nothing(self, mock_open):
        mock_open.return_value.__enter__ = lambda s: io.StringIO("time,meterusage\n")
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        cur = MagicMock()

        _seed(cur)

        args = cur.executemany.call_args[0]
        rows = args[1]
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
