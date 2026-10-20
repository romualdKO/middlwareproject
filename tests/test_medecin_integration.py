"""Test du client médecin de démonstration contre les deux services."""
from concurrent import futures
from pathlib import Path
import sys

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grpc_services.generated import pharmacie_pb2_grpc, radiologie_pb2_grpc
from grpc_services.clients import PharmacieClient, RadiologieClient
from grpc_services.medecin_client import obtenir_examens, verifier_stock
from grpc_services.pharmacie_server import PharmacieServicer
from grpc_services.radiologie_server import RadiologieServicer
from grpc_services.health import register_health_service


def demarrer(ajout_service, servicer, health_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    ajout_service(servicer, server)
    register_health_service(server, health_name)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    return server, port


def main():
    pharmacie, port_pharmacie = demarrer(
        pharmacie_pb2_grpc.add_PharmacieServiceServicer_to_server,
        PharmacieServicer({"MED-INT": {"nom": "Médicament intégration", "quantite": 9, "seuil_critique": 2}}),
        "clinique.pharmacie.PharmacieService",
    )
    radiologie, port_radiologie = demarrer(
        radiologie_pb2_grpc.add_RadiologieServiceServicer_to_server,
        RadiologieServicer({
            "RAD-INT": {"patient_id": "PAT-INT", "type_examen": "IRM", "etat": "termine", "resultat": "RAS", "date": "2026-10-20"},
        }),
        "clinique.radiologie.RadiologieService",
    )
    try:
        stock = verifier_stock("MED-INT", 5, host="127.0.0.1", port=port_pharmacie)
        examens = obtenir_examens(patient_id="PAT-INT", host="127.0.0.1", port=port_radiologie)
        assert stock.disponible and stock.quantite == 9
        assert len(examens.examens) == 1 and examens.examens[0].examen_id == "RAD-INT"
        with PharmacieClient(f"127.0.0.1:{port_pharmacie}") as client:
            assert client.is_healthy()
        with RadiologieClient(f"127.0.0.1:{port_radiologie}") as client:
            assert client.is_healthy()
        print("OK intégration client médecin : pharmacie et radiologie répondent")
    finally:
        pharmacie.stop(0).wait()
        radiologie.stop(0).wait()


if __name__ == "__main__":
    main()
