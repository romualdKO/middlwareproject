"""Client médecin de démonstration pour appeler Pharmacie et Radiologie."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import sys

import grpc

from grpc_services.clients import PharmacieClient, RadiologieClient


def verifier_stock(medicament_id, quantite_demandee=None, host="localhost", port=50052, timeout=2.0):
    """Interroge la pharmacie et retourne la réponse protobuf."""
    with PharmacieClient(f"{host}:{port}", timeout=timeout) as client:
        return client.verifier_stock(medicament_id, quantite_demandee)


def obtenir_examens(examen_id="", patient_id="", host="localhost", port=50053, timeout=2.0):
    """Interroge la radiologie par examen ou par patient."""
    with RadiologieClient(f"{host}:{port}", timeout=timeout) as client:
        return client.obtenir_examens(examen_id, patient_id)


def consulter_services(
    medicament_id, quantite_demandee, examen_id="", patient_id="", timeout=2.0,
    pharmacie_target=None, radiologie_target=None,
):
    """Le client MÃ©decin interroge Pharmacie et Radiologie en parallÃ¨le via gRPC."""
    def verifier_stock_cible():
        with PharmacieClient(pharmacie_target, timeout=timeout) as client:
            return client.verifier_stock(medicament_id, quantite_demandee)

    def obtenir_examens_cible():
        with RadiologieClient(radiologie_target, timeout=timeout) as client:
            return client.obtenir_examens(examen_id, patient_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        stock_future = pool.submit(verifier_stock_cible)
        examen_future = pool.submit(obtenir_examens_cible)
        try:
            stock = stock_future.result()
        except grpc.RpcError as erreur:
            stock = erreur
        try:
            examens = examen_future.result()
        except grpc.RpcError as erreur:
            examens = erreur
    return stock, examens


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
    consultation = sous_commandes.add_parser(
        "consultation", help="interroger pharmacie et radiologie depuis le client mÃ©decin"
    )
    consultation.add_argument("medicament_id")
    consultation.add_argument("examen_id", help="identifiant de l'examen radiologique")
    consultation.add_argument("--quantite", type=int, default=1)
    consultation.add_argument("--timeout", type=float, default=2.0)
    args = parser.parse_args(argv)

    try:
        if args.service == "consultation":
            stock, examens = consulter_services(
                args.medicament_id, args.quantite, examen_id=args.examen_id, timeout=args.timeout
            )
            echec = False
            if isinstance(stock, grpc.RpcError):
                print(f"Pharmacie — gRPC {stock.code().name}: {stock.details()}", file=sys.stderr)
                echec = True
            else:
                print(f"Pharmacie — {stock.nom} ({stock.medicament_id}) : {stock.message}; stock={stock.quantite}")
            if isinstance(examens, grpc.RpcError):
                print(f"Radiologie — gRPC {examens.code().name}: {examens.details()}", file=sys.stderr)
                echec = True
            else:
                for examen in examens.examens:
                    print(f"Radiologie — {examen.examen_id} | patient={examen.patient_id} | {examen.type_examen} | {examen.etat}")
            return 1 if echec else 0
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
