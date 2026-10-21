"""Serveur gRPC autonome de consultation des examens radiologiques."""
from concurrent import futures
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import grpc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.mock_pharmacie_radio import EXAMENS
from grpc_services.generated import clinique_pb2, clinique_pb2_grpc, radiologie_pb2, radiologie_pb2_grpc
from grpc_services.health import register_health_service
from grpc_services.clients import open_channel
from grpc_services.request_utils import latence_simulee
from grpc_services.security import server_credentials_from_env

DEFAULT_PORT = 50053
ETATS_VALIDES = {"en_attente", "en_cours", "termine"}


class RadiologieServicer(radiologie_pb2_grpc.RadiologieServiceServicer):
    def __init__(self, examens=None, latence_ms=None):
        self.examens = examens if examens is not None else EXAMENS
        self.latence_ms = int(os.getenv("RADIOLOGIE_LATENCE_MS", "0")) if latence_ms is None else latence_ms
        self.consultation_target = os.getenv("CONSULTATION_GRPC_TARGET", "").strip()
        self.consultation_rest_url = os.getenv("CONSULTATION_REST_URL", "").strip().rstrip("/")
        self.notification_timeout = float(os.getenv("CONSULTATION_NOTIFICATION_TIMEOUT_SECONDS", "2"))
        if self.latence_ms < 0:
            raise ValueError("La latence simulée ne peut pas être négative.")

    def ObtenirExamen(self, request, context):
        examen_id = request.examen_id.strip()
        patient_id = request.patient_id.strip()
        if not examen_id and not patient_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "examen_id ou patient_id est obligatoire.")
        if self.latence_ms:
            latence_simulee(self.latence_ms, context)

        if examen_id:
            examen = self.examens.get(examen_id)
            if examen is None or (patient_id and examen.get("patient_id") != patient_id):
                context.abort(grpc.StatusCode.NOT_FOUND, "Examen introuvable pour les critères fournis.")
            selection = [(examen_id, examen)]
        else:
            selection = [
                (identifiant, examen)
                for identifiant, examen in self.examens.items()
                if examen.get("patient_id") == patient_id
            ]
            if not selection:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Aucun examen trouvé pour le patient {patient_id}.")

        for _, examen in selection:
            if examen.get("etat") not in ETATS_VALIDES:
                context.abort(grpc.StatusCode.INTERNAL, "L'état d'un examen est invalide.")

        examens = [
            radiologie_pb2.Examen(
                examen_id=identifiant,
                patient_id=examen.get("patient_id", ""),
                type_examen=examen.get("type_examen", ""),
                etat=examen.get("etat", ""),
                resultat=examen.get("resultat", ""),
                date=examen.get("date", ""),
            )
            for identifiant, examen in selection
        ]
        premier = examens[0]
        return radiologie_pb2.ObtenirExamenResponse(
            examen_id=premier.examen_id,
            type_examen=premier.type_examen,
            etat=premier.etat,
            resultat=premier.resultat,
            message=f"{len(examens)} examen(s) trouvé(s)",
            patient_id=premier.patient_id,
            examens=examens,
        )

    def MettreAJourEtatExamen(self, request, context):
        examen_id = request.examen_id.strip()
        etat = request.etat.strip().lower()
        if not examen_id or not etat:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "examen_id et etat sont obligatoires.")
        if etat not in ETATS_VALIDES:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "etat doit être en_attente, en_cours ou termine.")
        examen = self.examens.get(examen_id)
        if examen is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Examen introuvable.")

        examen["etat"] = etat
        if request.resultat.strip():
            examen["resultat"] = request.resultat.strip()
        examen_message = radiologie_pb2.Examen(
            examen_id=examen_id,
            patient_id=examen.get("patient_id", ""),
            type_examen=examen.get("type_examen", ""),
            etat=etat,
            resultat=examen.get("resultat", ""),
            date=examen.get("date", ""),
        )

        if not self.consultation_target and not self.consultation_rest_url:
            return radiologie_pb2.MettreAJourEtatExamenResponse(
                examen=examen_message,
                message="État mis à jour en mémoire; notification désactivée (CONSULTATION_REST_URL/CONSULTATION_GRPC_TARGET absent).",
            )

        try:
            if self.consultation_rest_url:
                payload = json.dumps({
                    "id_dossier": examen_message.patient_id,
                    "id_resultat": examen_id,
                    "type": "R",
                }).encode("utf-8")
                requete = Request(
                    f"{self.consultation_rest_url}/api/notifs",
                    data=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    method="POST",
                )
                with urlopen(requete, timeout=self.notification_timeout) as reponse_http:
                    corps = json.loads(reponse_http.read().decode("utf-8") or "{}")
                id_notif = corps.get("id_notif", "")
                return radiologie_pb2.MettreAJourEtatExamenResponse(
                    examen=examen_message,
                    notification_envoyee=bool(id_notif),
                    message=f"Notification Consultation créée : {id_notif}" if id_notif else "Consultation n'a pas retourné d'identifiant de notification.",
                )

            notification = clinique_pb2.NotifierResultatRequest(
                id_dossier=examen_message.patient_id,
                id_resultat=examen_id,
                type="R",
            )
            with open_channel(self.consultation_target) as channel:
                stub = clinique_pb2_grpc.ConsultationStub(channel)
                reponse = stub.NotifierResultat(notification, timeout=self.notification_timeout)
            return radiologie_pb2.MettreAJourEtatExamenResponse(
                examen=examen_message,
                notification_envoyee=bool(reponse.id_notif),
                message=f"Notification Consultation créée : {reponse.id_notif}" if reponse.id_notif else "Consultation n'a pas retourné d'identifiant de notification.",
            )
        except grpc.RpcError as erreur:
            return radiologie_pb2.MettreAJourEtatExamenResponse(
                examen=examen_message,
                message=f"État mis à jour en mémoire, mais notification non confirmée: {erreur.code().name}.",
            )
        except HTTPError as erreur:
            return radiologie_pb2.MettreAJourEtatExamenResponse(
                examen=examen_message,
                message=f"État mis à jour en mémoire, mais Consultation REST a répondu HTTP {erreur.code}.",
            )
        except (URLError, TimeoutError, ValueError) as erreur:
            return radiologie_pb2.MettreAJourEtatExamenResponse(
                examen=examen_message,
                message=f"État mis à jour en mémoire, mais notification REST non confirmée: {erreur}.",
            )


def serve(port=None):
    port = int(port or os.getenv("RADIOLOGIE_PORT", DEFAULT_PORT))
    host = os.getenv("GRPC_BIND_HOST", "[::]")
    target = f"{host}:{port}" if host.startswith("[") else f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    radiologie_pb2_grpc.add_RadiologieServiceServicer_to_server(RadiologieServicer(), server)
    register_health_service(server, "clinique.radiologie.RadiologieService")
    credentials = server_credentials_from_env()
    bound_port = server.add_secure_port(target, credentials) if credentials else server.add_insecure_port(target)
    if bound_port == 0:
        raise RuntimeError(f"Impossible d'écouter sur le port {port}.")
    server.start()
    print(f"Serveur radiologie démarré sur {target} (TLS={'activé' if credentials else 'désactivé'})")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
