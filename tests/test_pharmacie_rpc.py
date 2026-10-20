"""Test individuel du serveur pharmacie : python tests/test_pharmacie_rpc.py"""
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
        PharmacieServicer({"TEST001": {"nom": "Médicament test", "quantite": 7}}), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = pharmacie_pb2_grpc.PharmacieServiceStub(channel)
            reponse = stub.VerifierStock(pharmacie_pb2.VerifierStockRequest(medicament_id="TEST001"), timeout=3)
            assert reponse.disponible and reponse.quantite == 7
            print(f"OK pharmacie : {reponse.nom}, quantité={reponse.quantite}")
            reponse = stub.VerifierStock(
                pharmacie_pb2.VerifierStockRequest(medicament_id="TEST001", quantite_demandee=7), timeout=3
            )
            assert reponse.disponible and reponse.statut == "disponible"
            reponse = stub.VerifierStock(
                pharmacie_pb2.VerifierStockRequest(medicament_id="TEST001", quantite_demandee=8), timeout=3
            )
            assert not reponse.disponible and reponse.statut == "insuffisant"
            for identifiant, statut in (("", grpc.StatusCode.INVALID_ARGUMENT), ("ABSENT", grpc.StatusCode.NOT_FOUND)):
                try:
                    stub.VerifierStock(pharmacie_pb2.VerifierStockRequest(medicament_id=identifiant), timeout=3)
                    raise AssertionError(f"Le statut {statut} était attendu")
                except grpc.RpcError as erreur:
                    assert erreur.code() == statut
            try:
                stub.VerifierStock(
                    pharmacie_pb2.VerifierStockRequest(medicament_id="TEST001", quantite_demandee=0), timeout=3
                )
                raise AssertionError("INVALID_ARGUMENT était attendu pour une quantité nulle")
            except grpc.RpcError as erreur:
                assert erreur.code() == grpc.StatusCode.INVALID_ARGUMENT
            print("OK pharmacie : requêtes invalides et médicaments absents gérés")
    finally:
        server.stop(0).wait()


if __name__ == "__main__":
    main()
