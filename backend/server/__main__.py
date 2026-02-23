import logging
from concurrent import futures

import grpc
import metrics_pb2_grpc

from .db import close_pool, init_pool, wait_for_db
from .orm import setup_db
from .servicer import MetricsServicer
from .settings import GRPC_PORT, GRPC_WORKERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def serve() -> None:
    wait_for_db()
    init_pool()
    setup_db()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=GRPC_WORKERS))
    metrics_pb2_grpc.add_MetricsServiceServicer_to_server(MetricsServicer(), server)
    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    server.start()
    log.info("gRPC server listening on port %d", GRPC_PORT)
    try:
        server.wait_for_termination()
    finally:
        close_pool()


if __name__ == "__main__":
    serve()
