"""Serveur gRPC autonome pour la consultation des stocks de pharmacie."""
from concurrent import futures
import os
from pathlib import Path
import sys
import time

import grpc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.mock_pharmacie_radio import MEDICAMENTS
from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc

DEFAULT_PORT = 50052


class PharmacieServicer(pharmacie_pb2_grpc.PharmacieServiceServicer):
    def __init__(self, medicaments=None, latence_ms=None):
        self.medicaments = medicaments if medicaments is not None else MEDICAMENTS
        self.latence_ms = int(os.getenv("PHARMACIE_LATENCE_MS", "0")) if latence_ms is None else latence_ms
        if self.latence_ms < 0:
            raise ValueError("La latence simulée ne peut pas être négative.")

    def VerifierStock(self, request, context):
        medicament_id = request.medicament_id.strip()
        if not medicament_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "medicament_id est obligatoire.")
        if request.HasField("quantite_demandee") and request.quantite_demandee <= 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "quantite_demandee doit être supérieure à zéro.")
        if self.latence_ms:
            time.sleep(self.latence_ms / 1000)

        medicament = self.medicaments.get(medicament_id)
        if medicament is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Médicament introuvable : {medicament_id}.")
        quantite = medicament.get("quantite")
        seuil = medicament.get("seuil_critique", 0)
        if not isinstance(quantite, int) or quantite < 0 or not isinstance(seuil, int) or seuil < 0:
            context.abort(grpc.StatusCode.INTERNAL, "Les données du stock sont invalides.")

        demande_presente = request.HasField("quantite_demandee")
        demandee = request.quantite_demandee if demande_presente else 1
        disponible = quantite >= demandee
        statut = "rupture" if quantite == 0 else (
            "insuffisant" if not disponible else "stock_critique" if quantite <= seuil else "disponible"
        )
        if not demande_presente and quantite == 0:
            message = "Rupture de stock"
        elif disponible:
            message = "Quantité disponible" if demande_presente else "Médicament disponible"
        else:
            message = f"Stock insuffisant : {quantite} unité(s) disponible(s) sur {demandee} demandée(s)"

        return pharmacie_pb2.VerifierStockResponse(
            medicament_id=medicament_id,
            nom=medicament.get("nom", ""),
            disponible=disponible,
            quantite=quantite,
            message=message,
            emplacement=medicament.get("emplacement", ""),
            statut=statut,
            quantite_demandee=demandee if demande_presente else 0,
        )


def serve(port=None):
    port = int(port or os.getenv("PHARMACIE_PORT", DEFAULT_PORT))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pharmacie_pb2_grpc.add_PharmacieServiceServicer_to_server(PharmacieServicer(), server)
    if server.add_insecure_port(f"[::]:{port}") == 0:
        raise RuntimeError(f"Impossible d'écouter sur le port {port}.")
    server.start()
    print(f"Serveur pharmacie démarré sur le port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
