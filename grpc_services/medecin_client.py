"""Client médecin de démonstration pour appeler Pharmacie et Radiologie."""
import argparse
import sys

import grpc

from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc
from grpc_services.generated import radiologie_pb2, radiologie_pb2_grpc


def verifier_stock(medicament_id, quantite_demandee=None, host="localhost", port=50052, timeout=2.0):
    """Interroge la pharmacie et retourne la réponse protobuf."""
    request = pharmacie_pb2.VerifierStockRequest(medicament_id=medicament_id)
    if quantite_demandee is not None:
        request.quantite_demandee = quantite_demandee
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        return pharmacie_pb2_grpc.PharmacieServiceStub(channel).VerifierStock(request, timeout=timeout)


def obtenir_examens(examen_id="", patient_id="", host="localhost", port=50053, timeout=2.0):
    """Interroge la radiologie par examen ou par patient."""
    request = radiologie_pb2.ObtenirExamenRequest(examen_id=examen_id, patient_id=patient_id)
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        return radiologie_pb2_grpc.RadiologieServiceStub(channel).ObtenirExamen(request, timeout=timeout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sous_commandes = parser.add_subparsers(dest="service", required=True)
    pharmacie = sous_commandes.add_parser("pharmacie", help="vérifier un stock")
    pharmacie.add_argument("medicament_id")
    pharmacie.add_argument("--quantite", type=int)
    pharmacie.add_argument("--host", default="localhost")
    pharmacie.add_argument("--port", type=int, default=50052)
    pharmacie.add_argument("--timeout", type=float, default=2.0)
    radiologie = sous_commandes.add_parser("radiologie", help="consulter un ou plusieurs examens")
    recherche = radiologie.add_mutually_exclusive_group(required=True)
    recherche.add_argument("--examen")
    recherche.add_argument("--patient")
    radiologie.add_argument("--host", default="localhost")
    radiologie.add_argument("--port", type=int, default=50053)
    radiologie.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)

    try:
        if args.service == "pharmacie":
            r = verifier_stock(args.medicament_id, args.quantite, args.host, args.port, args.timeout)
            print(f"{r.nom} ({r.medicament_id}) : {r.message}; stock={r.quantite}; statut={r.statut}; emplacement={r.emplacement}")
            return 0 if r.disponible else 2
        r = obtenir_examens(args.examen or "", args.patient or "", args.host, args.port, args.timeout)
        for examen in r.examens:
            print(f"{examen.examen_id} | patient={examen.patient_id} | {examen.type_examen} | {examen.etat} | {examen.date} | {examen.resultat}")
        return 0
    except grpc.RpcError as erreur:
        print(f"Erreur gRPC {erreur.code().name}: {erreur.details()}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
