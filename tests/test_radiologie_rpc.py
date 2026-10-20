"""Test individuel du serveur radiologie : python tests/test_radiologie_rpc.py"""
from concurrent import futures
from pathlib import Path
import sys

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grpc_services.generated import radiologie_pb2, radiologie_pb2_grpc
from grpc_services.radiologie_server import RadiologieServicer


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    radiologie_pb2_grpc.add_RadiologieServiceServicer_to_server(
        RadiologieServicer({
            "TEST-RAD": {"patient_id": "PAT-TEST", "type_examen": "IRM test", "etat": "termine", "resultat": "Normal"},
            "TEST-RAD-2": {"patient_id": "PAT-TEST", "type_examen": "Scanner test", "etat": "en_attente", "resultat": ""},
        }), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            stub = radiologie_pb2_grpc.RadiologieServiceStub(channel)
            reponse = stub.ObtenirExamen(radiologie_pb2.ObtenirExamenRequest(examen_id="TEST-RAD"), timeout=3)
            assert reponse.etat == "termine" and reponse.resultat == "Normal"
            print(f"OK radiologie : {reponse.type_examen}, état={reponse.etat}")
            par_patient = stub.ObtenirExamen(
                radiologie_pb2.ObtenirExamenRequest(patient_id="PAT-TEST"), timeout=3
            )
            assert len(par_patient.examens) == 2
            for identifiant, statut in (("", grpc.StatusCode.INVALID_ARGUMENT), ("ABSENT", grpc.StatusCode.NOT_FOUND)):
                try:
                    stub.ObtenirExamen(radiologie_pb2.ObtenirExamenRequest(examen_id=identifiant), timeout=3)
                    raise AssertionError(f"Le statut {statut} était attendu")
                except grpc.RpcError as erreur:
                    assert erreur.code() == statut
            print("OK radiologie : requêtes invalides et examens absents gérés")
    finally:
        server.stop(0).wait()


if __name__ == "__main__":
    main()
