"""Unit tests for server/servicer.py."""

import unittest
from unittest.mock import MagicMock, patch

from server.servicer import MetricsServicer


class TestMetricsServicer(unittest.TestCase):
    def setUp(self):
        self.servicer = MetricsServicer()
        self.request = MagicMock()
        self.context = MagicMock()

    @patch("server.servicer.get_readings")
    def test_get_metrics_returns_empty_response_when_no_data(self, mock_get_readings):
        mock_get_readings.return_value = []

        response = self.servicer.GetMetrics(self.request, self.context)

        self.assertEqual(len(response.data), 0)
        mock_get_readings.assert_called_once()

    @patch("server.servicer.get_readings")
    def test_get_metrics_maps_rows_to_response(self, mock_get_readings):
        mock_get_readings.return_value = [
            ("2021-01-01 00:00:00+00", 1.5),
            ("2021-01-01 01:00:00+00", 2.75),
        ]

        response = self.servicer.GetMetrics(self.request, self.context)

        self.assertEqual(len(response.data), 2)

        self.assertEqual(response.data[0].time, "2021-01-01 00:00:00+00")
        self.assertAlmostEqual(response.data[0].meterusage, 1.5)

        self.assertEqual(response.data[1].time, "2021-01-01 01:00:00+00")
        self.assertAlmostEqual(response.data[1].meterusage, 2.75)

    @patch("server.servicer.get_readings")
    def test_get_metrics_converts_time_to_string(self, mock_get_readings):
        from datetime import datetime, timezone

        dt = datetime(2021, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_get_readings.return_value = [(dt, 3.14)]

        response = self.servicer.GetMetrics(self.request, self.context)

        self.assertEqual(response.data[0].time, str(dt))

    @patch("server.servicer.get_readings")
    def test_get_metrics_converts_meterusage_to_float(self, mock_get_readings):
        from decimal import Decimal

        mock_get_readings.return_value = [("2021-01-01", Decimal("9.99"))]

        response = self.servicer.GetMetrics(self.request, self.context)

        self.assertIsInstance(response.data[0].meterusage, float)
        self.assertAlmostEqual(response.data[0].meterusage, 9.99, places=5)

    @patch("server.servicer.get_readings")
    def test_get_metrics_single_row(self, mock_get_readings):
        mock_get_readings.return_value = [("2021-03-10 08:30:00", 100.0)]

        response = self.servicer.GetMetrics(self.request, self.context)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0].time, "2021-03-10 08:30:00")
        self.assertAlmostEqual(response.data[0].meterusage, 100.0)


if __name__ == "__main__":
    unittest.main()
