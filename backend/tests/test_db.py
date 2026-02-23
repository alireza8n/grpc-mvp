"""Unit tests for server/db.py."""

import unittest
from unittest.mock import MagicMock, call, patch

import psycopg2

import server.db as db_module


def _reset_pool():
    """Helper: reset the module-level _pool to None between tests."""
    db_module._pool = None


class TestWaitForDb(unittest.TestCase):
    def setUp(self):
        _reset_pool()

    @patch("server.db.time.sleep")
    @patch("server.db.psycopg2.connect")
    def test_succeeds_on_first_try(self, mock_connect, mock_sleep):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        db_module.wait_for_db(retries=5, delay=1)

        mock_connect.assert_called_once()
        mock_conn.close.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("server.db.time.sleep")
    @patch("server.db.psycopg2.connect")
    def test_retries_on_transient_failure(self, mock_connect, mock_sleep):
        mock_conn = MagicMock()
        mock_connect.side_effect = [
            psycopg2.OperationalError("not ready"),
            psycopg2.OperationalError("not ready"),
            mock_conn,
        ]

        db_module.wait_for_db(retries=5, delay=1)

        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_conn.close.assert_called_once()

    @patch("server.db.time.sleep")
    @patch("server.db.psycopg2.connect")
    def test_raises_after_max_retries(self, mock_connect, mock_sleep):
        mock_connect.side_effect = psycopg2.OperationalError("not ready")

        with self.assertRaises(RuntimeError):
            db_module.wait_for_db(retries=3, delay=0)

        self.assertEqual(mock_connect.call_count, 3)


class TestInitPool(unittest.TestCase):
    def setUp(self):
        _reset_pool()

    def tearDown(self):
        _reset_pool()

    @patch("server.db.pool.ThreadedConnectionPool")
    def test_creates_pool(self, mock_pool_cls):
        mock_pool = MagicMock()
        mock_pool_cls.return_value = mock_pool

        db_module.init_pool()

        mock_pool_cls.assert_called_once_with(
            minconn=db_module.DB_POOL_MIN_CONN,
            maxconn=db_module.DB_POOL_MAX_CONN,
            host=db_module.DB_HOST,
            port=db_module.DB_PORT,
            dbname=db_module.DB_NAME,
            user=db_module.DB_USER,
            password=db_module.DB_PASS,
        )
        self.assertIs(db_module._pool, mock_pool)

    @patch("server.db.pool.ThreadedConnectionPool")
    def test_init_pool_is_idempotent(self, mock_pool_cls):
        existing = MagicMock()
        db_module._pool = existing

        db_module.init_pool()

        mock_pool_cls.assert_not_called()
        self.assertIs(db_module._pool, existing)


class TestClosePool(unittest.TestCase):
    def setUp(self):
        _reset_pool()

    def tearDown(self):
        _reset_pool()

    def test_closes_and_resets_pool(self):
        mock_pool = MagicMock()
        db_module._pool = mock_pool

        db_module.close_pool()

        mock_pool.closeall.assert_called_once()
        self.assertIsNone(db_module._pool)

    def test_close_when_no_pool_is_safe(self):
        db_module._pool = None
        # Should not raise
        db_module.close_pool()


class TestGetConn(unittest.TestCase):
    def setUp(self):
        _reset_pool()

    def tearDown(self):
        _reset_pool()

    def test_raises_when_pool_not_initialized(self):
        with self.assertRaises(RuntimeError):
            db_module.get_conn()

    def test_returns_connection_from_pool(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        db_module._pool = mock_pool

        result = db_module.get_conn()

        mock_pool.getconn.assert_called_once()
        self.assertIs(result, mock_conn)


class TestPutConn(unittest.TestCase):
    def setUp(self):
        _reset_pool()

    def tearDown(self):
        _reset_pool()

    def test_returns_conn_to_pool(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        db_module._pool = mock_pool

        db_module.put_conn(mock_conn)

        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_does_nothing_when_pool_is_none(self):
        mock_conn = MagicMock()
        db_module._pool = None
        # Should not raise
        db_module.put_conn(mock_conn)

    def test_does_nothing_when_conn_is_none(self):
        mock_pool = MagicMock()
        db_module._pool = mock_pool

        db_module.put_conn(None)

        mock_pool.putconn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
