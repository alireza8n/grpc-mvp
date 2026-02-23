import logging

import metrics_pb2
import metrics_pb2_grpc

from .orm import get_readings

log = logging.getLogger(__name__)

MetricsResponse = getattr(metrics_pb2, "MetricsResponse")


class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    def GetMetrics(self, request, context):
        rows = get_readings()

        response = MetricsResponse()
        for row in rows:
            point = response.data.add()
            point.time = str(row[0])
            point.meterusage = float(row[1])

        return response
