"""Passerelle REST destinée aux intégrations HTTP externes."""
from contextlib import asynccontextmanager
import hmac
import os
from pathlib import Path

import grpc
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from grpc_services.clients import PharmacieClient, RadiologieClient


STATUS_HTTP = {
    grpc.StatusCode.INVALID_ARGUMENT: 400,
    grpc.StatusCode.NOT_FOUND: 404,
    grpc.StatusCode.DEADLINE_EXCEEDED: 504,
    grpc.StatusCode.UNAVAILABLE: 503,
    grpc.StatusCode.RESOURCE_EXHAUSTED: 429,
    grpc.StatusCode.PERMISSION_DENIED: 403,
    grpc.StatusCode.UNAUTHENTICATED: 401,
    grpc.StatusCode.INTERNAL: 502,
}


class MiseAJourStock(BaseModel):
    nouvelle_quantite: int = Field(ge=0)


class MiseAJourEtatExamen(BaseModel):
    etat: str = Field(pattern="^(en_attente|en_cours|termine)$")
    resultat: str = ""


def erreur_http(erreur):
    statut = STATUS_HTTP.get(erreur.code(), 502)
    raise HTTPException(status_code=statut, detail={"code": erreur.code().name, "message": erreur.details()})


def create_app():
    @asynccontextmanager
    async def lifespan(app):
        app.state.pharmacie = PharmacieClient()
        app.state.radiologie = RadiologieClient()
        try:
            yield
        finally:
            app.state.pharmacie.close()
            app.state.radiologie.close()

    app = FastAPI(
        title="Clinique Espoir API Gateway",
        description="API REST versionnée, passerelle vers Pharmacie et Radiologie gRPC.",
        version="1.0.0",
        lifespan=lifespan,
    )
    origins = [value.strip() for value in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if value.strip()]
    api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "PUT", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key"],
        )

    @app.get("/", include_in_schema=False)
    def interface_web():
        return FileResponse(Path(__file__).resolve().parent.parent / "web_ui" / "index.html")

    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        read_secret = os.getenv("API_KEY", "")
        secret = (os.getenv("STOCK_WRITE_API_KEY") or read_secret) if request.method == "PUT" else read_secret
        if secret and request.url.path.startswith("/api/") and request.method != "OPTIONS":
            provided = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(provided.encode("utf-8"), secret.encode("utf-8")):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Clé API manquante ou invalide."},
                    headers={"WWW-Authenticate": "ApiKey"},
                )
        return await call_next(request)

    @app.get("/health/live", tags=["health"])
    def live():
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    def ready(request: Request):
        timeout = float(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "0.5"))
        etat = {}
        for nom in ("pharmacie", "radiologie"):
            client = getattr(request.app.state, nom, None)
            if client is None:
                etat[nom] = False
                continue
            etat[nom] = client.is_healthy(timeout=timeout)
        if not all(etat.values()):
            raise HTTPException(status_code=503, detail={"status": "not_ready", "services": etat})
        return {"status": "ready", "services": etat}

    @app.get(
        "/api/v1/pharmacie/medicaments", tags=["pharmacie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def lister_medicaments(request: Request):
        try:
            response = request.app.state.pharmacie.lister_medicaments()
            return {"medicaments": [dict(
                medicament_id=m.medicament_id,
                nom=m.nom,
                quantite=m.quantite,
                seuil_critique=m.seuil_critique,
                emplacement=m.emplacement,
                statut=m.statut,
            ) for m in response.medicaments]}
        except grpc.RpcError as erreur:
            erreur_http(erreur)

    @app.get(
        "/api/v1/pharmacie/medicaments/{medicament_id}/stock", tags=["pharmacie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def verifier_stock(medicament_id: str, request: Request, quantite_demandee: int | None = None):
        try:
            response = request.app.state.pharmacie.verifier_stock(medicament_id, quantite_demandee)
            return {key: getattr(response, key) for key in (
                "medicament_id", "nom", "disponible", "quantite", "message", "emplacement", "statut", "quantite_demandee"
            )}
        except grpc.RpcError as erreur:
            erreur_http(erreur)

    @app.put(
        "/api/v1/pharmacie/medicaments/{medicament_id}/stock", tags=["pharmacie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def mettre_a_jour_stock(medicament_id: str, body: MiseAJourStock, request: Request):
        try:
            response = request.app.state.pharmacie.mettre_a_jour_stock(medicament_id, body.nouvelle_quantite)
            return {key: getattr(response, key) for key in (
                "medicament_id", "nom", "disponible", "quantite", "message", "emplacement", "statut", "quantite_demandee"
            )}
        except grpc.RpcError as erreur:
            erreur_http(erreur)

    @app.get(
        "/api/v1/radiologie/examens/{examen_id}", tags=["radiologie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def obtenir_examen(examen_id: str, request: Request):
        return _examens_json(request, examen_id=examen_id)

    @app.get(
        "/api/v1/radiologie/patients/{patient_id}/examens", tags=["radiologie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def obtenir_examens_patient(patient_id: str, request: Request):
        return _examens_json(request, patient_id=patient_id)

    @app.put(
        "/api/v1/radiologie/examens/{examen_id}/etat", tags=["radiologie"],
        dependencies=[Depends(api_key_scheme)], responses={401: {"description": "Clé API manquante ou invalide."}},
    )
    def mettre_a_jour_etat_examen(examen_id: str, body: MiseAJourEtatExamen, request: Request):
        try:
            response = request.app.state.radiologie.mettre_a_jour_etat_examen(
                examen_id, body.etat, body.resultat
            )
            return {
                "examen": {
                    "examen_id": response.examen.examen_id,
                    "patient_id": response.examen.patient_id,
                    "type_examen": response.examen.type_examen,
                    "etat": response.examen.etat,
                    "resultat": response.examen.resultat,
                    "date": response.examen.date,
                },
                "notification_envoyee": response.notification_envoyee,
                "message": response.message,
            }
        except grpc.RpcError as erreur:
            erreur_http(erreur)

    return app


def _examens_json(request, examen_id="", patient_id=""):
    try:
        response = request.app.state.radiologie.obtenir_examens(examen_id, patient_id)
        return {"examens": [dict(
            examen_id=e.examen_id,
            patient_id=e.patient_id,
            type_examen=e.type_examen,
            etat=e.etat,
            resultat=e.resultat,
            date=e.date,
        ) for e in response.examens]}
    except grpc.RpcError as erreur:
        erreur_http(erreur)


app = create_app()
