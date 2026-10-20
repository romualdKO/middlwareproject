"""Aides aux handlers RPC pour libérer les workers lors des expirations."""
import time

import grpc


def latence_simulee(latence_ms, context):
    """Attend la latence configurée en interrompant le travail si le client annule."""
    fin = time.monotonic() + latence_ms / 1000
    while True:
        if not context.is_active():
            context.abort(grpc.StatusCode.CANCELLED, "La requête gRPC a été annulée.")
        reste = fin - time.monotonic()
        if reste <= 0:
            return
        time.sleep(min(reste, 0.05))
