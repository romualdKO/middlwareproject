"""Clients gRPC partagés, avec délais bornés et TLS activable par configuration."""
import os
from pathlib import Path

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc
from grpc_services.generated import radiologie_pb2, radiologie_pb2_grpc


def channel_credentials_from_env():
    ca_path = os.getenv("GRPC_TLS_CA")
    cert_path = os.getenv("GRPC_TLS_CLIENT_CERT")
    key_path = os.getenv("GRPC_TLS_CLIENT_KEY")
    if bool(cert_path) != bool(key_path):
        raise ValueError("GRPC_TLS_CLIENT_CERT et GRPC_TLS_CLIENT_KEY doivent être fournis ensemble.")
    if not ca_path and not cert_path:
        return None
    ca = Path(ca_path).read_bytes() if ca_path else None
    cert = Path(cert_path).read_bytes() if cert_path else None
    key = Path(key_path).read_bytes() if key_path else None
    return grpc.ssl_channel_credentials(root_certificates=ca, private_key=key, certificate_chain=cert)


def open_channel(target):
    credentials = channel_credentials_from_env()
    if credentials is None:
        return grpc.insecure_channel(target)
    return grpc.secure_channel(target, credentials)


def check_health(target, timeout=1.0):
    """Retourne True seulement si le serveur indique l'état SERVING."""
    channel = open_channel(target)
    try:
        response = health_pb2_grpc.HealthStub(channel).Check(
            health_pb2.HealthCheckRequest(), timeout=timeout
        )
        return response.status == health_pb2.HealthCheckResponse.SERVING
    except grpc.RpcError:
        return False
    finally:
        channel.close()


class PharmacieClient:
    def __init__(self, target=None, timeout=None):
        self.target = target or os.getenv("PHARMACIE_GRPC_TARGET", "localhost:50052")
        self.timeout = float(timeout if timeout is not None else os.getenv("GRPC_TIMEOUT_SECONDS", "2"))
        if self.timeout <= 0:
            raise ValueError("Le timeout gRPC doit être supérieur à zéro.")
        self.channel = open_channel(self.target)
        self.stub = pharmacie_pb2_grpc.PharmacieServiceStub(self.channel)

    def verifier_stock(self, medicament_id, quantite_demandee=None):
        request = pharmacie_pb2.VerifierStockRequest(medicament_id=medicament_id)
        if quantite_demandee is not None:
            request.quantite_demandee = quantite_demandee
        return self.stub.VerifierStock(request, timeout=self.timeout)

    def is_healthy(self, timeout=None):
        return _check_channel_health(self.channel, timeout or self.timeout)

    def lister_medicaments(self):
        return self.stub.ListerMedicaments(pharmacie_pb2.ListerMedicamentsRequest(), timeout=self.timeout)

    def mettre_a_jour_stock(self, medicament_id, nouvelle_quantite):
        request = pharmacie_pb2.MettreAJourStockRequest(
            medicament_id=medicament_id,
            nouvelle_quantite=nouvelle_quantite,
        )
        return self.stub.MettreAJourStock(request, timeout=self.timeout)

    def close(self):
        self.channel.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class RadiologieClient:
    def __init__(self, target=None, timeout=None):
        self.target = target or os.getenv("RADIOLOGIE_GRPC_TARGET", "localhost:50053")
        self.timeout = float(timeout if timeout is not None else os.getenv("GRPC_TIMEOUT_SECONDS", "2"))
        if self.timeout <= 0:
            raise ValueError("Le timeout gRPC doit être supérieur à zéro.")
        self.channel = open_channel(self.target)
        self.stub = radiologie_pb2_grpc.RadiologieServiceStub(self.channel)

    def obtenir_examens(self, examen_id="", patient_id=""):
        request = radiologie_pb2.ObtenirExamenRequest(examen_id=examen_id, patient_id=patient_id)
        return self.stub.ObtenirExamen(request, timeout=self.timeout)

    def mettre_a_jour_etat_examen(self, examen_id, etat, resultat=""):
        request = radiologie_pb2.MettreAJourEtatExamenRequest(
            examen_id=examen_id,
            etat=etat,
            resultat=resultat,
        )
        return self.stub.MettreAJourEtatExamen(request, timeout=self.timeout)

    def is_healthy(self, timeout=None):
        return _check_channel_health(self.channel, timeout or self.timeout)

    def close(self):
        self.channel.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _check_channel_health(channel, timeout):
    try:
        response = health_pb2_grpc.HealthStub(channel).Check(
            health_pb2.HealthCheckRequest(), timeout=timeout
        )
        return response.status == health_pb2.HealthCheckResponse.SERVING
    except grpc.RpcError:
        return False
