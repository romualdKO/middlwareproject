"""Serveur gRPC de consultation du stock de la pharmacie."""
from concurrent import futures
import json
from pathlib import Path
import sys

import grpc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc

DATA_PATH = ROOT / "data" / "medicaments.json"
DEFAULT_PORT = 50052


def charger_medicaments(path=DATA_PATH):
    with Path(path).open(encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    if not isinstance(donnees, dict):
        raise ValueError("Le fichier des médicaments doit contenir un objet JSON.")
    return donnees


class PharmacieServicer(pharmacie_pb2_grpc.PharmacieServiceServicer):
    def __init__(self, medicaments=None):
        self.medicaments = medicaments if medicaments is not None else charger_medicaments()

    def VerifierStock(self, request, context):
        medicament_id = request.medicament_id.strip()
        if not medicament_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "medicament_id est obligatoire.")
        medicament = self.medicaments.get(medicament_id)
        if medicament is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Médicament introuvable : {medicament_id}.")
        quantite = medicament.get("quantite")
        if not isinstance(quantite, int) or quantite < 0:
            context.abort(grpc.StatusCode.INTERNAL, "La quantité en stock est invalide.")
        return pharmacie_pb2.VerifierStockResponse(
            medicament_id=medicament_id,
            nom=medicament.get("nom", ""),
            disponible=quantite > 0,
            quantite=quantite,
            message="En stock" if quantite > 0 else "Rupture de stock",
        )


def serve(port=DEFAULT_PORT):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pharmacie_pb2_grpc.add_PharmacieServiceServicer_to_server(PharmacieServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Serveur pharmacie démarré sur le port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
