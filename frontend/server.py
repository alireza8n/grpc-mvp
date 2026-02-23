import json
import logging
import math
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import grpc
import metrics_pb2
import metrics_pb2_grpc

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GRPC_HOST = os.environ.get("GRPC_HOST", "grpc-server")
GRPC_PORT = os.environ.get("GRPC_PORT", "50051")
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8000"))


def fetch_metrics():
    channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
    stub = metrics_pb2_grpc.MetricsServiceStub(channel)
    response = stub.GetMetrics(metrics_pb2.Empty())
    return [
        {"time": p.time, "meterusage": None if math.isnan(
            p.meterusage) else p.meterusage}
        for p in response.data
    ]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence default access log spam
        log.info("%s - %s", self.address_string(), fmt % args)

    def do_GET(self):
        if self.path == "/api/metrics":
            try:
                data = fetch_metrics()
                body = json.dumps({"data": data}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                log.error("gRPC call failed: %s", e)
                msg = json.dumps({"error": str(e)}).encode()
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)

        elif self.path in ("/", "/index.html"):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            index_path = os.path.join(base_dir, "index.html")
            with open(index_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()


def serve():
    server = HTTPServer(("0.0.0.0", HTTP_PORT), Handler)
    log.info("HTTP server listening on port %d", HTTP_PORT)
    server.serve_forever()


if __name__ == "__main__":
    serve()
