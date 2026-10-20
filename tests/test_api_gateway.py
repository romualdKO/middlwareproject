"""Tests de la passerelle HTTP/JSON et de ses statuts d'erreur gRPC."""
from concurrent import futures
import os
from pathlib import Path
import sys

import grpc
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grpc_services.generated import pharmacie_pb2_grpc, radiologie_pb2_grpc
from grpc_services.pharmacie_server import PharmacieServicer
from grpc_services.radiologie_server import RadiologieServicer
from grpc_services.health import register_health_service
from rest_services.gateway import create_app


def demarrer(ajout_service, servicer, health_name):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    ajout_service(servicer, server)
    register_health_service(server, health_name)
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    return server, port


def _exercise_gateway():
    pharmacie, port_pharmacie = demarrer(
        pharmacie_pb2_grpc.add_PharmacieServiceServicer_to_server,
        PharmacieServicer({"MED-API": {"nom": "Test API", "quantite": 12, "seuil_critique": 3}}),
        "clinique.pharmacie.PharmacieService",
    )
    radiologie, port_radiologie = demarrer(
        radiologie_pb2_grpc.add_RadiologieServiceServicer_to_server,
        RadiologieServicer({
            "RAD-API": {"patient_id": "PAT-API", "type_examen": "IRM", "etat": "termine", "resultat": "RAS", "date": "2026-10-20"},
        }),
        "clinique.radiologie.RadiologieService",
    )
    anciennes_valeurs = {
        nom: os.environ.get(nom)
        for nom in (
            "PHARMACIE_GRPC_TARGET", "RADIOLOGIE_GRPC_TARGET", "API_KEY",
            "STOCK_WRITE_API_KEY", "CORS_ALLOW_ORIGINS",
        )
    }
    os.environ["PHARMACIE_GRPC_TARGET"] = f"127.0.0.1:{port_pharmacie}"
    os.environ["RADIOLOGIE_GRPC_TARGET"] = f"127.0.0.1:{port_radiologie}"
    os.environ["API_KEY"] = "cle-test"
    os.environ["STOCK_WRITE_API_KEY"] = ""
    os.environ["CORS_ALLOW_ORIGINS"] = "https://consumer.example"
    try:
        with TestClient(create_app()) as client:
            assert client.get("/health/live").status_code == 200
            schema = client.get("/openapi.json").json()
            schemes = schema["components"]["securitySchemes"].values()
            assert any(scheme.get("name") == "X-API-Key" for scheme in schemes)
            assert schema["paths"]["/api/v1/pharmacie/medicaments"]["get"]["security"]
            preflight = client.options(
                "/api/v1/pharmacie/medicaments",
                headers={
                    "Origin": "https://consumer.example",
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == "https://consumer.example"
            ready = client.get("/health/ready")
            assert ready.status_code == 200 and ready.json()["status"] == "ready"
            assert client.get("/api/v1/pharmacie/medicaments").status_code == 401
            headers = {"X-API-Key": "cle-test"}
            inventaire = client.get("/api/v1/pharmacie/medicaments", headers=headers)
            assert inventaire.status_code == 200 and inventaire.json()["medicaments"][0]["medicament_id"] == "MED-API"
            stock = client.get("/api/v1/pharmacie/medicaments/MED-API/stock?quantite_demandee=5", headers=headers)
            assert stock.status_code == 200 and stock.json()["disponible"] is True
            maj = client.put(
                "/api/v1/pharmacie/medicaments/MED-API/stock",
                json={"nouvelle_quantite": 6}, headers=headers,
            )
            assert maj.status_code == 200 and maj.json()["quantite"] == 6
            os.environ["STOCK_WRITE_API_KEY"] = "cle-admin"
            maj_refusee = client.put(
                "/api/v1/pharmacie/medicaments/MED-API/stock",
                json={"nouvelle_quantite": 7}, headers=headers,
            )
            assert maj_refusee.status_code == 401
            maj_admin = client.put(
                "/api/v1/pharmacie/medicaments/MED-API/stock",
                json={"nouvelle_quantite": 7}, headers={"X-API-Key": "cle-admin"},
            )
            assert maj_admin.status_code == 200 and maj_admin.json()["quantite"] == 7
            examen = client.get("/api/v1/radiologie/patients/PAT-API/examens", headers=headers)
            assert examen.status_code == 200 and examen.json()["examens"][0]["examen_id"] == "RAD-API"
            absent = client.get("/api/v1/radiologie/examens/ABSENT", headers=headers)
            assert absent.status_code == 404 and absent.json()["detail"]["code"] == "NOT_FOUND"
    finally:
        pharmacie.stop(0).wait()
        radiologie.stop(0).wait()
        for nom, valeur in anciennes_valeurs.items():
            if valeur is None:
                os.environ.pop(nom, None)
            else:
                os.environ[nom] = valeur


def test_rest_gateway_forwarding_errors_and_api_key():
    _exercise_gateway()


if __name__ == "__main__":
    _exercise_gateway()
    print("OK API REST : routes, authentification, readiness et erreurs gRPC")
