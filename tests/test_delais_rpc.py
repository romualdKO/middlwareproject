"""Test des délais gRPC simulés : python tests/test_delais_rpc.py"""
from concurrent import futures
from pathlib import Path
import sys

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc
from grpc_services.pharmacie_server import PharmacieServicer


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    pharmacie_pb2_grpc.add_PharmacieServiceServicer_to_server(
        PharmacieServicer({"TEST001": {"nom": "Médicament test", "quantite": 7}}, latence_ms=150), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = pharmacie_pb2_grpc.PharmacieServiceStub(channel)
            try:
                stub.VerifierStock(pharmacie_pb2.VerifierStockRequest(medicament_id="TEST001"), timeout=0.02)
                raise AssertionError("DEADLINE_EXCEEDED était attendu")
            except grpc.RpcError as erreur:
                assert erreur.code() == grpc.StatusCode.DEADLINE_EXCEEDED
                print("OK timeout gRPC : DEADLINE_EXCEEDED reçu après expiration du délai")
    finally:
        server.stop(0).wait()


if __name__ == "__main__":
    main()
