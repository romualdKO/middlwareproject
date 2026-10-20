"""Compare latence et taille des messages applicatifs gRPC et REST."""
import argparse
import json
import math
from statistics import mean, median
from time import perf_counter

import httpx

from grpc_services import clients as grpc_clients
from grpc_services.generated import pharmacie_pb2, radiologie_pb2


def mesurer(nom, fonction, iterations):
    durees = []
    tailles_requetes = []
    tailles_reponses = []
    fonction()  # ouvre/réchauffe le canal sans inclure la connexion dans la mesure
    for _ in range(iterations):
        debut = perf_counter()
        taille_requete, taille_reponse = fonction()
        durees.append((perf_counter() - debut) * 1000)
        tailles_requetes.append(taille_requete)
        tailles_reponses.append(taille_reponse)
    durees_triees = sorted(durees)
    p95 = durees_triees[max(0, math.ceil(0.95 * len(durees_triees)) - 1)]
    return {
        "operation": nom,
        "iterations": iterations,
        "latence_moyenne_ms": round(mean(durees), 3),
        "latence_mediane_ms": round(median(durees), 3),
        "latence_p95_ms": round(p95, 3),
        "requete_moyenne_octets": round(mean(tailles_requetes), 1),
        "reponse_moyenne_octets": round(mean(tailles_reponses), 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rest-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--medicament-id", default="MED001")
    parser.add_argument("--quantite", type=int, default=2)
    parser.add_argument("--examen-id", default="RAD001")
    args = parser.parse_args()
    if args.iterations < 1 or args.timeout <= 0 or args.quantite < 1:
        parser.error("iterations, timeout et quantite doivent être des valeurs positives.")

    pharmacie = grpc_clients.PharmacieClient(timeout=args.timeout)
    radiologie = grpc_clients.RadiologieClient(timeout=args.timeout)
    rest = httpx.Client(
        base_url=args.rest_url.rstrip("/"),
        headers={"X-API-Key": args.api_key} if args.api_key else {},
        timeout=args.timeout,
    )
    try:
        pharmacie_request = pharmacie_pb2.VerifierStockRequest(
            medicament_id=args.medicament_id,
            quantite_demandee=args.quantite,
        )
        radiologie_request = radiologie_pb2.ObtenirExamenRequest(examen_id=args.examen_id)
        stock_path = f"/api/v1/pharmacie/medicaments/{args.medicament_id}/stock?quantite_demandee={args.quantite}"
        examen_path = f"/api/v1/radiologie/examens/{args.examen_id}"

        def grpc_stock():
            response = pharmacie.stub.VerifierStock(pharmacie_request, timeout=args.timeout)
            return len(pharmacie_request.SerializeToString()), len(response.SerializeToString())

        def rest_stock():
            response = rest.get(stock_path)
            response.raise_for_status()
            return len(stock_path.encode("utf-8")), len(response.content)

        def grpc_examen():
            response = radiologie.stub.ObtenirExamen(radiologie_request, timeout=args.timeout)
            return len(radiologie_request.SerializeToString()), len(response.SerializeToString())

        def rest_examen():
            response = rest.get(examen_path)
            response.raise_for_status()
            return len(examen_path.encode("utf-8")), len(response.content)

        resultats = [
            mesurer("Pharmacie gRPC", grpc_stock, args.iterations),
            mesurer("Pharmacie REST", rest_stock, args.iterations),
            mesurer("Radiologie gRPC", grpc_examen, args.iterations),
            mesurer("Radiologie REST", rest_examen, args.iterations),
        ]
        print(json.dumps({
            "note": "Tailles applicatives; requêtes REST = chemin+query, en-têtes, framing réseau et TLS exclus.",
            "resultats": resultats,
        }, ensure_ascii=False, indent=2))
    finally:
        pharmacie.close()
        radiologie.close()
        rest.close()


if __name__ == "__main__":
    main()
