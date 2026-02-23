import sys
import os

# Ensure the backend directory is on sys.path so that top-level modules
# (metrics_pb2, metrics_pb2_grpc) and the server package are importable
# regardless of where pytest is invoked from.
sys.path.insert(0, os.path.dirname(__file__))
