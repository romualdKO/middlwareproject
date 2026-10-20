"""Serveur gRPC de consultation de l'état des examens radiologiques."""
from concurrent import futures
import json
from pathlib import Path
import sys

import grpc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grpc_services.generated import radiologie_pb2, radiologie_pb2_grpc

DATA_PATH = ROOT / "data" / "examens_radiologiques.json"
DEFAULT_PORT = 50053


def charger_examens(path=DATA_PATH):
    with Path(path).open(encoding="utf-8") as fichier:
        donnees = json.load(fichier)
    if not isinstance(donnees, dict):
        raise ValueError("Le fichier des examens doit contenir un objet JSON.")
    return donnees


class RadiologieServicer(radiologie_pb2_grpc.RadiologieServiceServicer):
    ETATS_VALIDES = {"en_attente", "en_cours", "termine"}

    def __init__(self, examens=None):
        self.examens = examens if examens is not None else charger_examens()

    def ObtenirExamen(self, request, context):
        examen_id = request.examen_id.strip()
        if not examen_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "examen_id est obligatoire.")
        examen = self.examens.get(examen_id)
        if examen is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Examen introuvable : {examen_id}.")
        etat = examen.get("etat", "")
        if etat not in self.ETATS_VALIDES:
            context.abort(grpc.StatusCode.INTERNAL, "L'état de l'examen est invalide.")
        return radiologie_pb2.ObtenirExamenResponse(
            examen_id=examen_id,
            type_examen=examen.get("type_examen", ""),
            etat=etat,
            resultat=examen.get("resultat", ""),
            message="Examen trouvé",
        )


def serve(port=DEFAULT_PORT):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    radiologie_pb2_grpc.add_RadiologieServiceServicer_to_server(RadiologieServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Serveur radiologie démarré sur le port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
