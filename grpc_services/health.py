"""Enregistrement du protocole standard de santé gRPC."""
from grpc_health.v1 import health, health_pb2, health_pb2_grpc


def register_health_service(server, service_name):
    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set(service_name, health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    return health_servicer
